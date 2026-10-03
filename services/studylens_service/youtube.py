"""Caption-first external sources. Fetching is isolated; snapshots are immutable."""
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from .job_errors import ExtractionFailure

MAX_BYTES = 4 * 1024**2
MAX_SECONDS = 4 * 3600
REVISION = "youtube-captions-1"
LANGUAGE = re.compile(r"^[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8})?$")


def parse_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("Paste a single YouTube video HTTPS link.")
    try:
        url = urlsplit(value.strip())
        if url.scheme != "https" or url.username or url.password or url.port is not None:
            raise ValueError()
        host = url.hostname
        if host in ("youtu.be", "www.youtu.be"):
            video_id = url.path.removeprefix("/")
        elif host in ("youtube.com", "www.youtube.com", "m.youtube.com"):
            if url.path == "/watch":
                values = parse_qs(url.query).get("v", [])
                video_id = values[0] if len(values) == 1 else ""
            else:
                match = re.fullmatch(r"/(?:shorts|embed|live)/([A-Za-z0-9_-]{11})/?", url.path)
                video_id = match[1] if match else ""
        else:
            raise ValueError()
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError()
    except ValueError as error:
        raise ValueError("Paste a single YouTube video HTTPS link, not a channel or playlist.") from error
    return video_id, "https://www.youtube.com/watch?v=" + video_id


def validate_snapshot(value):
    if not isinstance(value, dict) or value.get("revision") != REVISION:
        raise ExtractionFailure("Invalid YouTube caption snapshot.")
    video_id, url = parse_url(value.get("url"))
    if value.get("video_id") != video_id or value["url"] != url:
        raise ExtractionFailure("YouTube snapshot source identity changed.")
    if not LANGUAGE.fullmatch(value.get("requested_language", "")):
        raise ExtractionFailure("Invalid caption language.")
    snippets = value.get("snippets")
    tracks = value.get("tracks")
    if not isinstance(snippets, list) or len(snippets) > 30000 or not isinstance(tracks, list) or len(tracks) > 200:
        raise ExtractionFailure("YouTube captions exceed the snapshot limit.")
    for track in tracks:
        if not isinstance(track, dict) or not LANGUAGE.fullmatch(track.get("language_code", "")) or type(track.get("is_generated")) is not bool:
            raise ExtractionFailure("Invalid caption track metadata.")
        if not isinstance(track.get("language"), str) or len(track["language"]) > 100:
            raise ExtractionFailure("Invalid caption language name.")
    previous = -1
    for item in snippets:
        if not isinstance(item, dict) or not isinstance(item.get("text"), str) or len(item["text"]) > 4000:
            raise ExtractionFailure("Invalid caption text.")
        start, duration = item.get("start"), item.get("duration")
        if any(type(number) not in (int, float) or not math.isfinite(number) or number < 0 for number in (start, duration)):
            raise ExtractionFailure("Invalid caption timestamps.")
        if start < previous or start + duration > MAX_SECONDS:
            raise ExtractionFailure("Captions must be ordered and within four hours.")
        previous = start
    if snippets:
        if value.get("issue") is not None or not LANGUAGE.fullmatch(value.get("language_code", "")) or type(value.get("is_generated")) is not bool:
            raise ExtractionFailure("Invalid caption provenance.")
        if not any(track["language_code"] == value["language_code"] and track["is_generated"] == value["is_generated"] for track in tracks):
            raise ExtractionFailure("The fetched caption track is not in the available track list.")
    elif not isinstance(value.get("issue"), str) or len(value["issue"]) > 500:
        raise ExtractionFailure("Missing caption availability status.")
    if len(json.dumps(value, ensure_ascii=False).encode()) > MAX_BYTES:
        raise ExtractionFailure("YouTube captions exceed the 4 MB snapshot limit.")
    return value


def process(worker, job, guard):
    payload = json.loads(job["payload_json"])
    video_id, url = parse_url(payload["url"])
    checkpoint = json.loads(job["checkpoint_json"])
    digest = checkpoint.get("snapshot_sha256")
    if digest and re.fullmatch(r"[a-f0-9]{64}", digest):
        target = worker.root / "originals" / (digest + ".youtube.json")
        if target.is_file() and target.stat().st_size <= MAX_BYTES:
            data = target.read_bytes()
            if hashlib.sha256(data).hexdigest() == digest:
                snapshot = validate_snapshot(json.loads(data))
                if snapshot["url"] == url and snapshot["requested_language"] == payload["language"]:
                    return {"snapshot_sha256": digest, "bytes": len(data), "coverage": "captions_only" if snapshot["snippets"] else "link_only", "issue": snapshot["issue"]}
        raise ExtractionFailure("The saved caption snapshot is missing or damaged. Import the link again.")
    folder = worker.root / "derived" / ("youtube-" + job["id"])
    folder.mkdir(parents=True, exist_ok=True)
    request = folder / "request.json"
    request.write_text(json.dumps({"video_id": video_id, "url": url, "language": payload["language"]}), encoding="utf-8")
    worker.checkpoint(job, 0, 1, "Fetching YouTube captions", {})
    from .local_tools import run_tool
    output, _ = run_tool([sys.executable, "-m", "studylens_service.youtube_helper", str(request)], worker, job, guard, folder, timeout=45)
    snapshot = validate_snapshot(json.loads(output))
    if snapshot["url"] != url or snapshot["requested_language"] != payload["language"]:
        raise ExtractionFailure("The caption reader returned a different source.")
    data = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    digest = hashlib.sha256(data).hexdigest()
    target = worker.root / "originals" / (digest + ".youtube.json")
    temporary = folder / "snapshot.part"
    temporary.write_bytes(data)
    worker.check(job)
    os.replace(temporary, target)
    worker.checkpoint(job, 1, 1, "Caption snapshot saved", {"snapshot_sha256": digest})
    return {"snapshot_sha256": digest, "bytes": len(data), "coverage": "captions_only" if snapshot["snippets"] else "link_only", "issue": snapshot["issue"]}


def publish(worker, job, result):
    """Called inside worker completion's transaction; a racing cancel wins."""
    from .database import now
    from .jobs import job_values
    payload = json.loads(job["payload_json"])
    video_id, _ = parse_url(payload["url"])
    filename = f"youtube-{video_id}-{payload['language']}.youtube.json"
    name_key = "youtube:" + video_id + ":" + payload["language"]
    db = worker.connection
    source = db.execute("SELECT * FROM sources WHERE workspace_id=? AND subject_id=? AND name_key=?",
        (job["workspace_id"], job["subject_id"], name_key)).fetchone()
    if not source:
        source = {"id": str(uuid4()), "next_version": 1}
        db.execute("INSERT INTO sources (id,workspace_id,subject_id,display_name,name_key,kind,next_version,created_at) VALUES (?,?,?,?,?,'youtube',1,?)",
            (source["id"], job["workspace_id"], job["subject_id"], payload.get("title") or "YouTube · " + video_id, name_key, now()))
    elif source["kind"] != "youtube":
        raise ExtractionFailure("A different material already uses this source name.")
    version = db.execute("SELECT * FROM source_versions WHERE source_id=? AND sha256=?", (source["id"], result["snapshot_sha256"])).fetchone()
    duplicate = version is not None
    if not version:
        version = {"id": str(uuid4()), "version": source["next_version"]}
        db.execute("INSERT INTO source_versions (id,source_id,version,filename,sha256,size_bytes,relative_path,state,created_at) VALUES (?,?,?,?,?,?,?,'stored',?)",
            (version["id"], source["id"], version["version"], filename, result["snapshot_sha256"], result["bytes"], "originals/" + result["snapshot_sha256"] + ".youtube.json", now()))
        db.execute("UPDATE sources SET next_version=next_version+1 WHERE id=?", (source["id"],))
        for kind in ("verify_original", "extract_source"):
            values = job_values(job["workspace_id"], job["subject_id"], version["id"], kind, filename, result["bytes"] if kind == "verify_original" else 0)
            db.execute("INSERT INTO jobs (" + ",".join(values) + ") VALUES (" + ",".join("?" for _ in values) + ")", tuple(values.values()))
    # Import jobs can be repeated independently; their version FK stays null to
    # preserve the existing unique(kind,source_version_id) extraction contract.
    return result | {"source_id": source["id"], "version_id": version["id"], "version": version["version"], "duplicate": duplicate}


def caption_groups(snippets):
    """Bound units; retain overlapping/rolling captions and their original times."""
    group, chars = [], 0
    for snippet in snippets:
        if group and (chars + len(snippet["text"]) > 4000 or len(group) >= 80 or snippet["start"] - group[0]["start"] >= 60):
            yield group
            group, chars = [], 0
        # Only exact duplicate cues are redundant; repeated speech stays intact.
        if group and snippet == group[-1]:
            continue
        group.append(snippet)
        chars += len(snippet["text"]) + 1
    if group:
        yield group


def extract(worker, job, guard, row, target, completed):
    from .extraction import commit_unit
    snapshot = validate_snapshot(json.loads(target.read_bytes()))
    provenance = {key: snapshot.get(key) for key in ("video_id", "url", "requested_language", "language_code", "is_generated", "tracks", "issue")}
    provenance.update(coverage="captions_only" if snapshot["snippets"] else "link_only", translated=False, revision=REVISION)
    groups = list(caption_groups(snapshot["snippets"]))
    worker.checkpoint(job, completed, len(groups), "Reading saved YouTube captions", {"completed_units": completed})
    for index in range(completed, len(groups)):
        worker.check(job)
        guard.touch()
        group = groups[index]
        segments = [{"start_seconds": item["start"], "end_seconds": item["start"] + item["duration"], "text": item["text"]} for item in group]
        text = "\n".join(item["text"] for item in group)
        commit_unit(worker, job, index + 1, len(groups), text,
            {"kind": "time", "start_seconds": group[0]["start"], "end_seconds": max(item["end_seconds"] for item in segments)},
            "suspect", "YouTube captions are unverified. Compare with the video; slides and other visuals are not extracted.", REVISION,
            {"youtube": provenance, "segments": segments, "text_origin": "youtube_captions", "review_required": True})
    counts = {key: len(groups) if key == "suspect" else 0 for key in ("text", "needs_ocr", "empty", "unreadable", "too_large", "suspect")}
    return {"units": len(groups), "counts": counts, "warnings": max(1, len(groups)), "text_only": True, "source_sha256": row["sha256"], "youtube": provenance}
