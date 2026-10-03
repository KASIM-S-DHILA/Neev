"""Measure already-bundled VAD without Whisper transcription or downloads."""
import json
from pathlib import Path
import statistics
import time
import wave

started = time.perf_counter()
import numpy as np
from faster_whisper.vad import get_speech_timestamps
from studylens_service.resource_guard import private_bytes
import_seconds = time.perf_counter() - started
ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "docs/evaluation/audio-speed.json"
report = json.loads(path.read_text("utf-8"))
folder = Path(report["data_directory"]) / "inputs"
samples = []
for name in ("clean-cloud.wav", "noisy-cloud.wav", "continuous-60.wav", "silence-60.wav"):
    with wave.open(str(folder / name), "rb") as wav:
        assert wav.getframerate() == 16000 and wav.getnchannels() == 1 and wav.getsampwidth() == 2
        pcm = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").astype(np.float32) / 32768
    calls = []
    for repeat in range(3):
        started = time.perf_counter()
        timestamps = get_speech_timestamps(pcm)
        calls.append(time.perf_counter() - started)
    samples.append({"name": name, "audio_seconds": len(pcm) / 16000, "seconds": calls,
                   "median_seconds": statistics.median(calls), "speech_regions": len(timestamps),
                   "speech_seconds": sum(t["end"] - t["start"] for t in timestamps) / 16000})
report["vad_only"] = {"dependency_import_seconds": import_seconds, "samples": samples,
    "process_private_bytes_after": private_bytes(), "method": "Bundled faster-whisper Silero ONNX VAD; model session cached after first call; audio already decoded, no Whisper model loaded"}
path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report["vad_only"]))
