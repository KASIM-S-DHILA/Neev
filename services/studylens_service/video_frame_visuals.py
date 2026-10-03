"""Version-bound OCR and selective Groq transcription of retained video frames."""
import asyncio
import hashlib
import json
import os

from .cloud_vision import (MODEL, PROMPT_VERSION, GenerationFailure, automatic_enabled as groq_enabled,
                           load_image, request_image, reserve, route)
from .cloud_vision_wait import Deferred
from .job_errors import ExtractionFailure
from .visual import ocr, prepare

VERSION = "video-frame-visuals-1"
MAX_CLOUD_FRAMES = 12
MAX_OCR_CHARS = 8000


def automatic_enabled():
    return os.environ.get("STUDYLENS_AUTO_VIDEO_VISUALS", "1") != "0"


def manifest(checkpoint):
    frames = checkpoint.get("frames", [])
    identity = [[frame["id"], frame["seconds"], frame["asset"]["sha256"]] for frame in frames]
    return hashlib.sha256(json.dumps([checkpoint.get("source_sha256"), identity],
        separators=(",", ":")).encode()).hexdigest()


def retained(worker, job):
    row = worker.connection.execute("""SELECT j.*,v.sha256 FROM jobs j
        JOIN source_versions v ON v.id=j.source_version_id
        JOIN sources s ON s.id=v.source_id
        WHERE j.kind='video_frames' AND j.source_version_id=? AND s.kind='video'""",
        (job["source_version_id"],)).fetchone()
    if not row or row["state"] not in ("succeeded", "partial"):
        raise ExtractionFailure("Finish selecting video frames before visual extraction.")
    selected = json.loads(row["checkpoint_json"])
    if selected.get("source_sha256") != row["sha256"] or not selected.get("frames"):
        raise ExtractionFailure("No complete frame selection is saved for this source version.")
    return selected, manifest(selected)


def verify_source(worker, job, guard):
    row = worker.connection.execute("SELECT * FROM source_versions WHERE id=?", (job["source_version_id"],)).fetchone()
    target = (worker.root / row["relative_path"]).resolve() if row else None
    if not target or not target.is_relative_to((worker.root / "originals").resolve()) or not target.is_file():
        raise ExtractionFailure("The saved video original is missing. Restore it or import a new version.")
    digest = hashlib.sha256()
    with target.open("rb") as stream:
        while data := stream.read(1024 * 1024):
            worker.check(job)
            guard.touch()
            digest.update(data)
    if target.stat().st_size != row["size_bytes"] or digest.hexdigest() != row["sha256"]:
        raise ExtractionFailure("The video original changed. Restore it or import a new version.")
    return row["sha256"]


def cloud_choices(frames, results):
    """At most one routed frame per 30-second window, spread over the video."""
    first = {}
    for frame in frames:
        result = results[frame["id"]]
        if result["routing"]["decision"] == "cloud":
            first.setdefault(frame["window_start_seconds"], frame["id"])
    candidates = list(first.values())
    if len(candidates) <= MAX_CLOUD_FRAMES:
        return set(candidates)
    return {candidates[round(index * (len(candidates) - 1) / (MAX_CLOUD_FRAMES - 1))]
        for index in range(MAX_CLOUD_FRAMES)}


def process(worker, job, guard):
    selected, fingerprint = retained(worker, job)
    source_sha = verify_source(worker, job, guard)
    frames = selected["frames"]
    checkpoint = json.loads(job["checkpoint_json"])
    if checkpoint and (checkpoint.get("version") != VERSION or checkpoint.get("manifest") != fingerprint
                       or checkpoint.get("source_sha256") != source_sha):
        raise ExtractionFailure("The saved frame set changed. Start visual extraction again.")
    results = checkpoint.setdefault("results", {})
    checkpoint.update(version=VERSION, manifest=fingerprint, source_sha256=source_sha)
    total = len(frames)
    for index, frame in enumerate(frames):
        worker.check(job)
        guard.touch()
        if frame["id"] in results:
            continue
        image, _ = load_image(worker.root, frame["asset"])
        try:
            prepared, _ = prepare(image)
            try:
                value, details = ocr(prepared, worker, job, guard)
            except ExtractionFailure as error:
                value, details = "", {"available": False, "warning": str(error), "review_required": True}
            finally:
                prepared.close()
            clipped = len(value) > MAX_OCR_CHARS
            value = value[:MAX_OCR_CHARS]
            routing = route(image, value, {"ocr": details})
            results[frame["id"]] = {
                "frame_id": frame["id"], "seconds": frame["seconds"], "source_version_id": job["source_version_id"],
                "source_sha256": source_sha, "asset_sha256": frame["asset"]["sha256"],
                "ocr": {"text": value, "available": details.get("available", False),
                    "engine": details.get("engine"), "language": details.get("language"),
                    "mean_confidence": details.get("mean_confidence"),
                    "warning": details.get("warning") or ("OCR text was shortened to 8,000 characters." if clipped else None),
                    "review_required": True},
                "routing": routing, "cloud": None, "review_required": True}
            worker.connection.execute("BEGIN IMMEDIATE")
            try:
                worker.check(job)
                worker.checkpoint(job, len(results), total, "Reading text on selected frames", checkpoint)
                worker.connection.commit()
            except BaseException:
                worker.connection.rollback()
                raise
        finally:
            image.close()
    selected_cloud = cloud_choices(frames, results) if groq_enabled() else set()
    for index, frame in enumerate(frames):
        worker.check(job)
        guard.touch()
        result = results[frame["id"]]
        if result["cloud"] is not None:
            continue
        if result["routing"]["decision"] != "cloud":
            entry = {"status": "local", "reason": "Local OCR retained"}
        elif not groq_enabled():
            entry = {"status": "not_configured", "reason": "Groq vision is unavailable; local OCR retained"}
        elif frame["id"] not in selected_cloud:
            entry = {"status": "not_selected", "reason": "Bounded selective Groq pass; compare with the original"}
        else:
            image, raw = load_image(worker.root, frame["asset"])
            image.close()
            sent_sha = hashlib.sha256(raw).hexdigest()
            fallback_key = "fallback:" + frame["id"]
            fallback = bool(checkpoint.get(fallback_key))
            reserve(worker)
            worker.update(job, stage=f"Reading difficult frame {index + 1} of {total} with Groq")
            try:
                extraction = asyncio.run(request_image(worker, job, raw, fallback=fallback))
                entry = {"status": "complete", "provider": "groq", "model": MODEL,
                    "prompt_version": PROMPT_VERSION, "sent_sha256": sent_sha,
                    "output_mode": "text_with_local_validation" if fallback else "json_object",
                    "extraction": extraction, "verified": False, "review_required": True}
            except GenerationFailure as error:
                if not fallback:
                    checkpoint[fallback_key] = True
                    worker.checkpoint(job, len(results), total, "Retrying visual output", checkpoint)
                    raise Deferred(65, "Retrying visual output") from error
                entry = {"status": "needs_review", "reason": "Groq output could not be validated after one fallback."}
            except Deferred:
                key = "quota:" + frame["id"]
                checkpoint[key] = checkpoint.get(key, 0) + 1
                worker.checkpoint(job, len(results), total, "Waiting for Groq quota", checkpoint)
                if checkpoint[key] <= 3:
                    raise
                entry = {"status": "needs_review", "reason": "Groq quota remained unavailable after three waits."}
            except (ValueError, KeyError, TypeError):
                entry = {"status": "needs_review", "reason": "Groq output was incomplete or failed structure checks."}
        result["cloud"] = entry
        worker.connection.execute("BEGIN IMMEDIATE")
        try:
            worker.check(job)
            worker.checkpoint(job, sum(item["cloud"] is not None for item in results.values()), total,
                              "Frame visuals saved", checkpoint)
            worker.connection.commit()
        except BaseException:
            worker.connection.rollback()
            raise
    states = [item["cloud"]["status"] for item in results.values()]
    return {"frames": total, "local_ocr": sum(bool(item["ocr"]["text"]) for item in results.values()),
        "cloud_sent": states.count("complete"), "cloud_needs_review": states.count("needs_review"),
        "cloud_not_selected": states.count("not_selected"), "source_sha256": source_sha,
        "frame_manifest": fingerprint, "review_required": True,
        "limitations": "Sampled frames can miss brief content. OCR and Groq transcription require comparison with the original."}
