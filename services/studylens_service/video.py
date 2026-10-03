"""Video checkpoint 7A: bounded audio on the original container timeline."""
import json
import math

from . import audio
from .extraction import commit_unit
from .job_errors import ExtractionFailure
from .local_tools import find_tool, run_tool

VERSION = "video-audio-1"


def probe(worker, job, guard, source, folder):
    raw, _ = run_tool([find_tool("ffprobe"), "-v", "error", "-protocol_whitelist", "file",
        "-probesize", "5000000", "-analyzeduration", "5000000", "-show_entries",
        "stream=index,codec_type,codec_name,start_time,duration,width,height,channels,sample_rate,avg_frame_rate:stream_disposition=attached_pic:stream_tags=rotate:stream_side_data=rotation:format=start_time,duration",
        "-of", "json", str(source)], worker, job, guard, folder)
    try:
        data = json.loads(raw)
        videos = [s for s in data["streams"] if s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")]
        sounds = [s for s in data["streams"] if s.get("codec_type") == "audio"]
        if not videos:
            raise ExtractionFailure("This file has no playable video stream. Import it as audio or export a video copy; the original stays saved.")
        selected = videos[0]
        duration = float(data["format"]["duration"])
        origin = float(data["format"].get("start_time", selected.get("start_time", "nan")))
        if not math.isfinite(duration) or not 0 < duration <= audio.MAX_SECONDS or not math.isfinite(origin):
            raise ExtractionFailure("Video duration/timeline is unknown or exceeds four hours. Export a video copy or split it; the original stays saved.")
        # Nonzero container origins need a separately validated playback mapping.
        if abs(origin) > .1:
            raise ExtractionFailure("This video has a nonzero container start time. Export an MP4 copy with a timeline starting at zero; the original stays saved.")
        width, height = int(selected["width"]), int(selected["height"])
        if width <= 0 or height <= 0 or width * height > 40_000_000:
            raise ExtractionFailure("Video dimensions are invalid or exceed the processing limit. Export a smaller copy.")
        sound = sounds[0] if sounds else None
        sound_start = float(sound.get("start_time", "nan")) if sound else None
        if sound and (not math.isfinite(sound_start) or not -.1 <= sound_start <= duration):
            raise ExtractionFailure("The audio stream's starting timestamp is unusable. Export an MP4 copy; no transcript was saved.")
        rotation = next((item["rotation"] for item in selected.get("side_data_list", []) if "rotation" in item), selected.get("tags", {}).get("rotate", 0))
        rotation = float(rotation)
        if not math.isfinite(rotation):
            raise ValueError
        video = {"version": VERSION, "duration_seconds": duration, "container_start_seconds": origin,
            "stream_index": int(selected["index"]), "video_streams": len(videos), "codec": selected.get("codec_name"),
            "width": width, "height": height, "rotation": rotation, "frame_rate": selected.get("avg_frame_rate"),
            "audio_present": bool(sound), "audio_start_seconds": sound_start,
            "coverage": "audio_only", "timeline_method": "aresample-first-pts-0-v1"}
        return {"video": video, "duration_seconds": duration, "stream_index": int(sound["index"]) if sound else None,
            "audio_streams": len(sounds), "original_channels": int(sound.get("channels", 0)) if sound else 0,
            "original_sample_rate": sound.get("sample_rate") if sound else None}
    except (ValueError, KeyError, TypeError):
        raise ExtractionFailure("Video metadata is unusable. Import an exported video copy; the original stays saved.")


def extract_video(worker, job, guard, row, source, completed):
    import tempfile
    from pathlib import Path
    if not find_tool("ffmpeg") or not find_tool("ffprobe"):
        raise ExtractionFailure("Install FFmpeg with ffprobe, restart Neev and resume video processing.")
    with tempfile.TemporaryDirectory(prefix="video-", dir=worker.root / "staging") as directory:
        info = probe(worker, job, guard, source, Path(directory))
    if info["video"]["audio_present"]:
        audio.extract_audio(worker, job, guard, row, source, completed, media_info=info)
    elif not completed:
        commit_unit(worker, job, 1, 1, "", {"kind": "time", "start_seconds": 0, "end_seconds": info["duration_seconds"]},
            "empty", "This video has no audio stream. Visual extraction is pending; review the original video.", VERSION,
            {"video": info["video"], "text_origin": "video_probe", "review_required": True}, stage="Video audio checked")
