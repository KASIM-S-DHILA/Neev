# Gemma 4 E2B local multimodal evaluation

Test date: 2026-10-02. This is an isolated benchmark, not an app integration. StudyLens's production extraction settings and models were not changed. No cloud inference was used.

## Decision

Audio recognition is promising for a follow-up integration experiment, particularly Hindi and Hinglish. A universal replacement for native parsing, OCR, transcription and tutoring is not justified by these tests. The vision pilots changed a formula, invented table markup on a blank image, and lost a diagram's explicit branch relationships. Generated extraction still needs comparison with the source.

The 50-page comparison reinforces that decision: Gemma was slower and had higher text and reading-order error than Tesseract under the tested budget. Formula edit distance and table structure improved over plain OCR, but remained weak; 18/50 pages reached the inference deadline.

## Configuration and resources

- Machine: Intel i7-8750H, 6 physical / 12 logical cores, 15.86 GiB RAM, GTX 1060 Max-Q 3 GiB. **CPU only**; GPU was not used.
- Model: `ggml-org/gemma-4-E2B-it-GGUF`, revision `b4243c156154b6dca9324415f8c7ccc098b4aed1`.
- Decoder: `gemma-4-E2B-it-Q4_0.gguf`, 2,841,481,184 bytes. Audio/vision projector: `mmproj-gemma-4-E2B-it-BF16.gguf`, 986,833,664 bytes. Total **3.83 GB on disk** (3.57 GiB), excluding runtime, caches and datasets. SHA-256 checksums are retained in `tmp/gemma4-omni/manifest.json`.
- Runtime: llama.cpp build 11303, commit `60e9cf7a7`, existing Windows native server. Four inference and batch threads, context 4096, one request at a time, batch 256 / microbatch 128, reasoning off, temperature 0, no GPU or projector offload, no RAM prompt cache.
- Limits: 120 seconds per request; sampled server private/resident memory cap 5.5 GiB. Memory sampled every 100 ms. This is server memory, not whole-app memory.
- Persistent server with local loopback API and temporary authentication. Request timings exclude initial model loading. The server is stopped after each run.
- Vision benchmark: RGB PNG inputs with longest edge at most 1280; maximum 280 image tokens, at most 2048 generated tokens per dataset page. Default-image-budget pilot is retained separately.

The prior 400–500 MB download budget is **not met**. This machine is not the target 8 GB laptop; Electron responsiveness and whole-system memory on that laptop remain untested.

After evaluation, both final model files were verified again against their recorded sizes and SHA-256 hashes. The duplicate ranged-download chunk cache (3,828,314,848 bytes) was removed; the verified models and benchmark records are retained.

## Audio: 120 fixed clips

Same audio bytes, references and seeded selection as the earlier [Tiny benchmark](hinglish-asr.md). Dataset `addyo07/noisy-hinglish-asr`, revision `85cba6bc97ea02b78e23f562e0ccc8f772c94228`, seed 42. Total 531.802 seconds of audio; longest clip 20.993 seconds. Reference text is used only for scoring, never in inference prompts.

| Group | Clips | Gemma raw WER ↓ | Tiny raw WER ↓ | Gemma CER ↓ | Gemma median request |
|---|---:|---:|---:|---:|---:|
| Hinglish label | 40 | 24.93% | 93.91% | 24.21% | 3.82 s |
| Hindi | 20 | 24.52% | 125.29% | 15.84% | 5.16 s |
| English | 20 | 5.44% | 5.73% | 3.42% | 7.58 s |
| Separate noisy Hindi | 20 | 36.43% | 178.01% | 25.41% | 6.10 s |
| Neutral / empty reference | 20 | undefined | undefined | undefined | 4.20 s |

All 120 requests completed without API errors, output truncations or deadlines. Sampled peak server private memory: **1892.58 MiB**; resident: **2717.06 MiB**.

Normalization is identical for both recognizers: NFKC, case folding, punctuation/symbols to spaces, collapsed whitespace. No transliteration, translation, number rewriting or reference corrections. WER is micro-aggregated word edit distance divided by reference word count; insertions can make WER exceed 100%. Script differences contribute to these raw scores.

Both models returned blank on all 10 clips labeled pure silence. Gemma returned nonempty text on **4/10 room-background clips**, compared with Tiny's 3/10. Those clips have empty dataset references but have not been manually listened to for possible background voices, so this is an empty-reference mismatch count, not a confirmed hallucination count. Artificial silence and tone fixtures also returned blank.

Limitations:

- Dataset references were not independently audited. Hinglish labels include English-only clips. The separate noisy Hindi samples may overlap other dataset partitions; no independent held-out claim is made.
- Gemma returns plain text here, without aligned segment timestamps. This measures recognition, not source-seeking or app output. Tiny's earlier timestamp rejection behavior is separate from its raw recognition score.
- Tiny used two CPU threads and a new helper per interval; Gemma used a persistent four-thread server. Their elapsed times are not a controlled runtime speed comparison.
- Long lectures, overlapping speakers, interval boundaries and forced alignment were not tested with Gemma. Official audio input supports up to 30 seconds per clip; long recordings still need segmentation.

Raw outputs: [Gemma audio](gemma4-audio.json), [scores](gemma4-audio-scores.json), [paired Tiny outputs](hinglish-results-20261002-044052.json), [selection manifest](hinglish-manifest.json).

## Vision fixtures and failure checks

Known synthetic fixtures and the student's table slide were tested before the document corpus. These are small checks, not benchmark accuracy estimates.

| Input | Default image budget | 280 image tokens |
|---|---|---|
| Four-line scan | Exact text; 46.08 s | Exact text; 20.59 s |
| Bayes formula | Correct formula plus an extra wrong equation; 56.86 s | Wrong formula only; 21.75 s |
| Heads/tails branching diagram | Correct branches and probabilities; 48.05 s | Labels/probabilities made into a table, losing explicit branches; 23.44 s |
| Speaking-engagement table | All five rows and cell values correct; 112.95 s | All five rows and cell values correct; 32.09 s |
| Blank image | Invented empty HTML table; 6.23 s | Invented empty HTML table; 9.84 s |

The source equation is `P(A|B) = P(B|A)P(A)/P(B)`. The reduced-budget output instead starts with `P(B|A)P(A) = ...`, changing its meaning. The default-budget output also adds an incorrect equation alongside the correct one. Lowering the image token budget improved latency in these fixtures but did not preserve all content reliably. Table output at 280 tokens used Markdown despite the requested HTML.

The default pilot stopped on its first dataset page after 120 seconds; its initial nonstreaming request retained no partial output. The later streaming harness retains partial predictions and continues after a deadline. An eight-image 280-token pilot attempted all inputs, including one page that hit the deadline. These failures are retained, not omitted from the results.

Raw outputs: [default pilot](gemma4-pilot.json), [280-token vision pilot](gemma4-vision-280.json).

## Documents: fixed 50-page comparison

Dataset: `opendatalab/OmniDocBench`, revision `aa1ee96d106dbe53d0ae59474d75c6e6d9b53fec`. English student-material categories, seed 42: 14 book, 10 colorful textbook, 13 slide, 12 exam and 1 note page. The single note page is blank lined paper with printed NO./Date fields; this sample **does not test handwriting quality**. Hindi document OCR is also untested.

Both recognizers receive the same resized images. Tesseract runs through the existing production OCR function in isolated helpers. This is a **raster OCR comparison**, not the complete existing native PDF/PPT extraction pipeline; native table cells are not available to either recognizer here.

Ground truth is held outside inference. Predictions, page IDs, input hashes, partial output, errors and timings are retained. All attempted pages, including incomplete predictions, enter scoring.

The 280-token image configuration was selected after inspecting a pilot containing three pages from this selection. This is a fixed paired comparison, not a fully held-out validation. Benchmark categories cover varied material and do not constitute a single validated course curriculum.

Scores measure this CPU configuration's usable extraction within a 120-second request budget. They are not estimates of unlimited-time transcription quality, higher-image-budget performance or GPU latency. The default-budget fixture pilot also had fidelity failures, but it is too small for a general accuracy estimate.

Official OmniDocBench evaluator source is pinned to commit `f133a71e9e91c3621c7ce8994200a7b394a06eb3`, unchanged. It runs in an isolated Python 3.10.20 environment with frozen dependencies. Configuration uses quick matching, one worker, 60-second quick-match limit, 90-second page-match limit, text/formula/reading-order edit distances and table TEDS. No formula CDM dependencies were installed; therefore **no official overall leaderboard score** is reported. Formula edit distance alone does not establish mathematical equivalence.

### Final document results

| Metric | Tesseract | Gemma, 280 image tokens | Scored denominator |
|---|---:|---:|---|
| Text normalized edit distance ↓ | 0.0948 | 0.4592 | 48 eligible pages; page mean |
| Reading-order edit distance ↓ | 0.1921 | 0.4272 | 48 eligible pages; page mean |
| Formula edit distance ↓ | 0.8245 | 0.5413 | 22 eligible pages; page mean |
| Table TEDS ↑ | 0.0000 | 0.1677 | 5 table records on 4 pages; table mean |
| Table structure-only TEDS ↑ | 0.0000 | 0.2298 | 5 table records on 4 pages; table mean |
| Median extraction request | 1.67 s | 82.25 s | All 50 attempts |
| Inference deadlines | 0/50 | 18/50 | Partial outputs included in scoring |

Edit distance is error on a 0–1 scale; lower is better. TEDS is structural/content similarity on a 0–1 scale; higher is better. These are not interchangeable percentages of correct answers. TEDS values above use the evaluator's `table.all` aggregation; its separate page-mean TEDS for Gemma is 0.2096. The small table denominator limits conclusions about general table quality.

All 50 image IDs and SHA-256 hashes pair exactly between runs. Tesseract completed all requests without errors. Gemma completed 32 requests and retained partial output for 18 deadline errors; no other request errors, server crashes or memory-limit exits occurred. Total extraction request time was **66.24 minutes for Gemma** and **86.89 seconds for Tesseract**. These are observed times from different recognizer protocols: persistent four-thread Gemma versus production Tesseract helpers. They are not a hardware-independent speed ratio.

Gemma cold loading took 13.59 seconds. Sampled server peaks for this document run were **1933.96 MiB private** and **2779.82 MiB resident**. The default-budget pilot's resident peak was higher, **3364.57 MiB**. No combined Electron/system memory or target-laptop responsiveness result is claimed.

| Page category | Pages | Gemma median request | Gemma deadlines | Tesseract median request |
|---|---:|---:|---:|---:|
| Book | 14 | 101.16 s | 7 | 1.88 s |
| Colorful textbook | 10 | 52.30 s | 1 | 1.45 s |
| Slides | 13 | 41.25 s | 0 | 1.14 s |
| Exam | 12 | 120.08 s | 10 | 2.48 s |
| Printed blank note sheet | 1 | 18.98 s | 0 | 0.77 s |

Both official evaluation processes exited successfully and reported zero text matching fallbacks and zero TEDS timeout/error/exception cases. Formula matching nonetheless took **223.33 seconds on one page**, exceeding the configured matching limits for the overall page stage. Those limits should not be treated as a strict wall-clock bound on all formula candidate matching. Evaluator runtime is separate from extraction latency.

Raw results: [Gemma document outputs](gemma4-documents-280.json), [Tesseract outputs](omnidoc-local-baseline.json), [combined summary and evaluator diagnostics](gemma4-omni-summary.json). Full matching artifacts and runtime/dependency records remain under `tmp/omnidoc-eval/{run-name}`.

## Text smoke checks

Three short checks succeeded in their intended semantic behavior: compute 0.25 from two independent fair-coin tosses and cite `[S1]`; decline an entropy question absent from the supplied material; extract the four supplied numerical values without additions. Extracted JSON values were strings, so numeric schemas would still require validation/coercion. These checks do not validate a retrieval pipeline, general tutoring, assessments or a learner model.

## Reproduction

```powershell
node scripts/python.mjs scripts/evaluate-omni.py --setup
node scripts/python.mjs scripts/prepare-omni.py
node scripts/python.mjs scripts/evaluate-omni.py --samples tmp/gemma4-omni/audio-samples.json --tag audio
node scripts/python.mjs scripts/score-omni-audio.py docs/evaluation/gemma4-audio.json
node scripts/python.mjs scripts/evaluate-omni-local.py
node scripts/python.mjs scripts/score-omni-docs.py docs/evaluation/omnidoc-local-baseline.json
node scripts/python.mjs scripts/evaluate-omni.py --samples tmp/gemma4-omni/document-samples.json --tag documents-280 --image-tokens 280 --resume
node scripts/python.mjs scripts/score-omni-docs.py docs/evaluation/gemma4-documents-280.json
node scripts/python.mjs scripts/summarize-omni.py
```

The evaluator additionally requires the pinned OmniDocBench checkout and isolated environment prepared under `tmp/omnidoc-eval`. Dataset/license restrictions apply; benchmark material is retained locally under `tmp`, not bundled with StudyLens. Setup failures and subsequent ranged-download success are preserved in `tmp/gemma4-setup-*.log`.

## Primary documentation

- [Gemma model overview](https://ai.google.dev/gemma/docs/core)
- [Gemma audio capability and input limits](https://ai.google.dev/gemma/docs/capabilities/audio)
- [llama.cpp multimodal support](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md)
- [Pinned model repository](https://huggingface.co/ggml-org/gemma-4-E2B-it-GGUF/tree/b4243c156154b6dca9324415f8c7ccc098b4aed1)
- [OmniDocBench evaluation source](https://github.com/opendatalab/OmniDocBench/tree/f133a71e9e91c3621c7ce8994200a7b394a06eb3)
# Cleanup note

The multimodal trial weights, caches and document evaluation environment were removed at the student's request on October 3, 2026. Historical results remain available in the [cleanup record and evidence archive](ocr-cleanup.md).
