"""Isolated, offline CPU transcription of one bounded PCM chunk."""
import json
import sys
import threading
import time
from .resource_guard import private_bytes

finished = threading.Event()
peak = [private_bytes()]
def sample_memory():
    while not finished.wait(.05):
        peak[0] = max(peak[0], private_bytes())
threading.Thread(target=sample_memory, daemon=True).start()
started = time.monotonic()
cpu_started = time.process_time()
from faster_whisper import WhisperModel

model = WhisperModel(sys.argv[2], device="cpu", compute_type="int8", cpu_threads=2,
                     num_workers=1, local_files_only=True)
segments, info = model.transcribe(sys.argv[1], language=None if sys.argv[3] == "auto" else sys.argv[3],
    task="transcribe", beam_size=1, vad_filter=True, condition_on_previous_text=False,
    temperature=0, word_timestamps=False)
values = []
for segment in segments:
    if len(values) >= 100 or len(segment.text) > 4000:
        raise ValueError("Speech output exceeds chunk bounds")
    values.append({"start": segment.start, "end": segment.end, "text": segment.text,
                   "avg_logprob": segment.avg_logprob, "no_speech_prob": segment.no_speech_prob})
finished.set()
print(json.dumps({"segments": values, "language": info.language,
                  "language_probability": info.language_probability,
                  "private_bytes_after": private_bytes(), "sampled_peak_private_bytes": max(peak[0], private_bytes()),
                  "cpu_seconds": round(time.process_time() - cpu_started, 3),
                  "seconds": round(time.monotonic() - started, 3)}, ensure_ascii=True, allow_nan=False))
