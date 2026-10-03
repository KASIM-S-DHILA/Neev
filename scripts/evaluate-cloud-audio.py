"""Opt-in live audio pilot using authored and previously downloaded public clips."""
import argparse
import hashlib
import json
import os
import re
import sys
import threading
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/tests"))
from fastapi.testclient import TestClient
from test_storage import AUTH, BASE, SESSION, SOURCES, TOKEN
from studylens_service import cloud_audio
from studylens_service.api import create_app
from studylens_service.worker import Worker


def words(text):
    return re.sub(r"[^\w\s]", " ", unicodedata.normalize("NFKC", text).casefold()).split()


def errors(reference, hypothesis):
    left, right = words(reference), words(hypothesis)
    row = list(range(len(right) + 1))
    for i, token in enumerate(left, 1):
        new = [i]
        for j, other in enumerate(right, 1):
            new.append(min(new[-1] + 1, row[j] + 1, row[j-1] + (token != other)))
        row = new
    return {"edit_errors": row[-1], "reference_words": len(left), "raw_wer": row[-1] / len(left) if left else None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cloud", action="store_true", help="Send fixture speech to Groq using the configured key")
    parser.add_argument("--public-only", action="store_true", help="Only the eight public clips; use for a paired language check")
    parser.add_argument("--language", default="auto", choices=("auto", "hi", "en"))
    args = parser.parse_args()
    if not args.cloud or not cloud_audio.enabled():
        parser.error("Explicit --cloud and configured automatic Groq audio are required. No model downloads occur.")
    os.environ["STUDYLENS_AUDIO_LANGUAGE"] = args.language
    tag = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    root = ROOT / "tmp" / ("audio-integration-groq-" + tag)
    fixtures = ROOT / "docs/evaluation/fixtures/phase-06"
    gold = json.loads((fixtures / "gold.json").read_text("utf-8"))
    inputs = [{"name": name, "path": fixtures / name, "group": "authored"} for name in
              ("clean.wav", "noisy.wav", "silence.wav", "tone.wav", "intervals.wav", "corrupt.wav")]
    if args.public_only:
        inputs = []
    manifest = json.loads((ROOT / "docs/evaluation/hinglish-manifest.json").read_text("utf-8"))
    for group in ("hinglish", "hi", "noisy_hi", "neutral"):
        candidates = [s for s in manifest["samples"] if s["group"] == group]
        if group == "hinglish":
            candidates = [s for s in candidates if re.search("[\u0900-\u097f]", s["transcription"]) and re.search("[A-Za-z]", s["transcription"])]
        for index, item in enumerate(candidates[:2]):
            path = ROOT / item["sample_path"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != item["audio_sha256"]:
                raise ValueError("Public audio fixture changed: " + path.name)
            inputs.append({"name": f"{group}-{index}.wav", "path": path, "group": group, "reference": item["transcription"],
                           "sha256": item["audio_sha256"], "dataset_file": item["file_name"]})
    report = {"date_utc": tag, "data_directory": str(root), "method": "Real app API/worker, FFmpeg, bundled Silero VAD and Groq verbose transcription; local Tiny fallback when needed",
              "model": cloud_audio.MODEL, "language_hint": args.language, "dataset_revision": manifest["revision"], "samples": [], "requests": [],
              "limitations": ["Six known authored fixtures and eight selected public clips are a smoke pilot, not held-out accuracy evidence.",
                  "WER compares dataset scripts literally; Hindi/Latin script differences affect results. References are not human-audited.",
                  "No whole-app 8 GB measurement; development machine has 16 GB.", "Chunk boundaries can split words; no speaker separation."]}
    request = cloud_audio.request_audio
    async def measured(*arguments):
        started = time.monotonic()
        try:
            result = await request(*arguments)
            report["requests"].append({"seconds": round(time.monotonic() - started, 3), "status": "received"})
            return result
        except Exception as error:
            report["requests"].append({"seconds": round(time.monotonic() - started, 3), "status": "failed", "error": str(error)[:300]})
            raise
    with TestClient(create_app(root, TOKEN), headers=AUTH) as client, patch.object(cloud_audio, "request_audio", measured):
        client.put(BASE + "/session", json={"base_revision": 0, "session": SESSION}).raise_for_status()
        worker = Worker(root, threading.Event())
        try:
            for item in inputs:
                original = item["path"].read_bytes()
                uploaded = client.post(SOURCES, params={"filename": item["name"]}, content=original)
                uploaded.raise_for_status()
                version = uploaded.json()["version_id"]
                started = time.monotonic()
                deadline = started + 180
                while time.monotonic() < deadline:
                    job = worker.claim()
                    if job:
                        worker.execute(job)
                    content = client.get(BASE + "/source-versions/" + version + "/content?limit=10").json()
                    if content["state"] in ("succeeded", "partial", "failed", "cancelled"):
                        break
                    time.sleep(.05)
                else:
                    client.post(BASE + "/jobs/" + next(j["id"] for j in client.get(BASE + "/jobs").json()
                        if j["source_version_id"] == version and j["kind"] == "extract_source") + "/cancel")
                units = content["units"]
                text = " ".join(u["text"] for u in units)
                sample = {key: value for key, value in item.items() if key != "path"} | {
                    "version_id": version, "seconds": round(time.monotonic() - started, 3), "state": content["state"], "error": content["error"], "units": units,
                    "checks": {"original_unchanged": client.get("/source-versions/" + version + "/file").content == original,
                        "all_transcripts_unverified": all(u["status"] != "text" and u["metadata"]["review_required"] for u in units)}}
                for unit in units:
                    unit["metadata"]["audio"].pop("data_url", None)
                if item["name"] in ("clean.wav", "noisy.wav"):
                    sample["checks"]["known_phrases_recovered"] = all(needle in text.casefold() for needle in gold["needles"])
                elif item["name"] in ("silence.wav", "tone.wav") or item["group"] == "neutral":
                    sample["checks"]["no_invented_speech"] = bool(units) and not text.strip()
                elif item["name"] == "intervals.wav":
                    sample["checks"]["gold_interval_boundaries"] = [[u["locator"]["start_seconds"], u["locator"]["end_seconds"]] for u in units] == gold["intervals"]
                    sample["checks"]["second_chunk_absolute_time"] = len(units) >= 2 and bool(units[1]["metadata"]["segments"]) and all(s["start_seconds"] >= 30 for s in units[1]["metadata"]["segments"])
                elif item["name"] == "corrupt.wav":
                    sample["checks"]["corrupt_declined"] = content["state"] == "failed" and not units
                else:
                    sample["checks"]["speech_transcript_saved"] = bool(text.strip())
                if "reference" in item:
                    sample["error_metrics"] = errors(item["reference"], text)
                sample["status"] = "passed" if all(sample["checks"].values()) else "needs-review"
                report["samples"].append(sample)
                print(json.dumps({"sample": item["name"], "state": sample["state"], "status": sample["status"], "seconds": sample["seconds"],
                    "providers": [u["metadata"]["speech"]["provider"] for u in units], "error": sample["error"]}), flush=True)
        finally:
            worker.connection.close()
    report["usage"] = json.loads((root / "groq-audio-budget.json").read_text("utf-8"))
    report["status"] = "passed" if all(s["status"] == "passed" for s in report["samples"]) else "needs-review"
    report["pipeline_status"] = report["status"]
    report["quality_status"] = "requires-human-review"
    path = ROOT / "docs/evaluation" / ("cloud-audio-" + tag + ".json")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(path), "data_directory": str(root)}))


if __name__ == "__main__":
    main()
