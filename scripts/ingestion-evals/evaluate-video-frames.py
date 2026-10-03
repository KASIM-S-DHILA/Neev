"""Real, no-cloud frame-selection benchmark on authored gold video scenes."""
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.environ["GROQ_API_KEY"] = ""
os.environ["STUDYLENS_AUTO_VIDEO_FRAMES"] = "1"
sys.path.insert(0, str(ROOT / "services/tests"))
from fastapi.testclient import TestClient
from test_storage import AUTH, BASE, SESSION, SOURCES, TOKEN
from studylens_service.api import create_app
from studylens_service.worker import Worker

tag = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
root = ROOT / "tmp" / ("video-frames-integration-" + tag)
fixtures = ROOT / "tests/fixtures/ingestion/phase-07b"
gold = json.loads((fixtures / "gold.json").read_text("utf-8"))
report = {"date_utc":tag,"data_directory":str(root),"method":"Real API/worker, FFmpeg PTS, PySceneDetect 0.7.1 and low-resolution pixel changes; no ASR, OCR or cloud",
    "gold":gold,"samples":[],"limitations":["Small authored teaching scenes, not held-out natural video quality.",
    "One-second sampling can miss brief changes; previews are not extracted knowledge.","Helper private bytes after processing are not peak or whole-app 8 GB measurements."]}
with TestClient(create_app(root,TOKEN),headers=AUTH) as client:
    client.put(BASE + "/session",json={"base_revision":0,"session":SESSION}).raise_for_status()
    worker = Worker(root,threading.Event())
    try:
        for name in ("slides.mp4","whiteboard.mp4","return-slides.mp4","static.mp4","vfr.mp4","rotated.mp4"):
            original = (fixtures / name).read_bytes()
            uploaded = client.post(SOURCES,params={"filename":name},content=original)
            uploaded.raise_for_status()
            version = uploaded.json()["version_id"]
            worker.execute(worker.claim())
            audio_job = next(j for j in client.get(BASE + "/jobs").json() if j["source_version_id"] == version and j["kind"] == "extract_source")
            client.post(BASE + "/jobs/" + audio_job["id"] + "/cancel").raise_for_status()
            start = time.monotonic()
            worker.execute(worker.claim())
            first = client.get(BASE + "/source-versions/" + version + "/video-frames").json()
            frames = []
            for offset in range(0,first["total"],4):
                frames += client.get(BASE + "/source-versions/" + version + "/video-frames?offset=" + str(offset)).json()["frames"]
            points = [f["seconds"] for f in frames]
            checks = {"selection_finished":first["job"]["state"] in ("succeeded","partial"),
                "original_unchanged":client.get("/source-versions/" + version + "/file").content == original,
                "previews_available_and_unverified":bool(frames) and all(f["asset"].get("data_url") and f["ocr_pending"] and f["review_required"] for f in frames),
                "private_paths_absent":"path" not in json.dumps(first)}
            expected = {"slides.mp4":[0,4,8],"whiteboard.mp4":[0,3,6,9,12],"return-slides.mp4":[0,4,8],"static.mp4":[0,60],"vfr.mp4":[0,2.4,5.6]}.get(name)
            if expected is not None:
                checks["gold_changes_preserved"] = points == expected
            if name == "rotated.mp4":
                checks["rotation_applied"] = bool(frames) and frames[0]["asset"]["width"] == 360 and frames[0]["asset"]["height"] == 640
            for frame in frames:
                frame["asset"].pop("data_url",None)
            sample = {"name":name,"version_id":version,"seconds":round(time.monotonic()-start,3),"checks":checks,
                "job":first["job"],"frames":frames,"status":"passed" if all(checks.values()) else "needs-review"}
            report["samples"].append(sample)
            print(json.dumps({"name":name,"seconds":sample["seconds"],"status":sample["status"],"frame_times":points,"error":first["job"]["error"]}),flush=True)
    finally:
        worker.connection.close()
report["status"] = "passed" if all(s["status"] == "passed" for s in report["samples"]) else "needs-review"
target = ROOT / "tmp/ingestion-evals" / ("video-frames-" + tag + ".json")
target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"status":report["status"],"report":str(target),"data_directory":str(root)}))
