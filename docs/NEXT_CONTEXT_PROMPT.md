# Fresh-context prompt

Continue building **Neev** (नींव), the student-only desktop learning app formerly called StudyLens, in `C:\Users\User\OneDrive\Desktop\Study`.

First read `docs/CONTEXT_HANDOFF.md`, then the relevant current reports and `docs/PHASES.md`. Treat old dated milestones as history. Use the UX Pilot PDF as the visual baseline; do not use Stitch.

Completed scope includes the Electron/React shell, SQLite persistence and immutable originals, background ingestion for documents/audio/uploaded video, automatic Groq audio/vision with local fallback, independent video-frame selection/review, and YouTube timed-caption/link ingestion. YouTube currently imports captions, not video/audio or visual frames; keep coverage labels honest. Latest ingestion gates passed 156 service tests, 13 focused YouTube contracts, 15 JavaScript checks/build and native review; consult reports for the exact limitations. The app was renamed to Neev afterward, preserving existing data locations and internal identifiers.

Proceed with **Phase 7C: OCR and selective Groq vision for retained uploaded-video frames**, as a small independently evaluated checkpoint. Preserve original timestamps, versions, audio/visual provenance, partial checkpoints and cancellation/restart. Keep the UI responsive on the target 8 GB laptop and all model extraction visibly unverified. Student manual acceptance of the latest frame/YouTube checkpoint is still pending; report that separately from automated results.

Groq extraction is already authorized automatically. External SearXNG search requires the student's explicit permission for that action. Live voice tutoring remains on hold. Do not restart discarded OCR/model benchmarks or download replacement models. Keep the existing `%APPDATA%\StudyLens` store, `STUDYLENS_*` settings, IPC/storage keys and media scheme compatible so the rename cannot strand saved materials.

Inspect the actual code before editing, complete necessary routine work without repeated permission requests, and report what changed, how it was evaluated and remaining limitations. Do not claim unimplemented retrieval, tutoring, assessments or learner-model features are complete.
