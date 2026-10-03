"""Small authored video fixtures; existing synthetic speech, no downloads."""
import json
import os
import subprocess
from pathlib import Path
from studylens_service.local_tools import find_tool

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / "docs/evaluation/fixtures/phase-07"
folder.mkdir(parents=True, exist_ok=True)
audio = ROOT / "docs/evaluation/fixtures/phase-06"

def create(name, duration, sound=None, offset=0, container="mp4", extra=()):
    command = [find_tool("ffmpeg"), "-v", "error", "-nostdin", "-y", "-f", "lavfi", "-i",
        f"testsrc2=size=320x180:rate=10:duration={duration}"]
    if sound:
        command += ["-itsoffset", str(offset), "-i", str(audio / sound)]
    command += ["-map", "0:v:0"]
    if sound:
        command += ["-map", "1:a:0", "-c:a", "aac", "-b:a", "48k"]
    command += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast", "-threads", "1"]
    if container == "mp4":
        command += ["-movflags", "+faststart"]
    command += list(extra) + [str(folder / name)]
    subprocess.run(command, check=True, **({"creationflags": 0x08000000} if os.name == "nt" else {}))

create("lecture.mp4", 20, "clean.wav")
create("delayed-audio.mp4", 20, "clean.wav", offset=4)
create("no-audio.mp4", 5)
create("intervals.mp4", 65, "intervals.wav")
create("short-audio-long-video.mp4", 65, "clean.wav")
create("lecture.mkv", 20, "clean.wav", container="mkv")
(folder / "corrupt.mp4").write_bytes(b"Authored invalid video, deliberately not media")
(folder / "gold.json").write_text(json.dumps({"provenance": "FFmpeg testsrc2 animation plus self-authored Windows SAPI speech from phase-06; H264/AAC, 320x180/10fps",
    "audio_offset_seconds": 4, "offset_tolerance_seconds": .15, "duration_seconds": 20,
    "intervals": [[0, 30], [30, 60], [60, 65]],
    "limits": "Known synthetic fixtures, not lecture quality or 8 GB hardware evidence"}, indent=2), encoding="utf-8")
print(str(folder))
