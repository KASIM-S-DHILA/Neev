"""Gather completed multimodal benchmark results without recomputing inference."""
from collections import Counter
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/evaluation"
EVAL = ROOT / "tmp/omnidoc-eval"


def read(path):
    return json.loads(path.read_text("utf-8"))


def document_result(name):
    report = read(DOCS / (name + ".json"))
    samples = report["samples"]
    assert report["status"] == "completed" and len(samples) == 50, "Document run incomplete"
    result = EVAL / name / "result"
    metrics = read(result / "predictions_quick_match_metric_result.json")
    run = read(result / "predictions_quick_match_run_summary.json")
    return {
        "inference_status": report["status"], "attempted_pages": len(samples),
        "finish_reasons": dict(Counter(s.get("finish_reason", "not_recorded") for s in samples)),
        "request_errors": sum(bool(s.get("error")) for s in samples),
        "median_request_seconds": round(statistics.median(s["seconds"] for s in samples), 3),
        "total_request_seconds": round(sum(s["seconds"] for s in samples), 3),
        "groups": {group: {
            "pages": sum(s["group"] == group for s in samples),
            "request_errors": sum(bool(s.get("error")) for s in samples if s["group"] == group),
            "median_request_seconds": round(statistics.median(s["seconds"] for s in samples if s["group"] == group), 3),
        } for group in sorted({s["group"] for s in samples})},
        "peak_private_mib": round(report.get("peak_private_bytes", 0) / 1024**2, 2) or None,
        "peak_resident_mib": round(report.get("peak_resident_bytes", 0) / 1024**2, 2) or None,
        "text_edit_distance": metrics["text_block"]["all"]["Edit_dist"]["ALL_page_avg"],
        "formula_edit_distance": metrics["display_formula"]["all"]["Edit_dist"]["ALL_page_avg"],
        "reading_order_edit_distance": metrics["reading_order"]["all"]["Edit_dist"]["ALL_page_avg"],
        "table_teds": metrics["table"]["all"]["TEDS"]["all"],
        "table_structure_teds": metrics["table"]["all"]["TEDS_structure_only"]["all"],
        "metric_page_denominators": run["page_denominators"],
        "evaluator_stage_execution": run["stage_execution"],
        "formula_cdm": False, "overall_leaderboard_score": None,
    }, samples


def main():
    local, local_pages = document_result("omnidoc-local-baseline")
    gemma, gemma_pages = document_result("gemma4-documents-280")
    assert [(p["id"], p["input_sha256"]) for p in local_pages] == [
        (p["id"], p["input_sha256"]) for p in gemma_pages], "Unpaired document inputs"
    summary = {
        "model": read(ROOT / "tmp/gemma4-omni/manifest.json"),
        "cloud_inference_requests": 0, "production_app_modified": False,
        "audio": read(DOCS / "gemma4-audio-scores.json"),
        "documents": {"tesseract": local, "gemma4_280_image_tokens": gemma},
        "document_groups": dict(Counter(p["group"] for p in gemma_pages)),
        "evaluator_revision": read(EVAL / "revision.json")["sha"],
        "recommendation": "Promising Hindi/Hinglish recognition experiment; universal replacement not justified. Retain native extraction and source validation.",
    }
    (DOCS / "gemma4-omni-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary["documents"]))


if __name__ == "__main__":
    main()
