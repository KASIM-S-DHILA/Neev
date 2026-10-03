"""Independent, bounded sampled-frame selection. No OCR or provider calls."""
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path
from fractions import Fraction
from uuid import NAMESPACE_URL, uuid5

from .job_errors import ExtractionFailure
from .local_tools import find_tool, run_tool
from .video import probe
from .visual_assets import save_preview

VERSION = "sampled-video-frames-1"
WINDOW_SECONDS = 30
MAX_FRAMES = 600
CONFIG = {"version": VERSION, "sample_seconds": 1, "scene_threshold": 18,
          "changed_pixel_fraction": .002, "pixel_delta": 24, "max_duplicate_seconds": 60,
          "scenedetect": "0.7.1", "max_frames": MAX_FRAMES}


def automatic_enabled():
    return os.environ.get("STUDYLENS_AUTO_VIDEO_FRAMES", "1") != "0"


def candidates(worker, job, guard, source, folder, start, length, stream):
    run_tool([find_tool("ffmpeg"), "-hide_banner", "-v", "info", "-nostdin", "-y", "-threads", "1",
        "-protocol_whitelist", "file", "-ss", f"{start:.6f}", "-i", str(source), "-t", f"{length:.6f}",
        "-map", f"0:{stream}", "-an", "-sn", "-dn", "-vf",
        f"scale=w='min(1400,iw)':h='min(1400,ih)':force_original_aspect_ratio=decrease,select='lt(t,{length:.6f})*gte(t,0)*(isnan(prev_selected_t)+gte(t-prev_selected_t,1))',showinfo",
        "-fps_mode", "vfr", "-frames:v", "32", "-q:v", "2", "-pix_fmt", "yuvj420p", "-color_range", "pc", "-threads", "1", str(folder / "frame-%03d.jpg")],
        worker, job, guard, folder)
    log = (folder / "helper-error.log").read_text("utf-8", errors="replace")
    files = sorted(folder.glob("frame-*.jpg"))
    if not files and not re.search(r"\bn:\s*\d+.*?\bpts:", log):
        return []  # The audio/container can continue after its video track ends.
    # showinfo's decimal pts_time loses precision on long recordings. Use its
    # integer PTS and rational filter time base instead of frame/FPS arithmetic.
    bases = set(re.findall(r"config in time_base:\s*(\d+)/(\d+)", log))
    if len(bases) != 1 or next(iter(bases))[1] == "0":
        raise ExtractionFailure("Video frame time base is unavailable or changes. Export a consistent MP4 copy.")
    numerator, denominator = map(int, next(iter(bases)))
    ticks = [int(value) for value in re.findall(r"\bn:\s*\d+.*?\bpts:\s*(-?\d+)\s+pts_time:", log)]
    times = [float(Fraction(value * numerator, denominator)) for value in ticks]
    if len(files) != len(times) or len(files) > 32:
        raise ExtractionFailure("Video frame timestamps could not be matched to previews. Export an MP4 copy.")
    result = []
    previous = -1
    for target, value, tick in zip(files, times, ticks):
        if not math.isfinite(value) or value < 0 or value >= length + .001 or value <= previous or target.stat().st_size > 2 * 1024**2:
            raise ExtractionFailure("Video frame timestamps or preview sizes were unusable. The original stays saved.")
        result.append({"file": target.name, "seconds": round(start + value, 6), "relative_pts": tick,
            "time_base": f"{numerator}/{denominator}", "window_start_seconds": start})
        previous = value
    return result


def analyze(worker, job, guard, folder, frames, previous, quota):
    request = {"frames": frames, "previous": previous, "quota": quota, "config": CONFIG}
    (folder / "selection.json").write_text(json.dumps(request), encoding="utf-8")
    raw, _ = run_tool([sys.executable, "-m", "studylens_service.video_frames_helper", str(folder)],
        worker, job, guard, folder, timeout=15)
    try:
        value = json.loads(raw)
        chosen = value["selected"]
        allowed = {item["file"]: item["seconds"] for item in frames}
        if not isinstance(chosen, list) or len(chosen) > quota or len({f["file"] for f in chosen}) != len(chosen):
            raise ValueError
        for item in chosen:
            if item["file"] not in allowed or item["seconds"] != allowed[item["file"]] or not isinstance(item["reasons"], list):
                raise ValueError
        if not isinstance(value["omitted"], int) or value["omitted"] < 0:
            raise ValueError
        return value
    except (ValueError, KeyError, TypeError):
        raise ExtractionFailure("Frame selection returned unusable locations. Saved frame windows remain available.")


def process(worker, job, guard):
    if not find_tool("ffmpeg") or not find_tool("ffprobe"):
        raise ExtractionFailure("Install FFmpeg with ffprobe, restart and resume video frame processing.")
    if not importlib.util.find_spec("scenedetect") or not importlib.util.find_spec("cv2"):
        raise ExtractionFailure("Scene detection setup is missing. Run npm.cmd run api:install, restart and resume frames.")
    row = worker.connection.execute("""SELECT v.*,s.kind FROM source_versions v JOIN sources s ON s.id=v.source_id
        WHERE v.id=?""", (job["source_version_id"],)).fetchone()
    if not row or row["kind"] != "video":
        raise ExtractionFailure("Frame selection supports video sources.")
    checked = worker.connection.execute("SELECT state FROM jobs WHERE kind='verify_original' AND source_version_id=?", (row["id"],)).fetchone()
    source = (worker.root / row["relative_path"]).resolve()
    if not checked or checked[0] != "succeeded" or not source.is_relative_to((worker.root / "originals").resolve()) or not source.is_file():
        raise ExtractionFailure("Check the original before processing frames. Restore or reimport a missing source.")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        while data := handle.read(1024**2):
            worker.check(job)
            guard.touch()
            digest.update(data)
    if source.stat().st_size != row["size_bytes"] or digest.hexdigest() != row["sha256"]:
        raise ExtractionFailure("The original changed after its integrity check. Restore it or import a new version.")
    checkpoint = json.loads(job["checkpoint_json"])
    if checkpoint and (checkpoint.get("config") != CONFIG or checkpoint.get("source_sha256") != row["sha256"]):
        raise ExtractionFailure("Frame settings or source changed. Use Select frames again to rebuild consistent locations.")
    saved = checkpoint.get("frames", [])
    done = checkpoint.get("completed_windows", 0)
    sampled = checkpoint.get("sampled", 0)
    omitted = checkpoint.get("omitted", 0)
    peak = checkpoint.get("helper_private_bytes_after_max", 0)
    empty_windows = checkpoint.get("empty_windows", 0)
    from PIL import Image
    with tempfile.TemporaryDirectory(prefix="video-frames-", dir=worker.root / "staging") as directory:
        base = Path(directory)
        info = probe(worker, job, guard, source, base)["video"]
        total = math.ceil(info["duration_seconds"] / WINDOW_SECONDS)
        for index in range(done, total):
            worker.check(job)
            guard.touch()
            start = index * WINDOW_SECONDS
            with tempfile.TemporaryDirectory(prefix="window-", dir=base) as temporary:
                folder = Path(temporary)
                previous = None
                if saved:
                    asset = saved[-1]["asset"]
                    target = (worker.root / asset["path"]).resolve()
                    if not target.is_relative_to((worker.root / "derived").resolve()) or not target.is_file() or target.stat().st_size > 512 * 1024 or hashlib.sha256(target.read_bytes()).hexdigest() != asset["sha256"]:
                        raise ExtractionFailure("The previous frame preview is missing or damaged. Use Select frames again.")
                    previous = {"path": str(target), "seconds": saved[-1]["seconds"]}
                worker.update(job, stage=f"Sampling video frames {index + 1} of {total}")
                batch = candidates(worker, job, guard, source, folder, start, min(WINDOW_SECONDS, info["duration_seconds"] - start), info["stream_index"])
                # Share the budget across remaining windows so motion early in a
                # long recording cannot consume every slot and hide its ending.
                quota = min(20, math.ceil((MAX_FRAMES - len(saved)) / (total - index)))
                chosen = analyze(worker, job, guard, folder, batch, previous, quota) if batch else {"selected": [], "omitted": 0}
                retained = list(saved)
                for item in chosen["selected"]:
                    worker.check(job)
                    guard.touch()
                    with Image.open(folder / item["file"]) as image:
                        asset = save_preview(worker.root, image, "Video frame · compare with the original")
                    retained.append({"id": str(uuid5(NAMESPACE_URL, f"studylens-frame:{row['id']}:{item['seconds']:.6f}")),
                        "seconds": item["seconds"], "reasons": item["reasons"], "changed_fraction": item["changed_fraction"],
                        "relative_pts": item["relative_pts"], "time_base": item["time_base"], "window_start_seconds": item["window_start_seconds"],
                        "asset": asset, "ocr_pending": True, "review_required": True})
                worker.check(job)
                state = {"config": CONFIG, "source_sha256": row["sha256"], "video": info,
                    "completed_windows": index + 1, "frames": retained, "sampled": sampled + len(batch),
                    "omitted": omitted + chosen["omitted"], "helper_private_bytes_after_max": max(peak, chosen.get("private_bytes_after", 0))}
                state["empty_windows"] = empty_windows + (not batch)
                # One SQLite checkpoint publishes only fully completed windows.
                worker.connection.execute("BEGIN IMMEDIATE")
                try:
                    worker.check(job)
                    worker.checkpoint(job, index + 1, total, "Frame window saved", state)
                    worker.connection.commit()
                except BaseException:
                    worker.connection.rollback()
                    raise
                saved, sampled, omitted, peak = retained, state["sampled"], state["omitted"], state["helper_private_bytes_after_max"]
                empty_windows = state["empty_windows"]
    return {"selected_frames": len(saved), "sampled_frames": sampled, "omitted_candidates": omitted,
        "scanned_seconds": info["duration_seconds"], "coverage": "sampled_frames", "ocr_pending": True,
        "source_sha256": row["sha256"], "helper_private_bytes_after_max": peak,
        "empty_windows": empty_windows,
        "limitations": "One-second sampling can miss brief content. Frames are previews; OCR/vision has not run."}
