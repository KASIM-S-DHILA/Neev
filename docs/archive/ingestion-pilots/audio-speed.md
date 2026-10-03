# Audio pipeline latency pilot

Date: October 3, 2026 (Asia/Calcutta). Measured on this laptop: Intel i7-8750H, 6 cores/12 logical processors, 15.86 GiB installed RAM. Local speech uses the existing multilingual faster-whisper Tiny model, CPU int8, two inference threads. No models were downloaded. Imported-recording cloud transcription is not yet integrated into StudyLens.

## What was measured

- Eighteen real local app runs: six inputs, three repetitions each, through the API, original integrity check, background worker, FFprobe, FFmpeg, current isolated ASR helpers, transcript validation and persistence. File selection/transfer, UI rendering and queue contention are excluded.
- Nine live Groq transcription requests: clean/noisy authored synthetic English and the first 30 seconds of an authored continuous-speech recording, three repeats each. Requests used `whisper-large-v3-turbo`, `verbose_json`, temperature zero and a fresh HTTP connection. Network/upload/service/response time is included. Only authored fixtures were sent. No retries were made; all nine calls returned HTTP 200.
- Separate local VAD timing using the Silero ONNX model already bundled with faster-whisper. Measurements use decoded 16 kHz mono PCM and reuse the session after the initial call.

Raw times, transcripts, ASR diagnostics, memory and response rate-limit headers: [audio-speed.json](audio-speed.json). Scripts: `scripts/benchmark-audio-speed.py --cloud` and `scripts/benchmark-audio-vad.py` through the project Python. Omitting `--cloud` makes the first script local-only.

## Results

Times below are medians of three calls. These are a small pilot, not p95 estimates or guarantees.

| Input | Audio duration | Local app pipeline | Groq request |
|---|---:|---:|---:|
| Clean authored speech | 9.37 s | 3.62 s | 0.31 s |
| Noisy authored speech | 9.37 s | 3.82 s | 0.30 s |
| Continuous authored speech | 60 s | 9.09 s | 0.51 s for its first 30 s |
| Digital silence | 60 s | 1.15 s | Not sent |
| Hinglish-labeled public clip 1 | 9.57 s | 4.49 s; timestamp validation failed | Not sent |
| Hinglish-labeled public clip 2 | 6.73 s | 4.16 s; timestamp validation failed | Not sent |

The local 60-second speech pipeline ranged from 8.96 to 9.18 seconds. FFprobe plus decoding accounted for approximately 0.72 seconds; ASR helper calls accounted for approximately 7.98 seconds. The recognizer is the dominant local cost. Current helpers import the runtime and load the speech model afresh for each 30-second chunk. Filesystem caches can be warm between repetitions; this was not a reboot/cold-disk test.

VAD alone took approximately **0.125 seconds per minute of speech** and **0.132 seconds per minute of silence** with the session warm. Dependency imports took 0.284 seconds; the first 9-second VAD call took 0.459 seconds including initial session setup. The VAD process had 430.08 MiB private memory after processing. It did not load a Whisper transcription model. Run it in a background helper, within a verified memory budget.

The largest sampled speech-helper private-memory peak was **1297.07 MiB** (about 1.27 GiB). This does not include Electron, the parent service, other applications or the OS, and does not establish performance on the target 8 GB laptop.

## Implications for the proposed pipeline

Local preprocessing and speech detection are fast. Local Tiny transcription is faster than playback on these longer authored speech fixtures, but it adds seconds before any cloud fallback. Its setup overhead is proportionally more expensive on short clips. The two selected natural Hinglish-labeled clips failed the current strict timestamp validator on all three repeats. Their failed timings must not be presented as successful transcription throughput. The larger earlier [Hinglish quality evaluation](hinglish-asr.md) also leaves Tiny's quality gate open.

For this synthetic one-minute speech input, a mandatory local first pass costs approximately 9 seconds. A later Groq pass adds request time and any quota/pacing delay. Sending known challenging or mixed-language speech directly to Groq after local preparation avoids that initial ASR pass. Keep local Tiny available for offline processing or exhausted cloud quota. If local-first selection remains the chosen policy, retain confidence/coverage signals and reuse a bounded ASR helper across a recording's chunks to reduce repeated startup; those changes were not implemented or measured here.

Groq's advertised 216x speed factor is a provider throughput figure, not complete app latency. The published default Whisper Turbo limits include 20 requests/minute, 7,200 audio seconds/hour and 28,800 audio seconds/day; exact organization limits can differ. This pilot spaced requests by at least 3.2 seconds between starts. Its latency column excludes that deliberate spacing. At 30 seconds/request, processing every chunk of a one-hour recording requires 120 requests and roughly six minutes of request pacing at 20 RPM, even when individual responses are quick. Batching longer speech intervals can reduce request count but must be evaluated for timestamps, boundaries, accuracy and upload limits. [Speech API](https://console.groq.com/docs/speech-to-text), [Turbo model](https://console.groq.com/docs/model/whisper-large-v3-turbo), [rate limits](https://console.groq.com/docs/rate-limits).

No one-hour lecture was processed; long-recording estimates are extrapolations. Groq Hindi/Hinglish accuracy, denoising benefits, overlapping-chunk merging, automatic fallback routing and full Electron responsiveness were not evaluated by this speed pilot.

## Queue issue found and fixed

The first timing attempt stopped after five local repetitions when equal job creation timestamps allowed extraction to be claimed before its original integrity check. The queue now breaks timestamp ties by choosing verification before extraction while retaining local-work priority over cloud jobs. The completed timings above come from a fresh isolated run after that fix. A regression test forces tied timestamps and reverse-sorted job IDs. The automatic/ordering gate passed 9 tests; existing queue regression checks passed as recorded after this pilot. No audio model parameters, validation thresholds or production cloud-audio behavior were changed.
