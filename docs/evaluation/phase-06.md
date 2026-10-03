# Phase 6 — local audio ingestion

Date: October 2, 2026. Implementation and automated/native gates are ready for student review. Live voice tutoring remains on hold. This phase processes imported recordings.

October 3 update: the [automatic Groq audio extension](phase-06-cloud-audio.md) now provides cloud transcription with local Tiny fallback. This document retains the original local-only implementation and measurements; its no-cloud statements describe that earlier gate. Current setup, limits, quality findings and manual checks are in the extension report.

## Independent checkpoints

1. **Decode and preserve:** WAV, MP3, M4A, OGG and FLAC originals remain unchanged. FFprobe selects the first audio stream; FFmpeg decodes at most 30 seconds at a time into mono 16 kHz, signed 16-bit PCM. Each interval has an absolute source-time locator. No denoising or amplitude normalization changes the waveform beyond resampling/downmixing. Corrupt sources and unknown/nonfinite/over-limit durations are declined; they remain saved.
2. **Transcribe and resume:** Multilingual faster-whisper Tiny runs locally on CPU with int8 inference, two CPU threads, VAD and no prior-text conditioning. One isolated helper handles each nonsilent interval. Transcript text, segment timestamps, playback preview and checkpoint commit together. Cancel/restart retains completed intervals and resumes at the next one. Changed model/settings require **Reprocess audio**, preventing mixed configurations in a resumed transcript.
3. **Review in Electron:** Materials → **Review transcript** shows an interval player, transcript and clickable absolute timestamps. Clicking a timestamp seeks within the current clip. Source details retain original hash, stable unit ID, detected language and model fingerprint. **Reprocess audio** rebuilds this version's transcript; it keeps the original. No audio cloud endpoint is implemented.

ASR text always has `status=suspect`, `review_required=true`, and a comparison warning; it is not verified retrieval evidence. An empty result means “no speech recognized,” not proof that no speech exists. Near-zero PCM bypasses ASR. Clipping and multiple-stream warnings remain visible. The first audio stream is used and channels are downmixed; speakers are not identified or separated. The source is not translated, summarized or corrected.

## Setup and resource bounds

The development environment already has the runtime and model installed. For another checkout:

```powershell
npm.cmd run audio:setup
```

Install FFmpeg including ffprobe separately. Optional executable paths: `STUDYLENS_FFMPEG` and `STUDYLENS_FFPROBE`. `STUDYLENS_AUDIO_MODEL_DIR` can point to the downloaded local Tiny model folder. `STUDYLENS_AUDIO_LANGUAGE` defaults to `auto`; a language code such as `en` or `hi` can force recognition language. Restart after changing environment settings; settings/model changes during a partial job require reprocessing.

Setup explicitly downloads [Systran/faster-whisper-tiny](https://huggingface.co/Systran/faster-whisper-tiny), pinned to revision `d90ca5fe260221311c53c58e660288d3deb8d356`. The model binary is 75,538,270 bytes (72.04 MiB); tokenizer/config/vocabulary are additional small files. Runtime libraries occupy additional storage. Imports use `local_files_only=True` and never silently download a model or send recordings externally. The [faster-whisper documentation](https://github.com/SYSTRAN/faster-whisper) specifies CPU int8, generated segment timestamps and VAD support; [FFmpeg documentation](https://ffmpeg.org/ffmpeg.html) describes seeking, stream mapping and audio conversion.

Bounds: originals up to 2 GB; recordings up to four hours; 30-second intervals; each PCM preview at most 1 MiB; 100 ASR segments/12,000 transcript characters per interval. Every interval is released before decoding the next. Previews can add approximately 115 MB/hour to disk use, beyond the original. Only the requested interval is sent to the renderer. No long recording is loaded into renderer RAM.

The parent worker retains its existing sampled 512 MiB/30-second-step guard. Windows helper job objects keep OCR/FFmpeg at 512 MiB and cap the speech helper at **1536 MiB**. The CPU speech helper has a 25-second deadline; FFmpeg/ffprobe have 20-second deadlines. Cancellation is polled during helpers and closes the child tree. Credentials are removed from helper environments. Non-Windows native memory ownership still needs hardening.

Model storage size is not runtime RAM. The initial real transcription showed about 1.23 GiB private memory after ASR; measured sampled helper peaks in the retained pipeline reached about **1.264 GiB**. This motivated a separate speech-helper cap. No complete 8 GB laptop benchmark is claimed. Repeated helper imports/model loads add overhead but release speech memory before other work begins.

## Evaluation and failures retained

Fixtures in `fixtures/phase-06` are self-authored English Windows SAPI speech, plus deterministic noise, silence, tone, corrupt bytes, compressed-format copies, and a 65-second recording with speech at 0 and 32 seconds. [Gold/provenance](fixtures/phase-06/gold.json). Unicode handling has a labeled contract test, not a claim of speech accuracy.

The October 2 [public Hinglish dataset evaluation](hinglish-asr.md) tested 120 seeded clips and a 20-clip paired Hindi hint check through the real pipeline. Tiny has not demonstrated reliable Hinglish quality: raw WER was 93.91% on 40 Hinglish clips, and 20 of those clips were rejected for timestamps. Three of ten room-background clips produced false speech. Script differences and unaudited dataset references limit accuracy interpretation. The quality gate remains open; this evaluation changed no production model settings or timestamp rules.

```powershell
npm.cmd run audio:test
node scripts/python.mjs scripts/evaluate-audio.py
npm.cmd run api:test
npm.cmd run check
```

| Check | Observed result |
|---|---|
| Independent audio contract | 11 tests passed; real FFmpeg, labeled ASR fixtures, disposable databases |
| Full service regression | 93 tests passed |
| JS / TypeScript / production build | 13 tests passed; build passed |
| Native Electron transcript/player/seek | Passed; PCM duration 9.368 seconds, seek to 2.6 seconds |
| Clean speech pipeline | Both known phrases recovered; 6.235 seconds end to end |
| Noisy speech pipeline | 6.063 seconds; “degrees” became “degree,” failing exact-text match |
| Silence / tone | No invented speech; 1.047 / 4.578 seconds |
| 65-second recording | Three exact intervals (0–30, 30–60, 60–65); absolute segment times retained; 12.360 seconds |
| Corrupt recording | Declined with no saved transcript; original retained |

The clean/noisy/tone timings include process/model startup, conversion, inference and persistence, on this development machine. They are single known samples, not latency distributions or held-out accuracy estimates. Noisy audio intentionally remains `needs-review` in the [real pipeline report](audio-integration-20261002-041044.json); the overall quality report is not labeled passed. The native gate has [its own report](audio-desktop.json) and [visually inspected screenshot](screenshots/phase-06-audio-desktop.png).

Initial integration failed because faster-whisper 1.2.1 called `metadata_errors`, removed in PyAV 19. PyAV 16.1 is pinned and the real gate then completed. The first contract run also used the wrong exception expectation in two tests; corrected tests passed. The corrupt-source helper message was subsequently clarified to distinguish unsupported/damaged data from a time/memory limit; its earlier generic wording is retained in the initial pipeline report.

The native evaluation uses the isolated data directory from the pipeline report:

```powershell
node_modules/.bin/electron.cmd scripts/evaluate-audio-desktop.cjs tmp/audio-integration-20261002-041044
```

## Student acceptance checks

Restart StudyLens using the shortcut or `npm.cmd run dev`.

1. Add a short WAV/MP3/M4A recording, then **Review transcript**. Listen, compare words/numbers and click timestamps. Older saved audio files gain extraction jobs after restart.
2. Try a recording longer than one minute. Check intervals 1–3, especially words near 00:30/01:00. Cancel while it runs, restart, then **Background work → Resume**; earlier intervals should remain.
3. Navigate/scroll while transcription runs on the 8 GB laptop. Note freezes and Task Manager memory. Test a noisy or Hindi/Hinglish recording; report misheard/missing content. Poor output must retain its review warning.

Remaining limits: fixed interval boundaries can split words; tiny-model recognition is imperfect; language is detected per interval and can drift in mixed speech; background music and very quiet speech can confuse VAD. No diarization, speaker-channel selection, word-level gold alignment, semantic verification or automatic transcription correction is claimed. Long natural lectures, mixed languages and whole-app memory still need student/human evaluation. Phase 7 video work follows acceptance of this implemented scope.

## Multimodal model investigation

The separate [Gemma 4 E2B benchmark](gemma4-omni.md) compares audio recognition and document extraction with existing local models. It is an isolated evaluation; production audio still uses the implemented Tiny pipeline. Any model integration needs aligned source timestamps and whole-app evaluation on the target laptop.
