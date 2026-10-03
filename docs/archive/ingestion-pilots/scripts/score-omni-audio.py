"""Paired raw ASR comparison using the earlier frozen normalization and references."""
import importlib.util
import json
from pathlib import Path
import statistics
import sys
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hinglish_metrics", ROOT / "scripts/evaluate-hinglish.py")
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)
report_path = Path(sys.argv[1]).resolve()
report = json.loads(report_path.read_text("utf-8"))
baseline = json.loads((ROOT / "docs/evaluation/hinglish-results-20261002-044052.json").read_text("utf-8"))
lookup = {(s["shard"], s["row"]): s for s in baseline["samples"] if s["mode"] == "auto"}
samples = [s for s in report["samples"] if s.get("source") == "addyo07/noisy-hinglish-asr"]
groups = {}
for group in sorted({s["group"] for s in samples}):
    part = [s for s in samples if s["group"] == group]
    words, errors, chars, char_errors, tiny_errors = 0, 0, 0, 0, 0
    script_pairs = Counter()
    negative = []
    for sample in part:
        reference = metrics.normalize(sample["reference"])
        prediction = metrics.normalize(sample.get("prediction") or "")
        word = metrics.edits(reference.split(), prediction.split())
        char = metrics.edits(reference.replace(" ", ""), prediction.replace(" ", ""))
        words += word["reference_units"]
        errors += word["errors"]
        chars += char["reference_units"]
        char_errors += char["errors"]
        tiny_errors += lookup[(sample["shard"], sample["row"])]["raw_word_edits"]["errors"]
        script_pairs[metrics.script(sample["reference"]) + " -> " + metrics.script(sample.get("prediction") or "")] += 1
        if not reference:
            negative.append(sample)
    groups[group] = {"clips": len(part), "raw_wer_percent": round(100 * errors / words, 2) if words else None,
        "paired_tiny_raw_wer_percent": round(100 * tiny_errors / words, 2) if words else None,
        "cer_percent": round(100 * char_errors / chars, 2) if chars else None,
        "reference_words": words, "word_errors": errors,
        "median_request_seconds": round(statistics.median(s["seconds"] for s in part), 3),
        "audio_seconds": round(sum(s["duration_seconds"] for s in part), 3),
        "request_seconds": round(sum(s["seconds"] for s in part), 3),
        "request_failures": sum(bool(s.get("error")) for s in part),
        "output_truncations": sum(s.get("finish_reason") == "length" for s in part),
        "negative_clips": len(negative), "nonempty_outputs_on_negative_clips": sum(bool(metrics.normalize(s.get("prediction") or "")) for s in negative),
        "script_pairs": dict(script_pairs)}
summary = {"report": str(report_path.relative_to(ROOT)), "inference_status": report["status"], "groups": groups,
    "normalization": "Same NFKC, casefold, punctuation/symbol to spaces, collapsed whitespace as Tiny; no translation/transliteration/reference rewriting.",
    "timing_caveat": "Gemma is a persistent 4-thread server; per-request timings exclude cold loading. Tiny used 2 threads and started a new helper per interval. No identical-runtime speed claim.",
    "alignment_caveat": "Gemma returns plain text here, without aligned segment timestamps. Raw recognition only, not an integrated app-output score.",
    "peak_private_mib": round(report["peak_private_bytes"] / 1024**2, 2),
    "peak_resident_mib": round(report["peak_resident_bytes"] / 1024**2, 2)}
out = report_path.with_name(report_path.stem + "-scores.json")
out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=True))
