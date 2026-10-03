# Phase 7B — sampled video frames and review

Implemented October 3, 2026; ready for student acceptance. This checkpoint selects and preserves useful frame previews. It does **not** run OCR, send frames to Groq, interpret equations/diagrams or index visual knowledge. Phase 7C connects those steps. Audio processing and YouTube ingestion remain separate checkpoints.

## What changed

Videos have an independent `video_frames` background job. It can finish when ASR is missing, failed or cancelled. New imports and older saved videos receive the job automatically; no finished/cancelled job is resurrected by startup. `STUDYLENS_AUTO_VIDEO_FRAMES=0` disables automatic creation, while explicit **Select frames** remains available. Existing queued jobs still run and can be cancelled in Background work.

FFmpeg samples frames at approximately one-second intervals inside bounded 30-second windows. The selected frame's integer PTS and rational filter time base are retained, with the seek-window offset added back. Timestamps are not calculated from frame number divided by nominal FPS. This preserves the evaluated VFR changes at 2.4 and 5.6 seconds. FFmpeg applies the source display-rotation matrix before saving previews.

PySceneDetect 0.7.1 detects changes between sampled frames. A separate low-resolution pixel comparison against the last retained frame catches accumulated whiteboard changes that do not cause a strong scene cut. Defaults: scene threshold 18; more than 0.2% of pixels differing by over 24 in any color channel; a reference frame after 60 seconds without a retained change. Comparison is local in time: A → B → A remains three locations. These are tested initial thresholds, not universally tuned lecture settings.

The selector retains at most 20 frames per window and 600 per source. Remaining slots are divided among remaining windows, then useful candidates are spread through each window's allowance. Motion early in a recording cannot consume the entire budget. If changed candidates are skipped, their count is reported and the job stays partial. One-second sampling can miss brief content even when the budget is not exhausted.

Each preview is bounded to 1400 pixels per edge and 512 KiB, with further shrinking when needed. Only four checksum-validated previews are returned per API page. Frames and the completed-window counter are committed together in the SQLite job checkpoint; unfinished windows do not appear as saved. Resume preserves earlier IDs and rejects changed source/settings. Reprocessing rebuilds frames without deleting audio content. Original checksums are checked again before selection, and previews are tied to the immutable source version.

**Review video → Selected frames** is collapsed initially. It shows previews, source timestamps, pagination and **OCR pending** labels. It works even with no saved transcript. Clicking a timestamp seeks within the original video. Frame seeking is disabled when native playback is unavailable, with guidance to open the saved original. Damaged previews show an error and can be rebuilt.

FFmpeg, PySceneDetect and Whisper have complementary roles: FFmpeg decodes/timestamps media; PySceneDetect identifies sampled visual changes; Whisper transcribes speech in the existing audio job. No tool alone supplies the full video knowledge base. Current PySceneDetect APIs and VFR changes were checked against [the official changelog](https://www.scenedetect.com/changelog/) and [detector documentation](https://www.scenedetect.com/docs/latest/api/detectors.html). The initial `scenedetect-core` package was yanked; it was replaced with the supported headless package following [the maintainer's instruction](https://github.com/Breakthrough/PySceneDetect/issues/558). No AI weights were downloaded.

## Evaluation

| Gate | Result |
|---|---|
| Independent frame contracts | 10 passed: scoped/automatic jobs, source integrity, slide/whiteboard changes, returning slides, static deduplication, VFR/rotation, budget distribution, damaged previews, cancellation/restart/settings checks, video track ending before audio |
| Full service regression | 143 passed in 125.147 seconds |
| Queue focused retry | 16 passed |
| Renderer/build | 13 tests passed; TypeScript/Vite build passed |
| Real gold video pilot | 6/6 passed, with actual FFmpeg and PySceneDetect; no ASR or cloud |
| Native Electron | Frame review with cancelled ASR, real decoded previews, timestamp seeking to 8 seconds, second-page whiteboard frame at 12 seconds, coverage labels and desktop smoke passed |

Final raw evidence: [pilot](video-frames-20261003-080329.json), [native checks](video-frames-desktop.json), [screenshot](screenshots/phase-07b-frames-desktop.png). Final logs: `tmp/phase-07b-service-tests.log`, `tmp/phase-07b-frame-tests.log`, `tmp/phase-07b-queue-tests.log`.

| Authored fixture | Candidates | Retained | Source locations | Seconds | Helper private MiB after processing |
|---|---:|---:|---|---:|---:|
| Three slides | 12 | 3 | 0, 4, 8 | 1.063 | 411.6 |
| Gradual whiteboard steps | 15 | 5 | 0, 3, 6, 9, 12 | 1.360 | 411.7 |
| Return to earlier slide | 12 | 3 | 0, 4, 8 | 1.265 | 412.0 |
| Static 65-second slide | 65 | 2 | 0, 60 | 3.359 | 412.9 |
| Variable frame rate | 4 | 3 | 0, 2.4, 5.6 | 1.125 | 411.5 |
| Display rotation | 8 | 2 | 0, 4; previews 360×640 | 1.172 | 411.9 |

The additional contract fixture has a 12-second video track and 65-second audio/container. Earlier frames remain, and two later windows are explicitly reported without decoded frames. A reduced six-frame budget on a moving 65-second video retained locations in its last window and reported skipped candidates. Cancellation before a second window was committed preserved only the first window; restart resumed it with stable IDs. Changed selection settings failed closed until restored or rebuilt.

The approximately 0.5 MB visual fixture set is drawn locally; the short-video-track edge case adds an existing authored audio track. No real student content is used. The clips are 640×360 slides/whiteboard drawings, not held-out natural lectures. These are single development-laptop timings, sometimes concurrent with regression work, not a controlled comparison against alternative selectors. The helper uses a 512 MiB Windows job limit and 15-second timeout; FFmpeg has separate 512 MiB/20-second limits. Reported memory is private bytes **after** processing, not measured peak or total application usage. Whole-app 8 GB validation remains manual.

## Failures retained and repaired

- The first helper run used an integer FPS argument rejected by the current `FrameTimecode` constructor. Corrected to a float and retested; [first pilot](video-frames-20261003-074347.json) retains that failure.
- Initial static/rotated fixtures did not contain the intended full duration/rotation matrix. FFprobe exposed this; fixtures were regenerated with a CFR FPS filter and explicit display rotation. [Earlier partial pilot](video-frames-20261003-074535.json) is retained.
- An empty late-video window exposed FFmpeg's JPEG color-range initialization error. Explicit full-range JPEG output fixed it; all ten frame contracts passed afterward.
- One full regression run hit that frame error and a scheduler fixture's ten-second completion deadline. Its [failure log](phase-07b-service-first.log) is retained. The focused queue gate passed; the final 143-test full rerun passed. Test-load contention is a possible explanation for the scheduler timeout, not an established cause.

## Remaining boundaries

Brief changes between samples, very small formula edits, cursors/speaker movement, fades, slide animations and low contrast can be missed or cause extra frames. Budgeted sampling intentionally omits some useful candidates; it is not complete visual coverage. Natural teaching videos and human judgments of missing/redundant frames are the next quality gate. Nonzero container origins still require a zero-based MP4 export. Scene detection restarts per window using the last retained frame for continuity; its output is a preview-selection signal, not a complete scene list or semantic topic map.

Stage 7C will run local OCR/selective Groq vision on retained frames, preserve these timestamps, and combine visual extraction with the audio intervals. No current frame is treated as verified knowledge merely because selection succeeded.

## Reproduce

```powershell
npm.cmd run api:install
node scripts/python.mjs scripts/create-frame-fixtures.py
npm.cmd run video:frames:test
npm.cmd run api:test
npm.cmd run check
npm.cmd run smoke:desktop
node scripts/python.mjs scripts/evaluate-video-frames.py
node_modules/.bin/electron.cmd scripts/evaluate-video-frames-desktop.cjs tmp/video-frames-integration-20261003-080329
```

The pilot clears inherited Groq credentials and cancels ASR to prove frame independence. The native gate uses completed isolated data and sends nothing externally.

## Student manual checkpoint

1. Restart Electron and import a slide lecture. In **Review video**, expand **Selected frames**. Click timestamps and compare each preview with the original at that location.
2. Try a whiteboard lecture. Check that worked steps are retained and that repeated images do not fill every page. Also try a silent video; frame review should still work.
3. Cancel the job whose label ends **Frames**, reopen StudyLens and resume it. Earlier saved frame windows should remain. Continue navigating during selection and note responsiveness/memory on the target 8 GB laptop.

On-screen OCR/vision remains visibly pending; Phase 7C follows this checkpoint, then YouTube ingestion.
