"""Check retained cloud outputs against explicit fixture truth and write a report."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/"tmp/ingestion-evals"
HEADERS=["Impact factor","Measurement","Target","Achieved"]
ROWS=[["Audience interaction","Percentage (%)","85","88"],
      ["Knowledge retention","Percentage (%)","75","80"],
      ["Post-presentation surveys","Average rating","4.2","4.5"],
      ["Referral rate","Percentage (%)","10","12"],
      ["Collaboration opportunities","# of opportunities","8","10"]]


def conforms(value,schema):
    kind=schema["type"]
    if kind=="object":
        return (isinstance(value,dict) and set(value)==set(schema["required"])
                and all(conforms(value[k],v) for k,v in schema["properties"].items()))
    if kind=="array":return isinstance(value,list) and all(conforms(v,schema["items"]) for v in value)
    if kind=="string":return isinstance(value,str)
    if kind=="boolean":return isinstance(value,bool)
    raise ValueError("Unexpected pilot schema type")


def checks(sample,schema):
    content=sample.get("extraction")
    if content is None:return {"schema_valid":False,"quality":"No usable extraction"}
    result={"schema_valid":conforms(content,schema)}
    if not result["schema_valid"]:return result
    name=sample["sample"]
    if name=="table-slide-12":
        tables=content["tables"]
        result.update(table_count=len(tables),correct_complete_table_count=sum(t["headers"]==HEADERS and t["rows"]==ROWS for t in tables),
                      exact_single_table=len(tables)==1 and tables[0]["headers"]==HEADERS and tables[0]["rows"]==ROWS)
    elif name=="equation":
        target=r"P(A|B)=\frac{P(B|A)P(A)}{P(B)}"
        result.update(correct_fraction=target in ["".join(x.split()) for x in content["equations"]],
                      footer_present="Do not treat OCR as a verified mathematical formula." in content["text_lines"])
    elif name=="figure":
        edges={(e["from"],e["to"],e["label"]) for e in content["diagram_edges"]}
        result.update(exact_nodes=set(content["diagram_nodes"])=={"Start","Heads 0.5","Tails 0.5"},
                      exact_edges=edges=={("Start","Heads 0.5",""),("Start","Tails 0.5","")},
                      footer_present="OCR labels alone do not prove graph relationships." in content["text_lines"])
    elif name=="blank":
        result["empty_blank"]=content["is_blank"] and all(not v for k,v in content.items() if k!="is_blank")
    return result


def run():
    reports=[json.loads((DEST/n).read_text("utf-8")) for n in ("groq-vision-results.json","groq-vision-dedup-json-results.json")]
    outcomes=[]
    for label,report in zip(("Initial strict schema","Deduplication + JSON mode"),reports):
        for sample in report["samples"]:
            outcomes.append({"variant":label,"sample":sample["sample"],"status":sample["status"],
                "seconds":sample.get("wall_seconds"),"checks":checks(sample,report["schema"])})
    routing=json.loads((DEST/"vision-routing-results.json").read_text("utf-8"))
    data={"checks":outcomes,"routing":routing,
          "limitations":"Fixture-specific transcription/structure checks, not general OCR accuracy, held-out routing evaluation, or production integration."}
    (DEST/"groq-vision-checks.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Groq vision and local routing pilot","","Date: October 1, 2026.","",
        "Live model: `qwen/qwen3.8-27b`, confirmed through this account's Models API. The user's request authorized this cloud trial. The selected images were transmitted to Groq; credentials were read from the environment and not retained.","",
        "## Outcome","",
        "The second configuration returned one correct table, the correct diagram nodes/arrows, and an empty blank transcription. The first configuration correctly transcribed the stacked fraction and its footer. This supports trying a lightweight local OCR path with selective cloud extraction, while retaining validation and explicit failure states.","",
        "| Variant | Sample | Wall seconds | Observed result |","|---|---|---:|---|"]
    for entry in outcomes:
        c=entry["checks"];name=entry["sample"]
        if entry["status"]!="complete":note="HTTP 400 json_validate_failed; no usable extraction"
        elif name=="table-slide-12":note=f"{c['table_count']} tables; exact single-table check: {c['exact_single_table']}; one complete correct table plus duplicates in the initial variant"
        elif name=="equation":note=f"Correct fraction: {c['correct_fraction']}; footer: {c['footer_present']}"
        elif name=="figure":note=f"Exact nodes: {c['exact_nodes']}; exact arrows: {c['exact_edges']}; footer: {c['footer_present']}"
        else:note=f"Empty blank: {c['empty_blank']}"
        lines.append(f"| {entry['variant']} | {name} | {entry['seconds'] or '—'} | {note} |")
    lines += ["","The first table response contained the correct four-column, five-row table with all ten values, but also invented two partial duplicate tables and a claim about overlapping views. Visual inspection confirms there is only one source table. Strict JSON format did not prevent this semantic failure.","",
        "The figure request failed under strict schema decoding. The second variant used documented JSON object mode and an instruction to merge overlapping internal views rather than duplicating source content. Both the prompt and output mode changed; this does not isolate which change caused the improvement. Local schema checks passed for the successful responses, including JSON mode, and fixture-specific cell/arrow/formula checks are retained.","",
        "## Local routing experiment","","No cloud requests are made by the local router. It reads cached PP-OCRv6 Small text/boxes/confidence and computes inexpensive image-line/foreground signals.","",
        "| Input | Pilot decision | Local check seconds, excluding OCR |","|---|---|---:|"]
    for sample in routing["samples"]:lines.append(f"| {sample['sample']} | {sample['decision']} | {sample.get('seconds','—')} |")
    table=next(s for s in routing["samples"] if s["sample"]=="table-slide-12")
    lines += ["",f"The table's mean local OCR confidence was {table['signals']['mean_ocr_confidence']:.4f}. It was routed because of structural signals, despite that high confidence. The mixed Hindi page uses an explicitly selected Hindi language input and routes to a capable local recognizer first; this is not automatic language detection.","",
        "Rules: numeric repetitions plus horizontal boundaries flag a table candidate; mathematical expressions plus a long stroke flag stacked math; long diagonal connections flag diagrams; low confidence or non-white pixels without OCR text flag an extraction problem. Only an exactly white page with no text/boxes is skipped. The native-structure fast path is present but was not exercised by these image fixtures. Borderless/text-only tables and other complex layouts need additional rules and held-out evaluation.","",
        "The routing prototype produced the intended decisions on these seven known fixtures. The thresholds were not calibrated on a separate dataset, and these examples are not an unbiased routing accuracy test. A faint image must not be discarded merely because OCR is empty. Photographs, handwriting, rotation, borderless tables, dense pages and mixed layouts remain gates.","",
        "## Method and quota","",
        "Images reuse the exact 1,280-pixel-maximum fixture PNGs from the local OCR comparison; SHA256 values are retained. Each successful configuration/sample has one call, so these are observations rather than latency percentiles. Wall time includes API network round trip and output parsing, excludes intentional quota waits, and does not measure the whole Electron workflow.","",
        "Instruct mode (`reasoning_effort=none`), temperature 0, 1,536 maximum completion tokens, one image per request. Calls were spaced 65 seconds apart; HTTP 429 waits are bounded and respect retry-after. All five successful responses finished with `stop`. One strict figure request failed; the blank control was not reached in that initial run. The blank image was deliberately sent in the second run as a negative control, even though production routing would skip this fixture.","",
        "The account's response headers reported an 8,000 TPM limit. Raw usage fields, remaining/reset headers and errors are preserved. The documentation's 2,048 image-token figure does not directly match the reported prompt_tokens field in these responses, so prompt_tokens alone should not drive the budget. Use conservative image accounting and the actual limit/reset headers.","",
        "The pilot sends full fixture images, not automatically selected crops. Crop detection, student cloud controls, source-region locators, caching, resumable queue integration, cancellation and an 8 GB end-to-end responsiveness test are not implemented or validated here. No production ingestion provider was enabled.","",
        "## Evidence and reproduction","",
        "- [Initial responses and strict-schema failure](groq-vision-results.json)",
        "- [Corrected JSON-mode responses](groq-vision-dedup-json-results.json)",
        "- [Local routing signals](vision-routing-results.json)",
        "- [Schema and fixture checks](groq-vision-checks.json)",
        "- [Local OCR comparison](small-ocr.md)","",
        "Use the existing isolated OCR evaluation environment. GROQ_API_KEY must be supplied through the environment; never put it in the script. --run explicitly sends selected images to Groq. Tags preserve previous runs.","",
        "```powershell",
        "tmp/ocr-benchmark/venv/Scripts/python.exe scripts/ingestion-evals/evaluate-groq-vision.py --run --tag repeat",
        "tmp/ocr-benchmark/venv/Scripts/python.exe scripts/ingestion-evals/evaluate-groq-vision.py --run --only table-slide-12 figure blank --tag corrected-repeat --deduplicate --json-object",
        "tmp/ocr-benchmark/venv/Scripts/python.exe scripts/ingestion-evals/evaluate-vision-routing.py",
        "tmp/ocr-benchmark/venv/Scripts/python.exe scripts/ingestion-evals/report-groq-vision.py","```","",
        "The report command reads the retained original filenames. Python/Pillow/NumPy/OpenCV versions are recorded in the local OCR results; no additional dependency was installed for this pilot.","",
        "## Official documentation","",
        "- [Groq vision](https://console.groq.com/docs/vision)",
        "- [Qwen model card](https://console.groq.com/docs/model/qwen/qwen3.8-27b)",
        "- [Structured output modes](https://console.groq.com/docs/structured-outputs)",
        "- [Rate limits](https://console.groq.com/docs/rate-limits)",""]
    (DEST/"groq-vision.md").write_text("\n".join(lines),encoding="utf-8")
    print([(o["variant"],o["sample"],o["checks"]) for o in outcomes])


if __name__=="__main__":run()
