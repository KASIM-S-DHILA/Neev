# Phase 7C — retained uploaded-video frame text

Implemented October 3, 2026. This checkpoint adds local OCR and bounded selective Groq vision after Phase 7B frame selection. It does not process linked YouTube media, make extracted text verified, or add visual text to retrieval.

## Behavior and provenance

The separate `video_frame_visuals` job starts automatically after a completed frame-selection job, including for previously saved selected videos on startup. `STUDYLENS_AUTO_VIDEO_VISUALS=0` disables automatic creation; **Read frame text** remains available. It cannot run until saved frame selection succeeds or is partial with retained frames. Re-selecting frames invalidates prior visual results; it cannot race a running visual job.

The worker rehashes the immutable original, checks the selected-frame manifest, and verifies each saved preview before reading it. Each result retains its source version, original hash, frame ID, timestamp and preview hash. Local Tesseract uses the existing bounded image/OCR path; its text is capped at 8,000 characters per frame. Results commit one frame at a time. Cancellation or restart keeps completed frames; a changed frame manifest fails closed.

The existing difficult-visual router chooses Groq candidates after **all** retained frames have local OCR. Automatic requests are limited to one routed frame per 30-second selection window and twelve per video, spread across the timeline. Other difficult frames remain visibly unsent. The existing Groq adapter supplies checksum-checked image loading, response validation, quota pacing, bounded requests, one format fallback and cancellation checks. Automatic Groq use follows the student's existing authorization; external web search is separate and is not used.

**Selected frames** shows source timestamps, local OCR, optional structured Groq transcription and nearby timed speech. Each stays separately labeled and unverified. Nearby speech keeps its content-unit ID, source version, time interval and speech provider. No visual text is silently merged into the audio transcript or treated as retrieval evidence. The visual panel is collapsed by default and loads four previews per page.

## Independent evaluation

| Gate | Result |
|---|---|
| Phase 7C contracts | **7 passed**: real local OCR/version/timestamps, separately linked authored speech fixture, selective labeled Groq fixture, cancellation/restart, quota-pause restart without resending, damaged preview rejection, frame-reselection invalidation, saved-video backfill and workspace scope |
| Full Python service suite | **163 passed** in 195.415 seconds after all seven Phase 7C contracts and the bounded nearby-audio query. Log: `tmp/phase-07c-service-final.log` |
| Existing frame contracts | **10 passed** after queue integration |
| JavaScript/TypeScript/build | **15 passed**, TypeScript and Vite production build passed |
| Real local pilot | Passed on the authored 12-second slide clip: frames at 0, 4 and 8 seconds, local OCR saved on all three, original byte-for-byte unchanged and cancelled ASR independent |
| Authorized live Groq pilot | Passed on that same authored clip: one saved structured transcription for the 0-second frame, two frames unsent under the one-window budget; no provider retry |
| Hidden native Electron | Saved local and live cloud results displayed with timestamps and unverified labels while transcript was unavailable; screenshots visually inspected |

Local pilot: [report](video-visuals-20261003-104402.json), [native report](video-visuals-desktop.json), [screenshot](screenshots/phase-07c-frame-text-desktop.png). Live pilot: [report](video-visuals-20261003-104845.json), [native report](video-visuals-cloud-desktop.json), [screenshot](screenshots/phase-07c-cloud-frame-desktop.png). Isolated data is under `tmp/video-visuals-integration-*`; neither pilot changed the normal profile. The cloud fixture in the contract tests is labeled and made no request; the live pilot made one authorized request.

The live frame showed “Conditional probability” and `P(A | B) = P(A and B) / P(B)`. Local OCR retained those words and symbols. Groq returned the heading, line and a LaTeX representation of the formula. This is one known authored image, not held-out accuracy or a general math verification result. The two later slide frames had local OCR and were not sent to Groq.

## Remaining checks

- Student manual acceptance: restart Neev, import natural slide and whiteboard videos, compare all saved OCR and selected Groq results with the original at their timestamps, and confirm skipped frames are understandable. Try a silent video. Cancel and resume the frame-text job; verify earlier results persist.
- Check navigation and memory on the target 8 GB laptop while frame selection, OCR and quota waits run. Developer-machine tests do not establish whole-app resource use.
- Evaluate selective routing and transcription on held-out natural lectures, handwriting, low contrast, Hindi/Hinglish and dense equations/tables. One-second frame sampling and the Groq budget can omit useful content. A Groq format failure or quota pause may leave local OCR for review.
- YouTube media acquisition, linked-video visual extraction, retrieval and grounded tutoring remain separate phases. Voice tutoring remains on hold.

## Reproduce

```powershell
npm.cmd run video:visuals:test
npm.cmd run video:frames:test
npm.cmd run api:test
npm.cmd run check
node scripts/python.mjs scripts/evaluate-video-frame-visuals.py
node_modules/.bin/electron.cmd scripts/evaluate-video-frame-visuals-desktop.cjs tmp/video-visuals-integration-<pilot-id>
```

The live pilot is optional and sends one authored preview when a configured Groq key is available:

```powershell
$env:GROQ_API_KEY = [Environment]::GetEnvironmentVariable('GROQ_API_KEY', 'User')
node scripts/python.mjs scripts/evaluate-video-frame-visuals.py --cloud
```
