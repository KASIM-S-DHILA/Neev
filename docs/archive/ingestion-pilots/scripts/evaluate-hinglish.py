"""Pinned, seeded ASR benchmark through the real StudyLens ingestion pipeline."""
import argparse
import hashlib
import json
import os
import random
import statistics
import subprocess
import sys
import threading
import time
import unicodedata
import wave
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
os.environ["GROQ_API_KEY"] = ""  # Preserve this benchmark's local Tiny-only contract.
sys.path.insert(0, str(ROOT / "tmp/hinglish-eval-deps"))
sys.path.insert(0, str(ROOT / "services/tests"))
from fastapi.testclient import TestClient
from test_storage import AUTH, BASE, SESSION, SOURCES, TOKEN
from studylens_service.api import create_app
from studylens_service.worker import Worker
from studylens_service import audio as audio_processor

DATASET = "addyo07/noisy-hinglish-asr"
REVISION = "85cba6bc97ea02b78e23f562e0ccc8f772c94228"
SEED = 42
SIZES = {"hinglish": 40, "hi": 20, "en": 20, "neutral": 20, "noisy_hi": 20}


def normalize(value):
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join("".join(" " if unicodedata.category(c)[0] in "PS" else c for c in value).split())


def edits(reference, hypothesis):
    # Standard Levenshtein counts. Tie choices affect S/D/I, not total error rate.
    previous = [(i, 0, 0, i) for i in range(len(hypothesis) + 1)]
    for index, token in enumerate(reference, 1):
        current = [(index, 0, index, 0)]
        for column, predicted in enumerate(hypothesis, 1):
            if token == predicted:
                current.append(previous[column - 1])
            else:
                cost, s, d, i = previous[column - 1]
                substitution = (cost + 1, s + 1, d, i)
                cost, s, d, i = previous[column]
                deletion = (cost + 1, s, d + 1, i)
                cost, s, d, i = current[column - 1]
                insertion = (cost + 1, s, d, i + 1)
                current.append(min(substitution, deletion, insertion, key=lambda x: x[0]))
        previous = current
    cost, s, d, i = previous[-1]
    return {"errors": cost, "substitutions": s, "deletions": d, "insertions": i, "reference_units": len(reference)}


def script(value):
    devanagari = any("\u0900" <= c <= "\u097f" for c in value)
    latin = any(c.isalpha() and ord(c) < 128 for c in value)
    return "mixed" if devanagari and latin else "devanagari" if devanagari else "latin" if latin else "empty_or_other"


def metadata():
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download
    rows, paths = [], {}
    for shard in range(4):
        name = f"data/test/test-{shard:05d}-of-00003.parquet" if shard < 3 else "data/benchmark/noisy_hi/train-00000-of-00001.parquet"
        path = hf_hub_download(DATASET, name, repo_type="dataset", revision=REVISION,
                               cache_dir=ROOT / "tmp/hinglish-dataset/hub")
        paths[shard] = path
        for index, row in enumerate(pq.read_table(path, columns=["file_name", "transcription", "language", "noise_type", "source"]).to_pylist()):
            rows.append(row | {"shard": shard, "row": index, "group": "noisy_hi" if shard == 3 else row["language"],
                               "partition": "benchmark/noisy_hi" if shard == 3 else "test"})
    return rows, paths


def choose(rows):
    rng = random.Random(SEED)
    selected = []
    for group, count in SIZES.items():
        pool = [row for row in rows if row["group"] == group]
        if group == "neutral":
            for noise in ("pure_silence", "room_background"):
                selected.extend(rng.sample([row for row in pool if row["noise_type"] == noise], count // 2))
        else:
            selected.extend(rng.sample(pool, min(count, len(pool))))
    return selected


def extract_samples(selected, paths):
    import pyarrow.parquet as pq
    folder = ROOT / "tmp/hinglish-dataset/samples"
    folder.mkdir(parents=True, exist_ok=True)
    for shard, path in paths.items():
        wanted = {row["row"]: row for row in selected if row["shard"] == shard}
        offset = 0
        for batch in pq.ParquetFile(path).iter_batches(batch_size=16, columns=["audio"]):
            for index, audio in enumerate(batch.column(0).to_pylist(), offset):
                if index in wanted:
                    row = wanted[index]
                    raw = audio["bytes"]
                    sample_path = folder / f"sample-{shard}-{index:04d}.wav"
                    sample_path.write_bytes(raw)
                    with wave.open(str(sample_path), "rb") as wav:
                        row["duration_seconds"] = wav.getnframes() / wav.getframerate()
                    row["audio_sha256"] = hashlib.sha256(raw).hexdigest()
                    row["sample_path"] = str(sample_path.relative_to(ROOT))
            offset += len(batch)
        del batch
    return selected


def aggregate(samples):
    groups = {}
    for group in sorted({sample["group"] for sample in samples}):
        part = [sample for sample in samples if sample["group"] == group]
        words = sum(s["word_edits"]["reference_units"] for s in part)
        chars = sum(s["char_edits"]["reference_units"] for s in part)
        duration = sum(s["duration_seconds"] for s in part)
        negative = [s for s in part if not normalize(s["reference"])]
        groups[group] = {"clips": len(part), "audio_seconds": round(duration, 3),
            "pipeline_failures": sum(s["state"] == "failed" for s in part),
            "wer_percent": round(100 * sum(s["word_edits"]["errors"] for s in part) / words, 2) if words else None,
            "raw_asr_wer_percent": round(100 * sum(s["raw_word_edits"]["errors"] for s in part) / words, 2) if words else None,
            "cer_percent": round(100 * sum(s["char_edits"]["errors"] for s in part) / chars, 2) if chars else None,
            "raw_asr_cer_percent": round(100 * sum(edits(normalize(s["reference"]).replace(" ", ""), normalize(s["raw_prediction"]).replace(" ", ""))["errors"] for s in part) / chars, 2) if chars else None,
            "median_pipeline_seconds": round(statistics.median(s["pipeline_seconds"] for s in part), 3),
            "real_time_factor": round(sum(s["pipeline_seconds"] for s in part) / duration, 3),
            "empty_predictions_on_speech": sum(bool(normalize(s["reference"])) and not normalize(s["prediction"]) for s in part),
            "false_speech_negatives": sum(bool(normalize(s["prediction"])) for s in negative), "negative_clips": len(negative),
            "script_pairs": dict(Counter(s["reference_script"] + " -> " + s["prediction_script"] for s in part)),
            "raw_script_pairs": dict(Counter(s["reference_script"] + " -> " + s["raw_prediction_script"] for s in part)),
            "timestamp_rejections": sum(s["error"] is not None and "timestamps" in s["error"] for s in part),
            "peak_helper_mib": round(max((s["peak_helper_private_bytes"] for s in part), default=0) / 1024**2, 2)}
    return groups


def run(hint_count, resume_path=None):
    manifest_path = ROOT / "docs/evaluation/hinglish-manifest.json"
    manifest = json.loads(manifest_path.read_text("utf-8"))
    assert manifest["revision"] == REVISION and manifest["seed"] == SEED and manifest["allocation"] == SIZES
    selected = manifest["samples"]
    tag = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    data_root = ROOT / "tmp" / ("hinglish-integration-" + tag)
    report_path = ROOT / "docs/evaluation" / ("hinglish-results-" + tag + ".json")
    report = {"dataset": DATASET, "revision": REVISION, "seed": SEED, "data_directory": str(data_root),
        "harness_repair": "Initial same-process Parquet preparation retained memory over the app worker's 512 MiB bound and was correctly stopped before ASR. Preparation now runs in a separate process; app resource guards are unchanged.",
        "earlier_run": "hinglish-results-20261002-043540.json retains the interrupted 14-clip diagnostic run that exposed endpoint rejections; final baseline parameters are unchanged.",
        "method": "Real StudyLens API/worker/FFmpeg; offline multilingual Tiny CPU int8, VAD, beam1, original 30s intervals and helper bounds",
        "metrics": "NFKC/casefold, punctuation/symbols to spaces, whitespace collapsed; standard word edit rate and Unicode-codepoint CER. No transliteration, translation, number rewriting or reference-aware correction.",
        "limitations": ["Seeded small stratified sample, not the full dataset or population-weighted overall score.",
            "Dataset labels/transcripts have not been human audited; script differences contribute to errors.",
            "Noisy Hindi benchmark rows may overlap training/main partitions; no held-out independence claim for that group.",
            "Speech-helper sampled peak excludes Electron/OS; speed includes model startup per interval."], "samples": []}
    if resume_path:
        report_path = Path(resume_path).resolve()
        report = json.loads(report_path.read_text("utf-8"))
        assert report["dataset"] == DATASET and report["revision"] == REVISION and report["seed"] == SEED
        if report.get("status") == "completed":
            raise SystemExit("This benchmark is already complete.")
        report.setdefault("resumed_data_directories", []).append(str(data_root))
        report["resume_note"] = "The command stopped after saved clip 63 without a traceback. Completed results are retained; remaining clips use a fresh disposable database with unchanged inference parameters."
    completed = {(s["mode"], s["shard"], s["row"]) for s in report["samples"]}
    settings_before = os.environ.get("STUDYLENS_AUDIO_LANGUAGE")
    modes = [("auto", selected)]
    if hint_count:
        modes.append(("hi", [row for row in selected if row["group"] == "hinglish"][:hint_count]))
    with TestClient(create_app(data_root, TOKEN), headers=AUTH) as client:
        client.put(BASE + "/session", json={"base_revision": 0, "session": SESSION}).raise_for_status()
        worker = Worker(data_root, threading.Event())
        try:
            for mode, samples in modes:
                os.environ["STUDYLENS_AUDIO_LANGUAGE"] = mode
                for index, row in enumerate(samples, 1):
                    if (mode, row["shard"], row["row"]) in completed:
                        continue
                    raw = (ROOT / row["sample_path"]).read_bytes()
                    response = client.post(SOURCES, params={"filename": f"sample-{row['shard']}-{row['row']}-{mode}.wav"}, content=raw)
                    response.raise_for_status()
                    version = response.json()["version_id"]
                    worker.execute(worker.claim())
                    started = time.monotonic()
                    raw_outputs = []
                    production_transcribe = audio_processor.transcribe
                    def observe_transcription(*arguments):
                        result = production_transcribe(*arguments)
                        raw_outputs.append(result)
                        return result
                    # Observe the real helper return before app timestamp validation.
                    # This never changes output, bypasses validation or writes rejected text to app units.
                    with patch.object(audio_processor, "transcribe", side_effect=observe_transcription):
                        worker.execute(worker.claim())
                    content = client.get(BASE + f"/source-versions/{version}/content?limit=10").json()
                    elapsed = time.monotonic() - started
                    units = content["units"]
                    prediction = " ".join(unit["text"] for unit in units)
                    raw_prediction = " ".join(segment["text"].strip() for result in raw_outputs for segment in result["segments"])
                    reference_normalized, prediction_normalized = normalize(row["transcription"]), normalize(prediction)
                    sample = {k: row[k] for k in ("file_name", "partition", "group", "language", "noise_type", "source", "shard", "row", "audio_sha256", "duration_seconds")}
                    sample.update(mode=mode, state=content["state"], error=content["error"], version_id=version,
                        reference=row["transcription"], prediction=prediction, reference_script=script(row["transcription"]), prediction_script=script(prediction),
                        raw_prediction=raw_prediction, raw_prediction_script=script(raw_prediction),
                        raw_word_edits=edits(reference_normalized.split(), normalize(raw_prediction).split()),
                        raw_segment_times=[{"start": segment["start"], "end": segment["end"]} for result in raw_outputs for segment in result["segments"]],
                        word_edits=edits(reference_normalized.split(), prediction_normalized.split()),
                        char_edits=edits(reference_normalized.replace(" ", ""), prediction_normalized.replace(" ", "")),
                        pipeline_seconds=round(elapsed, 3), units=len(units),
                        detected_languages=[unit["metadata"].get("speech", {}).get("language") for unit in units],
                        peak_helper_private_bytes=max((result.get("sampled_peak_private_bytes") or 0 for result in raw_outputs), default=0),
                        all_transcripts_unverified=all(unit["status"] != "text" and unit["metadata"].get("review_required") for unit in units),
                        original_unchanged=client.get(f"/source-versions/{version}/file").content == raw)
                    report["samples"].append(sample)
                    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                    print(json.dumps({"mode": mode, "clip": index, "total": len(samples), "group": row["group"], "seconds": sample["pipeline_seconds"],
                                      "state": sample["state"], "word_errors": sample["word_edits"]["errors"], "reference_words": sample["word_edits"]["reference_units"]}), flush=True)
        finally:
            worker.connection.close()
            if settings_before is None:
                os.environ.pop("STUDYLENS_AUDIO_LANGUAGE", None)
            else:
                os.environ["STUDYLENS_AUDIO_LANGUAGE"] = settings_before
    report["summary"] = {mode: aggregate([s for s in report["samples"] if s["mode"] == mode]) for mode, _ in modes}
    report["status"] = "completed"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "completed", "report": str(report_path), "summary": report["summary"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--hint-count", type=int, default=20, choices=range(0, 41), help="Paired Hindi-language-hint check on first seeded Hinglish clips")
    parser.add_argument("--prepare-only", action="store_true", help="Isolated dataset preparation; does not run ASR")
    parser.add_argument("--resume", type=Path, help="Continue a saved incomplete run, retaining completed clip results")
    args = parser.parse_args()
    assert edits("a b c".split(), "a x c d".split())["errors"] == 2
    assert edits([], ["noise"])["insertions"] == 1
    if args.prepare_only:
        rows, paths = metadata()
        selected = extract_samples(choose(rows), paths)
        manifest = {"dataset": DATASET, "revision": REVISION, "seed": SEED, "allocation": SIZES,
            "population": dict(Counter(row["partition"] + ":" + row["language"] + ":" + row["noise_type"] for row in rows)), "samples": selected}
        (ROOT / "docs/evaluation/hinglish-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"prepared_clips": len(selected), "population": manifest["population"]}))
    else:
        if not args.resume:
            subprocess.run([sys.executable, str(Path(__file__).resolve()), "--prepare-only"], check=True)
        run(args.hint_count, args.resume)
