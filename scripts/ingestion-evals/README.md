# scripts/ingestion-evals

Runnable evaluation and benchmarking harnesses for the ingestion pipeline
(documents, audio, video, frames, YouTube, cloud vision).

Moved here from `scripts/` in the B1 cleanup so that build/dev entry points stay
at the top of `scripts/`. All of these are **standalone runners, not product
code**: they are not imported by the application, the test suite, or
`npm run check`.

## Running

Run from the repository root with the project Python:

```powershell
node scripts/python.mjs scripts/ingestion-evals/evaluate-video.py --help
```

Each script computes `ROOT` as `Path(__file__).resolve().parents[2]`, which is
the repository root from this directory. They read fixtures from
`tests/fixtures/ingestion/` and write results to `tmp/`.

Several call `studylens_service.Worker` and the internal database directly
rather than going through the HTTP API. That is a known deviation from the
public-interface-only target; see
[`docs/audit/CURRENT_ARCHITECTURE.md`](../../docs/audit/CURRENT_ARCHITECTURE.md)
section 12.

## Groups

| Prefix | Purpose |
| --- | --- |
| `evaluate-*.py` | Real pipeline evaluations against the local service and worker |
| `evaluate-*.cjs` | The same, driven through a hidden Electron window |
| `benchmark-*.py` | Stage timing for the local pipeline |
| `create-*-fixtures.py` | Fixture generators (see `tests/fixtures/ingestion/README.md`) |
| `prepare-*.py`, `summarize-*.py`, `report-*.py`, `score-*.py` | Result preparation and markdown reporting |

Some scripts reach external providers or download pinned models/datasets
(`evaluate-hunyuan.py`, `evaluate-omni*.py`, `prepare-omni.py`). Those transfers
happen only when you explicitly run them. See
[`docs/PRIVACY_AND_DATA_FLOW.md`](../../docs/PRIVACY_AND_DATA_FLOW.md).

## Not here

Stopped OCR/multimodal pilots and the LlamaIndex runner were archived, because
their dependencies were never in `services/requirements-lock.txt`. See
[`docs/archive/ingestion-pilots/scripts/`](../../docs/archive/ingestion-pilots/scripts/README.md).