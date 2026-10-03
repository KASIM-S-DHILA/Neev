"""Isolated real OCR pilot on an authored uploaded-video fixture; no cloud calls."""
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOUD = "--cloud" in sys.argv
if not CLOUD:
    os.environ["GROQ_API_KEY"] = ""
sys.path.insert(0, str(ROOT / "services/tests"))
from fastapi.testclient import TestClient
from test_storage import AUTH, BASE, SESSION, SOURCES, TOKEN
from studylens_service.api import create_app
from studylens_service.worker import Worker

tag = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
root = ROOT / "tmp" / ("video-visuals-integration-" + tag)
original = (ROOT / "docs/evaluation/fixtures/phase-07b/slides.mp4").read_bytes()
with TestClient(create_app(root, TOKEN), headers=AUTH) as client:
    client.put(BASE + "/session", json={"base_revision": 0, "session": SESSION}).raise_for_status()
    result = client.post(SOURCES, params={"filename": "slides.mp4"}, content=original)
    result.raise_for_status()
    version = result.json()["version_id"]
    worker = Worker(root, threading.Event())
    try:
        worker.execute(worker.claim())
        audio = next(j for j in client.get(BASE + "/jobs").json()
            if j["source_version_id"] == version and j["kind"] == "extract_source")
        client.post(BASE + "/jobs/" + audio["id"] + "/cancel").raise_for_status()
        worker.execute(worker.claim())
        worker.execute(worker.claim())
        deadline = time.monotonic() + 360
        while CLOUD:
            visual = next(j for j in client.get(BASE + "/jobs").json()
                if j["source_version_id"] == version and j["kind"] == "video_frame_visuals")
            if visual["state"] not in ("queued", "running") or time.monotonic() >= deadline:
                break
            if visual["state"] == "queued":
                claimed = worker.claim()
                if claimed:
                    worker.execute(claimed)
            time.sleep(1)
        page = client.get(BASE + "/source-versions/" + version + "/video-frames").json()
        checks = {
            "frame_times": [item["seconds"] for item in page["frames"]] == [0, 4, 8],
            "ocr_saved": all(item["visual"] and item["visual"]["ocr"]["text"] for item in page["frames"]),
            "cloud_scope": (sum((item["visual"]["cloud"] or {}).get("status") == "complete" for item in page["frames"]) == 1
                and all((item["visual"]["cloud"] or {}).get("status") in ("complete", "not_selected", "local")
                    for item in page["frames"])) if CLOUD else
                all((item["visual"]["cloud"] or {}).get("status") in ("local", "not_configured") for item in page["frames"]),
            "source_unchanged": client.get("/source-versions/" + version + "/file").content == original,
            "audio_cancelled": next(j for j in client.get(BASE + "/jobs").json()
                if j["id"] == audio["id"])["state"] == "cancelled",
            "visual_job_finished": page["visual_job"]["state"] == "succeeded",
        }
        report = {"status": "passed" if all(checks.values()) else "failed", "checks": checks,
            "version_id": version, "data_directory": str(root), "frame_times": [item["seconds"] for item in page["frames"]],
            "ocr_text": [item["visual"]["ocr"]["text"][:300] for item in page["frames"]],
            "method": "Real FFmpeg/PySceneDetect/Tesseract in isolated API/worker; audio cancelled; " +
                ("one authorized Groq frame request." if CLOUD else "no Groq request."),
            "cloud": CLOUD, "cloud_statuses": [item["visual"]["cloud"]["status"] if item["visual"]
                and item["visual"]["cloud"] else None for item in page["frames"]]}
        target = ROOT / "docs/evaluation" / ("video-visuals-" + tag + ".json")
        target.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"status": report["status"], "report": str(target), "data_directory": str(root),
            "checks": checks}))
        if report["status"] != "passed":
            raise SystemExit(1)
    finally:
        worker.connection.close()
