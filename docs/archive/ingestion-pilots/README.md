# Archived ingestion pilots — index

Historical material from the Phases 1–7 ingestion work: acceptance reports,
raw evaluation results, screenshots and run logs. Moved here from
`docs/evaluation/` in the B1 cleanup.

**These files are evidence of what was measured at the time. They are not
current documentation and they are not a specification of current behaviour.**
Nothing here is referenced by application code. Retained deliberately; do not
delete.

For current behaviour read [`docs/ARCHITECTURE.md`](../../ARCHITECTURE.md).
For the evidence-based audit read
[`docs/audit/CURRENT_ARCHITECTURE.md`](../../audit/CURRENT_ARCHITECTURE.md).

## What superseded this

| Area | Superseded by |
| --- | --- |
| Phase 1–7 acceptance narratives (`phase-*.md`) | [`docs/ARCHITECTURE.md`](../../ARCHITECTURE.md) sections 2–7, written from code |
| Data/cloud-boundary claims | [`docs/PRIVACY_AND_DATA_FLOW.md`](../../PRIVACY_AND_DATA_FLOW.md) |
| Rationale for choices these reports describe | [`docs/DECISIONS.md`](../../DECISIONS.md) |
| Standalone OCR/multimodal benchmarks (Gemma4, Hunyuan, LightOn, OmniDoc, SmolDocling) | Stopped. See `ocr-cleanup.md`; dependencies were never in `services/requirements-lock.txt` |
| LlamaIndex documentation pilot | Stopped. `llamaindex-docs-pilot.md`; runner archived, see `scripts/README.md` |

## Phase acceptance reports

| File | What it showed | Superseded by |
| --- | --- | --- |
| `phase-01.md` | Workspace shell, tabs, session restore | ARCHITECTURE.md §2 |
| `phase-02.md` | PDF/text extraction, Materials view | ARCHITECTURE.md §4, §5 |
| `phase-03.md` | Source versions, originals, previews | ARCHITECTURE.md §4 |
| `phase-04.md` | OCR, corrupt/encrypted/authored fixtures | ARCHITECTURE.md §5 |
| `phase-05.md` | Selective local→cloud vision routing, native tables | ARCHITECTURE.md §5; PRIVACY_AND_DATA_FLOW.md |
| `phase-05-cloud-vision.md` | Automatic Groq queueing after local extraction, consent-free upload | PRIVACY_AND_DATA_FLOW.md; DECISIONS.md |
| `phase-06.md` | Local faster-whisper Tiny audio pipeline | ARCHITECTURE.md §7 |
| `phase-06-cloud-audio.md` | Groq ASR with local fallback, quota deferral | PRIVACY_AND_DATA_FLOW.md |
| `phase-07a.md` | Video audio, container offsets, restart/cancel | ARCHITECTURE.md §5, §7 |
| `phase-07b.md` | Independent frame selection (PySceneDetect + pixel diff) | ARCHITECTURE.md §5, §7 |
| `phase-07c.md` | Durable frame-visual job, selective Groq on frames | ARCHITECTURE.md §5; PRIVACY_AND_DATA_FLOW.md |
| `phase-07d-youtube.md` | Caption import with immutable snapshots | ARCHITECTURE.md §5 |
| `phase-07d-media.md` | Attaching a local video version to a YouTube source | ARCHITECTURE.md §5 |

## OCR / multimodal pilots (all stopped)

Not part of application ingestion. Their dependencies were never pinned in
`services/requirements-lock.txt`, so they cannot run from this repository.

| File | What it showed | Superseded by |
| --- | --- | --- |
| `ocr-cleanup.md` / `ocr-cleanup.json` | Removal decision for alternative OCR/multimodal benchmarks | Nothing; decision applied |
| `retired-ocr-evidence.zip` | Raw retained OCR benchmark evidence | Nothing; archive only |
| `small-ocr.md` / `small-ocr-matrix.md` / `small-ocr-results.json` | Required model storage, CPU latency, memory, recognition output | Nothing; stopped |
| `hunyuan-local.md` / `hunyuan-local-results.json` | HunyuanOCR 1.5 local llama.cpp trial | Nothing; stopped |
| `lighton-ocr.md`, `lighton-*.json` | LightOn OCR via local Ollama | Nothing; stopped |
| `gemma4-*.json`, `gemma4-omni.md`, `gemma4-omni-summary.json` | Gemma4 audio/vision/document pilots and scores | Nothing; stopped |
| `omnidoc-local-baseline.json` | OmniDoc local baseline | Nothing; stopped |
| `groq-vision.md`, `groq-vision-*.json`, `groq-format-fallback-*.json` | Early Groq vision pilot and format failures | ARCHITECTURE.md §5; production router is `cloud_vision.py` |
| `vision-routing-results.json`, `desktop-routing-results.json` | Prototype routing over retired PP-OCR output | `cloud_vision.route` + Tesseract |
| `native-table-deck.json` | Native PPTX table extraction evidence | ARCHITECTURE.md §5 |
| `llamaindex-docs-pilot.md` / `llamaindex-docs-pilot.json` | LlamaIndex BM25 over Neev documentation | Nothing; stopped, runner archived |

## Remaining raw results

Timestamped `*.json` files are raw machine-readable evaluator output from the
runs named in the phase reports above. `audio-*`, `cloud-audio-*`,
`audio-integration-*`, `video-integration-*`, `video-frames-*`,
`video-visuals-*`, `youtube-*`, `hinglish-*`, `lighton-*`, `gemma4-*`,
`desktop-*` and the `-desktop.json` UI-probe files.

Fixtures are **not** here. Regression fixtures moved to
[`tests/fixtures/ingestion/`](../../../tests/fixtures/ingestion/README.md),
because tests and smoke run them.