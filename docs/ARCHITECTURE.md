# Neev — architecture

Written from the code at commit `24e82f7` (Phase A cleanup branch
`cleanup/architecture-reset`). This document replaces the older
`docs/architecture.md`, which described Phase 5 behaviour and had drifted from
the implementation.

Evidence, method and the unknowns are recorded in
[`docs/audit/CURRENT_ARCHITECTURE.md`](audit/CURRENT_ARCHITECTURE.md). Where the
two disagree, the audit report is the record of what was measured; this document
is the summary you should work from.

- Data leaving the machine: [`PRIVACY_AND_DATA_FLOW.md`](PRIVACY_AND_DATA_FLOW.md)
- Why things are the way they are: [`DECISIONS.md`](DECISIONS.md)

## 1. What this is

A single-student desktop workspace. Material is imported into a local database,
extracted on-device, optionally enriched by a cloud provider, and reviewed in
the app. Grounded answers, tutoring, assessment and learner modelling are **not
implemented** — see §9.

## 2. Process boundaries

```text
React renderer (src/main.tsx, App.tsx, storage/*, media review components)
  -> window.studyLens preload (electron/preload.cjs)
  -> Electron main/storage/media (electron/*.cjs)
  -> ephemeral-token authenticated HTTP at 127.0.0.1:<random port>
  -> FastAPI create_app (services/studylens_service/api.py)
       -> SQLAlchemy + aiosqlite -> studylens.sqlite3 (WAL)
       -> threaded hashing/file I/O -> staging/ + originals/<prefix>/<sha256>
       -> WorkerSupervisor -> separate OS-locked Worker process
            -> SQLite jobs/content_units + derived previews/caches
            -> Tesseract / LibreOffice / FFmpeg / FFprobe helper processes
            -> Python ASR/VAD/frame-analysis/YouTube helper processes
            -> configured Groq and optional loopback Ollama adapters
```

Also:

- **Development browser** → Vite same-origin `/api` proxy → the same local service.
- **YouTube "Watch here"** → `youtube-nocookie` iframe, loaded on click.
- **YouTube browser fallback** → canonical watch URL via `shell.openExternal`.
- **Evaluation scripts** → isolated `tmp/` data, local servers, and optional
  provider/dataset downloads. Not renderer features; see
  [`scripts/ingestion-evals/`](../scripts/ingestion-evals/README.md).

The renderer has no Node access, no arbitrary filesystem bridge, and no service
token. The service binds only `127.0.0.1` on an available port with a fresh
ephemeral bearer token (minimum 24 characters, enforced in `create_app`). This is
local single-student storage, not a multi-user authentication system.

## 3. Repository layout

| Path | Contents |
| --- | --- |
| `src/` | React renderer, typed storage client, hooks |
| `electron/` | Main process, preload bridge, backend client, media |
| `services/studylens_service/` | Python service — flat modules plus B4 interface scaffolds (§9) |
| `services/tests/` | Python test suite (188 collected; 174 pass, 14 skipped) |
| `tests/` | JavaScript test suite (25 tests across 7 files, §10) |
| `tests/fixtures/ingestion/` | Authored ingestion fixtures used by tests and smoke |
| `scripts/` | Build/dev/smoke entry points |
| `scripts/lint-docs.mjs` | Documentation lint, run by `npm run check` |
| `scripts/report-counts.mjs` | Measures every count quoted in the docs |
| `scripts/ingestion-evals/` | Runnable standalone ingestion evaluators |
| `docs/` | This document, audit, privacy, decisions, archive |
| `evaluation/` | **Reserved** for the Track D benchmark; interfaces only (§9) |

## 4. Storage and persistence

Ten tables, Alembic head `0005_youtube_media_links`:

`workspaces`, `workspace_sessions`, `subjects`, `topics`, `sources`,
`source_versions`, `content_units`, `jobs`, `youtube_media_links`,
`alembic_version`.

- An import writes a UUID staging file, computes SHA-256, fsyncs, then links it
  into `originals/<hash-prefix>/<sha256>`. Source metadata commits afterwards.
- Student filenames are metadata, never filesystem paths. One blob can be shared
  by several source records without duplicating bytes.
- SQLite foreign keys, WAL and a 5-second lock timeout are enabled. Alembic
  upgrades run under `BEGIN IMMEDIATE`; destructive downgrade is deliberately
  unsupported.
- Session saves compare the submitted `base_revision` against SQLite before
  writing. A stale revision returns HTTP 409. The client serialises saves,
  coalesces pending edits, and stops retrying after a failure.
- File writes and database writes cannot be one atomic transaction. A crash
  after finalising a blob but before committing metadata can leave an
  unreferenced blob; a killed process can leave staging files. Neither is
  reported as success.

## 5. API

31 route objects / 32 method-path pairs. Every route requires the local bearer
token; the browser proxy additionally rejects non-local hosts, foreign origins
and cross-site requests. Paths exclude the browser's `/api` prefix.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | SQLite/WAL journal mode, Alembic revision, worker status |
| GET | `/queue` | Worker availability, restarts, one-heavy-job limit |
| GET | `/vision` | Cloud vision capability and model ID |
| GET | `/audio` | FFmpeg/FFprobe/speech-model/cloud capability |
| GET | `/storage` | Data paths and per-file limit |
| POST | `/shutdown` | Launcher-owned shutdown |
| GET/POST | `/workspaces` | List or create |
| GET/PUT | `/workspaces/{id}/session` | Load/save with `base_revision` |
| GET/POST | `/workspaces/{id}/subjects/{sid}/sources` | Sources; streamed import |
| POST | `/workspaces/{id}/subjects/{sid}/youtube` | YouTube caption import |
| GET | `/source-versions/{id}/file` | Original after integrity check |
| GET/HEAD | `/workspaces/{id}/source-versions/{id}/playback` | Video playback |
| GET | `/workspaces/{id}/source-versions/{id}/content` | Bounded ordered units |
| GET | `/workspaces/{id}/source-versions/{id}/video-frames` | Paged frame viewer |
| GET/POST/DELETE | `/workspaces/{id}/source-versions/{id}/local-media` | YouTube media association |
| POST | `/workspaces/{id}/source-versions/{id}/verify` | Queue integrity check |
| POST | `/workspaces/{id}/source-versions/{id}/process-audio` | Queue audio extraction |
| POST | `/workspaces/{id}/source-versions/{id}/process-video-frames` | Queue frame selection |
| POST | `/workspaces/{id}/source-versions/{id}/process-frame-visuals` | Queue frame text |
| POST | `/workspaces/{id}/source-versions/{id}/process-visuals` | Queue visual reprocessing |
| POST | `/workspaces/{id}/source-versions/{id}/cloud-visuals` | Queue cloud vision |
| GET | `/workspaces/{id}/jobs`, `/jobs/{jid}` | Job list / one job |
| POST | `/workspaces/{id}/jobs/{jid}/cancel`, `/retry` | Cancel / requeue |

| POST | `/workspaces/{id}/queue-test` | Bounded fixture, evaluation mode only |

`GET /workspaces/{id}/source-versions/{id}/content` is an **inspection API, not
retrieval**. It returns scoped, ordered units with exact locators, at most 10 per
response, including units whose status is `needs_ocr`, `suspect`, `unreadable`,
`too_large` or `empty`. Do not treat it as a grounded-answer corpus.

## 6. Jobs

Job state is `queued`/`running`/`succeeded`/`partial`/`failed`/`cancelled`. Only
one heavy job runs at a time; the worker holds an OS-level lock. Cancel is
immediate when queued and cooperative while running. Retry requeues
failed/cancelled/partial work with its checkpoint.

Content-unit status is `text`/`needs_ocr`/`empty`/`unreadable`/`too_large`/`suspect`.

| Job | Automatic queueing | Disable with |
| --- | --- | --- |
| `extract_source` | on import | — |
| `cloud_visuals` | after terminal local extraction | `STUDYLENS_AUTO_GROQ_VISION=0` |
| audio (Groq or local) | on detected speech | `STUDYLENS_AUTO_GROQ_AUDIO=0` |
| `video_frames` | new and previously saved videos | `STUDYLENS_AUTO_VIDEO_FRAMES=0` |
| `video_frame_visuals` | after frame selection | `STUDYLENS_AUTO_VIDEO_VISUALS=0` |
| `youtube_import` | no — explicit action | — |

Resource guards: the worker samples a 512 MiB / 30-second-step budget; the
Windows ASR helper has a 1536 MiB child-job cap and a 25-second deadline; other
native helpers keep 512 MiB. These are **not** whole-app 8 GB budgets, and
external Ollama plus non-Windows helper memory sit outside them.

## 7. Extraction

- **Documents** — `pypdf`/`pypdfium2` for text; Tesseract for OCR; LibreOffice
  for full slide previews when installed. OCR language data must match the source.
- **Visual routing** — `cloud_vision.route` sends only difficult units to Groq;
  ordinary readable content stays local. A rebuilt local unit invalidates prior
  cloud results and consent jobs.
- **Audio/video** — FFprobe for duration and stream info; FFmpeg decodes
  30-second windows to mono 16 kHz PCM; a separate offline faster-whisper Tiny
  CPU int8 helper transcribes with VAD. No full-length decoded buffer and no
  speech model in the API, renderer, or parent worker.
- **Video frames** — FFmpeg samples source PTS in bounded 30-second windows;
  PySceneDetect and pixel change detect slide/whiteboard updates; adjacent
  duplicates are suppressed. Up to 600 frames, at most 20 retained per window.
- **YouTube** — caption tracks for the selected language, stored as immutable
  JSON snapshots. Refreshes create a version only when the snapshot changes.

Every automatic transcript is marked `suspect` and requires listening. Model
output never replaces `content_units.text` or changes its hash/status.

## 8. Electron IPC

`electron/preload.cjs` exposes a narrow, named-operation bridge. The renderer
supplies no URLs or credentials. Native IPC accepts only the app's main frame.
Chosen file paths stay behind short-lived file tickets; imports and downloads use
streams rather than whole-file buffers.
| POST | `/workspaces/{id}/queue-test` | Bounded fixture, evaluation mode only |

`GET /workspaces/{id}/source-versions/{id}/content` is an **inspection API, not
retrieval**. It returns scoped, ordered units with exact locators, at most 10 per
response, including units whose status is `needs_ocr`, `suspect`, `unreadable`,
`too_large` or `empty`. Do not treat it as a grounded-answer corpus.

## 9. Known gaps

Stated plainly so they are not mistaken for oversights:

- **The Python package is still flat in behaviour.** B4 scaffolded
  `knowledge/`, `grounding/`, `tutor/`, `assessment/`, `learner/`, `providers/`
  and a top-level `evaluation/` package, but they contain **interfaces only** —
  every entry point raises `NotImplementedError` and nothing in the application
  imports them. `database.py` still mixes CRUD, jobs and presentation;
  `schema.py` still mixes database and API concerns.
- **Not implemented:** retrieval, grounded answers and citations, tutoring,
  assessment, learner modelling, and scored evaluation.
- **Provenance is partial.** Immutable versions, hashes and locators exist.
  There are no external-web or generated-content tables.
- **Consent.** A one-time disclosure is shown at first run and permanently in
  Settings; automatic Groq vision and speech are **not** gated per upload. Cloud
  vision retains a `consent` flag on the job payload; audio does not use a
  consent flow. See
  [`PRIVACY_AND_DATA_FLOW.md`](PRIVACY_AND_DATA_FLOW.md).
- **Providers are inlined.** Groq/Ollama/YouTube clients are embedded in the
  modules that use them; there is no shared provider interface or prompt
  registry. Ollama results do not record a prompt revision.
- **No search, no telemetry client, no voice tutor.**
- **No installer build.** `package.json` has no packaging step.
- **Not verified:** whole-app 8 GB performance, live provider quotas and
  retention, YouTube policy/access, migration history on production data, and
  student acceptance.

## 10. Tests and gates

| Gate | Command | Count |
| --- | --- | --- |
| Python service | `npm.cmd run api:test` | 188 collected: 174 pass, 14 skipped (scaffold placeholders) |
| Docs lint | `npm.cmd run lint:docs` | section numbering, links, empty sections, truncation |
| JavaScript + build | `npm.cmd run check` | 25 tests + `tsc --noEmit` + `vite build` |
| Desktop smoke | `npm.cmd run smoke:desktop` | hidden Electron window, isolated data dir |

Every count in this section is measured, not remembered. Re-derive them with:

```sh
node scripts/report-counts.mjs
```

It runs the Python discovery, instantiates the app to enumerate routes, and
counts tests per file. If a number here disagrees with that output, this
document is wrong.

JavaScript tests per file (`node --test tests/<file>`), 25 total:

| File | Tests | Covers |
| --- | --- | --- |
| `tests/imports.test.ts` | 3 | import scope, cancel, partial failure |
| `tests/jobpanel.test.ts` | 3 | job status labels, badge, timing display |
| `tests/session.test.ts` | 7 | tabs, drafts, restore validation, tab cap |
| `tests/storage.test.ts` | 3 | `describeStorage` derives WAL from `/health` |
| `tests/disclosure.test.ts` | 4 | one-time cloud disclosure and show-once rule |
| `tests/writer.test.ts` | 3 | serialisation, coalescing, retry, conflict |
| `tests/youtube.test.ts` | 2 | URL guard, browser + IPC scope |

`tests/storage.test.ts` was added in B1b with 3 tests, not 4. The earlier
work report said 4; the file was correct and the report was not.

The 14 skips are the B4 scaffold placeholders. Each names its milestone
(`not implemented: knowledge index`, `grounding`, `tutor`, `assessment`,
`learner`, `providers`, `track D benchmark`). They are intentional: they mark the
test surface without asserting nothing and passing. One real test in that group
verifies every scaffold package imports and exposes its contracts.

Focused subsets exist as `queue:test`, `ingest:test`, `visual:test`,
`vision:test`, `audio:test`, `audio:cloud:test`, `video:test`,
`video:frames:test`, `video:visuals:test`, `youtube:test`, `youtube:media:test`.

The smoke test asserts renderer startup, Node isolation, the restricted bridge,
`journal_mode == "wal"`, migration head `0005_youtube_media_links`, one
supervised worker, and persisted session. It writes its screenshot to
`tmp/smoke-screenshots/` (ignored).

Cloud and many ASR outputs are mocked; native decoding/OCR/frame tests run real
tools. There is no live quality measurement and no coverage percentage.
