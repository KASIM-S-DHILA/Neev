"""Explicit live gate: one retained table image through the app API and worker."""
import argparse
import importlib.util
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/tests"))
from fastapi.testclient import TestClient
from test_storage import AUTH, BASE, SESSION, SOURCES, TOKEN
from studylens_service.api import create_app
from studylens_service.worker import Worker
from studylens_service.resource_guard import private_bytes
spec = importlib.util.spec_from_file_location("groq_fixture_truth", ROOT / "scripts/ingestion-evals/report-groq-vision.py")
truth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(truth)
HEADERS, ROWS = truth.HEADERS, truth.ROWS


def run():
    if not os.environ.get("GROQ_API_KEY", "").strip():
        raise SystemExit("GROQ_API_KEY is required; its value is never written to the report.")
    tag = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    root = ROOT / "tmp" / ("vision-integration-" + tag)
    report_path = ROOT / "tmp/ingestion-evals" / ("desktop-vision-" + tag + ".json")
    report = {"date_utc": tag, "sample": "table-slide-12", "method": "Real app API, real Tesseract and production cloud worker; isolated data directory, one image authorized for transfer.",
              "model": "qwen/qwen3.8-27b", "checks": {}, "limitation": "One known table image, not held-out routing or an 8 GB benchmark."}
    with TestClient(create_app(root, TOKEN), headers=AUTH) as client:
        client.put(BASE + "/session", json={"base_revision": 0, "session": SESSION}).raise_for_status()
        image = ROOT / "tmp/ocr-benchmark/fixtures/table-slide-12.png"
        original = client.post(SOURCES, params={"filename": "table-slide-12.png"}, content=image.read_bytes())
        original.raise_for_status()
        version = original.json()["version_id"]
        worker = Worker(root, threading.Event())
        try:
            for kind in ("verify_original", "extract_source"):
                job = worker.claim()
                if not job or job["kind"] != kind:
                    raise ValueError("Unexpected local job ordering")
                worker.execute(job)
            before = client.get(BASE + f"/source-versions/{version}/content").json()
            if not before["units"]:
                raise ValueError("Local extraction produced no unit")
            report["local_text"] = before["units"][0]["text"]
            response = client.post(BASE + f"/source-versions/{version}/cloud-visuals", json={"consent": True})
            response.raise_for_status()
            started = time.monotonic()
            worker.execute(worker.claim())
            after = client.get(BASE + f"/source-versions/{version}/content").json()
            report["selective_job"] = after["cloud_job"]
            entry = after["units"][0]["metadata"].get("cloud_visuals", [None])[0]
            if entry and entry["status"] == "local":
                report["manual_override_needed"] = True
                response = client.post(BASE + f"/source-versions/{version}/cloud-visuals", json={"consent": True, "ordinal": 1})
                response.raise_for_status()
                worker.execute(worker.claim())
                after = client.get(BASE + f"/source-versions/{version}/content").json()
                entry = after["units"][0]["metadata"].get("cloud_visuals", [None])[0]
            report["seconds"] = round(time.monotonic() - started, 3)
            report["final_job"] = after["cloud_job"]
            report["entry"] = entry
            tables = entry.get("extraction", {}).get("tables", []) if entry else []
            report["checks"] = {"exact_single_table": len(tables) == 1 and tables[0]["headers"] == HEADERS and tables[0]["rows"] == ROWS,
                "local_text_unchanged": before["units"][0]["text"] == after["units"][0]["text"],
                "source_locator_unchanged": before["units"][0]["locator"] == after["units"][0]["locator"],
                "original_unchanged": client.get(f"/source-versions/{version}/file").content == image.read_bytes(),
                "unverified": bool(entry and entry.get("verified") is False)}
            report["process_private_bytes_after"] = private_bytes()
            report["status"] = "passed" if all(report["checks"].values()) else "needs-review"
            # A second authorized pass must reuse the same image/model/prompt result.
            if entry and entry["status"] == "complete":
                client.post(BASE + f"/source-versions/{version}/cloud-visuals", json={"consent": True, "ordinal": 1}).raise_for_status()
                worker.execute(worker.claim())
                cache_job = client.get(BASE + f"/source-versions/{version}/content").json()["cloud_job"]
                report["cache_job"] = cache_job
                report["checks"]["cache_reused_without_new_send"] = cache_job["result"]["cached"] == 1 and cache_job["result"]["sent"] == 0
            report["status"] = "passed" if all(report["checks"].values()) else "needs-review"
        finally:
            worker.connection.close()
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": report["checks"], "seconds": report["seconds"], "report": str(report_path)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    if not parser.parse_args().run:
        parser.error("Explicit --run is required: this sends one retained fixture image to Groq.")
    run()
