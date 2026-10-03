# Small local OCR models — StudyLens pilot

Date: October 1, 2026. The requested footprint means **model download/storage size**, not running RAM. This is an isolated evaluation; it does not enable a new ingestion provider in StudyLens.

## Scope and budget

The budget is at most **500 decimal MB of required weights per configuration**, counting detection, recognition, orientation, vision projectors, and optional table/layout models together. Inference libraries and download caches are excluded; this is not a 500 MB whole-application installer budget. Florence has about 2.65 MB of additional tokenizer/configuration/publisher-source files, bringing its deployed model folder to about 465.87 MB excluding caches. GGUF model metadata is contained in the counted files. Smaller models are included because there is no benefit to using the entire allowance unnecessarily.

The candidate catalog covers local, full-page OCR options for this Windows student app: PP-OCR models through RapidOCR, docTR models through OnnxTR, EasyOCR, TrOCR Small with a page detector, Florence-2 Base, SmolDocling GGUF variants, and Tesseract language models. RapidOCR and OnnxTR are inference wrappers, not additional independent model families. The matrix varies every detection/recognition architecture in the installed OnnxTR catalog with a fixed counterpart, then tests available INT8 counterparts and a larger combination. It does not test the Cartesian product of every pair.

This is a documented candidate comparison, **not a claim to have tested every published OCR checkpoint, every historical version, every language pack, or every possible quantization**. Specialist handwriting-only, formula-only, and scene-text recognition models need a different evaluation set; a small recognizer without a page detector is not a complete page-OCR solution.

## Evidence and reproduction

- [Complete candidate matrix](small-ocr-matrix.md): individual sizes, timings, memory, transcription checks, and incomplete trials.
- [Raw results](small-ocr-results.json): exact configurations, output text, boxes/structured output where supported, image SHA256 hashes, model SHA256 hashes and download URLs, dependency versions, and failures.
- [HunyuanOCR trial](hunyuan-local.md): previously measured CPU and Vulkan runs, including failure details.
- Scripts: `scripts/evaluate-small-ocr.py` and `scripts/report-small-ocr.py`. Models, temporary images, logs, and the evaluation virtual environment live under ignored `tmp/ocr-benchmark/`.

```powershell
tmp/ocr-benchmark/venv/Scripts/python.exe scripts/evaluate-small-ocr.py --fixtures
tmp/ocr-benchmark/venv/Scripts/python.exe scripts/evaluate-small-ocr.py --run
tmp/ocr-benchmark/venv/Scripts/python.exe scripts/report-small-ocr.py
```

The script requires a prepared benchmark environment and the prior local slide render/llama.cpp runtime; it is not an end-user installer. Package versions are retained with the results. Download URLs/revisions and hashes identify the evaluated artifacts; a community conversion is not automatically equivalent to its original training checkpoint.

### Test method

Host: Intel i7-8750H, 15.86 GiB installed RAM, GTX 1060 Max-Q with 3 GiB VRAM. All new inference trials use CPU, four threads, and one configuration at a time. This host has more RAM than the target 8 GB laptop, so these measurements do not establish an 8 GB acceptance pass.

Seven inputs: a clean authored probability scan, its blurred/JPEG-compressed version, a stacked Bayes fraction, a branching diagram, a pure blank image, a visually inspected mixed Hindi/English page rendered with RAQM/Nirmala, and slide 12 of the student's actual `Presentation 2.pptx`. Input maximum edge is 1,280 pixels; each model applies its own internal resize/crop preprocessing. Tesseract and the classical OCR pipelines run twice per sample; generative models run once. Sample times exclude model setup/download and include local preprocessing and output decoding. Reported summary time is the median of nonblank sample statistics. These are pilot timings on an active laptop, not controlled throughput or p95 latency measurements.

Every configuration runs in a fresh hidden process. Process-tree resident memory and private memory are sampled every 0.1 seconds, including Tesseract/llama.cpp children. They overlap and must not be added together. The experiment stops above 3 GiB sampled private memory or 900 seconds per configuration. Classical candidates exceeding 20 seconds on a page retain their partial measurements and stop early; they have no complete quality ranking. Sampling is not an OS-enforced hard limit and can miss short spikes. Two startup launcher processes may contribute a small amount of overhead.

Clean/degraded/Hindi transcription checks use character edit distance after Unicode NFC normalization, case folding, and removal of whitespace. Punctuation/digits remain. This score can hide whitespace and line-order differences and must not be treated as full document correctness. CER can exceed 100% when an output repeats or invents enough text. The table check counts recovered numeric tokens out of ten, preserving multiplicity; it does **not** prove correct cell assignment. Diagram checks only cover text labels, not arrows. No automated metric certifies a reconstructed fraction as correct. Unsupported-language Hindi scores are diagnostic failures, not evidence about that model's supported-language quality. TrOCR's blank-page pass is gated by its page detector, not a standalone generative recognizer hallucination test.

## Measured shortlist and recommendation

The catalog contains **65 configurations across seven model families**: **61 completed all seven inputs, three stopped for slow processing, and one failed on a native runtime operation**. Six configurations fall within **400–500 MB**, all completing the trial; the others are smaller alternatives. Completion means the worker finished the test sequence, not that every output is correct or untruncated.

| Candidate pipeline | Required weights MB | Peak resident MiB | Median seconds/sample | Observations on this pilot |
|---|---:|---:|---:|---|
| PP-OCRv6 Small, RapidOCR/ONNX | 31.75 | 388 | 0.956 | Clean/degraded English CER 0%; all ten table values and the title recovered; empty blank |
| PP-OCRv5 English mobile, RapidOCR/ONNX | 13.28 | 376 | 1.089 | Same English/value checks; splits the table title across two lines; empty blank |
| PP-OCRv6 Tiny, RapidOCR/ONNX | 6.90 | 314 | 0.292 | Same scan/value checks, but inserts a stray `J` into the table title; empty blank |
| DB MobileNet + CRNN MobileNet Small, OnnxTR FP32 | 24.41 | 526 | 0.757 | Same scan/value checks; table text emitted by column; empty blank |
| TrOCR Small printed + PP detector | 259.12 | 862 | 2.114 | Same scan/value checks; no clear gain to justify the larger package here |
| EasyOCR CRAFT English | 98.30 | 1,453 | 5.718 | Clean/degraded CER 0.95%; nine table values recovered |
| Tesseract fast English + Hindi, PSM 3 | 5.24 | 101 | 0.395 | Mixed-page Hindi CER 3.75%; seven table values recovered |

**Recommended next implementation candidate:** PP-OCRv6 Small for English/general supported-script scans, with PP-OCRv5 English as the smaller alternative. Tiny is worth keeping as a speed-oriented option, but this pilot already exposes a title error. Use a separate language route for Hindi; PP-OCRv6's published language coverage includes Chinese, English, Japanese and Latin scripts, not Devanagari. [Publisher language coverage](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv6/PP-OCRv6.en.md).

For Hindi, **Tesseract fast `eng+hin` is the strongest measured small candidate on this one page**. The best pack is 27.30 MB and slower (0.608 seconds), with the same 3.75% CER here. EasyOCR Hindi/English uses 298.56 MB, 1,626 MiB resident RAM, and 7.698 seconds; its Hindi CER is 8.75%. Some literal errors are equivalent Arabic/Devanagari digits and punctuation, so CER is not a semantic numeral score. PP-v5 Devanagari missed whole lines here (48.75% CER). These observations do not establish general Hindi accuracy from a single font/page.

### Candidates specifically within 400–500 MB

| Configuration | Required weights MB | Measured suitability |
|---|---:|---|
| OnnxTR LinkNet ResNet50 + ViTSTR Base | 456.63 | 3.736 seconds; 1,024 MiB resident; scan CER 0%, table tokens 10/10. Column-wise output still needs reconstruction. No demonstrated advantage over the smaller shortlist on these pages. |
| Florence-2 Base | 463.22 | 8.716 seconds; 1,711 MiB resident; scan CER 0%, table tokens 10/10. Invented `CALIFORNIA` on the blank page; fraction bars became `I`. |
| Florence-2 Base-FT | 463.22 | 5.286 seconds; 1,722 MiB resident; scan CER 0%, table tokens 10/10. Invented `0:00 PM` on the blank page. |
| SmolDocling F16_Q8_0 decoder + F16 projector | 455.63 | 21.625 seconds; 873 MiB resident; clean CER 0%, degraded CER 100% from duplication, table tokens 10/10; blank not empty. |
| SmolDocling Q4_K_M decoder + F32 projector | 491.22 | 17.577 seconds; 916 MiB resident; clean CER 0%, degraded CER 100% from duplication, table tokens 10/10; blank not empty. |
| SmolDocling BF16 decoder + Q8_0 projector | 431.58 | 19.615 seconds; 869 MiB resident; clean CER 0%, degraded CER 100% from duplication, table tokens 10/10. Blank generation hit the 2,048-token output limit. |

Florence uses the pinned, inspected Microsoft implementation with a small compatibility adapter that disables automatic DynamicCache initialization and retains its legacy tuple cache. Initial processor/cache failures are preserved separately in the raw results. SmolDocling's first passes had special-token output disabled, which damaged DocTags; their CER/table scores are withheld. The corrected trials enable llama.cpp `--special`, preserving location and table tags. Neither runtime issue is evidence that the original checkpoint cannot recognize text.

The corrected SmolDocling Q8/F16 package is **365.08 MB**, below the requested band. It emits a four-column, six-row OTSL table with the correct ten values in this example. The smaller Q4/F16 package emits an extra empty cell before the header and after each data row, shifting header-to-data associations despite recovering all values. These are variant-specific observations, not a universal SmolDocling table score. OTSL's `ecel`, `ched`, `fcel`, and `nl` denote empty cells, column-header cells, content cells, and row boundaries. [Publisher token definitions](https://huggingface.co/datasets/docling-project/PubTables-1M_OTSL-v1.1/blob/main/README.md).

All five corrected variants reproduce the clean scan accurately but duplicate the degraded scan's four lines, producing 100% CER through insertions. Q4/F16 also treats the diagram interior as a picture rather than transcribing its labels. Blank outputs contain `/n` or other generated material, so they fail the empty-transcript check; BF16/Q8 blank generation also hits the output-token limit. Preserved DocTags enable checking these errors; they do not make the output verified. Image preprocessing, decoding settings, other conversions and backends were not exhaustively tuned.

### Failures and limits

EasyOCR DBNet18 loaded 71.07 MB of weights but failed at inference because its CPU deformable-convolution native operation was unavailable. This is a Windows/runtime compatibility failure; no OCR accuracy conclusion is justified. Three PP server/document configurations stopped after roughly 25–80 seconds per page and retain partial outputs. MASTER variants finished all seven images but exceeded 20 seconds on the last table; INT8 was slower than FP32 in this comparison. Quantizing a pipeline can change both detection and recognition, so shared missing tokens cannot be attributed to one component without another experiment.

Published weights excluded from the storage budget include original SmolDocling (513.03 MB), GOT-OCR2 HF (1,121 MB), PaddleOCR-VL (1,917 MB), GLM-OCR (2,651 MB), LightOnOCR2 (2,011 MB), the inspected older Surya recognizer alone (940.53 MB), and the current official Surya2 GGUF decoder plus projector (about 1,471 MB). Exact inspected assets are retained in the raw result catalog. These exclusions are file-size checks, not failed inference trials. A **500 MiB** allowance would be larger than the chosen **500 decimal MB** cap and would change the original SmolDocling exclusion.

**Storage alone does not pick the winner.** On these pages, packages near 500 MB do not demonstrate enough benefit to replace the smaller default candidates. None of the flat OCR outputs should be accepted as a verified mathematical formula or a verified table solely because all visible numbers appear.

## HunyuanOCR: speed and suitability

Our actual local trial used **HunyuanOCR 1.5**, a community Q8 decoder plus F16 vision projector, through llama.cpp `b11303`. Required weights: **1,575,185,152 bytes (1,575 MB)**. It exceeds this request's storage budget. A decoder-only size omits the large required vision model.

| Property | Measured result |
|---|---|
| Content-page CPU latency | 51–63 seconds with the official body-extraction prompt; strict equation retry 66 seconds |
| CPU peak resident memory | 2.66 GiB, server only |
| CPU peak private memory | 2.33 GiB, server only |
| Table | Correct four-column Markdown table, five rows, all ten target/achieved values |
| Fraction | Correct mathematical relationship in the tested image; original body prompt omitted the footer |
| Blank | Generated a sentence saying there was no text, even after a stricter empty-output prompt |
| Vulkan on this GPU | First run exceeded the experiment budget; a smaller-context retry crashed with an access violation |

The logs show roughly 47–62 seconds in vision/prompt prefill, with much less time decoding the short answer. Faster token decoding alone will not eliminate that bottleneck. Reducing context saved memory but did not establish a large speed gain. Tencent's DFlash acceleration was not tested on this host; its published results on different hardware should not be applied to this laptop.

**Assessment:** HunyuanOCR is a useful quality reference and could become an optional background reprocessing tool if we relax the storage budget. It is a poor default for this CPU-first, low-memory student app at the measured settings. The Vulkan failure does not establish that every CUDA/backend configuration will fail. We have no successful GPU timing, no Hindi evaluation, no handwriting evaluation, and no dense textbook benchmark for this model.

Native PDF/PPTX text and native table extraction should precede OCR when available. For scans, OCR must preserve page/slide locations and boxes, and equations/diagrams should retain the original visual for review. Better transcription does not turn uncertain extracted content into verified knowledge.

## Implementation implications

- Download only the selected default weights and explicitly selected language packs. The benchmark's entire multi-model cache is much larger than any single configuration; it is not the proposed app bundle.
- Keep inference in the existing cancellable background-workflow design, with a separate process for any provider that exceeds the current parser/helper memory boundary. Reuse one loaded provider within a bounded job and unload it afterward; avoid loading OCR plus the tutoring LLM concurrently on an 8 GB machine.
- Limit rendered image dimensions and recognition batch sizes. A 20 MB model can require hundreds of MB of RAM; the storage cap does not guarantee compatibility with StudyLens's existing 512 MiB worker limits.
- Preserve boxes and source locations alongside text. Row-wise PP output and column-wise docTR output require different reconstruction; flattening either into a single paragraph can destroy table meaning.
- Language selection must route to a capable recognizer. English-only confidence scores cannot certify Hindi content; the mixed-language pilot shows why silent fallback can discard material.
- Blank-page handling, truncation, failed inference, and uncertain math should produce review states. Do not substitute a generated explanation for an OCR transcript or index a partially generated table as complete.

### A concrete table-structure failure

The OnnxTR configuration with layout/table recognition used 182 MB of weights and roughly 1,959 MiB peak resident RAM. It transcribed all ten numeric values but predicted **seven rows rather than the actual six including the header**. The collaboration row's label/measurement went into row 6, while its `8` and `10` values went into row 5. The numeric cells had confidence near 1.0. Thus, neither 10/10 token recovery nor high recognizer confidence verified row associations. The complete structured export is retained in the raw results.

## Research sources

- [RapidOCR model catalog](https://rapidai.github.io/RapidOCRDocs/main/model_list/) and [implementation](https://github.com/RapidAI/RapidOCR): exact converted PP model options.
- [OnnxTR](https://github.com/felixdittrich92/OnnxTR) and [docTR architecture documentation](https://mindee.github.io/doctr/latest/using_doctr/using_models.html): detector/recognizer families and ONNX/INT8 variants.
- [EasyOCR](https://github.com/JaidedAI/EasyOCR): CRAFT/DBNet and script-specific recognition.
- [TrOCR Small printed](https://huggingface.co/microsoft/trocr-small-printed): a single-line recognizer, requiring an additional detector for pages.
- [Florence-2 Base](https://huggingface.co/microsoft/Florence-2-base): OCR and OCR with region output.
- [SmolDocling original](https://huggingface.co/docling-project/SmolDocling-256M-preview), [evaluated community GGUF conversion](https://huggingface.co/Mungert/SmolDocling-256M-preview-GGUF), and [llama.cpp multimodal support](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md).
- [llama.cpp server settings](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md): special-token output used for the corrected DocTags trials.
- [Tencent HunyuanOCR](https://github.com/Tencent-Hunyuan/HunyuanOCR) and [CPU/llama.cpp documentation](https://github.com/Tencent-Hunyuan/HunyuanOCR/blob/main/docs/llama_cpp.md).

Publisher benchmark claims are not our measured results. The raw asset catalog distinguishes over-budget published weights from models actually run locally.
# Cleanup note

The alternative OCR weights, caches and benchmark Python environment were removed at the student's request on October 3, 2026. Reports and raw results remain available in the [cleanup record and evidence archive](ocr-cleanup.md).
