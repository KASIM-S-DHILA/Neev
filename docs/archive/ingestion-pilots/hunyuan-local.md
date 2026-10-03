# Local HunyuanOCR trial

Date: October 1, 2026. This is a local model experiment, not an enabled StudyLens ingestion provider or a cloud OCR benchmark.

## Reproducible setup

- Tencent [HunyuanOCR 1.5](https://github.com/Tencent-Hunyuan/HunyuanOCR) documents [llama.cpp CPU/laptop inference](https://github.com/Tencent-Hunyuan/HunyuanOCR/blob/main/docs/llama_cpp.md).
- This trial uses the community conversion [prithivMLmods/HunyuanOCR-1.5-GGUF-Updated](https://huggingface.co/prithivMLmods/HunyuanOCR-1.5-GGUF-Updated), pinned to `9ddd3b47beb0de305ecd89a717748bac080d7aee`. This is not a Tencent-published GGUF. Published file hashes verify download integrity, not equivalence or recognition accuracy.
- Decoder: Q8_0, 577,949,408 bytes. Vision projector: F16, 997,235,744 bytes. Runtime: upstream llama.cpp `b11303`, Windows Vulkan distribution (also supports CPU).
- Host: Intel i7-8750H, 15.86 GiB RAM, GTX 1060 Max-Q with 3 GiB VRAM. This is **not an 8 GB acceptance test**.
- CPU trial: 4 threads, one request at a time, context 4,096, maximum 1,024 generated tokens, temperature 0, repetition penalty 1.08. Images share a maximum edge of 1,280 pixels for both providers. The official body-extraction prompt is recorded in the script; it can omit headers/footers.
- Model process is hidden, bound to loopback, protected by an ephemeral API key in the current script, limited to 3 GiB sampled private memory, and stopped after the trial. Download traffic retrieves weights/runtime; **no image or source document goes to cloud OCR**. Images and text stay in the workspace.

From the project directory:

```powershell
.venv\Scripts\python.exe scripts/evaluate-hunyuan.py --setup
.venv\Scripts\python.exe scripts/evaluate-hunyuan.py --baseline
.venv\Scripts\python.exe scripts/evaluate-hunyuan.py --cpu --tag cpu-4096
.venv\Scripts\python.exe scripts/evaluate-hunyuan.py --strict --only equation --tag cpu-strict-equation
.venv\Scripts\python.exe scripts/evaluate-hunyuan.py --strict --only blank --tag cpu-strict-blank
```

Setup downloads about 1.6 GB into ignored `tmp/hunyuan-ocr`, verifies SHA256 against the pinned model revision/GitHub asset metadata, and does not install global software. Existing verified files are reused. The table sample uses slide 12 of the user's `Presentation 2.pptx`, converted locally to `tmp/libreoffice-check-native/source.pdf`. If that private artifact is unavailable, the remaining four authored fixtures still run; requesting the unavailable table alone fails explicitly.

## Measured results

One CPU pass of each sample; these are wall-clock observations, not benchmark medians or general OCR accuracy scores. CPU model loading took 2.89 seconds. HunyuanOCR and Tesseract used the same resized pixels. The table rendering was visually checked against all four columns and five data rows.

| Sample | Tesseract seconds | HunyuanOCR seconds | Observed quality |
| --- | ---: | ---: | --- |
| Literal scan | 0.406 | 56.844 | Hunyuan recovered the authored four lines; Tesseract joined `A is` into `Ais`. |
| Slide 12 table | 0.454 | 51.156 | Hunyuan preserved all headings, row associations and ten numeric cells, including 85/88 and 4.2/4.5. Tesseract omitted headings/85/88 and returned 45 for 4.5. |
| Bayes fraction | 0.547 | 61.390 | Hunyuan preserved the fraction numerator and denominator in LaTeX. Tesseract flattened the fraction and misread a conditional bar. Hunyuan omitted the visible footer with the body-extraction prompt. This is transcription, not mathematical verification. |
| Branching figure | 0.421 | 62.906 | Hunyuan recovered Start, Heads 0.5 and Tails 0.5. Tesseract omitted Start/Tails. Hunyuan omitted the visible footer; extracted labels do not establish arrow relationships. |
| Blank image | 0.344 | 15.312 | Tesseract returned empty. Hunyuan returned a Chinese sentence meaning "there is no text in the image"; that sentence is not source text and must not be indexed as a transcription. |

CPU peak server private memory: **2.33 GiB**. Peak resident memory: **2.66 GiB**. These overlap and must not be added together. Sampling every 0.2 seconds is approximate; values exclude Electron, Python API, OS and other models. All five requests finished without output-token truncation. The server was deliberately terminated after the final result; Windows termination code 1 is not an OCR failure for that completed trial.

An initial CPU scan with context 8,192 also succeeded in 59.907 seconds (2.32 GiB private, 2.58 GiB resident). Reducing context was not an accuracy improvement claim.

## GPU failures retained

1. Context 8,192: the evaluator stopped the process for exceeding its 3 GiB private-memory budget. Sampled private peak 3.11 GiB; device memory peak 2,282 MiB.
2. Context 4,096: model loaded, then the Vulkan process exited with Windows access-violation code `3221225477` during the scan request. Private memory was below budget (2.68 GiB); device peak 2,075 MiB. The exact driver/backend cause is not established. This GPU path is not accepted. CUDA was not tested.

## Strict-prompt follow-up

- Equation image: 66.422 seconds. The stricter prompt recovered the previously omitted footer, including "Do not treat OCR as a verified mathematical formula." It expressed the fraction as `P(A|B) = P(B|A)P(A)/P(B)` rather than following the requested LaTeX format. The visible operands/denominator were preserved in this sample; exact output format is not guaranteed.
- Blank image: 14.640 seconds. It still returned `图片中没有文字。` ("there is no text in the image") despite the instruction to return empty. Prompt changes alone did not solve this failure. Production needs an explicit blank-image path and must keep model commentary out of the source transcription. The strict prompt was not evaluated on the table/figure, so their original scores must not be attributed to it.

## Product decision

Local HunyuanOCR is a promising **background extraction candidate** for tables and formula transcription. It is much slower than Tesseract on this CPU and must not run inside the UI or existing 512 MiB Python parser process. Production integration needs a separate supervised model helper, cancellation while decoding, bounded output, caching by source/page/model/settings, explicit empty/uncertain states and preserved page/slide provenance. Native text/table extraction should precede OCR, and tutoring models should not remain resident alongside OCR on an 8 GB machine.

Cloud remains a later option after the local trial. No cloud provider was added or called. HunyuanOCR is not automatically enabled for existing source imports. Keep extracted model content marked for comparison with the original; confidence in one correct fraction does not verify other formulas or student answers.

Missing gates: blank-image handling in the provider, strict-prompt table/figure quality, Hindi/mixed-language material, handwriting, denser/multi-column pages, rotation, repeated-run latency, 8 GB total-app memory, desktop responsiveness under this workload, cancellation and production provider integration.

Raw evidence is retained with model/runtime provenance in `hunyuan-local-results.json`; model assets and diagnostic logs remain under `tmp/hunyuan-ocr`.
# Cleanup note

The downloaded model and trial environment were removed at the student's request on October 3, 2026. Historical measurements below remain valid; [cleanup details and retained raw evidence](ocr-cleanup.md) explain how records were preserved.
