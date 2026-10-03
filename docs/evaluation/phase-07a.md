# Phase 7A — uploaded video audio and original playback

Implemented October 3, 2026; ready for student acceptance. This checkpoint extracts audio from uploaded videos. On-screen slides, diagrams, equations and silent visual teaching are **not extracted yet**. YouTube ingestion remains planned separately.

## Behavior

- MP4/MOV/MKV/WebM sources enter the existing durable queue, including older saved videos after restart. Originals remain immutable and downloadable.
- FFprobe checks real video/audio streams, finite duration up to four hours, dimensions and timeline. Attached cover pictures do not qualify as a video. Invalid inputs fail with the original retained.
- FFmpeg decodes 30-second mono 16 kHz PCM intervals on the container clock. Audio stream delay, gaps and trailing silence stay on that clock. If a successful decode beyond the audio track returns no samples, that interval stays silent.
- Silero VAD selects one contiguous speech window inside each video interval, with 0.2-second outer margins. Internal gaps remain. ASR receives that window; its sample-based offset is added back to every returned timestamp. Uncertain VAD uses the full interval with a warning. The saved listenable PCM retains the complete interval.
- Existing automatic Groq transcription, cache/pacing, cancellation and Tiny fallback apply. Text/timestamps remain unverified. No additional models were downloaded.
- Videos without an audio stream need no speech setup. They have an empty, explicitly labelled audio result and original playback.
- **Review video** streams the original through a private Electron protocol and supports absolute source-time seeking. The renderer receives neither the bearer token nor the original filesystem path. Authenticated workspace-scoped byte ranges support seeking without reading the entire video into renderer memory. **Reprocess video audio** rebuilds saved transcript intervals.

The local service hashes an original on its first playback request and again when its file-stat signature changes. Workspace/type/path/size checks run on every request. This avoids rehashing a large unchanged video on every seek; the cache is ordinary modification detection, not a guarantee against adversarial filesystem races. Streaming is stopped before service shutdown.

## Measured gates

| Gate | Result |
|---|---|
| Independent video contracts | 12 passed: delayed PCM, full video duration, no audio/setup, cancel/restart, silent tail, MKV, corrupt/disguised input, original tampering, scoped reprocessing, saved-video backfill, speech-window offset, playback/auth/ranges/cache |
| Full service regression | 133 passed in 107.380 seconds |
| Renderer regression/build | 13 passed; TypeScript and Vite build passed |
| Live authored video pilot | 7/7 passed after timing repair; actual Groq output retained |
| Native Electron | Decoded H.264 frames, original byte ranges, scope/query rejection, delayed/later-interval seeking, provenance/coverage and no-audio playback passed |

Raw evidence: [first pilot](video-integration-20261003-070850.json), [repaired pilot](video-integration-20261003-071221.json), [native checks](video-desktop.json), [native screenshot](screenshots/phase-07a-video-desktop.png). Service log: `tmp/phase-07a-service-tests.log`.

The first pilot retained the audio delay correctly in PCM, but Groq labelled the first delayed sentence at 0.000 seconds despite speech beginning around 4.111 seconds. The VAD window repair placed that sentence at 3.528 seconds: approximately 0.583 seconds early. The known-fixture timing check accepts an error of at most 0.75 seconds. This demonstrates preserved source mapping, not exact word timing. Phrase checks accept both “0 degrees” and “zero degrees”; raw transcripts are retained. The original failed report was not overwritten.

Native seeking placed the delayed sentence at 3.528 seconds and the second interval's sentence at **31.512 seconds of the original 65-second video**, rather than 1.512 seconds of a trimmed clip. The screenshot visibly shows the test pattern's 31.5-second source timestamp. Initial native playback failed because Chromium reports file initiators as `file://` while JavaScript URL.origin reports `null`; the corrected check was retested with actual decoded frames and settled seeking. Active playback shutdown was also corrected and retested without the earlier shutdown request loop.

| Fixture | End-to-end seconds | Result |
|---|---:|---|
| 20-second lecture | 2.203 | Known English phrases and original retained |
| 20-second video, four-second audio delay | 5.156 | PCM delay and approximate ASR source time preserved |
| Five-second video without audio | 0.312 | No invented transcript; playable original |
| 65-second video | 3.313 | Three intervals; second speech on original clock; silent last interval |
| 65-second video, short audio track | 2.109 | Later intervals silent without ASR |
| MKV lecture | 2.360 | Audio duration/stream metadata retained |
| Corrupt video | 0.219 | Declined; original retained |

These are single runs on the 16 GB development laptop, using synthetic English speech and small 320×180 test patterns. Cache reuse and concurrent regression work can affect timing. They do not establish natural lecture accuracy, all playback codecs, long-video speed or whole-app memory on an 8 GB laptop. Contract speech responses are authored mocks; live pilot speech is real Groq output.

## Known boundaries

Nonzero container start times currently fail with an instruction to export an MP4 timeline starting at zero. The first audio stream is processed, with a warning when more exist. Container extensions do not guarantee Electron codec playback; the viewer offers interval-audio fallback and Save original/export guidance. Variable-frame-rate visual sampling, rotation-aware frames, scene selection and visual/audio fusion belong to subsequent video checkpoints. No ASR recognition output becomes verified evidence automatically; VAD can miss quiet speech and timestamps can be approximate. Existing Hindi/Hinglish quality failures remain relevant.

## Reproduce

```powershell
node scripts/python.mjs scripts/create-video-fixtures.py
npm.cmd run video:test
npm.cmd run api:test
npm.cmd run check
npm.cmd run smoke:desktop
# Local Tiny, with inherited Groq credentials cleared:
node scripts/python.mjs scripts/evaluate-video.py
# Explicit live Groq pilot on authored fixtures:
node scripts/python.mjs scripts/evaluate-video.py --cloud
# Use the completed isolated directory printed by the pilot:
node_modules/.bin/electron.cmd scripts/evaluate-video-desktop.cjs tmp/video-integration-20261003-071221
```

The desktop gate clears Groq credentials and operates on completed fixture data. No student data is used. The approximately 8 MB fixture set is authored locally with FFmpeg and existing synthetic audio; it downloads nothing.

## Student manual checkpoint

1. Restart Electron, import a lecture MP4 and open **Review video** after processing. Compare the transcript with what you hear.
2. Click a sentence timestamp, including one after 30 seconds. It should seek within the original video. Check any Hindi/Hinglish names and technical terms manually.
3. Cancel a longer video's extraction, close/reopen StudyLens and resume. Saved intervals should remain, with later intervals added.
4. Import a video without audio. It should remain playable and say that no audio transcript exists. Visual extraction should remain visibly pending.

Continue checking responsiveness and memory on the target 8 GB laptop. Phase 7B frame selection follows this checkpoint; YouTube remains a later independent ingestion checkpoint.
