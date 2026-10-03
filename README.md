# Neev

A student-only Electron desktop application. The visual reference is the four-page UX Pilot PDF supplied on September 30, 2026 (`C:\Users\User\Downloads\uxpilot-export-09-30-26.pdf`). Do not use Stitch assets as the implementation baseline.

Neev (नींव, foundation) is the chosen product name, formerly StudyLens. The existing `%APPDATA%\StudyLens` profile and data store, `STUDYLENS_*` configuration, IPC keys and media scheme are preserved for compatibility; saved work needs no migration. Historical reports retain their original name.

## Local service setup

Requires Node.js 24 and Python 3.12. The Python interpreter used by the app is the project `.venv`; you can override it with `STUDYLENS_PYTHON`.

PowerShell, from this directory:

```powershell
py -3.12 -m venv .venv
npm.cmd ci
npm.cmd run api:install
```

The Python dependencies are pinned in `services/requirements-lock.txt`. The development environment in this workspace is already installed. Packaging Python into an installer is Phase 19.

## Run

On Windows, double-click `Neev.lnk` in the project folder to open the native Electron app using the built interface. The older `StudyLens.lnk` also launches this checkout. Rebuild with `npm.cmd run build` after interface changes. The shortcut uses this checkout's Electron and Python dependencies; the packaged installer arrives in Phase 19.

From PowerShell, you can also start the built Electron app with `npm.cmd start`.

For development with live updates:

```sh
npm run dev
```

This starts Vite and the Electron window. Electron launches the local Python service on an available loopback port. Close the window to stop the service and Vite.

The desktop launcher chooses another local port automatically when 5173 is already occupied, so it can run alongside the browser preview. The browser preview continues to use port 5173.

For a browser preview with the same storage API:

```sh
npm run dev:web
```

For a built desktop application:

```sh
npm run build
npm start
```

## Evaluate

```sh
npm run check
npm run api:test
npm run queue:test
npm run ingest:test
npm run visual:test
npm run vision:test
npm run audio:test
npm run audio:cloud:test
npm run smoke:desktop
```

The smoke command requires a completed build and launches a hidden Electron window. It checks renderer startup, the restricted preload bridge, Node isolation, SQLite health, migration version, background-worker startup, PDF text, OCR previews and visual reprocessing through IPC, then exits. It uses an isolated data directory. See the acceptance guides for [Phase 1](docs/evaluation/phase-01.md), [Phase 2](docs/evaluation/phase-02.md), [Phase 3](docs/evaluation/phase-03.md), [Phase 4](docs/evaluation/phase-04.md) and [Phase 5](docs/evaluation/phase-05.md). `queue:test` runs 16 queue checks; `ingest:test` runs 18 PDF/text checks. `visual:test` runs 16 checks and requires Tesseract English data. No AI model is needed; converter/provider fixtures are labeled.

## Current scope

Phases 1–5 implement the PDF-based desktop shell, study tabs, workspaces, subject/topics, sample lessons, reading completion, drafts, SQLite, immutable originals and a durable queue. Phase 6 adds audio ingestion, automatic Groq transcription with local fallback, and transcript playback. Phases 7A–7C add uploaded-video audio, original-video playback, selected-frame review and frame text extraction, ready for student review. One heavy worker checks originals and processes PDFs, TXT/Markdown, PPTX, still images/multipage TIFF, WAV/MP3/M4A/OGG/FLAC audio and MP4/MOV/MKV/WebM video audio/frames. **Background work** shows progress, cancellation and resume. Topics begin **Not assessed**; reading does not change mastery.

In Materials, **Review extracted text** shows physical PDF pages, slides, image pages or text line/character locations. **Visuals** shows source previews; **Process visuals again** rebuilds older/partial units after correcting local tool setup. OCR stays marked for review, with confidence/word locations retained. Native PPTX text, table cells, picture OCR and OMML equation structure remain separate. Legacy .ppt needs a PPTX/PDF export. Audio **Review transcript** shows timed speech and local playback; **Reprocess audio** rebuilds it. Video **Review video** plays the original and seeks to source timestamps; **Reprocess video audio** rebuilds its transcript. Expand **Selected frames** for locally selected previews, timestamp seeking, unverified local OCR and selected Groq transcriptions. Nearby speech is shown separately with its own time and provider. **Select frames again** rebuilds the visual frame set independently of speech. **Add YouTube link** imports a submitted video's timed captions; see the checkpoint below. Tutoring, retrieval, assessments, learner models and schedules arrive later. Local ingestion needs no cloud key; configuring the Groq backend key enables automatic selective visual fallback after local extraction. External search is not implemented yet.

Audio setup: install FFmpeg with ffprobe, then restart. With `GROQ_API_KEY`, detected speech intervals are automatically transcribed by Groq; installed Tiny provides local fallback. `npm.cmd run audio:setup` explicitly installs that fallback when missing. `STUDYLENS_AUTO_GROQ_AUDIO=0` keeps transcription local. Recordings up to four hours use 30-second intervals with clickable source timestamps. Transcripts need review, especially Hindi/Hinglish and short noisy speech. See the [cloud audio checkpoint and manual checks](docs/evaluation/phase-06-cloud-audio.md), with the [original local evaluation](docs/evaluation/phase-06.md) retained. The local speech helper can use up to 1.5 GiB RAM; VAD and the parent have separate 512 MiB guards. No whole-app 8 GB result is claimed.

Video audio uses the same Groq/Tiny pipeline and four-hour limit. The [Phase 7A report](docs/evaluation/phase-07a.md) covers audio stream delay, silent tails, restart/cancel and native range playback. Existing saved videos enter the processing queue on restart. Outer VAD silence is trimmed before video ASR and the exact window offset is added back; playback retains the full original. Unsupported playback codecs can use the saved original or an H.264 MP4 export. Videos with nonzero container origins currently need a zero-based export. On-screen content remains explicitly pending.

The [Phase 7B report](docs/evaluation/phase-07b.md) covers independent video-frame selection: FFmpeg samples source PTS in bounded 30-second windows, PySceneDetect and pixel changes detect slide/whiteboard updates, and adjacent duplicate suppression preserves later returns to earlier slides. Frame jobs run automatically for new and previously saved videos; `STUDYLENS_AUTO_VIDEO_FRAMES=0` disables automatic queuing. Existing jobs still run. Up to 600 frames are spread across the recording, with at most 20 retained per window and four previews per viewer page. Budget omissions and windows without a decoded frame stay visible. `npm.cmd run api:install` installs the pinned headless scene-detection code dependencies; it downloads no AI model.

The [Phase 7C report](docs/evaluation/phase-07c.md) covers a separate durable frame-visual job. It runs Tesseract on each retained preview and routes difficult frames through the existing selective Groq vision adapter when configured. Automatic Groq sends are limited to twelve frames per video and one per 30-second selection window, spread across the timeline. Unsent difficult frames remain labeled for review; **Read frame text again** rebuilds results. `STUDYLENS_AUTO_VIDEO_VISUALS=0` disables automatic job creation, while the explicit action remains available. Visual text, Groq structure and nearby speech stay separate and unverified.

YouTube [Phase 7D-1](docs/evaluation/phase-07d-youtube.md) is implemented ahead of frame OCR at the student's request. **Materials → Add YouTube link → Import captions** queues a caption fetch for one video in the selected language (`en` English, `hi` Hindi, or another track code). Manual captions are preferred. Immutable JSON snapshots preserve the canonical link, track provenance and cue times; changed snapshots create versions, identical snapshots reuse a version. **Review YouTube source** shows saved intervals, available languages and timestamp buttons that open the source in the system browser. **Refresh captions** queues a new snapshot. Blocked/unavailable captions retain a link-only snapshot with no invented text. Captions remain unverified; online playback, video downloading and visual extraction are separate. No YouTube API key or Groq key is needed. `npm.cmd run api:install` installs the pinned lightweight caption reader. `npm.cmd run youtube:test` runs thirteen offline contracts; the report also records one successful live public-lecture import and production Electron review.

Originals may be up to 2 GB. Processing caps: PDF/slide/image files 64 MB; 500 PDF pages/slides; 100 TIFF pages; 40 million source-image/video-frame pixels; text files 16 MB; audio/video up to 2 GB and four hours. YouTube caption snapshots are capped at 4 MB, 30,000 cues and four hours. OCR/rendering is bounded to 4 million pixels/2500 pixels per edge; previews to 512 KiB each. UTF-8/BOM-marked UTF-16 are supported; encrypted PDFs need an unencrypted copy. OCR does not verify equations, diagram relationships, tables, reading order or handwriting.

### Local visual tools

The unused alternative OCR/multimodal benchmark downloads and isolated test environments were [cleaned up on October 3, 2026](docs/evaluation/ocr-cleanup.md). Reports and raw evaluation evidence are retained; benchmark setup commands below require downloading their assets again.

Tesseract 5 and language data are required for OCR. This laptop has English data at C:\Program Files\Tesseract-OCR. Discovery uses PATH/common Windows locations; `STUDYLENS_TESSERACT` can name an executable. `STUDYLENS_OCR_LANG` defaults to `eng`; `eng+hin` requires both traineddata files. Missing tools/languages retain previews with actionable warnings. EXIF orientation is handled; arbitrary physical rotation/skew is not automatically corrected.

Full PPTX previews use LibreOffice when installed (`STUDYLENS_SOFFICE` can name its executable). LibreOffice is now installed and converted the user's 13-slide deck successfully; the student confirmed the full title-slide preview. Continue comparing converted layouts/fonts with the original. Native PPTX text/images still work. Decks with external relationships/macros/embedded objects skip conversion; linked resources are not fetched. Export slides to PDF when full previews are unavailable.

Optional `STUDYLENS_VISION_MODEL` enables an already-installed vision-capable Ollama model at fixed local `127.0.0.1:11434`. It is off by default. **Unverified visual interpretation** keeps model notes separate from source text; the adapter requests model unloading. Provider fixtures passed, but live vision quality/resource use remains a gate. Reliable diagram/formula interpretation is not established by OCR. Set overrides before `npm.cmd start`; the shortcut does not inherit a terminal-only override.

HunyuanOCR 1.5 has a separate [local trial and measured comparison](docs/evaluation/hunyuan-local.md). Run `scripts/evaluate-hunyuan.py --setup` using the project Python to download the pinned assets, then run the script in its default CPU mode. This experiment is not connected to app ingestion. Cloud OCR remains unconfigured.

The [small local OCR report](docs/evaluation/small-ocr.md) compares required model storage, measured CPU latency, memory, and retained recognition outputs. Its [complete candidate matrix](docs/evaluation/small-ocr-matrix.md) includes incomplete trials. Benchmark dependencies and multi-model downloads are isolated under `tmp/ocr-benchmark/`; the report is not an enabled ingestion-provider change.

The [Groq vision and routing pilot](docs/evaluation/groq-vision.md) records authorized cloud calls, initial failures and corrected table/diagram results. [Automatic Groq fallback](docs/evaluation/automatic-groq.md) now queues after local extraction for PDFs, slides and images when `GROQ_API_KEY` is configured. The existing router sends selected difficult previews; ordinary readable content remains local. No student confirmation is required for Groq. Materials shows the automatic upload notice, and Background work supports cancellation. Set `STUDYLENS_AUTO_GROQ_VISION=0` before launch to disable automatic sending. Already processed material is not swept automatically; **Process visuals again** starts the new pipeline for it.

Expand **Cloud help for difficult visuals** to retry Groq or request a specific location. Groq transcribes tables, equations and diagrams. Keys stay in the backend environment. Native PowerPoint table cells are read locally; cloud text appears under **Extracted text**, stays labeled and unverified, and is cached by model/prompt version. Quota waits release the worker for local jobs. Tesseract remains the local recognizer; local model benchmarks are separate. Google Cloud Vision was removed on October 3, 2026; Groq is the only cloud extraction provider.

## Data and recovery

On Windows, the default data directory is `%APPDATA%\StudyLens\data`, outside the OneDrive project directory. Settings shows the actual location. `STUDYLENS_DATA_DIR` overrides it for evaluation. Both launch modes use this default, so use distinct evaluation data if you want to keep test work separate:

```powershell
$env:STUDYLENS_DATA_DIR = Join-Path $PWD 'tmp/phase02-preview'
npm.cmd run dev:web
```

SQLite is the canonical store. A localStorage cache helps recover unsaved session edits; browser and Electron caches are separate. A valid Phase 1 session is imported only when the default workspace has no saved session. Existing SQLite data takes precedence. Save conflicts never automatically overwrite another window's changes: retry reads the current revision, or **Load saved workspace** preserves the unsaved cache in a `.recovery` key before loading SQLite. Recovery copies currently require developer tools to export; a student recovery/export screen belongs in hardening.

Back up the entire data directory with Neev closed, including the SQLite file, originals and derived previews. Copies of only the database or only the originals are incomplete backups. File transfers continue across tabs and workspaces, retaining their original subject. Keep the app open until a file is saved: unfinished file transfers are cancellable but do not resume after app closure. Saved background jobs survive restart. Extraction saves each page/text unit and its checkpoint in one transaction, with stable IDs tied to the immutable original version. The slow evaluation fixture resumes at its saved unit; interrupted original integrity checks safely restart the hashing stage.

To check queue progress and cancellation without a large file, enable the labeled evaluation fixture with `STUDYLENS_QUEUE_EVAL=1` before launching. Settings then offers **Run slow queue test**. It is disabled by default and does not process course content or affect learning evidence. See the Phase 3 guide for an isolated test setup.

## Structure

```text
electron/              Desktop lifecycle and restricted preload bridge
src/                   React/TypeScript renderer, session model, PDF-based CSS
services/              FastAPI, SQLAlchemy/aiosqlite, Alembic and isolated tests
scripts/               Development and desktop smoke entry points
tests/                 Session behavior and recovery checks
docs/PHASES.md         Dependency boundaries and acceptance gates
docs/evaluation/       Phase-specific evaluation guides
```

Each phase should be runnable and evaluated through its own fixtures before connecting to later phases. Work one milestone at a time; preserve evidence of failures and do not fabricate benchmark results. Live audio tutoring remains deferred.
