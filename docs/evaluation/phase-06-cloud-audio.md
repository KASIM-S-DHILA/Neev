# Phase 6 extension — automatic Groq audio

October 3, 2026. Uploaded recordings now use local preparation and automatic cloud transcription. Live voice tutoring remains deferred. No additional model was downloaded.

## Independent checkpoints

1. **Prepare:** Verify the original, probe the first audio stream, decode one 30-second mono 16 kHz PCM interval with FFmpeg. Exact-zero audio skips transcription. Bundled Silero VAD runs in an isolated child before cloud requests. A negative result saves an empty, reviewable interval; an unavailable detector transcribes the full interval with a warning. VAD does not trim audio or change timestamps.
2. **Transcribe:** With `GROQ_API_KEY`, send the full speech-containing interval to `whisper-large-v3-turbo` with `verbose_json`. Check text/segment agreement, timestamp order/range, size and finite diagnostics. On quota, network, access or malformed output, use the installed CPU Tiny model when available. Access/output failures switch the remaining recording to local processing; reprocessing clears that decision. All output remains unverified.
3. **Recover and review:** Transcript, playback and checkpoint commit together. Waits release the worker; cancellation retains earlier units; restart resumes at the next interval. Cloud responses are cached by WAV hash, model, adapter version and language hint, with a checksum. A response cached just before cancellation is reused. Corrupt caches fall back locally. Materials discloses uploads; Review transcript labels provenance and links absolute timestamps to clip playback.

## Setup and bounds

The existing Groq key enables audio on the next launch. FFmpeg/ffprobe are required. Tiny is optional for cloud operation, required for offline fallback. Settings shows readiness. `npm.cmd run audio:setup` explicitly installs the fallback; uploading never downloads a model.

`STUDYLENS_AUTO_GROQ_AUDIO=0` disables cloud audio independently of vision. `STUDYLENS_AUDIO_LANGUAGE` defaults to `auto`; `hi` or `en` gives a language hint. Restart after environment changes. **Reprocess audio** starts the current pipeline for older material. Partial transcripts from changed settings/model versions require reprocessing rather than mixing configurations.

Durable request spacing: at least 3.2 seconds. The local ledger reserves attempted requests before sending, counting at least ten seconds each, capped at 7,000 audio seconds/hour, 28,000/day and 1,900 requests/day. These are conservative limits for one data directory, not account-wide remaining quota. Other apps/directories can consume the same account quota. HTTP 429 respects Retry-After. Normal pacing never switches to Tiny. Without local fallback, quota requeues without consuming failure retries; after three unsuccessful waits it stops until manually resumed. Local text jobs can run during those waits.

Uploads: at most 1 MiB; responses: 2 MiB; request deadline: 23 seconds, cancellable. Existing limits remain four-hour recordings, 100 segments/12,000 transcript characters per interval. Parent and VAD child have separate 512 MiB guards; VAD has a 10-second deadline. Tiny retains its 1536 MiB/25-second bound. Keys stay in the backend and are stripped from helper environments. Originals remain local; decoded speech intervals are sent externally when cloud is enabled.

See [Groq speech documentation](https://console.groq.com/docs/speech-to-text) for models, diagnostics and billing, and [rate limits](https://console.groq.com/docs/rate-limits) for published defaults. Exact account limits can differ; the adapter handles exhausted quota.

## Measured gates

| Check | Result |
|---|---|
| Cloud contract | 18 tests: multipart/language, fallback, quota, cache, corruption, cancellation, restart, integrity and isolation |
| Local audio / automatic visual / durable queue | 11 / 9 / 16 tests passed |
| Renderer / build / Electron smoke | 13 tests passed; build and smoke passed |
| Live auto-language pipeline | 14/14 structural checks; ten cloud calls, 140 conservatively reserved seconds |
| Paired Hindi-hint pipeline | 8/8 structural checks, including two silent controls; six cloud calls |
| Native playback | Upload disclosure and Groq label visible; source label 00:34 seeks to 4.74 seconds in the second 30-second clip |

Raw evidence: [auto-language pilot](cloud-audio-20261002-193932.json), [Hindi hint](cloud-audio-20261002-194327.json), [Electron checks](cloud-audio-desktop.json), [screenshot](screenshots/cloud-audio-desktop.png). Filenames use UTC; local date is October 3. Pilot sample `passed` means ingestion passed, not speech accuracy certification.

English clean/noisy fixtures recovered both known phrases. Clean 9.37-second input took 3.813 seconds end to end, noisy 3.125 seconds, and the 65-second fixture 10.937 seconds. Ten transfers took 0.297–0.610 seconds each. These single runs include preparation, startup, fingerprinting, persistence and any pacing, on the 16 GB development laptop. Some fixture tests ran concurrently. This is not an isolated speed comparison or whole-app 8 GB result.

## Quality gate remains open

Eight public clips came from the existing pinned `addyo07/noisy-hinglish-asr` manifest: two genuinely mixed-script Hinglish, two Hindi, two noisy Hindi and two silent controls. References are not human-audited. Literal WER penalizes script differences and can exceed 100% through insertions.

| Clip | Auto raw WER | Hindi-hint raw WER |
|---|---:|---:|
| Hinglish 0 | 123.1% | 123.1% |
| Hinglish 1 | 80.0% | 200.0% |
| Hindi 0 | 100.0% | 23.1% |
| Hindi 1 | 12.5% | 12.5% |
| Noisy Hindi 0 | 100.0% | 35.7% |
| Noisy Hindi 1 | 100.0% | 200.0% |

Auto returned Hindi 0 in Urdu script, dropped/translated words in other clips, and returned Japanese for a short noisy Hindi utterance. Hindi hint improved two Hindi clips, but worsened one Hinglish clip and still misheard the shortest utterance. **Do not force Hindi globally or claim reliable Hinglish recognition.** Production remains auto; compare with the audio. ASR diagnostics are not correctness proofs. Natural lectures, accents, quiet speech and background false detections need broader human review.

Fixed intervals may split words. Overlap/merging, speaker separation and translation verification are not implemented. VAD can miss speech; empty intervals remain listenable with a warning. Neither cloud nor Tiny output becomes verified evidence through this change.

## Reproduce

```powershell
npm.cmd run audio:cloud:test
npm.cmd run audio:test
npm.cmd run queue:test
npm.cmd run check
npm.cmd run smoke:desktop
# Explicitly sends fixture speech to Groq:
node scripts/python.mjs scripts/evaluate-cloud-audio.py --cloud
node scripts/python.mjs scripts/evaluate-cloud-audio.py --cloud --public-only --language hi
# Use the completed isolated directory printed by the pilot:
node_modules/.bin/electron.cmd scripts/evaluate-audio-desktop.cjs tmp/audio-integration-groq-20261002-193932 --cloud-fixture
```

Contract tests use authored keys and mock HTTP. The native gate uses a fake key for status on completed fixture data and uploads nothing. The legacy local evaluator clears inherited cloud credentials.

## Student manual checkpoint

Restart Electron. Import a lecture, or **Reprocess audio** on an older version. In **Review transcript**, check the Groq label, listen to timestamps including an interval after 30 seconds, and compare Hindi/Hinglish terms. Cancel/resume a longer recording and confirm saved intervals remain. Check responsiveness and memory on the target 8 GB laptop; that hardware gate remains open.
