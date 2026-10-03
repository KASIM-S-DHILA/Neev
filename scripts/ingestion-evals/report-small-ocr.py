"""Build a transparent pilot score sheet from retained local OCR outputs."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import statistics
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "tmp/ocr-benchmark"
DEST = ROOT / "tmp/ingestion-evals"
SCAN = "Conditional probability\nThe sample space contains 100 outcomes.\nEvent A contains 25 outcomes.\nThe probability of A is 0.25."
HINDI = "प्रायिकता का परिचय\nकुल परिणामों की संख्या 100 है।\nघटना A में 25 परिणाम हैं।\nProbability of A = 0.25"
VALUES = Counter(["85", "88", "75", "80", "4.2", "4.5", "10", "12", "8", "10"])


def normalize(text):
    # Ignore case/whitespace for transcription CER; retain punctuation/digits.
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", text).casefold())


def distance(a, b):
    previous = list(range(len(b) + 1))
    for i, left in enumerate(a, 1):
        current = [i]
        for j, right in enumerate(b, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (left != right)))
        previous = current
    return previous[-1]


def scores(samples, family=None):
    score = {}
    for sample in samples:
        name = sample["sample"]; text = sample["output"]["text"]
        if family == "smol" and not sample["output"].get("special_tokens_enabled"):
            score["serialization_warning"] = "Special-token output disabled; transcription metrics withheld"
            if name == "blank": score["blank_empty"] = not normalize(text)
            continue
        if name in ("scan", "scan-degraded", "hindi-mixed"):
            truth = normalize(HINDI if name == "hindi-mixed" else SCAN)
            score[name + "_cer_percent"] = round(100 * distance(truth, normalize(text)) / len(truth), 2)
        if name == "blank": score["blank_empty"] = not normalize(text)
        if name == "table-slide-12":
            # Bag of numeric tokens: this DOES NOT validate row/column association.
            numbers = Counter(re.findall(r"(?<!\w)\d+(?:\.\d+)?(?!\w)", re.sub(r"<[^>]+>", " ", text)))
            score["table_numeric_tokens_recovered_of_10"] = sum((numbers & VALUES).values())
            score["table_unmatched_numeric_tokens"] = list((numbers - VALUES).elements())
        if name == "figure":
            compact = normalize(text)
            terms = ("A branching experiment", "Start", "Heads 0.5", "Tails 0.5",
                     "OCR labels alone do not prove graph relationships.")
            score["figure_text_items_recovered_of_5"] = sum(normalize(x) in compact for x in terms)
    return score


def build():
    reports = [json.loads(p.read_text("utf-8")) for p in sorted((WORK / "results").glob("*.json"))]
    fixtures = []
    for path in sorted((WORK / "fixtures").glob("*")):
        if path.suffix not in (".png", ".jpg"): continue
        fixtures.append({"name":path.name,"bytes":path.stat().st_size,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    for report in reports:
        report["pilot_scores"] = scores(report.get("samples", []),report["config"]["family"])
        times = [x["median_seconds"] for x in report.get("samples", []) if x["sample"] != "blank"]
        if times:report["median_nonblank_sample_seconds"] = round(statistics.median(times), 3)
    data = {"date":"2026-10-01", "storage_limit_bytes":500000000,
            "host":{"cpu":"Intel i7-8750H","ram_gib":15.86,"gpu":"GTX 1060 Max-Q, 3 GiB (unused)"},
            "method":{"threads":4,"fresh_process_per_config":True,"max_image_edge":1280,
                "memory_sampling_seconds":0.1,"memory_stop_private_bytes":3*1024**3,
                "classic_repeat_count":2,"generative_repeat_count":1,"classic_slow_stop_seconds":20,
                "time_statistic":"Median of two calls per classic sample; one generative call. Summary is median of nonblank sample statistics.",
                "cer":"NFC, casefold, remove whitespace; retain punctuation/digits. Strip serialized markup tags.",
                "table_metric":"Numeric-token multiset recall /10, NOT table structure or cell assignment accuracy.",
                "limitations":"Seven-image pilot; only one private real slide; no handwritten gold image; not target 8GB acceptance or an exhaustive worldwide model census."},
            "fixtures":fixtures,"dependencies":(WORK/"dependencies-lock.txt").read_text("utf-8-sig").splitlines(),
            "setup_failures_and_superseded_trials":[json.loads(p.read_text("utf-8")) for p in sorted((WORK/"setup-failures").glob("*.json"))],
            "catalog":json.loads((WORK/"catalog.json").read_text("utf-8")),"runs":reports,
            "publisher_assets":json.loads((WORK/"exclusions.json").read_text()),
            "onnx_release_asset_sizes":json.loads((WORK/"onnx-asset-sizes.json").read_text()) if (WORK/"onnx-asset-sizes.json").exists() else {},
            "current_surya_gguf_assets":json.loads((WORK/"surya-gguf-tree.json").read_text()) if (WORK/"surya-gguf-tree.json").exists() else {}}
    DEST.mkdir(parents=True,exist_ok=True)
    (DEST / "small-ocr-results.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    lines = ["# Local OCR pilot — complete candidate matrix", "", "Generated from retained outputs. See `small-ocr.md` for scope, interpretation, and recommendations.", "",
             "Weights use decimal MB. RAM uses MiB. Times exclude initialization/download. CER ignores whitespace/case. Lower CER is better. Hindi CER is only meaningful for Hindi-capable models.", "",
             "| Configuration | Status | Weights MB | Peak RSS MiB | Seconds/sample | Clean CER % | Degraded CER % | Hindi CER % | Table numbers /10 | Blank empty |", 
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    def show(value):return "—" if value is None else str(value)
    for report in reports:
        s=report["pilot_scores"]
        config=report["config"]
        hindi_capable = "hi" in config.get("langs", []) or config.get("rec", "").startswith("devanagari_") or "hin" in config.get("langs", "")
        lines.append("| " + " | ".join(map(str,[report["config"]["name"],report["status"],
            round(report["weight_bytes"]/1e6,2) if "weight_bytes" in report else "—",
            round(report.get("peak_process_tree_resident_bytes",0)/1024**2),
            show(report.get("median_nonblank_sample_seconds")),show(s.get("scan_cer_percent")),show(s.get("scan-degraded_cer_percent")),
            show(s.get("hindi-mixed_cer_percent") if hindi_capable else None),show(s.get("table_numeric_tokens_recovered_of_10")),show(s.get("blank_empty"))])) + " |")
    lines += ["", "## Failures, exclusions, and partial trials", ""]
    for report in reports:
        if report["status"] != "complete":lines.append(f"- **{report['config']['name']}** ({report['status']}): {report.get('error','See raw record')}.")
        for sample in report.get("samples",[]):
            if sample["output"].get("finish_reason") == "length":
                lines.append(f"- **{report['config']['name']} / {sample['sample']}**: generation hit the output-token limit; the worker completed, but this transcript is truncated.")
    (DEST / "small-ocr-matrix.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"{len(reports)} retained trials; {sum(x['status']=='complete' for x in reports)} complete")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    build()
