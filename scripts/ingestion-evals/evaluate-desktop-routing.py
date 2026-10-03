"""Local-only production router check with real Tesseract; no cloud access."""
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import time

from PIL import Image
from studylens_service.cloud_vision import route
from studylens_service.visual import ocr, prepare

ROOT = Path(__file__).resolve().parents[2]


class LocalFixture:
    root = ROOT / "tmp/desktop-router"
    stop = threading.Event()
    def check(self, _job):
        pass
    def touch(self):
        pass


def run():
    fixture = LocalFixture()
    (fixture.root / "staging").mkdir(parents=True, exist_ok=True)
    samples = []
    for name in ("scan", "scan-degraded", "table-slide-12", "equation", "figure", "blank", "hindi-mixed"):
        path = ROOT / "tmp/ocr-benchmark/fixtures" / (name + (".jpg" if name == "scan-degraded" else ".png"))
        with Image.open(path) as original:
            image, _scale = prepare(original)
        try:
            started = time.perf_counter()
            text, result = ocr(image, fixture, {}, fixture)
            local_seconds = time.perf_counter() - started
            image.thumbnail((1280, 1280))
            started = time.perf_counter()
            decision = route(image, text, {"ocr": result})
            samples.append({"sample": name, "local_seconds": round(local_seconds, 3),
                "routing_seconds": round(time.perf_counter() - started, 3), "language": result.get("language"),
                "mean_confidence": result.get("mean_confidence"), "local_text": text, **decision})
        finally:
            image.close()
    report = {"date": datetime.now(timezone.utc).isoformat(), "cloud_requests": 0,
        "method": "Actual production Tesseract + Pillow routing on the known seven-image fixture set; English configuration. This differs from the earlier cached PP-OCR/OpenCV pilot.",
        "limitations": "Not held-out accuracy or calibration. Hindi recognition is not claimed with English traineddata. Borderless tables, photographs, handwriting, densely packed or faint/rotated layouts require manual comparison and override.",
        "samples": samples}
    (ROOT / "tmp/ingestion-evals/desktop-routing-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps([{key: sample[key] for key in ("sample", "decision", "local_seconds", "routing_seconds")} for sample in samples]))


if __name__ == "__main__":
    run()
