# Groq vision and local routing pilot

Date: October 1, 2026.

Live model: `qwen/qwen3.8-27b`, confirmed through this account's Models API. The user's request authorized this cloud trial. The selected images were transmitted to Groq; credentials were read from the environment and not retained.

## Outcome

The second configuration returned one correct table, the correct diagram nodes/arrows, and an empty blank transcription. The first configuration correctly transcribed the stacked fraction and its footer. This supports trying a lightweight local OCR path with selective cloud extraction, while retaining validation and explicit failure states.

| Variant | Sample | Wall seconds | Observed result |
|---|---|---:|---|
| Initial strict schema | table-slide-12 | 1.125 | 3 tables; exact single-table check: False; one complete correct table plus duplicates in the initial variant |
| Initial strict schema | equation | 1.25 | Correct fraction: True; footer: True |
| Initial strict schema | figure | — | HTTP 400 json_validate_failed; no usable extraction |
| Deduplication + JSON mode | table-slide-12 | 0.953 | 1 tables; exact single-table check: True; one complete correct table plus duplicates in the initial variant |
| Deduplication + JSON mode | figure | 1.266 | Exact nodes: True; exact arrows: True; footer: True |
| Deduplication + JSON mode | blank | 0.578 | Empty blank: True |

The first table response contained the correct four-column, five-row table with all ten values, but also invented two partial duplicate tables and a claim about overlapping views. Visual inspection confirms there is only one source table. Strict JSON format did not prevent this semantic failure.

The figure request failed under strict schema decoding. The second variant used documented JSON object mode and an instruction to merge overlapping internal views rather than duplicating source content. Both the prompt and output mode changed; this does not isolate which change caused the improvement. Local schema checks passed for the successful responses, including JSON mode, and fixture-specific cell/arrow/formula checks are retained.

## Local routing experiment

No cloud requests are made by the local router. It reads cached PP-OCRv6 Small text/boxes/confidence and computes inexpensive image-line/foreground signals.

| Input | Pilot decision | Local check seconds, excluding OCR |
|---|---|---:|
| blank | skip-blank | 0.0523 |
| equation | vision-candidate | 0.1154 |
| figure | vision-candidate | 0.1654 |
| hindi-mixed | local-language-retry | 0.1355 |
| scan-degraded | local-ocr | 0.1015 |
| scan | local-ocr | 0.1819 |
| table-slide-12 | vision-candidate | 0.1986 |

The table's mean local OCR confidence was 0.9988. It was routed because of structural signals, despite that high confidence. The mixed Hindi page uses an explicitly selected Hindi language input and routes to a capable local recognizer first; this is not automatic language detection.

Rules: numeric repetitions plus horizontal boundaries flag a table candidate; mathematical expressions plus a long stroke flag stacked math; long diagonal connections flag diagrams; low confidence or non-white pixels without OCR text flag an extraction problem. Only an exactly white page with no text/boxes is skipped. The native-structure fast path is present but was not exercised by these image fixtures. Borderless/text-only tables and other complex layouts need additional rules and held-out evaluation.

The routing prototype produced the intended decisions on these seven known fixtures. The thresholds were not calibrated on a separate dataset, and these examples are not an unbiased routing accuracy test. A faint image must not be discarded merely because OCR is empty. Photographs, handwriting, rotation, borderless tables, dense pages and mixed layouts remain gates.

## Method and quota

Images reuse the exact 1,280-pixel-maximum fixture PNGs from the local OCR comparison; SHA256 values are retained. Each successful configuration/sample has one call, so these are observations rather than latency percentiles. Wall time includes API network round trip and output parsing, excludes intentional quota waits, and does not measure the whole Electron workflow.

Instruct mode (`reasoning_effort=none`), temperature 0, 1,536 maximum completion tokens, one image per request. Calls were spaced 65 seconds apart; HTTP 429 waits are bounded and respect retry-after. All five successful responses finished with `stop`. One strict figure request failed; the blank control was not reached in that initial run. The blank image was deliberately sent in the second run as a negative control, even though production routing would skip this fixture.

The account's response headers reported an 8,000 TPM limit. Raw usage fields, remaining/reset headers and errors are preserved. The documentation's 2,048 image-token figure does not directly match the reported prompt_tokens field in these responses, so prompt_tokens alone should not drive the budget. Use conservative image accounting and the actual limit/reset headers.

The pilot sends full fixture images, not automatically selected crops. Crop detection, student cloud controls, source-region locators, caching, resumable queue integration, cancellation and an 8 GB end-to-end responsiveness test are not implemented or validated here. No production ingestion provider was enabled.

## Evidence and reproduction

- [Initial responses and strict-schema failure](groq-vision-results.json)
- [Corrected JSON-mode responses](groq-vision-dedup-json-results.json)
- [Local routing signals](vision-routing-results.json)
- [Schema and fixture checks](groq-vision-checks.json)
- [Local OCR comparison](small-ocr.md)

Use the existing isolated OCR evaluation environment. GROQ_API_KEY must be supplied through the environment; never put it in the script. --run explicitly sends selected images to Groq. Tags preserve previous runs.

```powershell
tmp/ocr-benchmark/venv/Scripts/python.exe scripts/evaluate-groq-vision.py --run --tag repeat
tmp/ocr-benchmark/venv/Scripts/python.exe scripts/evaluate-groq-vision.py --run --only table-slide-12 figure blank --tag corrected-repeat --deduplicate --json-object
tmp/ocr-benchmark/venv/Scripts/python.exe scripts/evaluate-vision-routing.py
tmp/ocr-benchmark/venv/Scripts/python.exe scripts/report-groq-vision.py
```

The report command reads the retained original filenames. Python/Pillow/NumPy/OpenCV versions are recorded in the local OCR results; no additional dependency was installed for this pilot.

## Official documentation

- [Groq vision](https://console.groq.com/docs/vision)
- [Qwen model card](https://console.groq.com/docs/model/qwen/qwen3.8-27b)
- [Structured output modes](https://console.groq.com/docs/structured-outputs)
- [Rate limits](https://console.groq.com/docs/rate-limits)
