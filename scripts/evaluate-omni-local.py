"""Current production Tesseract OCR on exactly the prepared benchmark images."""
import json
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services"))
from studylens_service.visual import ocr

WORK = ROOT / "tmp/gemma4-omni/local-baseline"
WORK.mkdir(parents=True, exist_ok=True)
(WORK / "staging").mkdir(exist_ok=True)
worker = SimpleNamespace(root=WORK, check=lambda job: None, stop=threading.Event())
guard = SimpleNamespace(touch=lambda: None)
samples = json.loads((ROOT / "tmp/gemma4-omni/document-samples.json").read_text("utf-8"))
report_path = ROOT / "docs/evaluation/omnidoc-local-baseline.json"
report = {"status": "running", "model": "Current production Tesseract", "method": "Same 50 images and resolutions as Gemma; production visual.ocr; text OCR only, not native PDF/PPT extraction", "samples": []}
for sample in samples:
    started = time.monotonic()
    try:
        with Image.open(ROOT / sample["path"]) as original:
            image = original.convert("RGB")
            try:
                prediction, metadata = ocr(image, worker, {}, guard)
            finally:
                image.close()
        item = sample | {"prediction": prediction, "metadata": metadata, "finish_reason": "stop", "seconds": round(time.monotonic() - started, 3)}
    except Exception as error:
        item = sample | {"prediction": "", "error": str(error), "finish_reason": "error", "seconds": round(time.monotonic() - started, 3)}
    report["samples"].append(item)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(sample["id"], item["seconds"], item["finish_reason"], flush=True)
report["status"] = "completed"
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("Saved", report_path, flush=True)
