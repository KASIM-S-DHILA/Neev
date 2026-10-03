# StudyLens architecture — Phase 5

This document records Phase 5 foundations and historical API behavior. For the current continuation state, read [CONTEXT_HANDOFF.md](CONTEXT_HANDOFF.md). Later reports cover automatic Groq (no per-upload consent), audio/video processing, frame selection and YouTube captions; their implemented contracts supersede historical descriptions below.

## Process boundaries

```text
React renderer → narrow preload IPC → Electron main → loopback HTTP → Python service
Browser preview → same-origin /api proxy → loopback HTTP → Python service
Python service → SQLAlchemy/aiosqlite → SQLite WAL
Python file operations → worker threads → staging + content-addressed originals
Python service → supervised worker process → durable SQLite jobs → originals + content units
```

The renderer has no Node access, arbitrary filesystem bridge, or service token. Electron owns native open/save dialogs and keeps selected paths behind short-lived file tickets. Imports and original downloads use streams, not whole-file IPC buffers. Python hashes and writes upload chunks in threads. Heavy integrity checking and PDF/text/visual extraction run in a separate process. The renderer requests a bounded source-text unit through a named IPC operation. Electron opens immediately while the service initializes. Actual 8 GB memory/latency measurements remain required.

The service binds only `127.0.0.1` on an available port. Each launch creates an ephemeral bearer token. No cloud credentials are required. The browser preview proxy rejects nonlocal hosts, foreign origins and cross-site requests before adding authorization. Native IPC accepts only the app's main frame and named operations. This is local single-student storage, not a multiuser authentication system.

## Persistence

- Workspaces have a revision and unique case-folded name.
- Subject and topic IDs are scoped to their workspace/subject using composite keys and foreign keys.
- Tab context, drafts and sidebar layout are stored with the normalized curriculum in one transaction.
- Saves compare the submitted base revision with SQLite before modifying rows. A stale revision returns HTTP 409. The client serializes saves, coalesces pending edits and stops retries after a failure.
- Alembic upgrades run under `BEGIN IMMEDIATE`. Migration DDL and revision updates roll back together; destructive downgrade is deliberately unsupported.
- SQLite foreign keys, WAL and a 5-second lock timeout are enabled. Reads that span multiple tables use a consistent transaction snapshot.

## Source storage

An import writes a UUID staging file, calculates SHA-256, flushes/fsyncs it, then links it into `originals/<hash-prefix>/<sha256>`. Source metadata is committed afterward. Student filenames are metadata, never filesystem paths. A blob can be shared by separate source records without duplicating bytes.

Within a subject, reusing a filename selects its existing source. Same bytes under that source reuse the existing version. Changed bytes create a new version; **Add new version** targets a chosen source even when the incoming filename changes. Different filenames imported normally create separate source records. Explicit new versions must retain the material type. Earlier versions are immutable and downloadable, with integrity verified before serving. Extension eligibility is not content validity: corrupt PDFs/recordings will be evaluated during extraction.

File and database writes cannot be one atomic transaction. A crash after finalizing a blob but before committing metadata may leave an unreferenced blob; a killed process may leave staging files. Neither is shown as successful material. The elected worker audits unreferenced files older than one hour and writes `reconciliation.json` with a count and up to 100 paths. Files are retained for review. This age filter excludes recent uploads; the report alone is never authorization to delete a file.

An app-level import manager retains the captured workspace/subject while Materials unmounts or the student switches tabs. One batch streams at a time. Cancelling a batch stops unfinished work while preserving completed versions. Unfinished transfers do not resume after app closure; a saved version and its durable job are the restart boundary.

## Background jobs and ownership

Alembic `0002_background_jobs` adds the job ledger. Registering a new original version and its integrity job uses one database transaction. Identical versions reuse the same job; **Check original** explicitly schedules another check. Startup backfills integrity jobs for Phase 2 originals.

The service supervises a worker child with a stdlib queue loop; it lazily imports the pinned document/image libraries inside its extraction jobs. An OS file lock on `heavy-worker.lock` grants exactly one process execution ownership per data directory, including when two Electron windows launch separate services. Only its owner recovers abandoned running jobs and claims due work in a short `BEGIN IMMEDIATE` transaction. Waiting workers can acquire ownership when the current owner exits. The worker does not receive the service bearer token.

States are queued, running, succeeded, partial, failed and cancelled. Each job stores scope, kind, progress, checkpoint, attempts, failure count, recovery count and result. Partial extraction preserves readable units and flags incomplete or questionable content. Running cancellation is cooperative between bounded chunks/units. Completion checks cancellation atomically; cancelled jobs preserve their checkpoint for explicit Resume. Transient job failures stop after three failures with bounded backoff; missing or damaged originals and unsupported extraction input fail immediately. Explicit Resume resets the failure budget. Checkpoint recovery does not duplicate persisted units. SHA-256 state is not serialized, so an interrupted original check restarts hashing from byte zero.

The supervisor restarts an unexpectedly exited child up to three times, then surfaces an actionable error. Parent-owned stdin pipes trigger service and worker shutdown on parent exit; graceful shutdown is bounded, then the child is killed. SQLite checkpoints remain after a killed worker. Future FFmpeg/model subprocess ownership and cancellation still require evaluation when those processors are added.

`STUDYLENS_QUEUE_EVAL=1` enables an authored slow-unit fixture and its Settings button. Production defaults to disabled, and its API route returns 404. The test is clearly labeled and produces no course content or learner evidence.

## Visual content contract — Phase 5

Alembic `0004_visual_content` adds non-null `metadata_json` with an empty default, preserving existing text/IDs/originals. New image/slide originals and older stored image/slide versions receive extraction jobs. Existing completed PDF units are retained until the student chooses **Process visuals again**. That action checks workspace scope, rejects running/queued jobs, clears this version's derived units and resets the existing job atomically. Originals and other versions stay intact; deterministic unit IDs return when extraction completes. Later indices/learner evidence must invalidate derived evidence on reprocessing, using engine/revision/text hashes rather than unit ID alone.

The worker lazily loads Pillow and PDFium. PDFium calls occur on the worker's main thread only; pages, bitmaps and documents are explicitly closed. Full-page previews preserve diagram/equation appearance; OCR runs on image-like/no-text/suspect PDF pages. Readable text layers remain native text. Scanned text is `suspect`, not verified text. Every scanned/image unit retains OCR language, word boxes, confidence and preprocessing geometry. Confidence is a recognition score, not a correctness probability. Image pages preserve EXIF orientation, alpha on white and bounded resize; multipage TIFF has exact page order. OCR does not infer graph edges or validate mathematics. Hidden OCR and vector diagrams with text may still need manual review.

PPTX is read without unpacking ZIP paths. DefusedXML rejects DTD/entities; package/part/count limits bound expansion. Original slide order comes from the presentation relationships, not filename sorting. Native DrawingML text, picture OCR and original OMML structure are separate. Full slide conversion uses an isolated LibreOffice profile with high macro security; external relationships/macros/embedded objects skip it. Linked resources are never fetched by the extractor. Legacy PPT needs a PPTX/PDF export. Missing converter/render failures retain native text and embedded pictures with warnings. A converted-page count mismatch withholds full previews to avoid wrong citations. Layout/crop/group transforms, fonts, charts, SmartArt, presenter notes and hidden slides need comparison with the original; conversion is not pixel fidelity proof.

Derived preview PNGs are content-addressed under `derived/`, atomically replaced and checked by SHA-256 before the API returns a bounded data URL. The API exposes no filesystem paths. At most four previews per unit and one unit per renderer request keep buffers bounded; original uploads still stream. Preview corruption does not damage the original. Reprocessing repairs a damaged/missing preview. Failed/interrupted processing can leave unreferenced derived/staging artifacts, retained for later cleanup; no automatic deletion occurs.

Native OCR/conversion uses argument lists without a shell, hidden windows, one CPU thread for OCR, bounded output/time and cancellation polling. Windows child job objects impose a separate 512 MiB combined native-helper limit and close the child tree on worker exit. The worker retains its sampled 512 MiB/30-second-step guard; OCR helpers have 20-second deadlines, office conversion 30 seconds. These are separate limits, not a whole-app 512 MiB claim. Child ownership/memory on other operating systems needs additional hardening. OCR pages are bounded to 4 million pixels/2500 pixels per edge; source images to 40 million pixels/100 TIFF pages; slide packages to 5000 entries/100 MiB expanded/10 MiB per read part/500 slides. Live 8 GB measurements remain Phase 19.

Optional vision uses only an explicitly configured local Ollama model at fixed loopback, with bounded image/context/response and an unload request. It is off by default. Notes stay in metadata with `verified=false`; they are never appended to source text. Provider fixtures establish adapter/error behavior, not diagram/formula quality, model memory or cancellation of inference inside an independently running Ollama server. Those remain live quality/resource gates.

Supported native OMML rows, text, fractions and sub/superscripts have a conservative MathML preview in the student UI. It preserves operands and does not evaluate formulas. Unknown or overly deep constructs show an original-comparison message; raw XML stays in stored provenance rather than the student flow.

## PDF/text base contract — Phase 4

Alembic `0003_content_units` preserves prior data and adds version-bound content units. Every new PDF/TXT/Markdown original queues an `extract_source` job in the same transaction as its version. Startup backfills older supported originals. Extraction requires a completed integrity job, rechecks SHA-256 before parsing, and never modifies original bytes. Other media types have only integrity jobs until their own ingestion milestones.

One PDF physical page is one content unit, including empty and unreadable pages. Locators use 1-based physical page numbers, with dimensions and rotation; printed page labels can differ. Text units contain at most 4,000 decoded characters, preserve original line endings, and retain 1-based line spans plus zero-based, half-open Unicode character offsets. UTF-8/BOM and BOM-marked UTF-16 are supported without guessing legacy encodings. Deterministic UUIDs bind each unit to its original version and ordinal; text hashes record extracted bytes. Each unit and the completed-unit checkpoint commit atomically. Completed units survive cancellation/restart; old versions retain separate IDs and text.

Unit statuses are `text`, `needs_ocr`, `empty`, `unreadable`, `too_large`, and `suspect`. Image references are inspected without decoding image buffers. Little text plus images is a scan heuristic, not proof; logos and title pages can be false positives. Text plus images is retained with a visual-content warning. Blank/vector-only pages preserve their physical location and a no-text warning. Partial results do not invent OCR, equation, table or diagram content. The UI says **Text extracted**, rather than claiming complete semantic fidelity.

Limits: PDF 64 MiB/500 pages, text 16 MiB, uncompressed page content 1 MiB and extracted page text 50,000 characters. Pypdf decompression/tree/form limits are also configured. A watchdog samples worker private memory on Windows (resident memory on Linux), enforces a 512 MiB sampled budget and a 30-second step timeout, and gives an uncooperative parser one second to honour cancellation. It commits a failure/cancel/pause state before recycling the worker with exit code 75. The supervisor replaces intentional recycles without consuming its crash budget. These sampled safeguards are not an OS hard memory reservation; platform/machine benchmarks remain required. Platforms without a memory reader retain timeout/cancellation protection only.

The bounded content endpoint is an inspection API, not retrieval. Future indexing must require original integrity, a terminal succeeded/partial extraction, and eligible `text` units; all source warnings/coverage gaps must remain visible. Reading-order, font-map and existing OCR errors can escape heuristic checks. Source grounding quality requires the later gold retrieval/generation benchmark. Uploaded text is displayed as escaped React text, not executed or rendered as HTML.

## API surface

### Selective cloud vision extension

`GET /vision` exposes only capability and model ID. `POST /workspaces/{id}/source-versions/{version_id}/cloud-visuals` requires literal `{consent:true}` and optionally a 1-based `ordinal` to override local selection for that location. A durable `cloud_visuals` job starts only after terminal local extraction; competing local rebuilds/cloud jobs are rejected transactionally. Import/backfill never creates cloud jobs. The narrow Electron bridge exposes these two operations without URLs or credentials supplied by the renderer.

The worker rehashes the original, inspects one stored unit at a time, checks bounded preview hashes, routes locally with Pillow/Tesseract metadata, and requests one image from the fixed Groq HTTPS endpoint. JSON-mode responses pass strict local field/shape checks and duplicate-table checks before being saved to `metadata.cloud_visuals`. Native PPTX tables live in `metadata.native_tables`, with literal cells and merged-cell notes. Model content never replaces `content_units.text` or changes its hash/status. Results carry source version, unit, locator, original preview/sent-image hashes, preview bounds, image dimensions, model and prompt revision; all cloud results remain unverified.

Per-directory request spacing and provider rate headers create a `Deferred` scheduling signal. The worker requeues using `available_at`, retaining quota counters and a tiny atomic budget file instead of sleeping. Other local jobs remain claimable. Async HTTP transfer runs in the worker with cancellation polling, bounded time/response and no redirects. The existing parser guard applies. Cache reuse is per version/unit; successful per-image commits survive restart. Rebuilding local units invalidates outputs and consent jobs. A transfer interrupted before commit can be repeated; provider processing already started cannot be recalled. The [independent evaluation](evaluation/phase-05-cloud-vision.md) documents live evidence, fixture limits and pending student checks.

All routes require local authorization. Paths below exclude the browser's `/api` prefix.

| Operation  | Route                                                                        | Contract                                                                    |
| ---------- | ---------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Health     | `GET /health`                                                                | SQLite/WAL and Alembic revision                                             |
| Workspaces | `GET/POST /workspaces`                                                       | List or create `{name}`                                                     |
| Session    | `GET/PUT /workspaces/{id}/session`                                           | Save `{base_revision, session}`, return new revision                        |
| Materials  | `GET /workspaces/{id}/subjects/{id}/sources`                                 | Sources with newest-first versions                                          |
| Import     | `POST /workspaces/{id}/subjects/{id}/sources?filename=...&source_id=...`     | Raw streamed body; optional explicit source; duplicate/version IDs returned |
| Original   | `GET /source-versions/{id}/file`                                             | Unchanged attachment after integrity check                                  |
| Storage    | `GET /storage`                                                               | Data paths and per-file limit                                               |
| Queue      | `GET /queue`                                                                 | Worker availability, one-heavy-job limit and evaluation mode                |
| Jobs       | `GET /workspaces/{id}/jobs`                                                  | Latest scoped jobs, optional subject and bounded limit                      |
| Job        | `GET /workspaces/{id}/jobs/{job_id}`                                         | One scoped job including progress/checkpoint                                |
| Cancel     | `POST /workspaces/{id}/jobs/{job_id}/cancel`                                 | Immediate queued cancellation or cooperative running cancellation           |
| Resume     | `POST /workspaces/{id}/jobs/{job_id}/retry`                                  | Requeue failed/cancelled/partial work with its checkpoint                   |
| Recheck    | `POST /workspaces/{id}/source-versions/{version_id}/verify`                  | Queue an original integrity check                                           |
| Fixture    | `POST /workspaces/{id}/queue-test`                                           | Explicit evaluation mode only; bounded slow-unit fixture                    |
| Content    | `GET /workspaces/{id}/source-versions/{version_id}/content?offset=0&limit=1` | Scoped, ordered units with exact locators; at most 10 per response          |
| Stop       | `POST /shutdown`                                                             | Launcher-owned service shutdown                                             |

## Limits and next contract

### Phase 6 audio contract

Audio originals join the existing `extract_source` queue and backfill on startup. FFprobe supplies a bounded duration/first audio stream; FFmpeg decodes 30-second windows into mono 16 kHz PCM. A separate offline faster-whisper Tiny CPU int8 helper transcribes each nonsilent window with VAD. No full-length decoded buffer or speech model is loaded in the API/renderer/parent worker. All transcripts remain `suspect` and require listening/comparison. Each content unit records a `kind=time` locator, absolute segment times, model/settings fingerprint, audio levels and a hashed playback asset. Preview paths are validated and removed before the one-unit API response; the renderer receives only bounded audio data. Its media policy allows local/data playback.

PCM previews, transcript units and checkpoints are saved before the next interval; the database unit/checkpoint transaction is atomic. Cancel/restart keeps saved intervals; an interrupted helper is killed through the shared native boundary. Resuming with changed speech settings/model fails with a reprocess instruction. Windows speech helpers have a 1536 MiB child-job cap and 25-second deadline; other native helpers retain 512 MiB. The parent retains its sampled 512 MiB/30-second-step guard. Only one heavy queue job is active; helper exit releases speech memory. These caps do not establish whole-app 8 GB performance.

`GET /audio` exposes setup booleans only. `POST /workspaces/{id}/source-versions/{version_id}/process-audio` atomically clears prior derived units and requeues this version, rejecting another workspace, non-audio source or active job. `Resume` retains the checkpoint. Explicit `audio:setup` downloads the pinned Tiny model; app import never downloads or uploads audio. See [Phase 6 evidence](evaluation/phase-06.md) for measurements and limitations.

Maximum 2 GB per file, 32 selections per batch, 12 study tabs, 100 subjects per workspace, 300 topics per subject, 20,000 characters per draft, and 1 MB for a serialized session. These are guardrails, not throughput claims. Lists are currently appropriate for small course collections; pagination/virtualization must precede large-library support.

The background drawer polls at 1.2-second intervals and shows the latest 50 workspace jobs. Original metadata state remains `stored`; integrity and extraction are separate job results. The Materials viewer requests one unit at a time. No cited tutor answer, assessment or learner-model evidence is implied by a successful import or extraction. Phase 5 now adds the visual contract described above.
