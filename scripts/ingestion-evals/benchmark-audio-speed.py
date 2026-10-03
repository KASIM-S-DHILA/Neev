"""Stage timing of the real local pipeline and an explicit authored-audio Groq pilot.

No production settings or models are changed. No downloads. --cloud sends only
three authored test intervals, three times each, to the Groq transcription API.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import threading
import time
import wave
from datetime import datetime, timezone
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/tests"))
from test_storage import AUTH, BASE, SESSION, SOURCES, TOKEN
from studylens_service import audio
from studylens_service.api import create_app
from studylens_service.worker import Worker
from studylens_service.local_tools import find_tool


def duration(path):
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cloud", action="store_true")
    args = parser.parse_args()
    key = os.environ.pop("GROQ_API_KEY", "").strip()
    os.environ["STUDYLENS_AUTO_GROQ_VISION"] = "0"
    tag = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    folder = ROOT / "tmp" / ("audio-speed-" + tag)
    inputs = folder / "inputs"
    inputs.mkdir(parents=True)
    fixtures = ROOT / "tests/fixtures/ingestion/phase-06"
    continuous = inputs / "continuous-60.wav"
    subprocess.run([find_tool("ffmpeg"), "-v", "error", "-nostdin", "-y", "-threads", "1",
        "-stream_loop", "-1", "-i", str(fixtures / "clean.wav"), "-t", "60", "-ac", "1",
        "-ar", "16000", "-c:a", "pcm_s16le", str(continuous)], check=True,
        creationflags=0x08000000 if os.name == "nt" else 0)
    silence = inputs / "silence-60.wav"
    with wave.open(str(silence), "wb") as wav:
        wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        wav.writeframes(b"\0\0" * (60 * 16000))
    samples = [("clean", fixtures / "clean.wav"), ("noisy", fixtures / "noisy.wav"),
               ("continuous-60", continuous), ("silence-60", silence)]
    manifest = json.loads((ROOT / "docs/archive/ingestion-pilots/hinglish-manifest.json").read_text("utf-8"))
    # Two longest already-downloaded Hinglish-labeled clips, for timing only.
    available = [s for s in manifest["samples"] if s["language"] == "hinglish" and (ROOT / s["sample_path"]).is_file()]
    for index, sample in enumerate(sorted(available, key=lambda s: s["duration_seconds"], reverse=True)[:2]):
        samples.append((f"hinglish-{index + 1}", ROOT / sample["sample_path"]))
    report = {"date_utc": tag, "data_directory": str(folder), "repeat_count": 3,
        "local_model": "faster-whisper Tiny CPU int8, 2 threads, fresh helper per 30-second chunk",
        "local": [], "cloud": [], "cloud_model": "whisper-large-v3-turbo",
        "limitations": ["Small latency pilot; three repeats, not p95.", "16 GB development laptop, not an 8 GB whole-app test.",
            "Continuous speech repeats authored synthetic English; not a real lecture.",
            "Selective cloud audio integration and routing are not implemented. Cloud fallback is explicitly forced for timing.",
            "Local timings include original verification, decoding, ASR, validation and SQLite writes; exclude UI/file picker/upload and worker queue wait.",
            "Cloud timings include new HTTP connection, upload, service and response; exclude quota wait and retry.",
            "No denoising or overlapping chunks were added for this pilot."]}
    destination = ROOT / "tmp/ingestion-evals/audio-speed.json"
    def save():
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    originals = {name: getattr(audio, name) for name in ("probe", "decode", "transcribe", "validate_segments", "save_audio", "commit_unit")}
    stages, recognition, cloud_inputs = [], [], {}
    current = [""]
    def wrapped(name):
        def call(*values, **kwargs):
            started = time.perf_counter()
            try:
                result = originals[name](*values, **kwargs)
                if name == "transcribe":
                    recognition.append({"seconds": result.get("seconds"), "peak_private_bytes": result.get("sampled_peak_private_bytes"),
                        "segments": result["segments"], "language": result.get("language")})
                    if current[0] in ("clean", "noisy", "continuous-60") and current[0] not in cloud_inputs:
                        target = inputs / (current[0] + "-cloud.wav")
                        shutil.copyfile(values[3], target)
                        cloud_inputs[current[0]] = target
                return result
            finally:
                stages.append({"stage": name, "seconds": time.perf_counter() - started})
        return call
    with TestClient(create_app(folder / "data", TOKEN), headers=AUTH) as client:
        client.put(BASE + "/session", json={"base_revision": 0, "session": SESSION}).raise_for_status()
        worker = Worker(folder / "data", threading.Event())
        try:
            with patch.multiple(audio, **{name: wrapped(name) for name in originals}):
                for label, source in samples:
                    for repeat in range(1, 4):
                        current[0] = label
                        stages.clear()
                        recognition.clear()
                        original = source.read_bytes()
                        uploaded = client.post(SOURCES, params={"filename": f"{label}-{repeat}.wav"}, content=original)
                        uploaded.raise_for_status()
                        version = uploaded.json()["version_id"]
                        started = time.perf_counter()
                        verify = worker.claim()
                        if not verify or verify["kind"] != "verify_original":
                            raise RuntimeError("Unexpected benchmark job order")
                        worker.execute(verify)
                        verification_seconds = time.perf_counter() - started
                        extract = worker.claim()
                        if not extract or extract["kind"] != "extract_source":
                            raise RuntimeError("Unexpected benchmark extraction order")
                        worker.execute(extract)
                        total_seconds = time.perf_counter() - started
                        content = client.get(BASE + f"/source-versions/{version}/content?limit=10").json()
                        sample = {"sample": label, "repeat": repeat, "audio_seconds": duration(source),
                            "total_seconds": total_seconds, "verification_seconds": verification_seconds,
                            "state": content["state"], "error": content["error"], "units": len(content["units"]),
                            "stage_times": list(stages), "recognition": list(recognition),
                            "text": " ".join(unit["text"] for unit in content["units"]),
                            "sha256": hashlib.sha256(original).hexdigest()}
                        report["local"].append(sample)
                        save()
                        print(json.dumps({key: sample[key] for key in ("sample", "repeat", "total_seconds", "state", "error")}), flush=True)
        finally:
            worker.connection.close()
    if args.cloud and key:
        last_start = 0.0
        blocked = False
        for label, source in cloud_inputs.items():
            for repeat in range(1, 4):
                if blocked:
                    break
                time.sleep(max(0, 3.2 - (time.perf_counter() - last_start)))
                last_start = time.perf_counter()
                record = {"sample": label, "repeat": repeat, "audio_seconds": duration(source),
                    "upload_bytes": source.stat().st_size}
                try:
                    with httpx.Client(timeout=httpx.Timeout(30, connect=5)) as client, source.open("rb") as stream:
                        response = client.post("https://api.groq.com/openai/v1/audio/transcriptions",
                            headers={"Authorization": "Bearer " + key},
                            files={"file": ("authored-speed-fixture.wav", stream, "audio/wav")},
                            data={"model": report["cloud_model"], "response_format": "verbose_json", "temperature": "0"})
                    record["http_status"] = response.status_code
                    record["rate_limit_headers"] = {name: value for name, value in response.headers.items() if name.startswith("x-ratelimit") or name == "retry-after"}
                    if response.status_code != 200:
                        blocked = True  # No retries or further calls after quota/auth/provider errors.
                    elif len(response.content) > 2 * 1024**2:
                        record["error"] = "Response exceeded benchmark bound"
                        blocked = True
                    else:
                        data = response.json()
                        record["text"] = data.get("text")
                        record["segments"] = [{name: segment.get(name) for name in ("start", "end", "text", "avg_logprob", "no_speech_prob", "compression_ratio")} for segment in data.get("segments", [])]
                except Exception as error:
                    record["error"] = type(error).__name__
                    blocked = True
                record["request_seconds"] = time.perf_counter() - last_start
                report["cloud"].append(record)
                save()
                print(json.dumps({name: record.get(name) for name in ("sample", "repeat", "request_seconds", "http_status", "error")}), flush=True)
    else:
        report["cloud_skipped"] = "No cloud flag or configured key"
    report["summary"] = {}
    for label, _ in samples:
        records = [r for r in report["local"] if r["sample"] == label]
        median = statistics.median(r["total_seconds"] for r in records)
        report["summary"][label] = {"audio_seconds": records[0]["audio_seconds"], "local_median_seconds": median,
            "local_min_seconds": min(r["total_seconds"] for r in records),
            "local_max_seconds": max(r["total_seconds"] for r in records),
            "seconds_per_audio_minute": median * 60 / records[0]["audio_seconds"],
            "successful_repeats": sum(r["state"] in ("succeeded", "partial") for r in records),
            "stage_medians": {stage: statistics.median(sum(t["seconds"] for t in r["stage_times"] if t["stage"] == stage) for r in records) for stage in originals}}
        cloud = [r for r in report["cloud"] if r["sample"] == label and r.get("http_status") == 200 and not r.get("error")]
        if cloud:
            report["summary"][label]["cloud_interval_seconds"] = cloud[0]["audio_seconds"]
            report["summary"][label]["cloud_request_median_seconds"] = statistics.median(r["request_seconds"] for r in cloud)
    report["completed_utc"] = datetime.now(timezone.utc).isoformat()
    report["status"] = "measured"
    save()
    print(json.dumps({"report": str(destination), "summary": report["summary"]}), flush=True)


if __name__ == "__main__":
    main()
