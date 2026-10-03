"""Live checkpoint 7A pilot on small authored videos; no model downloads."""
import argparse
import array
import base64
import io
import json
import os
import sys
import threading
import time
import wave
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.environ["STUDYLENS_AUTO_VIDEO_FRAMES"] = "0"  # Keep the independent 7A gate focused on audio.
sys.path.insert(0, str(ROOT / "services/tests"))
from fastapi.testclient import TestClient
from test_storage import AUTH, BASE, SESSION, SOURCES, TOKEN
from studylens_service.api import create_app
from studylens_service.worker import Worker
from studylens_service import cloud_audio

parser = argparse.ArgumentParser()
parser.add_argument("--cloud", action="store_true", help="Send authored fixture speech to configured Groq")
args = parser.parse_args()
if args.cloud and not cloud_audio.enabled():
    parser.error("Configure automatic Groq audio before using --cloud")
if not args.cloud:
    os.environ["GROQ_API_KEY"] = ""
tag = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
root = ROOT / "tmp" / ("video-integration-" + tag)
fixtures = ROOT / "tests/fixtures/ingestion/phase-07"
gold = json.loads((ROOT / "tests/fixtures/ingestion/phase-06/gold.json").read_text("utf-8"))
report = {"date_utc": tag, "data_directory": str(root), "method": "Real API/worker, FFmpeg and Silero VAD; " + ("automatic Groq with local Tiny fallback" if args.cloud else "local Tiny"),
          "samples": [], "limitations": ["Synthetic authored English speech and test patterns; not held-out lecture accuracy.",
          "Audio only; no frames/visual knowledge or YouTube import yet.", "Not an 8 GB whole-app benchmark; development laptop has 16 GB RAM."]}
with TestClient(create_app(root, TOKEN), headers=AUTH) as client:
    client.put(BASE + "/session", json={"base_revision": 0, "session": SESSION}).raise_for_status()
    worker = Worker(root, threading.Event())
    try:
        for name in ("lecture.mp4", "delayed-audio.mp4", "no-audio.mp4", "intervals.mp4", "short-audio-long-video.mp4", "lecture.mkv", "corrupt.mp4"):
            original = (fixtures / name).read_bytes()
            uploaded = client.post(SOURCES, params={"filename": name}, content=original)
            uploaded.raise_for_status()
            version = uploaded.json()["version_id"]
            started = time.monotonic()
            deadline = started + 120
            while time.monotonic() < deadline:
                job = worker.claim()
                if job:
                    worker.execute(job)
                content = client.get(BASE + "/source-versions/" + version + "/content?limit=10").json()
                if content["state"] in ("succeeded", "partial", "failed", "cancelled"):
                    break
                time.sleep(.05)
            units = content["units"]
            text = " ".join(u["text"] for u in units).casefold()
            checks = {"original_unchanged": client.get("/source-versions/" + version + "/file").content == original}
            if name == "corrupt.mp4":
                checks["corrupt_declined"] = content["state"] == "failed" and not units
            else:
                checks["audio_only_explicit_unverified"] = bool(units) and all(u["metadata"]["video"]["coverage"] == "audio_only" and u["metadata"]["review_required"] and u["status"] != "text" for u in units)
                checks["playback_range_matches_original"] = client.get(BASE + "/source-versions/" + version + "/playback", headers={"Range": "bytes=0-63"}).content == original[:64]
            if name == "no-audio.mp4":
                checks["no_invented_audio"] = bool(units) and not text and not units[0]["metadata"]["video"]["audio_present"]
            elif name != "corrupt.mp4":
                # Both numeric spellings express the authored freezing point.
                checks["known_phrases_recovered"] = all(needle in text.replace("at 0 degrees", "at zero degrees") for needle in gold["needles"])
            if name == "delayed-audio.mp4" and units:
                wav_data = base64.b64decode(units[0]["metadata"]["audio"]["data_url"].split(",")[1])
                with wave.open(io.BytesIO(wav_data)) as wav:
                    pcm = array.array("h", wav.readframes(wav.getnframes()))
                first = next(i for i, sample in enumerate(pcm) if abs(sample) > 500) / 16000
                checks["pcm_delay_preserved"] = abs(first - 4.11) <= .15
                checks["asr_on_original_clock"] = bool(units[0]["metadata"]["segments"]) and abs(units[0]["metadata"]["segments"][0]["start_seconds"] - first) <= .75
            if name in ("intervals.mp4", "short-audio-long-video.mp4"):
                checks["interval_boundaries"] = [[u["locator"]["start_seconds"], u["locator"]["end_seconds"]] for u in units] == [[0, 30], [30, 60], [60, 65]]
                checks["silent_tail"] = len(units) == 3 and not units[-1]["text"]
                if name == "intervals.mp4":
                    checks["second_interval_absolute_time"] = len(units) > 1 and bool(units[1]["metadata"]["segments"]) and all(s["start_seconds"] >= 30 for s in units[1]["metadata"]["segments"])
            for unit in units:
                unit["metadata"].get("audio", {}).pop("data_url", None)
            sample = {"name": name, "version_id": version, "seconds": round(time.monotonic() - started, 3),
                      "state": content["state"], "error": content["error"], "checks": checks, "units": units,
                      "status": "passed" if all(checks.values()) else "needs-review"}
            report["samples"].append(sample)
            print(json.dumps({key: sample[key] for key in ("name", "seconds", "state", "status", "checks")}), flush=True)
    finally:
        worker.connection.close()
report["status"] = "passed" if all(s["status"] == "passed" for s in report["samples"]) else "needs-review"
path = ROOT / "tmp/ingestion-evals" / ("video-integration-" + tag + ".json")
path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"status": report["status"], "report": str(path), "data_directory": str(root)}))
