# Neev — current architecture audit

2026-10-03, Asia/Calcutta. Branch: `cleanup/architecture-reset`; baseline: `4deb661ecf21a13adcaee18ac1fc718203d518b5`. Repository: `C:/Users/User/OneDrive/Desktop/Study`.

Phase A only. Only durable addition: this report. No features, dependencies, migrations or persistent identifiers changed. Tests generated ignored build/log/test data; smoke screenshot restored byte-for-byte. Evidence: source/AST, Git, installed metadata, isolated migrated SQLite, registered routes and actual requested checks. Docs used only for comparison. UNVERIFIED explicitly marks unknowns. Sizes are logical bytes; dates are last Git author-commit dates.

## 1. Repository tree, counts and sizes

Tracked baseline:302 files. Depth is counted from the repository root; folders at depth3 summarize deeper descendants. Installed/generated folders are excluded from the tracked tree and included in the separate disk table.

```text
C:/Users/User/OneDrive/Desktop/Study/
  .gitignore
  LICENSE
  Neev.lnk
  README.md
  StudyLens-Design-Prompt.txt
  StudyLens.lnk
  docs/ (169 files)
    CONTEXT_HANDOFF.md
    NEXT_CONTEXT_PROMPT.md
    PHASES.md
    architecture.md
    evaluation/ (164 files)
      audio-desktop.json
      audio-integration-20261002-041044.json
      audio-speed.json
      audio-speed.md
      automatic-groq-ui.json
      automatic-groq.md
      cloud-audio-20261002-193932.json
      cloud-audio-20261002-194327.json
      cloud-audio-desktop.json
      cloud-extracted-text-ui.json
      desktop-routing-results.json
      desktop-vision-20261001-172849.json
      fixtures/ (62 files)
      gemma4-audio-scores.json
      gemma4-audio.json
      gemma4-documents-280.json
      gemma4-omni-summary.json
      gemma4-omni.md
      gemma4-pilot-scores.json
      gemma4-pilot.json
      gemma4-vision-280.json
      groq-format-fallback-20261001-181237.json
      groq-format-fallback-20261002-034941.json
      groq-vision-checks.json
      groq-vision-dedup-json-results.json
      groq-vision-results.json
      groq-vision.md
      hinglish-asr.md
      hinglish-hardware.json
      hinglish-manifest.json
      hinglish-results-20261002-043540.json
      hinglish-results-20261002-044052.json
      hinglish-summary.json
      hunyuan-local-results.json
      hunyuan-local.md
      lighton-gpu-documents-1280.json
      lighton-gpu-pilot-1280.json
      lighton-ocr.md
      lighton-pilot-1280.json
      lighton-setup.json
      llamaindex-docs-pilot.json
      llamaindex-docs-pilot.md
      native-table-deck.json
      ocr-cleanup.json
      ocr-cleanup.md
      omnidoc-local-baseline.json
      phase-01.md
      phase-02.md
      phase-03.md
      phase-04.md
      phase-05-cloud-vision.md
      phase-05.md
      phase-06-cloud-audio.md
      phase-06.md
      phase-07a.md
      phase-07b.md
      phase-07c.md
      phase-07d-media.md
      phase-07d-youtube.md
      retired-ocr-evidence.zip
      screenshots/ (23 files)
      small-ocr-matrix.md
      small-ocr-results.json
      small-ocr.md
      video-desktop.json
      video-frames-20261003-074347.json
      video-frames-20261003-074535.json
      video-frames-20261003-074703.json
      video-frames-20261003-075439.json
      video-frames-20261003-080329.json
      video-frames-desktop.json
      video-integration-20261003-070850.json
      video-integration-20261003-071221.json
      video-visuals-20261003-104402.json
      video-visuals-20261003-104845.json
      video-visuals-cloud-desktop.json
      video-visuals-desktop.json
      vision-routing-results.json
      youtube-20261003-083018.json
      youtube-desktop.json
      youtube-media-desktop.json
    youtube-ingestion-plan.md
  electron/ (6 files)
    backend.cjs
    main.cjs
    media.cjs
    preload.cjs
    storage.cjs
    youtube.cjs
  index.html
  package-lock.json
  package.json
  scripts/ (40 files)
    benchmark-audio-speed.py
    benchmark-audio-vad.py
    create-audio-fixtures.py
    create-frame-fixtures.py
    create-video-fixtures.py
    dev-web.mjs
    dev.mjs
    evaluate-audio-desktop.cjs
    evaluate-audio.py
    evaluate-cloud-audio.py
    evaluate-desktop-routing.py
    evaluate-desktop-vision.py
    evaluate-groq-vision.py
    evaluate-hinglish.py
    evaluate-hunyuan.py
    evaluate-lighton.py
    evaluate-llamaindex-docs.py
    evaluate-omni-local.py
    evaluate-omni.py
    evaluate-small-ocr.py
    evaluate-video-desktop.cjs
    evaluate-video-frame-visuals-desktop.cjs
    evaluate-video-frame-visuals.py
    evaluate-video-frames-desktop.cjs
    evaluate-video-frames.py
    evaluate-video.py
    evaluate-vision-routing.py
    evaluate-youtube-desktop.cjs
    evaluate-youtube-media-desktop.cjs
    evaluate-youtube.py
    prepare-omni.py
    python.mjs
    report-groq-vision.py
    report-hinglish.py
    report-small-ocr.py
    score-omni-audio.py
    score-omni-docs.py
    setup-audio.py
    smoke.mjs
    summarize-omni.py
  services/ (50 files)
    migrations/ (6 files)
      env.py
      versions/ (5 files)
    requirements-lock.txt
    studylens_service/ (29 files)
      __init__.py
      __main__.py
      api.py
      audio.py
      audio_helper.py
      audio_vad_helper.py
      cloud_audio.py
      cloud_vision.py
      cloud_vision_wait.py
      database.py
      equations.py
      extraction.py
      job_errors.py
      jobs.py
      local_tools.py
      resource_guard.py
      schema.py
      slides.py
      supervisor.py
      video.py
      video_frame_visuals.py
      video_frames.py
      video_frames_helper.py
      visual.py
      visual_assets.py
      worker.py
      youtube.py
      youtube_helper.py
      youtube_media.py
    tests/ (14 files)
      test_audio.py
      test_automatic_vision.py
      test_cloud_audio.py
      test_cloud_vision.py
      test_extraction.py
      test_jobs.py
      test_storage.py
      test_video.py
      test_video_frame_visuals.py
      test_video_frames.py
      test_visual.py
      test_youtube.py
      test_youtube_media.py
      worker_fixture.py
  src/ (22 files)
    App.tsx
    AudioTranscript.tsx
    ContentPreview.tsx
    EquationPreview.tsx
    JobPanel.tsx
    Materials.tsx
    StorageSettings.tsx
    VideoFrames.tsx
    VideoTranscript.tsx
    VisualExtraction.tsx
    YouTubeReview.tsx
    global.d.ts
    main.tsx
    model.ts
    storage/ (7 files)
      client.ts
      files.ts
      imports.ts
      useImports.ts
      useJobs.ts
      useWorkspace.ts
      writer.ts
    styles.css
  tests/ (4 files)
    imports.test.ts
    session.test.ts
    writer.test.ts
    youtube.test.ts
  tsconfig.json
  vite.config.ts
```

| Top level | Tracked files | Tracked bytes |
| --- | --- | --- |
| (root files) | 11 | 124,994 |
| docs | 169 | 34,193,520 |
| electron | 6 | 30,496 |
| scripts | 40 | 256,490 |
| services | 50 | 428,818 |
| src | 22 | 189,216 |
| tests | 4 | 11,199 |

Workspace disk snapshot: recursive logical bytes; symlink directories not followed;0 unreadable entries. Pre-report/test snapshot, not post-cleanup disk savings.

| Folder | Files | Bytes |
| --- | --- | --- |
| .electron-cache | 1 | 157,998,329 |
| .git | 124 | 16,433,926 |
| .npm-cache | 539 | 288,930,278 |
| .venv | 7046 | 481,436,627 |
| dist | 11 | 578,771 |
| docs | 170 | 34,217,234 |
| electron | 6 | 30,496 |
| models | 11 | 78,205,119 |
| node_modules | 6804 | 553,075,933 |
| scripts | 52 | 446,635 |
| services | 98 | 1,177,731 |
| src | 22 | 189,216 |
| tests | 4 | 11,199 |
| tmp | 11779 | 898,110,102 |

Largest20 tracked source files by bytes (Python/TS/TSX/CSS/CJS/MJS, including tests/evaluators; JSON/docs/media/locks excluded). Physical lines include comments/blanks; Git/stdlib inventory evidence.

| Source | Bytes | Lines |
| --- | --- | --- |
| [src/App.tsx](C:/Users/User/OneDrive/Desktop/Study/src/App.tsx) | 38,602 | 1153 |
| [src/styles.css](C:/Users/User/OneDrive/Desktop/Study/src/styles.css) | 31,966 | 1672 |
| [scripts/evaluate-small-ocr.py](C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-small-ocr.py) | 26,487 | 430 |
| [services/studylens_service/jobs.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/jobs.py) | 25,124 | 342 |
| [services/studylens_service/cloud_vision.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/cloud_vision.py) | 23,525 | 424 |
| [services/tests/test_cloud_vision.py](C:/Users/User/OneDrive/Desktop/Study/services/tests/test_cloud_vision.py) | 22,507 | 389 |
| [services/studylens_service/audio.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/audio.py) | 20,605 | 320 |
| [src/ContentPreview.tsx](C:/Users/User/OneDrive/Desktop/Study/src/ContentPreview.tsx) | 20,444 | 457 |
| [services/studylens_service/database.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/database.py) | 18,600 | 274 |
| [src/storage/client.ts](C:/Users/User/OneDrive/Desktop/Study/src/storage/client.ts) | 18,321 | 529 |
| [services/tests/test_extraction.py](C:/Users/User/OneDrive/Desktop/Study/services/tests/test_extraction.py) | 17,177 | 332 |
| [src/Materials.tsx](C:/Users/User/OneDrive/Desktop/Study/src/Materials.tsx) | 16,791 | 379 |
| [services/tests/test_visual.py](C:/Users/User/OneDrive/Desktop/Study/services/tests/test_visual.py) | 16,765 | 306 |
| [scripts/evaluate-hinglish.py](C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-hinglish.py) | 16,143 | 251 |
| [services/studylens_service/worker.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/worker.py) | 15,767 | 319 |
| [scripts/evaluate-hunyuan.py](C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-hunyuan.py) | 15,596 | 289 |
| [services/tests/test_cloud_audio.py](C:/Users/User/OneDrive/Desktop/Study/services/tests/test_cloud_audio.py) | 15,348 | 299 |
| [services/studylens_service/slides.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/slides.py) | 15,343 | 239 |
| [services/tests/test_jobs.py](C:/Users/User/OneDrive/Desktop/Study/services/tests/test_jobs.py) | 14,473 | 283 |
| [scripts/evaluate-omni.py](C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-omni.py) | 14,205 | 282 |

## 2. Actual processes, components and external transfers

```text
React renderer (src/main.tsx, App.tsx, storage/*, media review components)
  -> window.studyLens preload (electron/preload.cjs)
  -> Electron main/storage/media (electron/*.cjs)
  -> ephemeral-token authenticated HTTP at 127.0.0.1:<random port>
  -> FastAPI create_app (services/studylens_service/api.py)
       -> SQLAlchemy + aiosqlite -> studylens.sqlite3 (WAL)
       -> threaded hashing/file I/O -> staging/ + originals/<prefix>/<sha256>
       -> WorkerSupervisor -> separate OS-locked Worker
            -> SQLite jobs/content_units + derived previews/caches
            -> Tesseract / LibreOffice / FFmpeg / FFprobe helper processes
            -> Python ASR/VAD/frame-analysis/YouTube helper processes
            -> configured Groq and optional loopback Ollama adapters

Development browser -> Vite same-origin /api proxy -> same local service.
YouTube "Watch here" click -> youtube-nocookie iframe.
YouTube browser fallback -> canonical watch URL via Electron shell.openExternal.
Standalone evaluation scripts -> isolated tmp data / local servers / optional
provider or dataset/model downloads; these are not renderer features.
```

Sources: [main.cjs](C:/Users/User/OneDrive/Desktop/Study/electron/main.cjs), [backend.cjs](C:/Users/User/OneDrive/Desktop/Study/electron/backend.cjs), [storage.cjs](C:/Users/User/OneDrive/Desktop/Study/electron/storage.cjs), [media.cjs](C:/Users/User/OneDrive/Desktop/Study/electron/media.cjs), [vite.config.ts](C:/Users/User/OneDrive/Desktop/Study/vite.config.ts), [__main__.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/__main__.py), [api.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/api.py), [database.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/database.py), [worker.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/worker.py), [local_tools.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/local_tools.py).

| External boundary | Data sent / trigger / actual code |
| --- | --- |
| Groq vision, https://api.groq.com/openai/v1/chat/completions | Resized source preview PNG as base64, transcription instruction/schema, model/settings and backend authentication. No original filename or whole document is placed in the request. Automatic difficult visual processing requires key + enabled flag; manual version/ordinal operation also exists. Code: [cloud_vision.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/cloud_vision.py), [worker.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/worker.py). |
| Groq retained-frame vision, same endpoint | Selected uploaded-video frame images, same instruction/model. At most 12 routed frames per pass and one per 30-second window; source audio is not included in these image requests. Code: [video_frame_visuals.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/video_frame_visuals.py). |
| Groq ASR, https://api.groq.com/openai/v1/audio/transcriptions | Bounded decoded WAV speech interval, generic name source-interval.wav, model/format/temperature and optional language hint. Configured automatic speech detection precedes transfer; local Tiny fallback is available. Code: [cloud_audio.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/cloud_audio.py), [audio.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/audio.py). |
| Ollama, http://127.0.0.1:11434/api/generate | Optional <=768-pixel image, fixed unverified-description prompt, configured model, context/prediction caps, keep_alive=0. No Neev remote URL is configurable here. Ollama's own server/model behaviour and provider retention are UNVERIFIED. Code: [visual.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/visual.py). |
| YouTube caption helper | Submitted video ID and caption-track requests, requested-language selection, YouTube/consent endpoint traffic; no student course files or app token. HTTPS destinations allowlisted to youtube.com, www.youtube.com, consent.youtube.com and consent.google.com; session proxies disabled. Requests may use session/consent cookies generated by the library; no user browser-cookie import is implemented. Code: [youtube_helper.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/youtube_helper.py). |
| YouTube embedded playback | Student-selected video ID, start time, normal browser playback/network metadata to youtube-nocookie and the embedded player's dependencies. Loads on click. Subresource destinations/data/retention are UNVERIFIED; no network capture performed. Code: [YouTubeReview.tsx](C:/Users/User/OneDrive/Desktop/Study/src/YouTubeReview.tsx), [index.html](C:/Users/User/OneDrive/Desktop/Study/index.html). |
| YouTube external browser | Canonical video URL and optional bounded t parameter. Browser/account state is outside Neev. Code: [youtube.cjs](C:/Users/User/OneDrive/Desktop/Study/electron/youtube.cjs), [storage.cjs](C:/Users/User/OneDrive/Desktop/Study/electron/storage.cjs). |
| Explicit local audio setup | Hugging Face model/revision/file requests via snapshot_download; no student audio. Not run in this audit; runtime Whisper helper uses local_files_only=True. Code: [setup-audio.py](C:/Users/User/OneDrive/Desktop/Study/scripts/setup-audio.py), [audio_helper.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/audio_helper.py). |
| Standalone pilots | Groq selected authored/public audio or retained OCR images: benchmark-audio-speed, evaluate-cloud-audio, evaluate-desktop-vision, evaluate-groq-vision. Hugging Face pinned dataset/model requests: evaluate-hinglish, prepare-omni, evaluate-omni, evaluate-small-ocr, evaluate-hunyuan. Hunyuan also queries GitHub llama.cpp releases/download assets. LightOn invokes local Ollama pull (remote registry requests initiated by Ollama). Local inference: Hunyuan/Omni llama.cpp, LightOn Ollama. These scripts can transfer data/download assets when explicitly run; none was run during A. Code: corresponding scripts in section 3. |
| Developer infrastructure | Git push sends repository content to GitHub. Existing package/model setup scripts can download dependencies; no install/setup/model download was run. Vite development browser uses localhost HTTP/WebSocket. Code: [package.json](C:/Users/User/OneDrive/Desktop/Study/package.json), [dev.mjs](C:/Users/User/OneDrive/Desktop/Study/scripts/dev.mjs), [dev-web.mjs](C:/Users/User/OneDrive/Desktop/Study/scripts/dev-web.mjs). |

Groq credentials stay in backend environment/request headers; native helper environments remove GROQ_API_KEY and STUDYLENS_API_TOKEN, and worker supervision removes the local API token. Secret values were not read or retained. Source sent to a provider cannot be recalled by cancelling a job. No SearXNG/search implementation, telemetry client or voice tutor was found in tracked runtime source. Library/native-tool behaviour beyond inspected boundaries is UNVERIFIED; this is a static architecture audit, not exhaustive network tracing.

## 3. Complete tracked Python module inventory

81 modules, including migrations/tests/runners/fixture generators. All distinct AST imports include deferred/conditional imports; dots are relative. Purposes derive from source/functions, not architectural docs.

Import key: I1=.; I2=.api; I3=.audio; I4=.cloud_audio; I5=.cloud_vision; I6=.cloud_vision_wait; I7=.database; I8=.equations; I9=.extraction; I10=.job_errors; I11=.jobs; I12=.local_tools; I13=.resource_guard; I14=.schema; I15=.slides; I16=.supervisor; I17=.video; I18=.video_frame_visuals; I19=.video_frames; I20=.visual; I21=.visual_assets; I22=.youtube; I23=.youtube_media; I24=PIL; I25=alembic; I26=alembic.config; I27=alembic.operations; I28=argparse; I29=array; I30=asyncio; I31=atexit; I32=base64; I33=collections; I34=concurrent.futures; I35=contextlib; I36=copy; I37=csv; I38=ctypes; I39=cv2; I40=datetime; I41=defusedxml.ElementTree; I42=easyocr; I43=fastapi; I44=fastapi.responses; I45=fastapi.testclient; I46=faster_whisper; I47=faster_whisper.vad; I48=fcntl; I49=fractions; I50=functools; I51=hashlib; I52=hmac; I53=httpx; I54=huggingface_hub; I55=importlib; I56=importlib.metadata; I57=importlib.util; I58=io; I59=json; I60=llama_index.core.schema; I61=llama_index.core.storage.docstore; I62=llama_index.core.vector_stores.types; I63=llama_index.retrievers.bm25; I64=logging; I65=math; I66=msvcrt; I67=numpy; I68=onnxruntime; I69=onnxtr.models; I70=onnxtr.models.engine; I71=os; I72=pathlib; I73=posixpath; I74=psutil; I75=pyarrow.parquet; I76=pydantic; I77=pypdf; I78=pypdf._page; I79=pypdf.errors; I80=pypdf.generic; I81=pypdfium2; I82=random; I83=rapidocr; I84=re; I85=reportlab.lib.utils; I86=reportlab.pdfgen; I87=reportlab.pdfgen.canvas; I88=requests; I89=scenedetect; I90=secrets; I91=shutil; I92=signal; I93=socket; I94=sqlalchemy; I95=sqlalchemy.dialects.sqlite; I96=sqlalchemy.engine; I97=sqlalchemy.exc; I98=sqlalchemy.ext.asyncio; I99=sqlite3; I100=starlette.requests; I101=statistics; I102=struct; I103=studylens_service; I104=studylens_service.api; I105=studylens_service.cloud_vision; I106=studylens_service.cloud_vision_wait; I107=studylens_service.equations; I108=studylens_service.extraction; I109=studylens_service.job_errors; I110=studylens_service.jobs; I111=studylens_service.local_tools; I112=studylens_service.resource_guard; I113=studylens_service.schema; I114=studylens_service.slides; I115=studylens_service.visual; I116=studylens_service.visual_assets; I117=studylens_service.worker; I118=studylens_service.youtube; I119=studylens_service.youtube_helper; I120=subprocess; I121=sys; I122=tempfile; I123=test_audio; I124=test_cloud_vision; I125=test_extraction; I126=test_storage; I127=test_video_frames; I128=test_youtube; I129=threading; I130=time; I131=torch; I132=traceback; I133=tracemalloc; I134=transformers; I135=types; I136=typing; I137=unicodedata; I138=unittest; I139=unittest.mock; I140=urllib.error; I141=urllib.parse; I142=urllib.request; I143=uuid; I144=uvicorn; I145=wave; I146=yaml; I147=youtube_transcript_api; I148=zipfile; I149=zlib.

| Absolute module path | Lines | Purpose | Imports (key above) |
| --- | --- | --- | --- |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-04/generate.py | 64 | Authored fixtures only. Run using the bundled document Python runtime | I24, I59, I72, I77, I85, I86 |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-05/generate.py | 95 | Authored extraction fixtures; not a student course or presentation tem | I24, I58, I59, I72, I85, I87, I148 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/benchmark-audio-speed.py | 192 | Stage timing of the real local pipeline and an explicit authored-audio | I28, I40, I45, I51, I53, I59, I65, I71, I72, I91, I101, I103, I104, I111, I117, I120, I121, I126, I129, I130, I139, I145 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/benchmark-audio-vad.py | 33 | Measure already-bundled VAD without Whisper transcription or downloads | I47, I59, I67, I72, I101, I112, I130, I145 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/create-audio-fixtures.py | 34 | Deterministic synthetic audio variants; not natural student speech | I29, I59, I65, I72, I82, I120, I145 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/create-frame-fixtures.py | 59 | Authored slide, whiteboard, static, return-slide, VFR and rotated clip | I24, I59, I71, I72, I111, I120 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/create-video-fixtures.py | 38 | Small authored video fixtures; existing synthetic speech, no downloads | I59, I71, I72, I111, I120 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-audio.py | 66 | Real local audio gate. No provider requests; preserve failed results | I40, I45, I59, I71, I72, I104, I112, I117, I121, I126, I129, I130 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-cloud-audio.py | 141 | Opt-in live audio pilot using authored and previously downloaded publi | I28, I40, I45, I51, I59, I71, I72, I84, I103, I104, I117, I121, I126, I129, I130, I137, I139 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-desktop-routing.py | 53 | Local-only production router check with real Tesseract; no cloud acces | I24, I40, I59, I72, I105, I115, I129, I130 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-desktop-vision.py | 94 | Explicit live gate: one retained table image through the app API and w | I28, I40, I45, I57, I59, I71, I72, I104, I112, I117, I121, I126, I129, I130 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-groq-vision.py | 169 | Explicit cloud pilot on selected existing OCR fixtures; never modifies | I28, I32, I40, I51, I59, I71, I72, I130, I140, I142 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-hinglish.py | 251 | Pinned, seeded ASR benchmark through the real StudyLens ingestion pipe | I28, I33, I40, I45, I51, I54, I59, I71, I72, I75, I82, I101, I103, I104, I117, I120, I121, I126, I129, I130, I137, I139, I145 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-hunyuan.py | 289 | Isolated local HunyuanOCR experiment. No app-data writes or cloud OCR  | I24, I28, I32, I38, I51, I58, I59, I71, I72, I90, I93, I115, I120, I121, I129, I130, I135, I140, I142, I148 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-lighton.py | 269 | Exact community Ollama LightOnOCR-2 benchmark in a private local serve | I24, I28, I32, I51, I57, I59, I71, I72, I74, I91, I93, I111, I120, I121, I129, I130, I142 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-llamaindex-docs.py | 125 | Isolated Phase 8 LlamaIndex BM25 pilot over Neev's own documentation | I51, I56, I59, I60, I61, I62, I63, I71, I72, I93, I101, I120, I121, I130, I133, I139 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-omni-local.py | 39 | Current production Tesseract OCR on exactly the prepared benchmark ima | I24, I59, I72, I115, I121, I129, I130, I135 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-omni.py | 282 | Isolated Gemma 4 E2B CPU evaluation; no application data or settings c | I28, I32, I34, I51, I54, I57, I59, I71, I72, I90, I93, I120, I129, I130, I140, I142 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-small-ocr.py | 430 | Isolated CPU OCR comparison. Assets/cache in tmp; never writes student | I24, I28, I31, I32, I42, I51, I54, I55, I58, I59, I67, I68, I69, I70, I71, I72, I74, I83, I84, I90, I93, I101, I120, I121, I130, I131, I132, I134, I142, I146 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-video-frame-visuals.py | 74 | Isolated real OCR pilot on an authored uploaded-video fixture; no clou | I40, I45, I59, I71, I72, I104, I117, I121, I126, I129, I130 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-video-frames.py | 65 | Real, no-cloud frame-selection benchmark on authored gold video scenes | I40, I45, I59, I71, I72, I104, I117, I121, I126, I129, I130 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-video.py | 94 | Live checkpoint 7A pilot on small authored videos; no model downloads | I28, I29, I32, I40, I45, I58, I59, I71, I72, I103, I104, I117, I121, I126, I129, I130, I145 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-vision-routing.py | 77 | Local routing pilot from retained PP-OCRv6 Small outputs; no cloud req | I24, I39, I51, I59, I67, I72, I84, I130 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-youtube.py | 59 | Live, caption-only import smoke test plus clearly labelled authored UI | I36, I40, I45, I59, I71, I72, I104, I117, I121, I126, I128, I129, I130, I139 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/prepare-omni.py | 104 | Fixed inputs for local multimodal comparison; references never enter m | I24, I28, I33, I51, I54, I59, I71, I72, I82 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/report-groq-vision.py | 110 | Check retained cloud outputs against explicit fixture truth and write  | I59, I72 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/report-hinglish.py | 74 | Summarize a completed Hinglish run without changing benchmark outputs | I33, I57, I59, I72, I121 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/report-small-ocr.py | 113 | Build a transparent pilot score sheet from retained local OCR outputs | I33, I51, I59, I72, I84, I101, I121, I137 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/score-omni-audio.py | 56 | Paired raw ASR comparison using the earlier frozen normalization and r | I33, I57, I59, I72, I101, I121 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/score-omni-docs.py | 56 | Export completed page predictions and run the pinned official OmniDocB | I28, I59, I71, I72, I120, I121, I146 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/setup-audio.py | 15 | Explicit setup download. Importing student audio never downloads a mod | I28, I54, I72 |
| C:/Users/User/OneDrive/Desktop/Study/scripts/summarize-omni.py | 66 | Gather completed multimodal benchmark results without recomputing infe | I33, I59, I72, I101 |
| C:/Users/User/OneDrive/Desktop/Study/services/migrations/env.py | 24 | Alembic engine/WAL/transaction | I25, I94, I96, I113 |
| C:/Users/User/OneDrive/Desktop/Study/services/migrations/versions/0001_local_storage.py | 71 | Initial local workspace and immutable source version storage | I25, I94 |
| C:/Users/User/OneDrive/Desktop/Study/services/migrations/versions/0002_background_jobs.py | 44 | Durable jobs; existing workspace and original file records are preserv | I25, I94 |
| C:/Users/User/OneDrive/Desktop/Study/services/migrations/versions/0003_content_units.py | 29 | Version-bound content units with exact physical page or decoded-text l | I25, I94 |
| C:/Users/User/OneDrive/Desktop/Study/services/migrations/versions/0004_visual_content.py | 16 | Preserve visual provenance without changing existing source units | I25, I94 |
| C:/Users/User/OneDrive/Desktop/Study/services/migrations/versions/0005_youtube_media_links.py | 24 | Append-only associations between saved YouTube sources and permitted l | I25, I94 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/__init__.py | 1 | Neev local storage service | — |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/__main__.py | 43 | Loopback service entry and parent EOF | I2, I28, I59, I71, I72, I93, I121, I129, I144 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/api.py | 277 | Authenticated app and all routes | I3, I5, I7, I11, I14, I16, I23, I30, I35, I43, I44, I51, I52, I71, I72, I84, I100, I143 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/audio.py | 320 | Bounded audio ingestion with automatic Groq speech and offline ASR fal | I1, I4, I6, I9, I10, I12, I29, I32, I51, I57, I59, I65, I71, I72, I84, I121, I122, I145 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/audio_helper.py | 34 | Isolated, offline CPU transcription of one bounded PCM chunk | I13, I46, I59, I121, I129, I130 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/audio_vad_helper.py | 14 | Speech detection in a bounded child; uses the already-bundled Silero m | I47, I59, I67, I121, I145 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/cloud_audio.py | 165 | Bounded Groq speech transcription, durable pacing and validated chunk  | I3, I6, I10, I30, I51, I53, I59, I65, I71, I130 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/cloud_vision.py | 424 | Automatic/manual selective Groq routing/transcription/provenance | I6, I10, I24, I30, I32, I51, I53, I58, I59, I71, I76, I84, I130 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/cloud_vision_wait.py | 7 | A scheduling signal with no model/runtime dependencies | — |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/database.py | 274 | Engine/migrations, CRUD and content presentation | I11, I14, I19, I21, I23, I25, I26, I30, I40, I51, I59, I72, I94, I95, I96, I97, I98, I143 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/equations.py | 29 | Conservative OMML structure preview. No evaluation or inferred missing | — |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/extraction.py | 218 | Page/line-bound extraction. Runs only inside the single heavy worker | I3, I10, I17, I20, I22, I51, I59, I64, I77, I79, I143 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/job_errors.py | 14 | Cancellation/interruption/permanent errors | — |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/jobs.py | 342 | Queue scheduling, cancel/retry/rebuild and frame presentation | I5, I7, I14, I18, I19, I21, I22, I30, I59, I94, I95, I130, I143 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/local_tools.py | 99 | Bound native helper processes; never invoke a shell or put them on the | I10, I38, I71, I72, I91, I92, I120, I130 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/resource_guard.py | 83 | Bound uncooperative parser work without putting it on the API event lo | I38, I71, I99, I129, I130 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/schema.py | 217 | SQL tables and API/session validation | I76, I94, I136 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/slides.py | 239 | Bounded OpenXML extraction; optional isolated LibreOffice slide render | I8, I9, I10, I12, I20, I21, I24, I41, I58, I72, I73, I81, I91, I122, I148 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/supervisor.py | 77 | Heavy worker child lifecycle | I30, I71, I121 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/video.py | 67 | Video checkpoint 7A: bounded audio on the original container timeline | I1, I9, I10, I12, I59, I65, I72, I122 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/video_frame_visuals.py | 177 | Version-bound OCR and selective Groq transcription of retained video f | I5, I6, I10, I20, I30, I51, I59, I71 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/video_frames.py | 168 | Independent, bounded sampled-frame selection. No OCR or provider calls | I10, I12, I17, I21, I24, I49, I51, I57, I59, I65, I71, I72, I84, I121, I122, I143 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/video_frames_helper.py | 58 | Isolated low-resolution change analysis, never a speech or OCR model | I13, I39, I59, I67, I72, I89, I121 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/visual.py | 209 | CPU OCR, page previews, and version-bound visual provenance. Worker on | I9, I10, I12, I15, I21, I24, I32, I37, I58, I59, I65, I71, I72, I81, I84, I122, I142 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/visual_assets.py | 64 | Small immutable derived previews. The API never exposes filesystem pat | I3, I24, I32, I51, I58, I71 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/worker.py | 319 | OS-lock queue, integrity, lazy processors and recovery | I5, I6, I9, I10, I11, I13, I18, I19, I22, I28, I35, I48, I51, I59, I66, I71, I72, I99, I121, I129, I130, I143 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/youtube.py | 186 | Caption-first external sources. Fetching is isolated; snapshots are im | I7, I9, I10, I11, I12, I51, I59, I65, I71, I72, I84, I121, I141, I143 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/youtube_helper.py | 82 | One bounded network helper per submitted YouTube link; no cookies/prox | I10, I22, I59, I72, I88, I121, I141, I147 |
| C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/youtube_media.py | 110 | Student-supplied local video associations for saved YouTube caption so | I7, I14, I59, I94 |
| C:/Users/User/OneDrive/Desktop/Study/services/tests/test_audio.py | 199 | Contracts: audio | I51, I59, I71, I72, I103, I109, I111, I117, I125, I126, I129, I138, I139 |
| C:/Users/User/OneDrive/Desktop/Study/services/tests/test_automatic_vision.py | 151 | Contracts: automatic vision | I59, I71, I109, I117, I124, I126, I129, I138, I139 |
| C:/Users/User/OneDrive/Desktop/Study/services/tests/test_cloud_audio.py | 299 | Contracts: cloud audio | I30, I53, I59, I71, I72, I103, I106, I109, I111, I117, I123, I126, I129, I130, I138, I139 |
| C:/Users/User/OneDrive/Desktop/Study/services/tests/test_cloud_vision.py | 389 | Contracts: cloud vision | I24, I30, I41, I53, I58, I59, I71, I103, I108, I109, I114, I116, I117, I125, I126, I129, I130, I138, I139, I143 |
| C:/Users/User/OneDrive/Desktop/Study/services/tests/test_extraction.py | 332 | Contracts: extraction | I30, I35, I45, I51, I58, I59, I71, I72, I77, I80, I99, I104, I108, I120, I121, I122, I126, I130, I138, I139 |
| C:/Users/User/OneDrive/Desktop/Study/services/tests/test_jobs.py | 283 | Contracts: jobs | I35, I45, I51, I59, I71, I72, I99, I104, I120, I121, I122, I126, I130, I138 |
| C:/Users/User/OneDrive/Desktop/Study/services/tests/test_storage.py | 195 | Contracts: storage | I27, I34, I35, I36, I45, I51, I72, I99, I104, I122, I138, I139 |
| C:/Users/User/OneDrive/Desktop/Study/services/tests/test_video.py | 214 | Contracts: video | I29, I32, I58, I59, I72, I103, I109, I110, I111, I117, I123, I126, I129, I138, I139, I145 |
| C:/Users/User/OneDrive/Desktop/Study/services/tests/test_video_frame_visuals.py | 214 | Contracts: video frame visuals | I51, I59, I103, I106, I110, I117, I125, I126, I127, I129, I138, I139, I143 |
| C:/Users/User/OneDrive/Desktop/Study/services/tests/test_video_frames.py | 189 | Contracts: video frames | I51, I57, I59, I71, I72, I103, I110, I111, I117, I125, I126, I129, I138, I139 |
| C:/Users/User/OneDrive/Desktop/Study/services/tests/test_visual.py | 306 | Contracts: visual | I24, I32, I35, I41, I45, I58, I59, I71, I72, I99, I102, I104, I107, I115, I125, I126, I130, I138, I139, I148, I149 |
| C:/Users/User/OneDrive/Desktop/Study/services/tests/test_youtube.py | 221 | Contracts: youtube | I36, I59, I99, I109, I117, I118, I119, I125, I126, I129, I135, I138, I139 |
| C:/Users/User/OneDrive/Desktop/Study/services/tests/test_youtube_media.py | 110 | Contracts: youtube media | I35, I45, I59, I72, I99, I104, I117, I125, I126, I128, I129, I138, I139 |
| C:/Users/User/OneDrive/Desktop/Study/services/tests/worker_fixture.py | 60 | Subprocess-only fault injection for Phase 4 evaluation. Never used by  | I50, I72, I77, I78, I103, I121, I130 |

### Cycles and layer direction

All AST imports, including deferred imports, form one13-module SCC: audio, cloud_audio, database, extraction, jobs, slides, video, video_frame_visuals, video_frames, visual, visual_assets, youtube, youtube_media. **No eager top-level relative-import cycle**. Examples: audio↔cloud_audio/extraction, database↔jobs/youtube_media, extraction↔video/visual/youtube, slides↔visual, jobs↔youtube.

No domain imports api. db imports job construction/ingestion settings/presentation; jobs imports ingestion/asset presentation; ingestion directly writes worker SQL. Schema mixes tables and API validation. These impede target layer direction; deferred imports currently avoid eager failures. Evidence: module inventory, [database.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/database.py), [jobs.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/jobs.py), [extraction.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/extraction.py).

## 4. Database and migrations

Observed fresh-database head: **0005_youtube_media_links**; nine application tables plus alembic_version. No production database was opened. The following comes from applied migration source and SQLite PRAGMA output in the isolated database, not SQLAlchemy metadata alone.

| Migration | Changes |
| --- | --- |
| [0001_local_storage.py](C:/Users/User/OneDrive/Desktop/Study/services/migrations/versions/0001_local_storage.py) | workspaces, subjects, topics, workspace_sessions, sources, source_versions; source_versions source_id index. |
| [0002_background_jobs.py](C:/Users/User/OneDrive/Desktop/Study/services/migrations/versions/0002_background_jobs.py) | jobs with queue/workspace indexes, ownership/checkpoints/retries and state CHECK. |
| [0003_content_units.py](C:/Users/User/OneDrive/Desktop/Study/services/migrations/versions/0003_content_units.py) | content_units with exact locator, text/hash/status/engine and version index. |
| [0004_visual_content.py](C:/Users/User/OneDrive/Desktop/Study/services/migrations/versions/0004_visual_content.py) | Adds NOT NULL metadata_json DEFAULT '{}' to content_units; no new table. |
| [0005_youtube_media_links.py](C:/Users/User/OneDrive/Desktop/Study/services/migrations/versions/0005_youtube_media_links.py) | youtube_media_links with source/id index and bounded offset CHECK. |

All downgrade functions refuse destructive reversal. Migration environment uses a locked transaction and WAL; app enables foreign_keys and 5000 ms busy_timeout. Applied migrations must remain unchanged. Source: [env.py](C:/Users/User/OneDrive/Desktop/Study/services/migrations/env.py), [database.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/database.py), [schema.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/schema.py).

Tables below list every column, declared indexes (including SQLite PK/unique autoindexes), and foreign keys. Composite FK entries are grouped; all FK updates are NO ACTION.

### alembic_version

Columns: version_num.

Indexes: sqlite_autoindex_alembic_version_1(version_num) UNIQUE.

Foreign keys: none.

### content_units

Columns: id, source_version_id, job_id, ordinal, locator_json, text, text_sha256, status, warning, engine, metadata_json.

Indexes: ix_content_version(source_version_id,ordinal); sqlite_autoindex_content_units_2(source_version_id,ordinal) UNIQUE; sqlite_autoindex_content_units_1(id) UNIQUE.

Foreign keys: (job_id)→jobs(id) ON DELETE RESTRICT; (source_version_id)→source_versions(id) ON DELETE RESTRICT.

### jobs

Columns: id, workspace_id, subject_id, source_version_id, kind, label, state, stage, done, total, checkpoint_json, payload_json, result_json, error, cancel_requested, attempts, failures, max_attempts, recoveries, owner, available_at, created_at, updated_at.

Indexes: ix_jobs_workspace(workspace_id,created_at); ix_jobs_queue(state,available_at,created_at); sqlite_autoindex_jobs_2(kind,source_version_id) UNIQUE; sqlite_autoindex_jobs_1(id) UNIQUE.

Foreign keys: (source_version_id)→source_versions(id) ON DELETE RESTRICT; (workspace_id)→workspaces(id) ON DELETE RESTRICT; (workspace_id,subject_id)→subjects(workspace_id,id) ON DELETE RESTRICT.

### source_versions

Columns: id, source_id, version, filename, sha256, size_bytes, relative_path, state, created_at.

Indexes: ix_source_versions_source_id(source_id); sqlite_autoindex_source_versions_3(source_id,sha256) UNIQUE; sqlite_autoindex_source_versions_2(source_id,version) UNIQUE; sqlite_autoindex_source_versions_1(id) UNIQUE.

Foreign keys: (source_id)→sources(id) ON DELETE RESTRICT.

### sources

Columns: id, workspace_id, subject_id, display_name, name_key, kind, next_version, created_at.

Indexes: sqlite_autoindex_sources_2(workspace_id,subject_id,name_key) UNIQUE; sqlite_autoindex_sources_1(id) UNIQUE.

Foreign keys: (workspace_id,subject_id)→subjects(workspace_id,id) ON DELETE RESTRICT.

### subjects

Columns: workspace_id, id, name, name_key, icon, demo, position.

Indexes: sqlite_autoindex_subjects_2(workspace_id,name_key) UNIQUE; sqlite_autoindex_subjects_1(workspace_id,id) UNIQUE.

Foreign keys: (workspace_id)→workspaces(id) ON DELETE RESTRICT.

### topics

Columns: workspace_id, subject_id, id, title, title_key, description, unit, read, read_minutes, lesson, position.

Indexes: sqlite_autoindex_topics_2(workspace_id,subject_id,title_key) UNIQUE; sqlite_autoindex_topics_1(workspace_id,subject_id,id) UNIQUE.

Foreign keys: (workspace_id,subject_id)→subjects(workspace_id,id) ON DELETE CASCADE.

### workspace_sessions

Columns: workspace_id, layout_json.

Indexes: sqlite_autoindex_workspace_sessions_1(workspace_id) UNIQUE.

Foreign keys: (workspace_id)→workspaces(id) ON DELETE CASCADE.

### workspaces

Columns: id, name, name_key, revision, created_at.

Indexes: sqlite_autoindex_workspaces_2(name_key) UNIQUE; sqlite_autoindex_workspaces_1(id) UNIQUE.

Foreign keys: none.

### youtube_media_links

Columns: id, youtube_source_id, caption_version_id, media_version_id, youtube_start_seconds, created_at.

Indexes: ix_youtube_media_source(youtube_source_id,id).

Foreign keys: (media_version_id)→source_versions(id) ON DELETE RESTRICT; (caption_version_id)→source_versions(id) ON DELETE RESTRICT; (youtube_source_id)→sources(id) ON DELETE RESTRICT.

CHECKs: jobs state∈queued/running/succeeded/partial/failed/cancelled; content status∈text/needs_ocr/empty/unreadable/too_large/suspect; YouTube offset0–14400. youtube_media.py appends associations/detach tombstones and selects newest id; constraints alone do not enforce append-only access. No learner/question/retrieval/external/generated tables.

## 5. Registered API routes versus documented table

Runtime create_app inspection found **31 route objects / 32 method-path pairs**. No OpenAPI/docs routes are enabled. Every route passes bearer authentication; foreign Origin is rejected. The queue-test route remains registered but returns 404 unless allow_eval is enabled. Evidence: [api.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/api.py); runtime output in ignored tmp/audit-runtime.json.

In the table, W=/workspaces/{workspace_id}, V=W/source-versions/{version_id}, S=W/subjects/{subject_id}, J=W/jobs/{job_id}. “Absent” refers specifically to the 16-row route table in [architecture.md](C:/Users/User/OneDrive/Desktop/Study/docs/architecture.md), not adjacent prose. Generic {id} spelling and query parameters are normalized for comparison.

| Method | Path | Handler | Docs table |
| --- | --- | --- | --- |
| GET | /health | health | Present |
| GET | /queue | queue_status | Present |
| GET | /vision | vision_status | Absent |
| GET | /audio | audio_status | Absent |
| POST | V/process-audio | process_audio | Absent |
| POST | V/process-video-frames | process_frames | Absent |
| POST | V/process-frame-visuals | process_frame_visuals | Absent |
| GET | V/video-frames | video_frames | Absent |
| POST | V/cloud-visuals | cloud_visuals | Absent |
| GET | W/jobs | list_jobs | Present |
| GET | J | get_job | Present |
| GET | V/content | content | Present |
| POST | V/verify | verify_original | Present |
| POST | V/process-visuals | process_visuals | Absent |
| POST | J/cancel | cancel_job | Present |
| POST | J/retry | retry_job | Present |
| POST | W/queue-test | test_queue | Present |
| GET | /workspaces | list_workspaces | Present |
| POST | /workspaces | create_workspace | Present |
| GET | W/session | load_session | Present |
| PUT | W/session | save_session | Present |
| GET | S/sources | list_sources | Present |
| POST | S/youtube | import_youtube | Absent |
| GET | V/local-media | read_youtube_media | Absent |
| POST | V/local-media | attach_youtube_media | Absent |
| DELETE | V/local-media | detach_youtube_media | Absent |
| POST | S/sources | upload | Present |
| GET | /source-versions/{version_id}/file | original | Present |
| GET | V/playback | video_playback | Absent |
| HEAD | V/playback | video_playback | Absent |
| GET | /storage | storage | Present |
| POST | /shutdown | stop | Present |

No route-table entry describes a nonexistent route after placeholder/query normalization. **14 method-path pairs are absent** from that table: vision, audio, all three video-frame processing/review endpoints plus process-audio, process-visuals, cloud-visuals, YouTube import, three local-media methods and GET/HEAD playback. Vision/audio/cloud/process-audio appear elsewhere in prose but still need table entries.

Contract mismatches outside that table: cloud schema no longer accepts consent:true (strict extra-forbid CloudVisualRequest); automatic jobs are created after local extraction, contrary to “Import/backfill never creates cloud jobs” when read as a general lifecycle promise. Backfill itself does not launch cloud_visuals. Audio import can upload decoded speech to Groq, contradicting “app import never ... uploads audio”. process-audio supports uploaded video as well as audio. The native bridge does not expose every service endpoint/query option: readContent uses service default limit=1; listJobs omits optional subject/limit; GET-one-job and shutdown are launcher/service operations. Evidence: [schema.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/schema.py), [worker.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/worker.py), [jobs.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/jobs.py), [cloud_audio.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/cloud_audio.py), [storage.cjs](C:/Users/User/OneDrive/Desktop/Study/electron/storage.cjs).

## 6. Electron IPC/preload

[preload.cjs](C:/Users/User/OneDrive/Desktop/Study/electron/preload.cjs) exposes window.studyLens.storage: request, listSources, chooseFiles, importFile, cancelImport, download; each invokes its matching storage:* channel. windowAction accepts minimize/maximize/close; onMaximized subscribes window:maximized with cleanup.

[storage.cjs](C:/Users/User/OneDrive/Desktop/Study/electron/storage.cjs) request actions: listWorkspaces, createWorkspace, loadSession, saveSession, storageInfo, health, queueStatus, visionStatus, audioStatus, importYouTube, openYouTube, readYouTubeMedia, attachYouTubeMedia, detachYouTubeMedia, processCloudVisuals, listJobs, cancelJob, retryJob, verifyOriginal, processVisuals, processAudio, processVideoFrames, processFrameVisuals, readContent, readVideoFrames, createQueueTest.

Storage checks sender/main frame and IDs; opaque tickets expire15min;32selections; streamed upload/download+abort; session1,000,000bytes. No arbitrary path/URL/token bridge. Window actions check sender. [media.cjs](C:/Users/User/OneDrive/Desktop/Study/electron/media.cjs) implements read-only scoped GET/HEAD/range/initiator-checked studylens-media proxy; CSP allows only youtube-nocookie iframe entry. Browser dev fallback uses same-origin /api and Vite host/origin guard.

Preserve %APPDATA%/StudyLens, studylens.sqlite3, STUDYLENS_*, window.studyLens, studylens.session.v1, studylens_service, studylens-media. Evidence: [main.cjs](C:/Users/User/OneDrive/Desktop/Study/electron/main.cjs), [backend.cjs](C:/Users/User/OneDrive/Desktop/Study/electron/backend.cjs), [model.ts](C:/Users/User/OneDrive/Desktop/Study/src/model.ts), [useWorkspace.ts](C:/Users/User/OneDrive/Desktop/Study/src/storage/useWorkspace.ts), [index.html](C:/Users/User/OneDrive/Desktop/Study/index.html), [vite.config.ts](C:/Users/User/OneDrive/Desktop/Study/vite.config.ts).

## 7. Jobs, limits and recovery

| Job kind | Processor / checkpoint |
| --- | --- |
| verify_original | Worker.verify; rehashes immutable original from byte zero on resume. |
| extract_source | extraction.extract dispatches pdf/text/image/slides/audio/video/youtube; atomic per-unit progress. |
| cloud_visuals | cloud_vision.process; per-image provenance/output, quota/fallback counters. |
| video_frames | video_frames.process; completed 30-second windows and retained-frame manifest. |
| video_frame_visuals | video_frame_visuals.process; per-frame OCR/cloud output bound to manifest and source hash. |
| youtube_import | youtube.process then publish; immutable caption/link snapshot before source publication. |
| queue_fixture | Evaluation only; durable completed steps/fault injection, no course evidence. |

Source: [worker.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/worker.py), [jobs.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/jobs.py), [extraction.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/extraction.py) and named processors.

States: queued, running, succeeded, partial, failed, cancelled (DB CHECK). Claim uses BEGIN IMMEDIATE and owner UUID under one OS lock per data root. Claim order deprioritizes cloud_visuals, frame visuals and frame selection behind other due work; extract_source tie-break follows creation time. Not preemptive: an already running local/helper job remains active.

Default failure budget=3; transient failures requeue with min(4,0.3*2^(failures-1)) seconds; PermanentFailure/FileNotFoundError/ValueError/KeyError fail immediately. Attempts count claims, including deferred quota claims; failures control retry budget. Deferred quota/pacing requeues via available_at without occupying the worker. Explicit retry allows failed/cancelled/partial, preserves checkpoints, resets failures; running/succeeded retry is refused. Reprocessing clears version-derived units/checkpoints and cloud jobs, preserving immutable originals/version history. Frame reselection invalidates visual job/results.

Queued cancellation is immediate; running cancellation is checked between units/HTTP polls/native work. Completion checks cancellation inside a transaction. Owner recovery requeues abandoned running jobs or marks requested cancellations; recoveries increments. Parent EOF stops service/worker. Worker shutdown waits 1.5 s before kill; backend shutdown waits 2.5 s after its request. Unexpected worker exit allows three restarts; deliberate exit75 recycles do not consume that budget. Orphan auditing reports old staging/original files (>1h, up to100 paths) and retains them. This is recovery reporting, not automatic cleanup. Evidence: [worker.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/worker.py), [supervisor.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/supervisor.py), [resource_guard.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/resource_guard.py), [backend.cjs](C:/Users/User/OneDrive/Desktop/Study/electron/backend.cjs).

| Resource boundary | Implemented limit / source |
| --- | --- |
| Import/session/UI | 2 GiB original; 32 file selections; 12 tabs; 100 subjects; 300 topics/subject; 20,000 draft characters; request/session caps. api.py, schema.py, electron/storage.cjs, src/model.ts. |
| Parent parser worker | Sampled 512 MiB private-memory budget, 30-second heartbeat timeout; uncooperative cancellation after1s commits state then exit75. resource_guard.py. |
| Native helpers | Default512 MiB Windows child-tree job cap,20s,4MiB stdout/stderr files; LibreOffice30s; ASR1536 MiB/25s; VAD512 MiB/10s; frame analysis15s; caption helper45s. local_tools.py, slides.py, audio.py, video_frames.py, youtube.py. Non-Windows hard memory cap is absent. |
| PDF/text | PDF/slide/image source64MiB, PDF500pages,1MiB page stream,50,000 extracted page chars; text16MiB/4,000-char units. extraction.py. |
| OCR/slides/previews | Image40M pixels/100TIFF pages; OCR4M pixels/2500edge/5000words; slide ZIP5000entries/100MiB expansion/10MiB read part/500slides; preview512KiB and <=4 returned assets/unit. visual.py, slides.py, visual_assets.py. |
| Audio/video | <=4h,30s mono16kHz PCM windows,1MiB upload/preview budget; original container timeline and bounded validated speech segments. audio.py, video.py, cloud_audio.py. |
| Frames | 1-second sampling,30-second windows,<=32 candidates/window,<=20 retained/window with global600 cap and quota spread; review4frames/page; OCR8,000 chars/frame; cloud12/pass and1/window. video_frames.py, video_frame_visuals.py, jobs.py. |
| Groq vision | 1280edge resized PNG,20s HTTP/23s overall,2MiB response,1536tokens or4096 fallback;65s persisted request spacing; bounded quota waits/fallback. cloud_vision.py, video_frame_visuals.py. |
| Groq ASR | 20s HTTP/23s overall,2MiB response;3.2s pacing; conservative7000audio-sec/hour,28000/day,1900requests/day,>=10sec/request accounting; local fallback or bounded quota waits. cloud_audio.py, audio.py. |
| YouTube | 10 active imports/subject;4MiB snapshot;30,000 cues/200tracks/4h clock; HTTPS helper5s connect/10s read/8MiB response. youtube.py, youtube_helper.py, jobs.py. |

These are code caps, not measured whole-app RAM or target-laptop responsiveness. Helpers can coexist with the parent worker/service/Electron and Ollama is independently hosted.

## 8. Python and npm dependencies

No analysis dependency was installed. Checked all 81 tracked Python ASTs (including deferred imports), JS/TS/CSS bare specifiers, package scripts/config, distribution→import-name mapping and installed Requires-Dist with default markers/extras filtered. Static absence is not proof of non-use: SQLAlchemy loads aiosqlite dynamically, greenlet supports its async bridge, and many locks are transitive. Versions below are lock declarations checked against installed app .venv metadata; all 50 matched. Only installed extra distribution was pip25.0.1. Optional-extra requirements were not counted as evidence of necessity.

R=direct service/migration import; A=setup/test/evaluation import; T=required by a locked distribution with default markers; D=dynamic use. No Python package is proven removable. aiosqlite and greenlet have no static app import/default parent under this metadata configuration but are required by the selected async SQLite/SQLAlchemy path. Dependencies of retired experiments remain isolated under ignored tmp; they are not app locks.

Sources: {services/requirements-lock.txt}, [database.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/database.py), [package.json](C:/Users/User/OneDrive/Desktop/Study/package.json), [package-lock.json](C:/Users/User/OneDrive/Desktop/Study/package-lock.json), [vite.config.ts](C:/Users/User/OneDrive/Desktop/Study/vite.config.ts), [tsconfig.json](C:/Users/User/OneDrive/Desktop/Study/tsconfig.json); generated metadata evidence: ignored tmp/audit-inventory.json and tmp/audit-runtime.json.

| Python lock | Version | Use (module stems resolve above) |
| --- | --- | --- |
| aiosqlite | 0.22.1 | D:async SQLAlchemy/SQLite |
| alembic | 1.20.0 | R:env,0001_local_storage,0002_background_jobs,0003_content_units,0004_visual_content,0005_youtube_media_links,database; A:test_storage |
| annotated-doc | 0.0.5 | T:fastapi |
| annotated-types | 0.8.0 | T:pydantic |
| anyio | 4.15.1 | T:httpx,starlette |
| certifi | 2026.7.22 | T:httpcore,httpx,requests |
| click | 8.5.0 | T:uvicorn,huggingface-hub,scenedetect-headless |
| fastapi | 0.142.2 | R:api; A:benchmark-audio-speed,evaluate-audio,evaluate-cloud-audio,evaluate-desktop-vision,evaluate-hinglish,evaluate-video-frame-visuals,evaluate-video-frames,evaluate-video,evaluate-youtube,test_extraction,test_jobs,test_storage,test_visual,test_youtube_media |
| greenlet | 3.5.6 | D:async SQLAlchemy/SQLite |
| h11 | 0.16.0 | T:httpcore,uvicorn |
| httpcore | 1.0.9 | T:httpx |
| httpx | 0.28.1 | R:cloud_audio,cloud_vision; A:benchmark-audio-speed,test_cloud_audio,test_cloud_vision; T:huggingface-hub |
| idna | 3.20 | T:anyio,httpx,requests |
| Mako | 1.4.3 | T:alembic |
| MarkupSafe | 3.0.3 | T:Mako |
| opentelemetry-api | 1.45.0 | T:fastapi |
| pydantic | 2.13.5 | R:cloud_vision,schema; T:fastapi |
| pydantic_core | 2.46.5 | T:pydantic |
| pypdf | 6.19.0 | R:extraction; A:generate,test_extraction,worker_fixture |
| pypdfium2 | 5.13.0 | R:slides,visual |
| Pillow | 12.3.0 | R:cloud_vision,slides,video_frames,visual,visual_assets; A:generate,generate,create-frame-fixtures,evaluate-desktop-routing,evaluate-hunyuan,evaluate-lighton,evaluate-omni-local,evaluate-small-ocr,evaluate-vision-routing,prepare-omni,test_cloud_vision,test_visual |
| defusedxml | 0.7.1 | R:slides; A:test_cloud_vision,test_visual; T:youtube-transcript-api |
| SQLAlchemy | 2.1.1 | R:env,0001_local_storage,0002_background_jobs,0003_content_units,0004_visual_content,0005_youtube_media_links,database,jobs,schema,youtube_media; T:alembic |
| starlette | 1.7.0 | R:api; T:fastapi |
| typing-inspection | 0.4.4 | T:fastapi,pydantic |
| typing_extensions | 4.16.0 | T:alembic,anyio,fastapi,opentelemetry-api,pydantic,pydantic_core,SQLAlchemy,starlette,typing-inspection,huggingface-hub |
| uvicorn | 0.54.0 | R:__main__ |
| faster-whisper | 1.2.1 | R:audio_helper,audio_vad_helper; A:benchmark-audio-vad |
| av | 16.1.0 | T:faster-whisper |
| ctranslate2 | 4.8.2 | T:faster-whisper |
| huggingface-hub | 1.33.0 | A:evaluate-hinglish,evaluate-omni,evaluate-small-ocr,prepare-omni,setup-audio; T:faster-whisper,tokenizers |
| tokenizers | 0.23.2 | T:faster-whisper |
| onnxruntime | 1.30.0 | A:evaluate-small-ocr; T:faster-whisper |
| numpy | 2.5.3 | R:audio_vad_helper,video_frames_helper; A:benchmark-audio-vad,evaluate-small-ocr,evaluate-vision-routing; T:ctranslate2,onnxruntime,scenedetect-headless,opencv-python-headless |
| PyYAML | 6.0.3 | A:evaluate-small-ocr,score-omni-docs; T:ctranslate2,huggingface-hub |
| filelock | 4.0.9 | T:huggingface-hub |
| fsspec | 2026.9.0 | T:huggingface-hub |
| hf-xet | 1.6.0 | T:huggingface-hub |
| packaging | 26.3 | T:huggingface-hub,onnxruntime |
| protobuf | 7.36.2 | T:onnxruntime |
| flatbuffers | 25.12.19 | T:onnxruntime |
| tqdm | 4.70.1 | T:faster-whisper,huggingface-hub,scenedetect-headless |
| colorama | 0.4.6 | T:tqdm |
| scenedetect-headless | 0.7.1 | R:video_frames_helper |
| opencv-python-headless | 4.13.0.92 | R:video_frames_helper; A:evaluate-vision-routing; T:scenedetect-headless |
| platformdirs | 4.9.6 | T:scenedetect-headless |
| youtube-transcript-api | 1.2.4 | R:youtube_helper |
| requests | 2.34.2 | R:youtube_helper; T:youtube-transcript-api |
| charset-normalizer | 3.5.2 | T:requests |
| urllib3 | 2.8.0 | T:requests |

| npm declaration | Version | Use |
| --- | --- | --- |
| @fontsource/inter | 5.3.0 | main.tsx CSS |
| lucide-react | 1.49.0 | Renderer icons |
| react | 19.3.0 | Renderer/hooks |
| react-dom | 19.3.0 | main.tsx createRoot |
| @tailwindcss/vite | 4.3.3 | vite.config.ts plugin |
| @types/node | 26.6.3 | tsconfig types=node/tests/config |
| @types/react | 19.3.0 | TSX/React declarations |
| @types/react-dom | 19.3.0 | react-dom/client declaration |
| @vitejs/plugin-react | 6.1.1 | vite.config.ts plugin |
| electron | 44.5.1 | Main/preload/launch/smoke/evaluators |
| tailwindcss | 4.3.3 | styles.css @import |
| typescript | 7.0.2 | package build tsc |
| vite | 8.3.1 | Config/dev/build |

All13 npm direct declarations have runtime/build/type evidence; none looks safely unused. package-lock retains transitive reproducibility. Full transitive npm runtime tracing: UNVERIFIED.

## 9. Actual test runs

| Required command | Actual result |
| --- | --- |
| npm.cmd run api:test | PASS:165 tests in188.887s; no failures/errors/skips reported. Log: ignored tmp/audit-api-tests.log. |
| npm.cmd run check | PASS:15 JS tests,0fail/0cancel/0skip/0todo;344.8581ms test runner. tsc --noEmit passed; Vite8.3.1 production build passed in1.50s (1909 transformed modules). Log: ignored tmp/audit-check.log. |
| npm.cmd run smoke:desktop | PASS:STUDYLENS_SMOKE_OK; production renderer isolated, bridge available, session persisted, WAL/head0005/one worker, native text page2, OCR partial/review preview, invalid cloud provider rejected, reprocessing preserved unit. Log: ignored tmp/audit-smoke.log. |

Smoke is one scripted desktop gate, not a reported unit-test count. It uses tmp/electron-smoke and writes a historical screenshot; the original screenshot bytes were backed up and restored, SHA256 equality confirmed. Production student data was not used. Cloud key is excluded in the smoke launcher. Sources: [smoke.mjs](C:/Users/User/OneDrive/Desktop/Study/scripts/smoke.mjs), [main.cjs](C:/Users/User/OneDrive/Desktop/Study/electron/main.cjs), [package.json](C:/Users/User/OneDrive/Desktop/Study/package.json).

Python groups (counts from actual unittest output checked against AST test names):

| Python group | Tests | Coverage |
| --- | --- | --- |
| [test_audio.py](C:/Users/User/OneDrive/Desktop/Study/services/tests/test_audio.py) | 11 | Decode/formats/silence/time/resume/setup/corruption |
| [test_automatic_vision.py](C:/Users/User/OneDrive/Desktop/Study/services/tests/test_automatic_vision.py) | 9 | Queue/key/opt-out/dedup/priority/local evidence |
| [test_cloud_audio.py](C:/Users/User/OneDrive/Desktop/Study/services/tests/test_cloud_audio.py) | 18 | Multipart/cache/VAD/fallback/quota/validation/cancel |
| [test_cloud_vision.py](C:/Users/User/OneDrive/Desktop/Study/services/tests/test_cloud_vision.py) | 20 | Provider/shape/tables/routing/cache/quota/rebuild |
| [test_extraction.py](C:/Users/User/OneDrive/Desktop/Study/services/tests/test_extraction.py) | 18 | PDF/text locators/limits/encoding/integrity/recycle |
| [test_jobs.py](C:/Users/User/OneDrive/Desktop/Study/services/tests/test_jobs.py) | 16 | Claims/retries/locks/restart/EOF/supervisor/orphans |
| [test_storage.py](C:/Users/User/OneDrive/Desktop/Study/services/tests/test_storage.py) | 13 | Migrations/WAL/CRUD/revisions/auth/versions/integrity |
| [test_video.py](C:/Users/User/OneDrive/Desktop/Study/services/tests/test_video.py) | 12 | Timeline/silence/corruption/reprocess/playback/ranges |
| [test_video_frame_visuals.py](C:/Users/User/OneDrive/Desktop/Study/services/tests/test_video_frame_visuals.py) | 7 | OCR/provenance/mock cloud/manifest/resume |
| [test_video_frames.py](C:/Users/User/OneDrive/Desktop/Study/services/tests/test_video_frames.py) | 10 | Slide/board/static/VFR/rotation/budgets/windows |
| [test_visual.py](C:/Users/User/OneDrive/Desktop/Study/services/tests/test_visual.py) | 16 | OCR/previews/PPTX/OMML/unsafe/helper/Ollama |
| [test_youtube.py](C:/Users/User/OneDrive/Desktop/Study/services/tests/test_youtube.py) | 13 | Links/snapshots/cues/tracks/versions/scope/errors |
| [test_youtube_media.py](C:/Users/User/OneDrive/Desktop/Study/services/tests/test_youtube_media.py) | 2 | Separate versions/scope/offset/type/integrity |

JS groups: [imports.test.ts](C:/Users/User/OneDrive/Desktop/Study/tests/imports.test.ts)3 (scope/cancel/partial failure); [session.test.ts](C:/Users/User/OneDrive/Desktop/Study/tests/session.test.ts)7 (tabs/drafts/validation/caps); [writer.test.ts](C:/Users/User/OneDrive/Desktop/Study/tests/writer.test.ts)3 (serialization/coalescing/retry/conflict); [youtube.test.ts](C:/Users/User/OneDrive/Desktop/Study/tests/youtube.test.ts)2 (URL guard/browser+IPC scope).

CORRECTION 2026-10-03 (B1): this line previously named model.test.ts. No such file exists; the group tests session state in src/model.ts, and the file is tests/session.test.ts. The §1 tree was right and this line was wrong. Fixed.

NOTE ON PATHS IN THIS REPORT: the absolute `C:/.../scripts/*.py` and `docs/evaluation/*` paths above record the layout as it stood at baseline `4deb661` and are left unchanged as evidence. The B1 cleanup since moved scripts/ingestion-evals/*, tests/fixtures/ingestion/* and docs/archive/ingestion-pilots/*. Every route, size, table and count in this report still describes the same code.

Cloud and many ASR outputs are mocked; native decoding/OCR/frame tests run actual tools. No live quality or coverage percentage established. TestClient emits an httpx deprecation warning; no dependency changed. No skips in A. Historical {docs/evaluation/phase-07b-service-first.log}:143tests,2failures (queue completion timeout; frame native helper failure); both pass in A. Root cause/repeatability: UNVERIFIED.

Pending student checks: natural frame/OCR/Groq and Hindi/Hinglish accuracy, seeking/cancel/restart, inaccessible/embedding-disabled YouTube and local-copy alignment, whole-app8GB responsiveness. No manual acceptance asserted.

## 10. Complete docs and root inventory

169tracked docs +1untracked historical test log +11root files=181 before this report. Dates: git log -1 --format=%aI; not experiment dates. This report adds row182. No files moved/deleted.

KEEP=active setup/config/fixtures. MERGE=consolidate current contracts, retain originals/history. ARCHIVE=retain historical reports/results/screenshots/raw evidence. DELETE requires proven expendable generated/duplicate content; none recommended in this inventory. TrackD writeup references and binary fidelity: UNVERIFIED.

Stale/contradictory:
- [architecture.md](C:/Users/User/OneDrive/Desktop/Study/docs/architecture.md): old consent/automatic-cloud/audio-never-upload statements and incomplete routes; code schema/worker/cloud_audio supersedes these.
- [NEXT_CONTEXT_PROMPT.md](C:/Users/User/OneDrive/Desktop/Study/docs/NEXT_CONTEXT_PROMPT.md): says implement7C/156tests; frame visuals already implemented/current165.
- [PHASES.md](C:/Users/User/OneDrive/Desktop/Study/docs/PHASES.md): mixes dated pending7C/7D/consent milestones with newer implementation entries.
- [CONTEXT_HANDOFF.md](C:/Users/User/OneDrive/Desktop/Study/docs/CONTEXT_HANDOFF.md): shorten historical context; no implemented-feature contradiction established in current continuation.
- [README.md](C:/Users/User/OneDrive/Desktop/Study/README.md): retains useful setup/disclosure; local no-key mode remains possible.
- Dated evaluation reports describe historical configurations, not current runtime; preserve results with superseding links.
- UI [StorageSettings.tsx](C:/Users/User/OneDrive/Desktop/Study/src/StorageSettings.tsx) and audio.py still say on-screen extraction pending; separate frame visuals exist. Settings hardcodes WAL status; future approved correction should derive it from health.

| Absolute file path | Bytes | Last commit date | Class | Reason |
| --- | --- | --- | --- | --- |
| C:/Users/User/OneDrive/Desktop/Study/.gitignore | 168 | 2026-10-03 | KEEP | Cache/data/secret exclusions |
| C:/Users/User/OneDrive/Desktop/Study/LICENSE | 1,091 | 2026-10-03 | KEEP | Project license |
| C:/Users/User/OneDrive/Desktop/Study/Neev.lnk | 2,702 | 2026-10-03 | KEEP | Current launch; portability UNVERIFIED |
| C:/Users/User/OneDrive/Desktop/Study/README.md | 15,834 | 2026-10-03 | KEEP | Setup/current scope; refresh links |
| C:/Users/User/OneDrive/Desktop/Study/StudyLens-Design-Prompt.txt | 12,518 | 2026-10-03 | MERGE | Design/contracts; preserve original |
| C:/Users/User/OneDrive/Desktop/Study/StudyLens.lnk | 2,708 | 2026-10-03 | ARCHIVE | Historical launch; target UNVERIFIED |
| C:/Users/User/OneDrive/Desktop/Study/docs/CONTEXT_HANDOFF.md | 12,742 | 2026-10-03 | MERGE | Short handoff; archive history |
| C:/Users/User/OneDrive/Desktop/Study/docs/NEXT_CONTEXT_PROMPT.md | 2,200 | 2026-10-03 | MERGE | STALE: says implement completed7C |
| C:/Users/User/OneDrive/Desktop/Study/docs/PHASES.md | 15,921 | 2026-10-03 | MERGE | STALE current/history mix |
| C:/Users/User/OneDrive/Desktop/Study/docs/architecture.md | 21,849 | 2026-10-03 | MERGE | CONTRADICTS cloud/audio/schema/routes |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/audio-desktop.json | 439 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/audio-integration-20261002-041044.json | 19,495 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/audio-speed.json | 69,166 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/audio-speed.md | 6,306 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/automatic-groq-ui.json | 180 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/automatic-groq.md | 4,513 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/cloud-audio-20261002-193932.json | 55,857 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/cloud-audio-20261002-194327.json | 30,778 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/cloud-audio-desktop.json | 617 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/cloud-extracted-text-ui.json | 403 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/desktop-routing-results.json | 3,445 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/desktop-vision-20261001-172849.json | 5,715 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-02-notes-v2.txt | 228 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-02-notes.txt | 202 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-04/corrupt-notes.pdf | 56 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-04/digital-notes.pdf | 3,159 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-04/encrypted-notes.pdf | 3,186 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-04/generate.py | 3,559 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-04/gold.json | 1,072 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-04/mixed-language.txt | 140 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-04/mixed-notes.pdf | 22,385 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-05/blank.png | 1,961 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-05/corrupt.png | 44 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-05/equation.png | 30,885 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-05/figure.png | 33,578 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-05/generate.py | 7,338 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-05/gold.json | 1,045 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-05/ordered-visuals.pptx | 28,992 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-05/oriented-scan.jpg | 51,011 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-05/scan.png | 36,082 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-05/scanned-visuals.pdf | 100,726 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-05/two-pages.tiff | 121,008 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-06/clean.flac | 188,123 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-06/clean.m4a | 73,239 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-06/clean.mp3 | 37,948 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-06/clean.ogg | 46,108 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-06/clean.wav | 413,178 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-06/corrupt.wav | 50 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-06/gold.json | 655 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-06/intervals.wav | 2,866,544 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-06/noisy.wav | 413,176 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-06/silence.wav | 220,544 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-06/tone.wav | 220,544 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07/corrupt.mp4 | 46 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07/delayed-audio.mp4 | 838,603 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07/gold.json | 439 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07/intervals.mp4 | 2,664,879 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07/lecture.mkv | 838,032 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07/lecture.mp4 | 838,587 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07/no-audio.mp4 | 198,633 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07/short-audio-long-video.mp4 | 2,597,708 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/board-0.png | 8,594 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/board-1.png | 12,812 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/board-2.png | 15,735 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/board-3.png | 20,323 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/board-4.png | 23,587 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/gold.json | 586 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/return-slides.mp4 | 60,724 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/return-slides.txt | 114 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/rotate-base.mp4 | 43,039 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/rotate-base.txt | 82 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/rotated.mp4 | 43,039 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/slide-a.png | 10,716 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/slide-b.png | 12,291 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/slide-c.png | 21,784 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/slides.mp4 | 75,243 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/slides.txt | 114 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/static.mp4 | 49,322 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/static.txt | 51 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/vfr.mp4 | 43,750 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/vfr.txt | 120 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/video-ends-first.mp4 | 232,094 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/whiteboard.mp4 | 43,356 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/fixtures/phase-07b/whiteboard.txt | 178 | 2026-10-03 | KEEP | Regression fixture/truth/generator |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/gemma4-audio-scores.json | 3,761 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/gemma4-audio.json | 186,863 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/gemma4-documents-280.json | 140,536 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/gemma4-omni-summary.json | 10,707 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/gemma4-omni.md | 14,466 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/gemma4-pilot-scores.json | 1,228 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/gemma4-pilot.json | 24,520 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/gemma4-vision-280.json | 15,335 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/groq-format-fallback-20261001-181237.json | 611 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/groq-format-fallback-20261002-034941.json | 718 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/groq-vision-checks.json | 7,034 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/groq-vision-dedup-json-results.json | 12,943 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/groq-vision-results.json | 16,949 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/groq-vision.md | 6,933 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/hinglish-asr.md | 5,606 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/hinglish-hardware.json | 132 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/hinglish-manifest.json | 69,996 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/hinglish-results-20261002-043540.json | 19,717 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/hinglish-results-20261002-044052.json | 267,393 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/hinglish-summary.json | 7,354 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/hunyuan-local-results.json | 15,040 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/hunyuan-local.md | 7,506 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/lighton-gpu-documents-1280.json | 49,514 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/lighton-gpu-pilot-1280.json | 17,708 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/lighton-ocr.md | 2,111 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/lighton-pilot-1280.json | 8,499 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/lighton-setup.json | 2,867 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/llamaindex-docs-pilot.json | 6,673 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/llamaindex-docs-pilot.md | 5,625 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/native-table-deck.json | 2,203 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/ocr-cleanup.json | 1,388 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/ocr-cleanup.md | 1,820 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/omnidoc-local-baseline.json | 3,230,782 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/phase-01.md | 4,738 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/phase-02.md | 6,151 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/phase-03.md | 6,658 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/phase-04.md | 8,937 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/phase-05-cloud-vision.md | 14,607 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/phase-05.md | 10,586 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/phase-06-cloud-audio.md | 7,605 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/phase-06.md | 9,513 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/phase-07a.md | 7,679 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/phase-07b-service-first.log | 23,714 | UNTRACKED | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/phase-07b.md | 9,645 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/phase-07c.md | 5,912 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/phase-07d-media.md | 5,113 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/phase-07d-youtube.md | 8,615 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/retired-ocr-evidence.zip | 7,734,565 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/automatic-groq-desktop.png | 88,851 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/cloud-audio-desktop.png | 84,672 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/cloud-extracted-text-desktop.png | 83,703 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/phase-01-workspace-browser.jpg | 34,708 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/phase-01-workspace.png | 82,105 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/phase-02-materials-browser.jpg | 19,044 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/phase-02-workspace-desktop.png | 82,808 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/phase-03-materials-browser.png | 28,886 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/phase-03-workspace-desktop.png | 82,808 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/phase-04-ocr-browser.png | 29,167 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/phase-04-text-browser.png | 31,638 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/phase-04-workspace-desktop.png | 84,975 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/phase-05-cloud-desktop.png | 88,724 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/phase-05-slide-browser.png | 27,940 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/phase-05-visual-browser.png | 24,970 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/phase-05-workspace-desktop.png | 84,227 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/phase-06-audio-desktop.png | 79,448 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/phase-07a-video-desktop.png | 141,484 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/phase-07b-frames-desktop.png | 121,081 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/phase-07c-cloud-frame-desktop.png | 137,563 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/phase-07c-frame-text-desktop.png | 135,228 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/youtube-desktop.png | 84,357 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/screenshots/youtube-media-desktop.png | 103,362 | 2026-10-03 | ARCHIVE | Historical visual evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/small-ocr-matrix.md | 7,209 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/small-ocr-results.json | 6,311,221 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/small-ocr.md | 18,707 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/video-desktop.json | 1,461 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/video-frames-20261003-074347.json | 8,739 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/video-frames-20261003-074535.json | 23,153 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/video-frames-20261003-074703.json | 24,239 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/video-frames-20261003-075439.json | 26,142 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/video-frames-20261003-080329.json | 26,511 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/video-frames-desktop.json | 529 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/video-integration-20261003-070850.json | 41,908 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/video-integration-20261003-071221.json | 42,925 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/video-visuals-20261003-104402.json | 789 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/video-visuals-20261003-104845.json | 933 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/video-visuals-cloud-desktop.json | 460 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/video-visuals-desktop.json | 404 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/vision-routing-results.json | 4,903 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/youtube-20261003-083018.json | 6,859 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/youtube-desktop.json | 653 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/evaluation/youtube-media-desktop.json | 456 | 2026-10-03 | ARCHIVE | Historical report/result/evidence |
| C:/Users/User/OneDrive/Desktop/Study/docs/youtube-ingestion-plan.md | 7,735 | 2026-10-03 | MERGE | Source decisions; policy not reverified |
| C:/Users/User/OneDrive/Desktop/Study/index.html | 686 | 2026-10-03 | KEEP | Active root entry/config/lock |
| C:/Users/User/OneDrive/Desktop/Study/package-lock.json | 84,664 | 2026-10-03 | KEEP | Active root entry/config/lock |
| C:/Users/User/OneDrive/Desktop/Study/package.json | 2,495 | 2026-10-03 | KEEP | Active root entry/config/lock |
| C:/Users/User/OneDrive/Desktop/Study/tsconfig.json | 436 | 2026-10-03 | KEEP | Active root entry/config/lock |
| C:/Users/User/OneDrive/Desktop/Study/vite.config.ts | 1,692 | 2026-10-03 | KEEP | Active root entry/config/lock |
| C:/Users/User/OneDrive/Desktop/Study/docs/audit/CURRENT_ARCHITECTURE.md | 122147 | Phase A new | KEEP | This audit; no earlier commit |

Only exact docs/root duplicate pair: phase-02/phase-03 workspace screenshots. Retired evidence ZIP retained. No tracked evaluation evidence has DELETE classification.

## 11. Dead/experimental candidates

Static methods: module callers, helper/entrypoint invocation, tracked filename/stem references and SHA256 duplicates. No proven dead production module or removable app dependency.

| Candidate | Evidence / disposition |
| --- | --- |
| scripts/evaluate-lighton.py | No other tracked filename/stem reference; standalone stopped Ollama pilot. ARCHIVE with results. |
| scripts/create-audio-fixtures.py | No tracked filename/stem reference; regression fixture generator. MOVE with evaluation tooling, keep fixtures. |
| Hunyuan/SmallOCR/Omni scripts | Standalone model/download/scoring paths, absent app runtime graph. ARCHIVE scripts/results/retired-ocr-evidence.zip; no resumed experiments. |
| evaluate-vision-routing.py | Prototype uses retired PP-OCR outputs; production uses cloud_vision.route/Tesseract. ARCHIVE. |
| evaluate-llamaindex-docs.py | Isolated llama_index/documentation BM25 runner; no app lock/import. MOVE to evaluation, retain pilot. |
| Active ingestion/native evaluators | Many call Worker/internal SQL directly; retain and plan public-interface migration. |
| phase-02/phase-03 workspace screenshots | Only byte-identical docs/root pair. ARCHIVE both until downstream references reviewed. |
| phase-07b-service-first.log | Untracked143-test/2-failure evidence. ARCHIVE; do not discard as a generic log. |
| StudyLens.lnk | Historical machine shortcut; target UNVERIFIED. ARCHIVE after review; current Neev.lnk retained. |
| Ignored tmp/dist/caches/venvs/models | Disk sizes in section1; may hold raw evidence/data. No blanket deletion. |

Evidence: module/reference/hash inventories, [package.json](C:/Users/User/OneDrive/Desktop/Study/package.json), [worker.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/worker.py), corresponding scripts and docs inventory. Zero-import helpers/__main__/__init__ are not dead-code proof.

## 12. Target architecture gaps

| Target | As built / gap |
| --- | --- |
| Processes | Required renderer/preload/main/loopback/WAL/single-worker boundaries exist; sections2/6/7. |
| Python layout | Flat modules; no routers/registry/config.py. database mixes CRUD/job/presentation; schema mixes DB/API. |
| knowledge/eligibility | Missing chunking/embedding/FTS/vector/retrieval/graph and one eligibility gate. database.content is inspection, returns status/warnings/integrity, including unfinished/suspect units. |
| grounding | Missing answer composition/citations/verifier/five evidence-state contract. Existing source locators are foundations. |
| tutor/assessment/learner | Missing production logic/tables/routers and append-only learner events/estimators/FSRS/calibration/schedules. Ask disabled; Practice/Today labelled future. |
| Provenance | Immutable versions/hashes/locators, unverified metadata/frame checkpoints, separate caption/local versions exist. External-web/generated tables absent. Deliberately imported YouTube captions are course sources. |
| Invalidation | Rebuild clears units/cloud job; deterministic IDs return; resume checks audio config/frame manifest. No future index/learner invalidation layer yet. |
| providers/prompts | Embedded httpx Groq/urllib Ollama/transcript client, no own shared/official-provider interfaces. Groq vision stores prompt_version; ASR stores engine/config/model. Ollama stores model/text without prompt revision: violation. No app LiteLLM/LangChain/LlamaIndex. |
| Permissions | Automatic configured Groq disclosed, stale docs/UI noted. Search absent; tested per-question/per-assessment consent flow absent. No voice tutor. |
| Renderer | Flat App/review components/storage; typed client/hooks exist, styles.css variables exist, no target folders/tokens.css/general virtualization. |
| Evaluation | scripts+docs/evaluation exist; no top-level evaluation. Several isolated runners directly use Worker/internal DB, violating public-interface-only target. No scored Ragas/simulated learner benchmark. |
| UI evidence | Reading counts derive from session; Not assessed mastery; demo recommendation disclosed; demo readMinutes are authored, not measured. WAL text hardcoded. |
| Docs/packaging |169tracked docs with history/evidence; target grounding/learner/evaluation/decisions docs absent; package scripts do not build installer. |

Evidence: tree/import/schema/route inventories; [App.tsx](C:/Users/User/OneDrive/Desktop/Study/src/App.tsx), [model.ts](C:/Users/User/OneDrive/Desktop/Study/src/model.ts), [StorageSettings.tsx](C:/Users/User/OneDrive/Desktop/Study/src/StorageSettings.tsx), [styles.css](C:/Users/User/OneDrive/Desktop/Study/src/styles.css), [database.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/database.py), [visual.py](C:/Users/User/OneDrive/Desktop/Study/services/studylens_service/visual.py), [evaluate-video.py](C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-video.py), [evaluate-hinglish.py](C:/Users/User/OneDrive/Desktop/Study/scripts/evaluate-hinglish.py), [package.json](C:/Users/User/OneDrive/Desktop/Study/package.json). No missing milestone implemented in A.

## 13. Risks/unknowns

- UNVERIFIED: production migration/data history, TrackD references, student acceptance, natural accuracy, live quotas/retention, YouTube policy/access, whole-app8GB performance.
- B3 must preserve deferred imports, helper -m names, PYTHONPATH, migration/model-path calculations. IDs alone cannot identify reprocessed evidence.
- Worker sampled512MiB and separate ASR1536MiB caps are not whole-app budgets; external Ollama/non-Windows helper memory remains outside those guarantees.
- Remote transfers may process/bill after cancellation; uncommitted retries can repeat sends. Filesystem mutation races and retained orphan/derived artifacts remain.
- Migration-created indexes exceed declared schema metadata; inspect migrated DB. NULL-version jobs rely on code import caps. cloud_vision budget corruption resets pacing deadline; audio ledger fails closed.
- One actual run proves no reliability rate; historical failures retained. Dynamic/transitive imports prevent confident unused-dependency deletion. Full supply-chain/license/security/network tracing not performed.
- Only Phase A: separate commit/push, then STOP for written approval. B1–B7 require individual go-aheads.

## Exact commands run

PowerShell in C:\Users\User\OneDrive\Desktop\Study. Read statements are grouped below for navigation; independent batches ran concurrently. No install, live provider evaluation, source restructuring or production-DB command was run. Tool-side temporary artifact rendering and snapshot byte restore are identified explicitly.

### Request, Git baseline and initial inventory

```powershell
Get-Content 'C:\Users\User\.codex\attachments\30cabb0c-083e-42b6-8302-2e4a9242520a\Pasted text.txt'
git status --short --branch
rg --files -g AGENTS.md -g '!node_modules' -g '!tmp' -g '!.venv' -g '!dist' -g '!.git'
git switch -c cleanup/architecture-reset
git ls-files
Get-Content package.json; Get-Content services\requirements-lock.txt
rg --files electron src services scripts tests -g '!__pycache__/**'
Get-Content .gitignore; Get-Content vite.config.ts
```

### Required checks and byte-preserving smoke

```powershell
npm.cmd run api:test *> tmp\audit-api-tests.log; exit $LASTEXITCODE
npm.cmd run check *> tmp\audit-check.log; exit $LASTEXITCODE
$shotPath = (Resolve-Path 'docs\evaluation\screenshots\phase-05-workspace-desktop.png').Path; $shotBackup = Join-Path (Get-Location) 'tmp\audit-smoke-screenshot-original.png'; Copy-Item -LiteralPath $shotPath -Destination $shotBackup; $beforeHash = (Get-FileHash -LiteralPath $shotPath -Algorithm SHA256).Hash; try { npm.cmd run smoke:desktop *> tmp\audit-smoke.log; $smokeExit = $LASTEXITCODE } finally { Copy-Item -LiteralPath $shotBackup -Destination $shotPath -Force }; $afterHash = (Get-FileHash -LiteralPath $shotPath -Algorithm SHA256).Hash; Write-Output "Smoke exit: $smokeExit; screenshot restored: $($beforeHash -eq $afterHash)"; exit $smokeExit
```

### Stdlib inventory / installed metadata (exact inline script)

```powershell
$auditCode = @'
import ast, collections, hashlib, importlib.metadata as md, json, os, re, subprocess
from pathlib import Path
root=Path.cwd()
tracked=subprocess.check_output(['git','ls-files','-z']).decode().split('\0')[:-1]
info={}
for name in tracked:
    p=root/name
    b=p.read_bytes()
    info[name]={'bytes':len(b),'lines':len(b.splitlines()) if p.suffix.lower() in ('.py','.ts','.tsx','.css','.cjs','.mjs','.md','.txt','.html','.json') else None}
top={}
for name,v in info.items():
    key=name.split('/')[0] if '/' in name else '(root files)'
    row=top.setdefault(key,{'count':0,'bytes':0})
    row['count']+=1;row['bytes']+=v['bytes']
disk={}
for entry in root.iterdir():
    if entry.is_dir():
        n=size=errors=0
        for folder,dirs,files in os.walk(entry,followlinks=False):
            dirs[:]=[d for d in dirs if not Path(folder,d).is_symlink()]
            for f in files:
                try:size+=Path(folder,f).stat().st_size;n+=1
                except OSError:errors+=1
        disk[entry.name]={'count':n,'bytes':size,'errors':errors}
sources=sorted([(k,v) for k,v in info.items() if Path(k).suffix in ('.py','.ts','.tsx','.css','.cjs','.mjs')],key=lambda x:x[1]['lines'],reverse=True)[:20]
modules={}
for name in tracked:
    if not name.endswith('.py'):continue
    tree=ast.parse((root/name).read_text(encoding='utf-8-sig'))
    imports=[]
    tests=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.Import):imports.extend({'module':a.name,'line':n.lineno,'relative':0} for a in n.names)
        if isinstance(n,ast.ImportFrom):
            imports.append({'module':n.module or '', 'names':[a.name for a in n.names],'line':n.lineno,'relative':n.level})
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test_'):tests.append(n.name)
    modules[name]={'imports':imports,'tests':tests,'docstring':ast.get_docstring(tree),'lines':info[name]['lines']}
service={Path(k).stem:k for k in modules if k.startswith('services/studylens_service/')}
edges={}
for mod,path in service.items():
    deps=[]
    for imp in modules[path]['imports']:
        if imp['relative']>0:
            dep=imp['module'].split('.')[0]
            if dep in service:deps.append(dep)
            elif not dep:deps.extend(n for n in imp.get('names',[]) if n in service)
        elif imp['module'].startswith('studylens_service.'):
            dep=imp['module'].split('.')[1]
            if dep in service:deps.append(dep)
    edges[mod]=sorted(set(deps))
cycles=set()
def walk(start,cur,path):
    for nxt in edges.get(cur,[]):
        if nxt==start:
            cycle=path+[start]
            core=cycle[:-1];rot=min(tuple(core[i:]+core[:i]) for i in range(len(core)))
            cycles.add(rot)
        elif nxt not in path and len(path)<10:walk(start,nxt,path+[nxt])
for m in edges:walk(m,m,[m])
log=subprocess.check_output(['git','log','--format=COMMIT %aI','--name-only']).decode()
dates={};date=None
for line in log.splitlines():
    if line.startswith('COMMIT '):date=line[7:]
    elif line.strip():dates.setdefault(line.strip(),date)
root_files=[]
for p in root.iterdir():
    if p.is_file():root_files.append(p.name)
docfiles=[]
for p in (root/'docs').rglob('*'):
    if p.is_file():
        name=p.relative_to(root).as_posix()
        docfiles.append({'path':name,'bytes':p.stat().st_size,'date':dates.get(name,'UNCOMMITTED'),'tracked':name in info})
for name in root_files:
    p=root/name
    docfiles.append({'path':name,'bytes':p.stat().st_size,'date':dates.get(name,'UNCOMMITTED'),'tracked':name in info})
locks=[]
distmap=md.packages_distributions()
for line in (root/'services/requirements-lock.txt').read_text().splitlines():
    name,pin=line.split('==')
    try:
        dist=md.distribution(name); version=dist.version
        req=[re.match(r'[A-Za-z0-9_.-]+',x).group(0) for x in (dist.requires or [])]
    except md.PackageNotFoundError:version='NOT INSTALLED';req=[]
    mods=[m for m,ds in distmap.items() if any(d.lower().replace('_','-')==name.lower().replace('_','-') for d in ds)]
    runtime=[];aux=[]
    for path,detail in modules.items():
        used=any(i['relative']==0 and i['module'].split('.')[0] in mods for i in detail['imports'])
        if used:(runtime if path.startswith('services/studylens_service/') or path.startswith('services/migrations/') else aux).append(path)
    locks.append({'name':name,'pin':pin,'installed':version,'requirements':req,'import_names':mods,'runtime_imports':runtime,'aux_imports':aux})
out={'baseline':subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),'tracked_files':info,'tracked_top':top,'workspace_disk':disk,'largest_source':sources,'python_modules':modules,'service_edges':edges,'cycles':[list(c) for c in sorted(cycles)],'documents':sorted(docfiles,key=lambda x:x['path']),'python_dependencies':locks}
(root/'tmp/audit-inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'baseline':out['baseline'],'tracked_files':len(tracked),'tracked_top':top,'workspace_disk':disk,'largest_source':sources,'cycles':out['cycles'],'document_count':len(docfiles),'python_modules':len(modules)},indent=2))
'@
.\.venv\Scripts\python.exe -c $auditCode
```

### Registered routes and isolated migrated schema (exact inline script)

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'services'
$auditCode = @'
import ast, asyncio, hashlib, json, re, subprocess, tempfile
from collections import Counter, defaultdict
from pathlib import Path
from fastapi.testclient import TestClient
from studylens_service.api import create_app
root=Path.cwd()
inv=json.loads((root/"tmp/audit-inventory.json").read_text())
out={}
with tempfile.TemporaryDirectory(prefix="neev-architecture-audit-") as temporary:
    app=create_app(Path(temporary), "audit-token-placeholder-at-least-24-characters",start_worker=False)
    with TestClient(app) as client:
        out["routes"]=[{"methods":sorted(r.methods),"path":r.path,"name":r.name} for r in app.routes]
        import sqlite3
        con=sqlite3.connect(Path(temporary)/"studylens.sqlite3")
        out["schema_version"]=con.execute("select version_num from alembic_version").fetchone()[0]
        out["tables"]={}
        for (name,) in con.execute("select name from sqlite_master where type='table' order by name"):
            indexes=[]
            for row in con.execute('PRAGMA index_list("'+name+'")'):
                indexes.append({"name":row[1],"unique":bool(row[2]),"origin":row[3],"columns":[x[2] for x in con.execute('PRAGMA index_info("'+row[1]+'")')]})
            out["tables"][name]={"columns":[list(r) for r in con.execute('PRAGMA table_info("'+name+'")')],"indexes":indexes,"foreign_keys":[list(r) for r in con.execute('PRAGMA foreign_key_list("'+name+'")')],"sql":con.execute("select sql from sqlite_master where type='table' and name=?",(name,)).fetchone()[0]}
        con.close()
mods={}
for path in inv["python_modules"]:
    tree=ast.parse((root/path).read_text(encoding="utf-8-sig"))
    top_imports=[ast.get_source_segment((root/path).read_text(encoding="utf-8-sig"),n).replace("\n"," ") for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
    mods[path]={"functions":[n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))],"classes":[n.name for n in tree.body if isinstance(n,ast.ClassDef)],"eager_imports":top_imports}
out["module_details"]=mods
doc=(root/"docs/architecture.md").read_text(encoding="utf-8-sig")
out["documented_route_rows"]=[l for l in doc.splitlines() if l.startswith("|") and re.search(r"\b(GET|POST|PUT|HEAD|DELETE)\b",l)]
out["test_groups"]={}
for path,meta in inv["python_modules"].items():
    if path.startswith("services/tests/test_"):
        out["test_groups"][path]={"count":len(meta["tests"]),"tests":meta["tests"]}
hashes=defaultdict(list)
for path in inv["tracked_files"]:
    if path.startswith("docs/") or "/" not in path:
        hashes[hashlib.sha256((root/path).read_bytes()).hexdigest()].append(path)
out["exact_duplicates"]=[p for p in hashes.values() if len(p)>1]
out["npm_imports"]={}
for path in inv["tracked_files"]:
    if Path(path).suffix in (".ts",".tsx",".cjs",".mjs",".css"):
        text=(root/path).read_text(encoding="utf-8-sig")
        found=re.findall(r"""(?:from\s+|require\(\s*|import\s+|import\(\s*|@import\s+)['"]([^'"]+)""",text)
        for name in found:
            if not name.startswith((".","node:","/")):
                out["npm_imports"].setdefault(name,[]).append(path)
out["python_installed"]=json.loads(subprocess.check_output([str(root/".venv/Scripts/python.exe"),"-m","pip","list","--format=json"],text=True))
(root/"tmp/audit-runtime.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps({k:out[k] for k in ("schema_version","routes","documented_route_rows","exact_duplicates","npm_imports","test_groups")},indent=2))

'@
.\.venv\Scripts\python.exe -c $auditCode
```

### Review the generated inventories

```powershell
$auditCode = @'
import json
from pathlib import Path
v=json.loads(Path("tmp/audit-inventory.json").read_text())
r=json.loads(Path("tmp/audit-runtime.json").read_text())
print("MODULES")
for p,m in v["python_modules"].items(): print(p,m["lines"],repr(m["docstring"]),r["module_details"][p]["functions"],r["module_details"][p]["classes"])
print("DOCS")
for d in v["documents"]: print(d["path"],d["bytes"],d["date"])
print("DEPS")
for d in v["python_dependencies"]: print(d)
print("TABLES")
for n,t in r["tables"].items(): print(n,t["indexes"],t["foreign_keys"])

'@
.\.venv\Scripts\python.exe -c $auditCode
```

### Default dependency markers, cycles and references (exact inline script)

```powershell
$auditCode = @'
import ast, importlib.metadata as md, json, re
from pathlib import Path
from collections import defaultdict
from packaging.requirements import Requirement
root=Path.cwd();v=json.loads((root/"tmp/audit-inventory.json").read_text());r=json.loads((root/"tmp/audit-runtime.json").read_text())
norm=lambda s:re.sub(r"[-_.]+","-",s).lower()
parents=defaultdict(list)
for d in v["python_dependencies"]:
    for raw in md.requires(d["name"]) or []:
        q=Requirement(raw)
        if q.marker is None or q.marker.evaluate({"extra":""}): parents[norm(q.name)].append(d["name"])
r["dependency_parents"]=dict(parents)
r["installed_extra"]=[d for d in r["python_installed"] if norm(d["name"]) not in {norm(x["name"]) for x in v["python_dependencies"]}]
r["all_service_imports"]={};r["eager_service_imports"]={}
for path in v["python_modules"]:
    if not path.startswith("services/studylens_service/"):continue
    tree=ast.parse((root/path).read_text(encoding="utf-8-sig"))
    r["all_service_imports"][Path(path).stem]=sorted({n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n,ast.ImportFrom) and n.level and n.module})
    r["eager_service_imports"][Path(path).stem]=sorted({n.module.split(".")[0] for n in tree.body if isinstance(n,ast.ImportFrom) and n.level and n.module})
def scc(graph):
    index=0;idx={};low={};stack=[];active=set();out=[]
    def visit(n):
        nonlocal index
        idx[n]=low[n]=index;index+=1;stack.append(n);active.add(n)
        for t in graph.get(n,[]):
            if t not in idx:visit(t);low[n]=min(low[n],low[t])
            elif t in active:low[n]=min(low[n],idx[t])
        if low[n]==idx[n]:
            comp=[]
            while True:
                t=stack.pop();active.remove(t);comp.append(t)
                if t==n:break
            if len(comp)>1:out.append(sorted(comp))
    for n in graph:
        if n not in idx:visit(n)
    return out
r["all_import_scc"]=scc(r["all_service_imports"]);r["eager_import_scc"]=scc(r["eager_service_imports"])
tracked_text={}
for p in v["tracked_files"]:
    if Path(p).suffix.lower() in (".py",".ts",".tsx",".mjs",".cjs",".md",".json",".css",".txt",".html"):
        tracked_text[p]=(root/p).read_text(encoding="utf-8-sig",errors="replace")
r["script_references"]={}
for p in v["tracked_files"]:
    if p.startswith("scripts/"):
        name=Path(p).name
        r["script_references"][p]=[q for q,t in tracked_text.items() if q!=p and (p in t or name in t or Path(p).stem.replace("-","_") in t)]
r["service_module_callers"]={}
for mod in r["all_service_imports"]:
    r["service_module_callers"][mod]=[n for n,targets in r["all_service_imports"].items() if mod in targets]
(root/"tmp/audit-runtime.json").write_text(json.dumps(r,indent=2),encoding="utf-8")
print("Dependency count",len(v["python_dependencies"]),"extra installed",r["installed_extra"])
print("ALL SCC",r["all_import_scc"],"EAGER SCC",r["eager_import_scc"])
print("Unreferenced scripts",[(p,refs) for p,refs in r["script_references"].items() if not refs])
print("Markdown documents",[(d["path"],d["bytes"]) for d in v["documents"] if d["path"].endswith(".md")])
print("No direct source imports or default parent",[(d["name"],parents.get(norm(d["name"]),[])) for d in v["python_dependencies"] if not d["runtime_imports"] and not d["aux_imports"] and not parents.get(norm(d["name"]))])
print("Schema SQL", {n:t["sql"] for n,t in r["tables"].items()})

'@
.\.venv\Scripts\python.exe -c $auditCode
```

### Source, documentation and log reads/searches

```powershell
Get-Content 'C:\Users\User\.codex\attachments\30cabb0c-083e-42b6-8302-2e4a9242520a\Pasted text.txt'; Get-Content services\studylens_service\api.py; Get-Content electron\preload.cjs; Get-Content electron\main.cjs
Get-Content tmp\audit-api-tests.log -Tail 12; Get-Content tmp\audit-check.log -Tail 24; Get-Content services\studylens_service\jobs.py; Get-Content services\studylens_service\worker.py; Get-Content services\studylens_service\supervisor.py; Get-Content electron\storage.cjs; Get-Content electron\backend.cjs
Get-Content services\studylens_service\worker.py; Get-Content services\studylens_service\resource_guard.py; Get-Content services\studylens_service\schema.py; Get-Content services\migrations\versions\*.py
Get-Content services\studylens_service\cloud_audio.py; Get-Content services\studylens_service\cloud_vision.py; Get-Content services\studylens_service\video_frame_visuals.py
Get-Content docs\architecture.md; Get-Content docs\CONTEXT_HANDOFF.md; Get-Content docs\PHASES.md; Get-Content tmp\audit-smoke.log; Get-Content services\studylens_service\__main__.py
rg -n 'https?://|httpx|requests\.|urlopen|snapshot_download|hf_hub|download_model|WhisperModel|prompt|PROMPT|MODEL|STUDYLENS_|MAX_' services\studylens_service scripts vite.config.ts electron src -g '*.py' -g '*.mjs' -g '*.cjs' -g '*.ts' -g '*.tsx'
rg -n '^\|.*(GET|POST|PUT|HEAD|DELETE)' docs\architecture.md
rg -n -i 'local.only|private|no cloud|consent|permission|mastery|accuracy|streak|mock|coming soon|placeholder|82%|74%' src README.md docs -g '*.md' -g '*.tsx' -g '*.ts' -g '!phase-*' -g '!hunyuan*' -g '!lighton*' -g '!small*' -g '!omni*'
Get-Content tmp\audit-inventory.json -TotalCount 5
Get-Content services\studylens_service\database.py; Get-Content services\studylens_service\extraction.py; Get-Content services\studylens_service\audio.py; Get-Content services\studylens_service\visual.py
Get-Content services\studylens_service\cloud_audio.py; Get-Content services\studylens_service\youtube_helper.py; Get-Content services\studylens_service\local_tools.py
Get-Content services\studylens_service\audio.py -TotalCount 160; Get-Content services\studylens_service\video_frames.py; Get-Content electron\media.cjs; Get-Content index.html
Get-Content src\StorageSettings.tsx; Get-Content src\model.ts -TotalCount 170; Get-Content src\App.tsx | Select-Object -Skip 510 -First 260; Get-Content scripts\evaluate-llamaindex-docs.py -TotalCount 70
rg -n 'timeout|memory_limit|CHUNK|local_files|model|sample' services\studylens_service\audio.py services\studylens_service\audio_helper.py services\studylens_service\video_frames.py services\studylens_service\youtube.py
Get-Content services\studylens_service\cloud_vision.py -TotalCount 110; Get-Content services\studylens_service\cloud_vision.py | Select-Object -Skip 195 -First 125; Get-Content src\StorageSettings.tsx
Get-Content services\studylens_service\youtube_media.py; Get-Content services\studylens_service\jobs.py | Select-Object -Skip 235; Get-Content vite.config.ts; Get-Content src\storage\client.ts -TotalCount 100; Get-Content services\studylens_service\extraction.py | Select-Object -Skip 50 -First 85
rg -n '^#|local.only|private|no cloud|consent' README.md StudyLens-Design-Prompt.txt docs\*.md
Get-Content package.json; Get-Content .gitignore; Get-Content tests\*.test.ts
Get-Content src\StorageSettings.tsx; Get-Content services\studylens_service\video_frames.py -TotalCount 80; Get-Content services\studylens_service\youtube.py -TotalCount 115; Get-Content index.html; Get-Content tsconfig.json; Get-Content tmp\audit-check.log -TotalCount 29; Get-Content docs\architecture.md -Tail 44; git status --short --branch
rg -n 'sqlite3|worker\.connection|Database\(|JobStore|create_app|httpx|startBackend|testData|root=' scripts -g '*.py' -g '*.cjs'
Get-Content scripts\setup-audio.py; Get-Content services\studylens_service\youtube_media.py; Get-Content services\studylens_service\job_errors.py; Get-Content electron\media.cjs; Get-Content docs\evaluation\ocr-cleanup.md; Get-Content docs\evaluation\lighton-ocr.md; Get-Content docs\NEXT_CONTEXT_PROMPT.md
rg -n -i 'local.only|no cloud credentials|consent:true|on.screen|mastery' docs -g '*.md' -g '!evaluation/**' -g '!PHASES.md' -g '!CONTEXT_HANDOFF.md' -g '!architecture.md'
git remote get-url origin
Get-Content src\styles.css -TotalCount 75; Get-Content services\migrations\env.py; Get-Content scripts\smoke.mjs
```

The docs\*.md rg invocation reported a Windows literal-glob path error; the later docs -g '*.md' search ran successfully. Large tool displays sometimes truncated; AST/schema/log artifacts were inspected separately. Report rendering uses the existing Python interpreter and only local JSON/text evidence.

Read-only report validation also ran:

```powershell
$auditCode = @'
import json,re
from pathlib import Path
p=Path("docs/audit/CURRENT_ARCHITECTURE.md")
t=p.read_text(encoding="utf-8")
for s in re.split(r"(?m)(?=^## )",t):
 print(s.splitlines()[0],len(s),len(s.splitlines()))
v=json.loads(Path("tmp/audit-inventory.json").read_text(encoding="utf-8"))
print("Generated doc:",[d for d in v["documents"] if not d["tracked"]])
print("Methods:",[x for x in json.loads(Path("tmp/audit-runtime.json").read_text(encoding="utf-8"))["module_details"]["services/studylens_service/schema.py"]["eager_imports"]])
'@
.\.venv\Scripts\python.exe -c $auditCode
Get-Content docs\evaluation\phase-07b-service-first.log -Tail 32; Get-Content docs\audit\CURRENT_ARCHITECTURE.md | Select-Object -Skip 325 -First 8
Get-Content docs\evaluation\phase-07b-service-first.log -Tail 25
```

The first report render failed on Windows default text encoding; explicit UTF-8 corrected the temporary renderer. The render command was then repeated. No application code changed.

### Artifact and Phase A publication

```powershell
.\.venv\Scripts\python.exe tmp\audit-render.py
git diff --check
git status --short
git add -- docs/audit/CURRENT_ARCHITECTURE.md
git commit -m "docs(audit): record Phase A current architecture"
git push -u origin cleanup/architecture-reset
git rev-parse HEAD
git ls-remote --heads origin refs/heads/cleanup/architecture-reset
git status --short --branch
```

Publication commands are the Phase A closeout; remote/local SHA equality and clean status are verified in the accompanying reply. Phase B requires written approval.
