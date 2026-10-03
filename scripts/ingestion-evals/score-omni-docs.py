"""Export completed page predictions and run the pinned official OmniDocBench evaluator."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "tmp/gemma4-omni"
EVAL = ROOT / "tmp/omnidoc-eval"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text("utf-8"))
    pages = [s for s in report["samples"] if s.get("source") == "opendatalab/OmniDocBench"]
    if not pages:
        raise SystemExit("No document predictions were completed")
    ground_truth = json.loads((WORK / "omnidoc-selected-ground-truth.json").read_text("utf-8"))
    destination = EVAL / args.report.stem
    predictions = destination / "predictions"
    predictions.mkdir(parents=True, exist_ok=True)
    chosen = []
    for page in pages:
        chosen.append(ground_truth[page["ground_truth_index"]])
        (predictions / Path(page["source_image"]).with_suffix(".md").name).write_text(page.get("prediction") or "", encoding="utf-8")
    gt = destination / "ground-truth.json"
    gt.write_text(json.dumps(chosen, ensure_ascii=False), encoding="utf-8")
    config = {"end2end_eval": {"metrics": {
        "text_block": {"metric": ["Edit_dist"]},
        "display_formula": {"metric": ["Edit_dist"]},
        "table": {"metric": ["TEDS", "Edit_dist"], "teds_workers": 1},
        "reading_order": {"metric": ["Edit_dist"]}},
        "dataset": {"dataset_name": "end2end_dataset", "ground_truth": {"data_path": str(gt)},
            "prediction": {"data_path": str(predictions)}, "match_method": "quick_match", "match_workers": 1,
            "quick_match_truncated_timeout_sec": 60, "match_timeout_sec": 90,
            "timeout_fallback_max_chunk_span": 10, "timeout_fallback_order_penalty": 0.10}}}
    config_path = destination / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    info = json.loads((EVAL / "revision.json").read_text())
    source = EVAL / ("OmniDocBench-" + info["sha"])
    env = {k: v for k, v in os.environ.items() if not any(x in k.upper() for x in ("TOKEN", "API_KEY", "SECRET"))}
    env.update(HF_HOME=str(EVAL / "hf-cache"), XDG_CACHE_HOME=str(EVAL / "hf-cache"), PYTHONUTF8="1")
    with (destination / "evaluation.log").open("wb") as log:
        result = subprocess.run([str(EVAL / "venv/Scripts/python.exe"), str(source / "pdf_validation.py"), "--config", str(config_path)],
            cwd=destination, env=env, stdout=log, stderr=log, creationflags=0x08000000, timeout=900)
    print(json.dumps({"evaluated_pages": len(pages), "inference_status": report["status"], "evaluation_exit_code": result.returncode,
        "output_directory": str(destination), "repo_revision": info["sha"], "formula_cdm": False}))


if __name__ == "__main__":
    main()
