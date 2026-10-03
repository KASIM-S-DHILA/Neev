# Ingestion test fixtures

Authored inputs used by the Python test suite (`services/tests/`), the Electron
smoke test, and the ingestion evaluators in `scripts/ingestion-evals/`.

These live here, not in `docs/`, because they are test inputs rather than
documentation. They were moved from `docs/evaluation/fixtures/` in the B1
cleanup; every reference was updated in the same commit.

| Directory | Contents | Used by |
| --- | --- | --- |
| *(root)* | `phase-02-notes.txt`, `phase-02-notes-v2.txt` — authored plain-text notes, UTF-16 and mixed encoding | `test_extraction.py` |
| `phase-04/` | PDF fixtures: digital, corrupt, encrypted, mixed-language, plus `gold.json` and `generate.py` | `test_extraction.py`, `test_storage.py`, `electron/main.cjs` smoke |
| `phase-05/` | Visual fixtures: scan, equation, figure, blank, oriented, corrupt; slides/PDF/PPTX; `gold.json`, `generate.py` | `test_visual.py`, `test_automatic_vision.py`, smoke |
| `phase-06/` | Audio fixtures (clean, noisy, silence, tone, hinge words) with `gold.json` | `test_audio.py`, `test_cloud_audio.py` |
| `phase-07/` | Video fixtures and metadata | `test_video.py`, `evaluate-video.py` |
| `phase-07b/` | Video and slides fixtures including `slides.mp4` | `test_video_frames.py`, `test_video_frame_visuals.py`, `evaluate-youtube-media-desktop.cjs` |
| `pilot/` | Copied real provider output (not authored) | `test_cloud_vision.py` |

## `pilot/` is a copy, not a move

`pilot/groq-vision-results.json` is a **real Groq vision result** from the
original pilot, kept because `test_cloud_vision.py` needs a genuine malformed
partial to prove duplicate rejection. It is byte-identical to
`docs/archive/ingestion-pilots/groq-vision-results.json`
(SHA256 `cb340cd7a2f17…c15c27f`) and stays in the archive too, because the archive
index cites it as evidence.

Do not regenerate or edit it. `test_pilot_fixture_is_present_and_matches_the_retained_original`
asserts the hash, so any edit fails loudly.

**No test may read from `docs/archive/`.** That directory may be reorganised;
the suite must not depend on documentation layout. This already broke once —
B1 moved the pilot file out from under `test_cloud_vision.py`. Two guard tests in
`services/tests/test_benchmark_scaffold.py` enforce both rules.

## Regenerating

`generate.py` in `phase-04/` and `phase-05/` rebuilds the authored fixtures.
They are self-relative (`ROOT = Path(__file__).resolve().parent`), so they can be
run from anywhere:

```powershell
.\.venv\Scripts\python.exe tests\fixtures\ingestion\phase-04\generate.py
```

Regeneration needs the document Python runtime (ReportLab, python-pptx) and
overwrites committed binaries. Review the diff before committing.