"""Real local audio gate. No provider requests; preserve failed results."""
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["GROQ_API_KEY"] = ""  # This legacy local-only gate must not inherit cloud credentials.
sys.path.insert(0, str(ROOT / "services/tests"))
from fastapi.testclient import TestClient
from test_storage import AUTH, BASE, SESSION, SOURCES, TOKEN
from studylens_service.api import create_app
from studylens_service.worker import Worker
from studylens_service.resource_guard import private_bytes

tag = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
root = ROOT / "tmp" / ("audio-integration-" + tag)
fixtures = ROOT / "docs/evaluation/fixtures/phase-06"
gold = json.loads((fixtures / "gold.json").read_text("utf-8"))
report = {"date_utc": tag, "data_directory": str(root), "method": "Real app API, FFmpeg and isolated CPU int8 faster-whisper Tiny helpers; synthetic authored speech, no cloud",
          "gold": gold, "samples": [], "limitations": ["Synthetic known English fixtures; not held-out natural speech accuracy.",
            "Hindi/Hinglish and noisy student recordings require human review.", "Sampled helper peak is not an 8 GB whole-app measurement."]}
with TestClient(create_app(root, TOKEN), headers=AUTH) as client:
    client.put(BASE + "/session", json={"base_revision": 0, "session": SESSION}).raise_for_status()
    worker = Worker(root, threading.Event())
    try:
        for name in ("clean.wav", "noisy.wav", "silence.wav", "tone.wav", "intervals.wav", "corrupt.wav"):
            original = (fixtures / name).read_bytes()
            uploaded = client.post(SOURCES, params={"filename": name}, content=original)
            uploaded.raise_for_status()
            version = uploaded.json()["version_id"]
            worker.execute(worker.claim())
            started = time.monotonic()
            worker.execute(worker.claim())
            content = client.get(BASE + "/source-versions/" + version + "/content?limit=10").json()
            units = content["units"]
            text = " ".join(unit["text"] for unit in units).casefold()
            sample = {"name": name, "version_id": version, "seconds": round(time.monotonic() - started, 3),
                      "state": content["state"], "error": content["error"], "units": units,
                      "parent_private_bytes_after": private_bytes(), "checks": {
                          "original_unchanged": client.get("/source-versions/" + version + "/file").content == original,
                          "all_transcripts_unverified": all(u["status"] != "text" and u["metadata"]["review_required"] for u in units)}}
            for unit in units:
                # Retain metadata/transcript truth without large inline audio or private asset paths.
                unit["metadata"]["audio"].pop("data_url", None)
            if name in ("clean.wav", "noisy.wav"):
                sample["checks"]["known_phrases_recovered"] = all(needle in text for needle in gold["needles"])
            elif name in ("silence.wav", "tone.wav"):
                sample["checks"]["no_invented_speech"] = bool(units) and not text.strip()
            elif name == "intervals.wav":
                sample["checks"]["gold_interval_boundaries"] = [[u["locator"]["start_seconds"], u["locator"]["end_seconds"]] for u in units] == gold["intervals"]
                sample["checks"]["second_chunk_absolute_time"] = len(units) >= 2 and all(s["start_seconds"] >= 30 for s in units[1]["metadata"]["segments"])
            else:
                sample["checks"]["corrupt_declined"] = content["state"] == "failed" and not units
            sample["status"] = "passed" if all(sample["checks"].values()) else "needs-review"
            report["samples"].append(sample)
            print(json.dumps({"sample": name, "state": sample["state"], "status": sample["status"], "seconds": sample["seconds"], "error": sample["error"]}), flush=True)
    finally:
        worker.connection.close()
report["status"] = "passed" if all(s["status"] == "passed" for s in report["samples"]) else "needs-review"
path = ROOT / "docs/evaluation" / ("audio-integration-" + tag + ".json")
path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"status": report["status"], "report": str(path), "fixture_data": str(root)}))
