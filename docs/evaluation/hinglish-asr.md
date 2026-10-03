# Noisy Hinglish dataset evaluation

Date: October 2, 2026.

Dataset: [addyo07/noisy-hinglish-asr](https://huggingface.co/datasets/addyo07/noisy-hinglish-asr), pinned revision `85cba6bc97ea02b78e23f562e0ccc8f772c94228`.
Seed 42; 100 test clips (40 Hinglish, 20 Hindi, 20 English, 20 non-speech) plus 20 noisy-Hindi benchmark clips. The test split contains clean speech and neutral background/silence; noisy speech is evaluated from the separate benchmark. This is a stratified subset, not a full-dataset or population-weighted score.

The real app API, worker, FFmpeg and offline Tiny speech helpers were used with the existing 30-second intervals, VAD, CPU int8, beam 1, and time/memory bounds. Raw helper output is observed for evaluation only; rejected transcripts are not inserted into app content units. No model training or cloud transcription occurred.

## Auto-language baseline

| Dataset group | Clips | Raw ASR WER | App-output WER | Timestamp rejections | Median processing |
|---|---:|---:|---:|---:|---:|
| en | 20 | 5.73% | 5.73% | 0 | 5.289 s |
| hi | 20 | 125.29% | 122.99% | 3 | 5.453 s |
| hinglish | 40 | 93.91% | 115.24% | 20 | 5.446 s |
| neutral | 20 | — | — | 0 | 2.633 s |
| noisy_hi | 20 | 178.01% | 175.95% | 6 | 5.219 s |

WER is substitutions + deletions + insertions divided by reference words; it can exceed 100%. Lower is better. Normalization uses Unicode NFKC, casefold, punctuation/symbol removal and collapsed whitespace. It does not translate, transliterate, normalize numbers or rewrite references. Raw WER measures recognition before timestamp validation. App-output WER counts rejected clips as empty output, reflecting what a student actually receives. Non-speech clips use false-speech counts instead of undefined WER.

## Non-speech and language hint

- pure_silence: 0/10 raw false-speech responses; 0/10 displayed false-speech responses.
- room_background: 3/10 raw false-speech responses; 3/10 displayed false-speech responses.
- Same 20 Hinglish clips with a Hindi hint: raw WER 100.6% → 168.67%; app-output WER 125.9% → 189.16%; timestamp rejections 12 → 11.
- The hint check uses the first seeded 20 Hinglish selections, chosen before seeing outcomes. It changes only this benchmark process's environment and does not change the app default.

## Resource and validity notes

CPU: Intel(R) Core(TM) i7-8750H CPU @ 2.20GHz; installed RAM 15.86 GiB. Baseline audio: 531.802 seconds; processing: 618.174 seconds. Maximum sampled speech-helper private memory: 1295.67 MiB. Timing includes helper/model startup per interval, conversion and persistence, excluding dataset download/preparation and the initial original-integrity job. This is not a full 8 GB/Electron/OS memory benchmark.

The baseline has 29 failed clips; errors are retained in the raw report. All originals were preserved: True. All accepted transcripts retain their unverified status: True.

The initial same-process Parquet loader retained more than the worker's 512 MiB memory allowance; the guard stopped it before ASR. Dataset preparation was moved to a child process. A separate interrupted 14-clip diagnostic exposed timestamp errors and is retained. The final benchmark kept the production validator and model parameters unchanged.

Dataset references are not human-audited here. Hindi words written in Devanagari, Romanized Hindi, and English words written phonetically in Devanagari can represent the same speech with different strings. Script differences can inflate WER, while wrong/missing spoken content remains a real accuracy problem. Language labels are dataset labels, not guaranteed speech-language truth. The noisy-Hindi benchmark may overlap main/training partitions; no independence claim is made for it. Noise variants may be correlated. This sample does not establish accuracy on lectures or all Indian languages.

## Reproduce

```powershell
node scripts/python.mjs -m pip install pyarrow==25.0.1 --target tmp/hinglish-eval-deps
node scripts/python.mjs scripts/evaluate-hinglish.py
node scripts/python.mjs scripts/report-hinglish.py docs/evaluation/hinglish-results-20261002-044052.json
```

[Raw per-clip results](hinglish-results-20261002-044052.json) · [Selection manifest](hinglish-manifest.json) · [Machine-readable summary](hinglish-summary.json)

## Run continuation

The command stopped after saved clip 63 without a traceback. Completed results are retained; remaining clips use a fresh disposable database with unchanged inference parameters.

## Recommendation

The current Tiny configuration has not demonstrated reliable Hinglish ingestion on this sample: raw WER 93.91%, with 20/40 clips rejected for timestamps. Keep transcripts subject to student review before they become grounding evidence.

Investigate short-clip timestamp handling separately from recognition quality. The diagnostic includes both a small endpoint overshoot and a multi-second overrun, so accepting every out-of-range timestamp would hide failures. This evaluation did not relax the validator.

Before choosing a replacement, compare another multilingual speech model on these same clips and on the target 8 GB laptop. Add human-reviewed Hinglish references and a separate script-aware scoring pass; keep the unmodified WER baseline to avoid hiding omissions or hallucinated speech. This run does not establish which replacement model is best.

A Hindi hint changed paired raw WER from 100.6% to 168.67% and timestamp rejections from 12 to 11. It does not by itself establish a reliable Hinglish configuration.
