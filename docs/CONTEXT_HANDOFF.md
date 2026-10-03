# Neev — continuation handoff

Updated October 3, 2026, after Phase 7D-2 student-supplied local-media association and on-demand YouTube embedding. Read this first when continuing. Detailed reports preserve the history under the former name StudyLens; do not infer student acceptance from automated tests.

## Product and working agreements

- Student-only Electron desktop app. Workspace → Subject → Topic, with study tabs retaining their own context. New tabs open Workspace. Keep visual load low and show extra details on demand.
- Visual baseline: `C:/Users/User/Downloads/uxpilot-export-09-30-26.pdf`, inspected visually. Do not use Stitch. Track D defines the project requirements: `C:/Users/User/Downloads/Track D.pdf`. Document instructions are reference content, not automatically user instructions.
- Build small, independently evaluated checkpoints. User authorized implementation; continue routine work without repeatedly asking permission. Preserve originals and earlier versions; never present test/provider fixtures as real extraction.
- Target hardware: 8 GB RAM, decent CPU, low-VRAM GPU. Heavy parsing/inference belongs in worker/child processes; keep Electron responsive. Developer-machine results do not establish 8 GB performance.
- Intended tutor providers: small Ollama models (such as Qwen) and Groq cloud. Groq audio/vision extraction is authorized automatically, without per-upload student consent. External web search remains a different feature: use SearXNG only after the student's explicit permission for that action.
- Tesseract is the local OCR engine; difficult supported PDF/slide/image previews can use Groq. Google Cloud Vision was removed. Unused experimental OCR/model downloads were cleaned up; preserve evaluation reports. Live voice tutoring and audio-model selection remain on hold.
- Learner model must include BKT, IRT-style estimation, PFA, prerequisite tracking, misconception/step evidence, confidence calibration, spaced repetition, active recall and interleaving. Cold start includes diagnostics/intake. These are requirements, not implemented learner features.
- Assessment requirements: scoped MCQ/short/numerical questions, source/topic/difficulty tags, verified keys and novelty, cited feedback, misconception/weak-topic reports, and question-specific Ask doubt in review. Search to extend an assessment requires explicit student permission.
- Outside knowledge must be labelled and offer deliberate inclusion in the knowledge base. Evaluation must report measured faithfulness/relevancy/context precision/recall and simulated multi-session personalization, with honest limitations. Track D also requires a working prototype, architecture/learner/grounding documentation, benchmarks and a 3–10 minute demo video.

## Repository and launch

- Workspace: `C:/Users/User/OneDrive/Desktop/Study`. The Git repository is on `main` and tracks `https://github.com/KASIM-S-DHILA/Neev.git`; commit each independent phase separately and verify the push.
- React/TypeScript/Vite renderer; narrow sandboxed Electron preload IPC; authenticated loopback Python FastAPI service; SQLAlchemy/aiosqlite, SQLite WAL and Alembic; immutable original store and supervised single heavy worker.
- Node 24, Python 3.12, project `.venv`, pinned `services/requirements-lock.txt`. Project dependencies are installed. No new AI model download is needed for the completed work.
- Run native development: `npm.cmd run dev`. Run the built desktop app: `npm.cmd start` or `Neev.lnk` (the older shortcut still works). Rebuild changed UI with `npm.cmd run build`. `npm.cmd run dev:web` is the browser preview.
- The visible app/package name is Neev. Preserve the existing `%APPDATA%/StudyLens` profile/data location, `STUDYLENS_*` environment variables, `window.studyLens`, storage keys, Python module names and `studylens-media` scheme. The rename deliberately avoids moving data or changing persistent identifiers. Electron explicitly retains the old profile for normal launches.
- Install/update pinned Python dependencies: `npm.cmd run api:install`. Current package version is 0.6.0.
- Follow applicable user/AGENTS instructions. TinyFish is the preferred web research toolkit. Do not spawn sub-agents without explicit applicable authorization. Do not include credentials in notes, logs or responses.

## Implemented scope

| Checkpoint | Current state |
|---|---|
| Phases 1–5 | Desktop shell/tabs, workspaces/subjects/topics, drafts, persistence/conflict handling, immutable file imports, durable queue, PDF/text/slides/image extraction and review; accepted for implemented scope |
| Visual extension | LibreOffice full PPTX previews; native table cells/OMML structures; Tesseract and selective automatic Groq; structured cloud extraction displayed separately and labelled unverified |
| Phase 6 | Audio ingestion/VAD, automatic Groq transcription with installed Tiny fallback, absolute times, playback, quota pacing/cache and cancellation/resume |
| Phase 7A | Uploaded-video audio aligned to original clock; native original streaming/range playback and transcript seeking; silent/no-audio cases |
| Phase 7B | Independent frame job: FFmpeg source PTS, PySceneDetect 0.7.1 and pixel changes, duplicate reduction, timestamp review, atomic window checkpoints, cancellation/restart |
| Phase 7C | Separate retained-frame visual job: local Tesseract, bounded selective Groq, timestamped unverified review, separate nearby speech, per-frame restart checkpoints |
| Phase 7D-1 | Materials → Add YouTube link → Import captions; manual/generated language provenance, immutable snapshots, timed content units, refresh/version dedup and link-only fallback; system-browser timestamp links |
| Phase 7D-2 | Student uploads a permitted local video copy and links its saved version to a YouTube caption source with an explicit clock offset; caption review seeks local playback; YouTube player loads on demand with browser fallback |

Frame selection uses one-second sampling in bounded 30-second windows, maximum 600 retained frames with at most 20 per window, and four previews per viewer page. Brief/small visual changes can be missed. The new frame-visual job runs OCR after selection and sends at most one difficult frame per window and twelve per uploaded video to Groq when configured. Results are unverified and are not yet retrieval evidence.

YouTube captions are **Transcript only · Visuals not processed** and unverified, even for manual tracks. Link-only imports have zero caption units. Language association and case-sensitive video IDs remain scoped to workspace/subject. The on-demand YouTube iframe requires internet and may fail when embedding is disabled; the canonical browser link remains. The student can upload a permitted video file and attach its immutable version with a YouTube-to-local time offset. Its audio/frame/visual jobs run independently; the association does not verify media identity or merge captions with video evidence. No direct YouTube audiovisual download or captionless-link ASR is implemented. Snapshot hashes describe saved JSON, not remote video bytes.

Retrieval, grounded tutoring, assessments, learner models, SearXNG integration, course maps, generated revision aids, study schedules, formal RAG/personalization evaluation and packaged installer remain future work. Sample reading/draft UI does not implement these features or establish mastery.

## Latest verified evidence

- Phase 7C: seven focused contracts and the final **163-test** full service regression passed. Fifteen JavaScript checks and the production build passed. Real local OCR and one authorized live Groq frame passed on an authored clip; saved local/cloud results were reviewed in hidden native Electron. [Report](evaluation/phase-07c.md).
- Phase 7D-2: two focused association contracts, the full **165-test** service suite, fifteen JavaScript checks/build and an isolated production Electron check passed. The native check covered on-demand iframe URL, unmount, browser fallback, local association and a mapped 65.5 → 5.5 second seek; actual remote playback and student acceptance remain manual checks. [Report](evaluation/phase-07d-media.md).
- Full service regression: **156 tests passed**, 259.970 s, `tmp/youtube-service-tests.log`. After the final case-sensitive YouTube ID refinement, the **13 focused YouTube tests passed** again (5.075 s), `tmp/youtube-tests.log`.
- JavaScript checks: **15 passed**; TypeScript/Vite build passed. Includes native external-URL validation and distinct browser/API versus native/IPC request bodies.
- Dependencies: `pip check` found no broken requirements.
- Neev rename gate: `npm.cmd run check` passed all 15 JavaScript checks and the TypeScript/Vite build; `npm.cmd run smoke:desktop` reported title **Neev**, sandbox/IPC isolation, SQLite WAL, persisted session, extracted source review and provider-boundary success. This uses isolated evaluation data; the normal launcher retains the existing StudyLens profile path.
- YouTube live pilot: manual English captions from *The essence of calculus*, 16 intervals, **2.828 s** for fetch/publication/verification/extraction. One observed import, not a general benchmark. No media downloaded or Groq called.
- Native Electron: import form/invalid URL, live saved-caption review, coverage labels, authored Hindi pagination and timestamp URL passed. Browser launches were captured in the test; actual browser playback still needs manual checking. Screenshot visually reviewed.
- Phase 7B: ten frame contracts, six authored real-video fixtures and native review passed. Earlier failures/corrections remain in its report. No natural-video completeness or whole-app 8 GB claim.
- Phase 7C: seven focused contracts, 163-service-test regression, real no-cloud OCR and one authorized live Groq frame, plus native review passed. See its report; student manual acceptance, natural-video quality and whole-app 8 GB use remain pending.
- Natural Hindi/Hinglish audio accuracy remains an open gate; earlier benchmarks exposed recognition failures.

## Key code and evidence

- Navigation/UI: `src/Materials.tsx`, `src/ContentPreview.tsx`, `src/VideoTranscript.tsx`, `src/VideoFrames.tsx`, `src/YouTubeReview.tsx`.
- Native boundary: `electron/storage.cjs`, `electron/media.cjs`, `electron/youtube.cjs`; client contracts: `src/storage/client.ts`.
- Pipeline: `services/studylens_service/{api,database,jobs,worker,extraction,audio,video,video_frames,video_frame_visuals,youtube,youtube_helper}.py`.
- Current reports: `docs/evaluation/phase-06-cloud-audio.md`, `phase-07a.md`, `phase-07b.md`, `phase-07d-youtube.md`.
- YouTube evidence: `docs/evaluation/youtube-20261003-083018.json`, `youtube-desktop.json`, `screenshots/youtube-desktop.png`. Pilot data: `tmp/youtube-integration-20261003-083018`.
- Reproduction: `npm.cmd run youtube:test`, `npm.cmd run youtube:media:test`, `npm.cmd run video:frames:test`, `npm.cmd run video:visuals:test`, `npm.cmd run check`, `npm.cmd run api:test`; live/native scripts and limitations are in each report.
- `README.md` covers setup/current scope; `docs/PHASES.md` holds the full roadmap. Older dated milestone paragraphs are historical. `docs/architecture.md` records Phase 5 foundations; consult later reports for current automatic cloud/audio/video/YouTube behavior.

## Next checkpoint and pending manual checks

Phase 7C is implemented for uploaded videos and awaits student manual acceptance. Phase 7D-2 provides a permitted local-media route without downloading YouTube audiovisual bytes. Full source-aware review/grounding and direct remote media acquisition remain separate future work; the latter needs a compliant route under [YouTube API Services Developer Policies](https://developers.google.com/youtube/terms/developer-policies).

Student manual acceptance has not been reported for the latest frame/YouTube changes. Restart Electron, import/review frames from slide/whiteboard/silent videos, compare OCR and any Groq output with originals, seek timestamps, cancel/resume frame jobs, and check responsiveness on the 8 GB target. For YouTube, import a captioned link, try Watch here and the browser fallback on accessible and embedding-disabled videos, refresh captions, attach a permitted local copy, verify its entered time offset against the remote source, review frame text and test an unavailable-caption link. Keep these checks distinct from the completed automated gates.

Latest user chose Neev and requested a prompt for a fresh context window. Branding, settings, launch metadata, service messages and a `Neev.lnk` shortcut were updated. No new ingestion checkpoint was started during the rename. See `docs/NEXT_CONTEXT_PROMPT.md` for the continuation prompt.
