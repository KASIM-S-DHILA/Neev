"""Speech detection in a bounded child; uses the already-bundled Silero model."""
import json
import sys
import wave

import numpy as np
from faster_whisper.vad import get_speech_timestamps

with wave.open(sys.argv[1], "rb") as wav:
    if wav.getframerate() != 16000 or wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getnframes() > 480000:
        raise ValueError("Invalid VAD interval")
    samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").astype(np.float32) / 32768
regions = get_speech_timestamps(samples)
print(json.dumps({"regions": [{"start": r["start"] / 16000, "end": r["end"] / 16000} for r in regions]}, allow_nan=False))
