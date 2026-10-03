# Archived ingestion scripts — not runnable from this repo

These evaluation runners were **not runnable from this repository** at the time
of the B1 cleanup. Their third-party dependencies were never present in
`services/requirements-lock.txt`, and the models/datasets they need are not
vendored here. They are retained as a record of what was measured.

**Do not try to run these from a clean checkout.** To reproduce one you would
have to recreate its isolated environment yourself (see `../README.md`).

Moved from `scripts/` in B1. Nothing in the application, test suite, or
`package.json` references them.

| Script | Missing dependencies | Retained evidence |
| --- | --- | --- |
| `evaluate-hinglish.py` | `pyarrow` | `../hinglish-asr.md`, `../hinglish-results-*.json` |
| `report-hinglish.py` | `pyarrow` (imports the above) | `../hinglish-summary.json` |
| `score-omni-audio.py` | `pyarrow` (imports the above) | `../gemma4-audio-scores.json` |
| `evaluate-lighton.py` | `psutil` | `../lighton-ocr.md`, `../lighton-*.json` |
| `evaluate-llamaindex-docs.py` | `llama_index` | `../llamaindex-docs-pilot.md`, `../llamaindex-docs-pilot.json` |
| `evaluate-small-ocr.py` | `easyocr`, `onnxtr`, `rapidocr`, `torch`, `transformers`, `psutil` | `../small-ocr.md`, `../small-ocr-results.json` |

`evaluate-llamaindex-docs.py` is archived deliberately. It was **not** moved to
the top-level `evaluation/` directory: that directory is reserved for the Track
D benchmark and is not a home for archived pilots.

Path note: these files still compute `ROOT = Path(__file__).resolve().parents[1]`,
which was correct when they lived in `scripts/`. From this directory that
resolves one level too shallow. They are archived and not runnable, so this was
not "fixed" — it is noted here instead of silently left to surprise a reader.