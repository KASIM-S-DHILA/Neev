"""Authored slide, whiteboard, static, return-slide, VFR and rotated clips."""
import json
import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from studylens_service.local_tools import find_tool

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / "docs/evaluation/fixtures/phase-07b"
folder.mkdir(parents=True, exist_ok=True)
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 32)

def page(name, title, color="white", step=0):
    image = Image.new("RGB", (640, 360), color)
    draw = ImageDraw.Draw(image)
    draw.text((40, 28), title, font=font, fill="#162039")
    for index in range(step):
        draw.text((40, 90 + index * 50), ("P(A | B) = P(A and B) / P(B)", "P(B) = 0.5", "P(A and B) = 0.2", "P(A | B) = 0.4")[index], font=font, fill="#162039")
    image.save(folder / (name + ".png"))

page("slide-a", "Conditional probability", "#e8effd", 1)
page("slide-b", "Independent events", "#ffe6cf", 2)
page("slide-c", "Example and solution", "#e4f2df", 4)
for i in range(5):
    page("board-" + str(i), "Whiteboard: worked example", step=i)

def create(name, sequence, durations, extra=()):
    lines = []
    for frame, duration in zip(sequence, durations):
        lines += [f"file '{frame}.png'", f"duration {duration}"]
    lines += [f"file '{sequence[-1]}.png'"]
    manifest = folder / (name + ".txt")
    manifest.write_text("\n".join(lines), encoding="utf-8")
    command = [find_tool("ffmpeg"), "-v", "error", "-nostdin", "-y", "-f", "concat", "-safe", "1", "-i", str(manifest),
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-threads", "1", "-preset", "ultrafast", "-t", str(sum(durations) + (.1 if extra else 0))]
    if not extra:
        command += ["-vf", "fps=5"]
    command += list(extra) + ["-movflags", "+faststart", str(folder / (name + ".mp4"))]
    subprocess.run(command, check=True, **({"creationflags":0x08000000} if os.name == "nt" else {}))

create("slides", ["slide-a", "slide-b", "slide-c"], [4, 4, 4])
create("return-slides", ["slide-a", "slide-b", "slide-a"], [4, 4, 4])
create("whiteboard", ["board-" + str(i) for i in range(5)], [3] * 5)
create("static", ["slide-a"], [65])
create("vfr", ["slide-a", "slide-b", "slide-c"], [2.4, 3.2, 4.4], ["-fps_mode", "vfr"])
create("rotate-base", ["slide-a", "slide-b"], [4, 4])
subprocess.run([find_tool("ffmpeg"), "-v", "error", "-nostdin", "-y", "-i", str(folder / "slides.mp4"),
    "-i", str(ROOT / "docs/evaluation/fixtures/phase-06/intervals.wav"), "-map", "0:v:0", "-map", "1:a:0",
    "-c:v", "copy", "-c:a", "aac", "-threads", "1", str(folder / "video-ends-first.mp4")], check=True,
    **({"creationflags":0x08000000} if os.name == "nt" else {}))
subprocess.run([find_tool("ffmpeg"), "-v", "error", "-nostdin", "-y", "-display_rotation:v:0", "90", "-i", str(folder / "rotate-base.mp4"),
    "-c", "copy", str(folder / "rotated.mp4")], check=True,
    **({"creationflags":0x08000000} if os.name == "nt" else {}))
(folder / "gold.json").write_text(json.dumps({"provenance":"Locally drawn, authored teaching slides and worked equation; FFmpeg H264. No audio or model-generated content.",
    "slides_change_seconds":[4,8], "whiteboard_change_seconds":[3,6,9,12], "return_change_seconds":[4,8],
    "vfr_change_seconds":[2.4,5.6], "sample_delay_tolerance_seconds":1.2, "static_references_seconds":[0,60],
    "limitations":"Known synthetic scenes; not held-out frame-selection quality. Brief changes between samples can be missed."},indent=2),encoding="utf-8")
print(str(folder))
