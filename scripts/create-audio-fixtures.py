"""Deterministic synthetic audio variants; not natural student speech."""
import array
import json
import math
import random
import subprocess
import wave
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "docs/evaluation/fixtures/phase-06"
with wave.open(str(root / "clean.wav"), "rb") as original:
    params = original.getparams()
    samples = array.array("h", original.readframes(original.getnframes()))
assert params.nchannels == 1 and params.sampwidth == 2
def save(name, values):
    with wave.open(str(root / name), "wb") as target:
        target.setparams(params)
        target.writeframes(values.tobytes())
random.seed(6)
save("noisy.wav", array.array("h", (max(-32768, min(32767, int(value * .65 + random.gauss(0, 1400)))) for value in samples)))
save("silence.wav", array.array("h", [0]) * (params.framerate * 5))
save("tone.wav", array.array("h", (int(12000 * math.sin(2 * math.pi * 440 * i / params.framerate)) for i in range(params.framerate * 5))))
long = array.array("h", [0]) * (params.framerate * 65)
long[:len(samples)] = samples
long[params.framerate * 32:params.framerate * 32 + len(samples)] = samples
save("intervals.wav", long)
(root / "corrupt.wav").write_bytes(b"Authored invalid WAV, deliberately not a recording")
for extension, codec in (("mp3", "libmp3lame"), ("m4a", "aac"), ("ogg", "libvorbis"), ("flac", "flac")):
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-i", str(root / "clean.wav"),
                    "-c:a", codec, str(root / ("clean." + extension))], check=True)
(root / "gold.json").write_text(json.dumps({"provenance": "Microsoft Windows SAPI English synthetic voice, self-authored StudyLens evaluation text; noisy/silent/tone/65s variants constructed locally with seed 6",
    "text": "A triangle has three sides. Water freezes at zero degrees Celsius. This is an authored audio test for Study Lens.",
    "needles": ["triangle has three sides", "water freezes at zero degrees celsius"],
    "intervals": [[0, 30], [30, 60], [60, 65]], "mixed_language": "Human Hindi/Hinglish quality review remains required; no synthetic English result establishes it."}, indent=2), encoding="utf-8")
