"""Summarize a completed Hinglish run without changing benchmark outputs."""
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hinglish_eval", ROOT / "scripts/evaluate-hinglish.py")
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)
source = Path(sys.argv[1]) if len(sys.argv) > 1 else max((ROOT / "docs/evaluation").glob("hinglish-results-*.json"), key=lambda p: p.stat().st_mtime)
source = source.resolve()
report = json.loads(source.read_text("utf-8"))
if report.get("status") != "completed":
    raise SystemExit("The benchmark is still running; use its per-clip progress output.")
samples = report["samples"]
auto = [s for s in samples if s["mode"] == "auto"]
hint = [s for s in samples if s["mode"] == "hi"]
paired_keys = {(s["shard"], s["row"]) for s in hint}
paired_auto = [s for s in auto if (s["shard"], s["row"]) in paired_keys]
paired = {"auto": evaluation.aggregate(paired_auto), "hi": evaluation.aggregate(hint)}
summary = {"source_report": str(source.relative_to(ROOT)), "allocation": evaluation.SIZES,
    "baseline": evaluation.aggregate(auto), "paired_hinglish": paired,
    "baseline_failures": dict(Counter(s["error"] for s in auto if s["error"])),
    "failed_count": sum(s["state"] == "failed" for s in auto),
    "audio_seconds": round(sum(s["duration_seconds"] for s in auto), 3),
    "pipeline_seconds": round(sum(s["pipeline_seconds"] for s in auto), 3),
    "max_helper_mib": round(max(s["peak_helper_private_bytes"] for s in samples) / 1024**2, 2),
    "all_originals_unchanged": all(s["original_unchanged"] for s in samples),
    "all_transcripts_unverified": all(s["all_transcripts_unverified"] for s in samples),
    "hardware": json.loads((ROOT / "docs/evaluation/hinglish-hardware.json").read_text("utf-8-sig")),
    "model": {"name": "Multilingual faster-whisper Tiny", "model_binary_sha256": "dcb76c6586fc06cbdac6dd21f14cfd129cc4cdd9dce19bf4ffa62e59cbe6e6d1", "compute_type": "int8", "device": "cpu", "cpu_threads": 2,
              "faster_whisper": "1.2.1", "ctranslate2": "4.8.2", "av": "16.1.0", "onnxruntime": "1.30.0"}}
(ROOT / "docs/evaluation/hinglish-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
lines = ["# Noisy Hinglish dataset evaluation", "", "Date: October 2, 2026.", "",
    "Dataset: [addyo07/noisy-hinglish-asr](https://huggingface.co/datasets/addyo07/noisy-hinglish-asr), pinned revision `" + evaluation.REVISION + "`.",
    "Seed 42; 100 test clips (40 Hinglish, 20 Hindi, 20 English, 20 non-speech) plus 20 noisy-Hindi benchmark clips. The test split contains clean speech and neutral background/silence; noisy speech is evaluated from the separate benchmark. This is a stratified subset, not a full-dataset or population-weighted score.", "",
    "The real app API, worker, FFmpeg and offline Tiny speech helpers were used with the existing 30-second intervals, VAD, CPU int8, beam 1, and time/memory bounds. Raw helper output is observed for evaluation only; rejected transcripts are not inserted into app content units. No model training or cloud transcription occurred.", "",
    "## Auto-language baseline", "", "| Dataset group | Clips | Raw ASR WER | App-output WER | Timestamp rejections | Median processing |", "|---|---:|---:|---:|---:|---:|"]
for group, value in summary["baseline"].items():
    raw = "—" if value["raw_asr_wer_percent"] is None else f"{value['raw_asr_wer_percent']}%"
    accepted = "—" if value["wer_percent"] is None else f"{value['wer_percent']}%"
    lines.append(f"| {group} | {value['clips']} | {raw} | {accepted} | {value['timestamp_rejections']} | {value['median_pipeline_seconds']} s |")
lines += ["", "WER is substitutions + deletions + insertions divided by reference words; it can exceed 100%. Lower is better. Normalization uses Unicode NFKC, casefold, punctuation/symbol removal and collapsed whitespace. It does not translate, transliterate, normalize numbers or rewrite references. Raw WER measures recognition before timestamp validation. App-output WER counts rejected clips as empty output, reflecting what a student actually receives. Non-speech clips use false-speech counts instead of undefined WER.", "",
    "## Non-speech and language hint", ""]
for noise in ("pure_silence", "room_background"):
    part = [s for s in auto if s["group"] == "neutral" and s["noise_type"] == noise]
    hallucinated = sum(bool(evaluation.normalize(s["raw_prediction"])) for s in part)
    displayed = sum(bool(evaluation.normalize(s["prediction"])) for s in part)
    lines.append(f"- {noise}: {hallucinated}/{len(part)} raw false-speech responses; {displayed}/{len(part)} displayed false-speech responses.")
if hint:
    a = paired["auto"]["hinglish"]
    h = paired["hi"]["hinglish"]
    lines += [f"- Same {len(hint)} Hinglish clips with a Hindi hint: raw WER {a['raw_asr_wer_percent']}% → {h['raw_asr_wer_percent']}%; app-output WER {a['wer_percent']}% → {h['wer_percent']}%; timestamp rejections {a['timestamp_rejections']} → {h['timestamp_rejections']}.",
              "- The hint check uses the first seeded 20 Hinglish selections, chosen before seeing outcomes. It changes only this benchmark process's environment and does not change the app default."]
lines += ["", "## Resource and validity notes", "",
    f"CPU: {summary['hardware']['cpu']}; installed RAM {summary['hardware']['ram_bytes']/1024**3:.2f} GiB. Baseline audio: {summary['audio_seconds']} seconds; processing: {summary['pipeline_seconds']} seconds. Maximum sampled speech-helper private memory: {summary['max_helper_mib']} MiB. Timing includes helper/model startup per interval, conversion and persistence, excluding dataset download/preparation and the initial original-integrity job. This is not a full 8 GB/Electron/OS memory benchmark.", "",
    f"The baseline has {summary['failed_count']} failed clips; errors are retained in the raw report. All originals were preserved: {summary['all_originals_unchanged']}. All accepted transcripts retain their unverified status: {summary['all_transcripts_unverified']}.", "",
    "The initial same-process Parquet loader retained more than the worker's 512 MiB memory allowance; the guard stopped it before ASR. Dataset preparation was moved to a child process. A separate interrupted 14-clip diagnostic exposed timestamp errors and is retained. The final benchmark kept the production validator and model parameters unchanged.", "",
    "Dataset references are not human-audited here. Hindi words written in Devanagari, Romanized Hindi, and English words written phonetically in Devanagari can represent the same speech with different strings. Script differences can inflate WER, while wrong/missing spoken content remains a real accuracy problem. Language labels are dataset labels, not guaranteed speech-language truth. The noisy-Hindi benchmark may overlap main/training partitions; no independence claim is made for it. Noise variants may be correlated. This sample does not establish accuracy on lectures or all Indian languages.", "",
    "## Reproduce", "", "```powershell", "node scripts/python.mjs -m pip install pyarrow==25.0.1 --target tmp/hinglish-eval-deps", "node scripts/python.mjs scripts/evaluate-hinglish.py", f"node scripts/python.mjs scripts/report-hinglish.py {source.relative_to(ROOT).as_posix()}", "```", "",
    f"[Raw per-clip results]({source.name}) · [Selection manifest](hinglish-manifest.json) · [Machine-readable summary](hinglish-summary.json)", ""]
if report.get("resume_note"):
    lines += ["## Run continuation", "", report["resume_note"], ""]
baseline_hinglish = summary["baseline"]["hinglish"]
lines += ["## Recommendation", "",
    f"The current Tiny configuration has not demonstrated reliable Hinglish ingestion on this sample: raw WER {baseline_hinglish['raw_asr_wer_percent']}%, with {baseline_hinglish['timestamp_rejections']}/{baseline_hinglish['clips']} clips rejected for timestamps. Keep transcripts subject to student review before they become grounding evidence.", "",
    "Investigate short-clip timestamp handling separately from recognition quality. The diagnostic includes both a small endpoint overshoot and a multi-second overrun, so accepting every out-of-range timestamp would hide failures. This evaluation did not relax the validator.", "",
    "Before choosing a replacement, compare another multilingual speech model on these same clips and on the target 8 GB laptop. Add human-reviewed Hinglish references and a separate script-aware scoring pass; keep the unmodified WER baseline to avoid hiding omissions or hallucinated speech. This run does not establish which replacement model is best.", ""]
if hint:
    lines += [f"A Hindi hint changed paired raw WER from {a['raw_asr_wer_percent']}% to {h['raw_asr_wer_percent']}% and timestamp rejections from {a['timestamp_rejections']} to {h['timestamp_rejections']}. It does not by itself establish a reliable Hinglish configuration.", ""]
(ROOT / "docs/evaluation/hinglish-asr.md").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=True))
