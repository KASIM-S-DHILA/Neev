"""Bounded audio ingestion with automatic Groq speech and offline ASR fallback."""
import array
import base64
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import tempfile
import wave
from pathlib import Path

from .extraction import commit_unit
from .job_errors import ExtractionFailure
from .local_tools import find_tool, run_tool

CHUNK_SECONDS = 30
MAX_SECONDS = 4 * 3600
PCM_LIMIT = 1024 * 1024
ENGINE = "faster-whisper-1.2.1-tiny-cpu-int8-v1"


def model_directory():
    return Path(os.environ.get("STUDYLENS_AUDIO_MODEL_DIR", str(Path(__file__).resolve().parents[2] / "models/faster-whisper-tiny"))).resolve()


def capability():
    from .cloud_audio import enabled, MODEL
    return {"ffmpeg": bool(find_tool("ffmpeg")), "ffprobe": bool(find_tool("ffprobe")),
            "recognizer": importlib.util.find_spec("faster_whisper") is not None,
            "model_ready": all((model_directory() / name).is_file() for name in ("model.bin", "config.json", "tokenizer.json")),
            "model": MODEL if enabled() else "Multilingual Tiny · CPU int8", "cloud_enabled": enabled(),
            "chunk_seconds": CHUNK_SECONDS, "max_seconds": MAX_SECONDS}


def probe(worker, job, guard, source, folder):
    raw, _ = run_tool([find_tool("ffprobe"), "-v", "error", "-protocol_whitelist", "file",
        "-probesize", "5000000", "-analyzeduration", "5000000", "-show_entries",
        "stream=index,codec_type,duration,channels,sample_rate:format=duration", "-of", "json", str(source)],
        worker, job, guard, folder)
    try:
        info = json.loads(raw)
        streams = [item for item in info["streams"] if item.get("codec_type") == "audio"]
        if not streams:
            raise ExtractionFailure("This source contains no audio stream. The original stays saved.")
        selected = streams[0]
        duration = float(selected.get("duration", info.get("format", {}).get("duration", "nan")))
        if not math.isfinite(duration) or duration <= 0:
            raise ExtractionFailure("Audio duration could not be established. Export a WAV/MP3 copy.")
        if duration > MAX_SECONDS:
            raise ExtractionFailure("Audio processing supports recordings up to four hours. Split the recording; the original stays saved.")
        return {"duration_seconds": duration, "stream_index": int(selected["index"]), "audio_streams": len(streams),
                "original_channels": int(selected.get("channels", 0)), "original_sample_rate": selected.get("sample_rate")}
    except (ValueError, KeyError, TypeError) as error:
        raise ExtractionFailure("Could not read audio metadata. Import an exported audio copy.") from error


def decode(worker, job, guard, source, folder, start, length, stream, *, timeline=False):
    target = folder / "chunk.wav"
    command = [find_tool("ffmpeg"), "-v", "error", "-nostdin", "-y", "-threads", "1",
        "-protocol_whitelist", "file", "-ss", f"{start:.6f}", "-i", str(source), "-t", f"{length:.6f}",
        "-map", f"0:{stream}", "-vn", "-sn", "-dn", "-ac", "1", "-ar", "16000"]
    if timeline:
        # Preserve stream delay and pad gaps/tail on the selected video interval's clock.
        command += ["-af", "aresample=16000:async=1:first_pts=0,apad"]
    command += ["-c:a", "pcm_s16le", "-threads", "1", "-fs", str(PCM_LIMIT), str(target)]
    run_tool(command, worker, job, guard, folder)
    if not target.is_file() or target.stat().st_size > PCM_LIMIT:
        raise ExtractionFailure("Decoded audio exceeds its chunk budget.")
    if timeline:
        with wave.open(str(target), "rb") as decoded:
            empty = decoded.getnframes() == 0
        if empty:
            # A successful decode beyond the audio stream's end yields only a
            # WAV header. Keep that video interval silent on its original clock.
            with wave.open(str(target), "wb") as silent:
                silent.setnchannels(1)
                silent.setsampwidth(2)
                silent.setframerate(16000)
                silent.writeframes(b"\0" * (round(length * 16000) * 2))
    with wave.open(str(target), "rb") as wav:
        frames = wav.getnframes()
        if wav.getframerate() != 16000 or wav.getnchannels() != 1 or wav.getsampwidth() != 2 or not frames:
            raise ExtractionFailure("Could not decode this audio interval. Saved earlier intervals remain available.")
        duration = frames / 16000
        if duration > length + .1 or duration < length - .25:
            raise ExtractionFailure("Audio decoding returned an unexpected duration. Export an audio copy; earlier intervals are retained.")
        samples = array.array("h", wav.readframes(frames))
        if sys.byteorder != "little":
            samples.byteswap()
    level = {"rms": round(math.sqrt(sum(value * value for value in samples) / len(samples)) / 32768, 6),
             "clipped_fraction": round(sum(abs(value) >= 32760 for value in samples) / len(samples), 6),
             "near_zero": max(abs(value) for value in samples) <= 1}
    return target, duration, level


def transcribe(worker, job, guard, source, folder, model, language):
    raw, _ = run_tool([sys.executable, "-m", "studylens_service.audio_helper", str(source), str(model), language],
                      worker, job, guard, folder, timeout=25, memory_limit=1536 * 1024**2)
    try:
        data = json.loads(raw)
        if not isinstance(data["segments"], list) or len(data["segments"]) > 100:
            raise ValueError("Too many segments")
        return data
    except (ValueError, KeyError, TypeError) as error:
        raise ExtractionFailure("The speech recognizer returned unusable output. No transcript was saved for this interval.") from error


def validate_segments(data, start, duration):
    if not isinstance(data, dict) or not isinstance(data.get("segments"), list) or len(data["segments"]) > 100:
        raise ExtractionFailure("Speech segments exceeded their interval limit.")
    result, previous_end = [], 0.0
    for segment in data["segments"]:
        if not isinstance(segment, dict) or any(isinstance(segment.get(key), bool) or not isinstance(segment.get(key), (int, float)) for key in ("start", "end")):
            raise ExtractionFailure("Speech timestamps were invalid. No transcript was saved for this interval.")
        left, right = float(segment["start"]), float(segment["end"])
        text = segment.get("text")
        if not all(math.isfinite(value) for value in (left, right)) or left < previous_end - .05 or left < 0 or right <= left or right > duration + .1:
            raise ExtractionFailure("Speech timestamps were invalid. No transcript was saved for this interval.")
        if not isinstance(text, str) or len(text) > 4000 or any(ord(c) < 32 and c not in "\n\r\t" for c in text):
            raise ExtractionFailure("Speech text exceeded its limits.")
        for name in ("avg_logprob", "no_speech_prob", "compression_ratio"):
            score = segment.get(name)
            if score is not None and (isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score)):
                raise ExtractionFailure("Speech diagnostics were invalid.")
            if score is not None and ((name == "no_speech_prob" and not 0 <= score <= 1) or (name == "compression_ratio" and score < 0)):
                raise ExtractionFailure("Speech diagnostics were invalid.")
        previous_end = right
        if text.strip():
            result.append({"start_seconds": round(start + left, 3), "end_seconds": round(start + min(right, duration), 3),
                           "text": text.strip()})
    if sum(len(item["text"]) for item in result) > 12000:
        raise ExtractionFailure("Speech text exceeded its interval limit.")
    return result


def detect_speech(worker, job, guard, source, folder, duration):
    raw, _ = run_tool([sys.executable, "-m", "studylens_service.audio_vad_helper", str(source)],
        worker, job, guard, folder, timeout=10, memory_limit=512 * 1024**2)
    try:
        regions = json.loads(raw)["regions"]
        if not isinstance(regions, list) or len(regions) > 100:
            raise ValueError
        previous = 0
        for region in regions:
            left, right = region["start"], region["end"]
            if not all(isinstance(t, (int, float)) and not isinstance(t, bool) and math.isfinite(t) for t in (left, right)) or left < previous or right <= left or right > duration + .001:
                raise ValueError
            previous = right
        return {"regions": regions, "method": "silero-vad", "speech_detected": bool(regions)}
    except (ValueError, KeyError, TypeError):
        raise ExtractionFailure("Speech detection returned unusable intervals.")


def save_audio(root, source, duration):
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    relative = f"derived/audio/{digest[:2]}/{digest}.wav"
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.is_file() or target.stat().st_size != len(raw) or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        temporary = target.with_suffix(".part")
        temporary.write_bytes(raw)
        os.replace(temporary, target)
    return {"path": relative, "sha256": digest, "duration_seconds": round(duration, 3), "sample_rate": 16000, "channels": 1}


def video_speech_window(source, folder, duration, vad):
    """Trim only outer detected silence; preserve every gap between speech regions."""
    regions = vad.get("regions", [])
    if not regions:
        return source, 0, duration
    left = max(0, int((regions[0]["start"] - .2) * 16000))
    right = min(round(duration * 16000), math.ceil((regions[-1]["end"] + .2) * 16000))
    target = folder / "speech-window.wav"
    with wave.open(str(source), "rb") as original:
        original.setpos(left)
        frames = original.readframes(right - left)
        params = original.getparams()
    with wave.open(str(target), "wb") as window:
        window.setparams(params)
        window.writeframes(frames)
    return target, left / 16000, (right - left) / 16000


def public_audio(root, audio):
    value = {key: audio[key] for key in ("sha256", "duration_seconds", "sample_rate", "channels") if key in audio}
    target = (root / audio.get("path", "")).resolve()
    try:
        if not target.is_relative_to((root / "derived/audio").resolve()) or target.stat().st_size > PCM_LIMIT:
            raise ValueError("Invalid audio preview")
        with target.open("rb") as stream:
            raw = stream.read(PCM_LIMIT + 1)
        if hashlib.sha256(raw).hexdigest() != audio.get("sha256"):
            raise ValueError("Damaged audio preview")
        value["data_url"] = "data:audio/wav;base64," + base64.b64encode(raw).decode("ascii")
    except (OSError, ValueError):
        value["error"] = "Audio preview is missing or damaged. Reprocess audio; the original stays saved."
    return value


def extract_audio(worker, job, guard, row, source, completed, *, media_info=None):
    from . import cloud_audio
    from .cloud_vision_wait import Deferred
    status = capability()
    if not status["ffmpeg"] or not status["ffprobe"]:
        raise ExtractionFailure("Install FFmpeg with ffprobe, restart Neev, then Resume audio processing.")
    local_ready = status["recognizer"] and status["model_ready"]
    cloud_ready = status.get("cloud_enabled", False)
    if not local_ready and not cloud_ready:
        raise ExtractionFailure("Speech setup is missing. Configure GROQ_API_KEY or run npm.cmd run audio:setup for local transcription, then restart and Resume.")
    language = os.environ.get("STUDYLENS_AUDIO_LANGUAGE", "auto")
    if not re.fullmatch(r"auto|[a-z]{2,3}", language):
        raise ExtractionFailure("Choose auto or a valid speech language code in STUDYLENS_AUDIO_LANGUAGE.")
    model = model_directory()
    fingerprint = hashlib.sha256()
    if local_ready:
        for name in sorted(path.name for path in model.iterdir() if path.is_file()):
            fingerprint.update(name.encode())
            with (model / name).open("rb") as stream:
                while chunk := stream.read(1024**2):
                    worker.check(job)
                    guard.touch()
                    fingerprint.update(chunk)
    config = {"model_sha256": fingerprint.hexdigest() if local_ready else None, "language_hint": language,
        "chunk_seconds": CHUNK_SECONDS, "pipeline_version": 2, "cloud_model": cloud_audio.MODEL if cloud_ready else None}
    if media_info:
        config["video_timeline"] = media_info["video"]["timeline_method"]
        config["video_speech_window"] = "outer-vad-silence-margin-0.2-v1"
    checkpoint = json.loads(job["checkpoint_json"])
    if completed and checkpoint.get("audio_config") != config:
        raise ExtractionFailure("Speech settings or model changed since processing began. Use Reprocess audio to rebuild a consistent transcript.")
    checkpoint["completed_units"] = completed
    with tempfile.TemporaryDirectory(prefix="audio-", dir=worker.root / "staging") as directory:
        folder = Path(directory)
        try:
            info = media_info if media_info is not None else probe(worker, job, guard, source, folder)
            total = math.ceil(info["duration_seconds"] / CHUNK_SECONDS)
            worker.checkpoint(job, completed, total, "Preparing audio", checkpoint)
            for index in range(completed, total):
                worker.check(job)
                start = index * CHUNK_SECONDS
                length = min(CHUNK_SECONDS, info["duration_seconds"] - start)
                worker.update(job, stage=f"Decoding audio {index + 1} of {total}")
                wav, duration, level = decode(worker, job, guard, source, folder, start, length, info["stream_index"], **({"timeline": True} if media_info else {}))
                worker.update(job, stage=f"Checking speech {index + 1} of {total}")
                vad = {"method": "exact-zero" if level["near_zero"] else "local-asr-vad", "speech_detected": not level["near_zero"]}
                if (cloud_ready or media_info) and not level["near_zero"]:
                    try:
                        vad = detect_speech(worker, job, guard, wav, folder, duration)
                    except ExtractionFailure:
                        # Uncertain detection never discards the original interval.
                        vad = {"method": "unavailable", "speech_detected": True, "warning": "Speech detection could not finish; the full interval was transcribed."}
                data = {"segments": [], "language": None, "language_probability": None, "provider": "none", "model": "speech-detection"}
                speech_wav, speech_offset, speech_duration = video_speech_window(wav, folder, duration, vad) if media_info else (wav, 0, duration)
                fallback = checkpoint.get("cloud_audio_unavailable") if cloud_ready else None
                if vad["speech_detected"]:
                    if cloud_ready and not fallback:
                        try:
                            data = cloud_audio.transcribe(worker, job, guard, speech_wav, language, speech_duration)
                            checkpoint["audio_quota_waits"] = 0
                        except Deferred as wait:
                            if wait.stage == "Pacing Groq audio requests":
                                worker.checkpoint(job, index, total, wait.stage, checkpoint | {"audio_config": config})
                                raise
                            if not local_ready:
                                checkpoint["audio_quota_waits"] = checkpoint.get("audio_quota_waits", 0) + 1
                                worker.checkpoint(job, index, total, wait.stage, checkpoint | {"audio_config": config})
                                if checkpoint["audio_quota_waits"] > 3:
                                    raise ExtractionFailure("Groq audio quota remained unavailable after three waits. Configure local speech or resume when quota returns.")
                                raise
                            fallback = "Groq audio quota is unavailable; local transcription was used."
                        except ExtractionFailure as error:
                            if not local_ready:
                                raise
                            fallback = str(error)
                            checkpoint["cloud_audio_unavailable"] = fallback
                    if not cloud_ready or fallback:
                        worker.update(job, stage=f"Transcribing audio locally {index + 1} of {total}")
                        guard.touch()
                        data = transcribe(worker, job, guard, speech_wav, folder, model, language) | {"provider": "local", "model": "faster-whisper-tiny"}
                segments = validate_segments(data, start + speech_offset, speech_duration)
                text = "\n".join(item["text"] for item in segments)
                warning = "Automatic transcript: compare with the audio. Chunk boundaries may split words; speakers are not identified." if text else "No speech recognized in this interval. This may be silence, music or missed speech; listen to the original."
                if level["clipped_fraction"] >= .001:
                    warning += " Clipping detected; some speech may be distorted."
                if info["audio_streams"] > 1:
                    warning += " Only the first audio stream was processed."
                if media_info:
                    # This unit is the audio stream only. Frame selection and frame
                    # text are separate jobs, so do not claim they are missing here.
                    warning += " This unit covers the audio stream only; selected frames and their text are produced by separate jobs."
                if fallback:
                    warning += " " + fallback
                if vad.get("warning"):
                    warning += " " + vad["warning"]
                diagnostics = [{key: segment[key] for key in ("start", "end", "avg_logprob", "no_speech_prob", "compression_ratio") if key in segment} for segment in data["segments"]]
                metadata = {"text_origin": "automatic_speech_transcription", "review_required": True,
                    "audio": save_audio(worker.root, wav, duration), "segments": segments,
                    "speech": config | {key: value for key, value in info.items() if key != "video"} | {"language": data.get("language"), "language_probability": data.get("language_probability"),
                                              "provider": data["provider"], "model": data["model"], "cached": data.get("cached", False),
                                              "input_sha256": data.get("input_sha256"), "fallback_reason": fallback,
                                              "vad": vad, "diagnostics": diagnostics,
                                              "levels": level, "helper_private_bytes_after": data.get("private_bytes_after"),
                                              "helper_sampled_peak_private_bytes": data.get("sampled_peak_private_bytes"),
                                              "helper_cpu_seconds": data.get("cpu_seconds"), "helper_seconds": data.get("seconds")}}
                if media_info:
                    metadata["video"] = media_info["video"]
                    metadata["speech"]["window"] = {"start_seconds": round(start + speech_offset, 3), "duration_seconds": round(speech_duration, 3)}
                commit_unit(worker, job, index + 1, total, text,
                    {"kind": "time", "start_seconds": round(start, 3), "end_seconds": round(start + duration, 3)},
                    "suspect" if text else "empty", warning, cloud_audio.VERSION if data["provider"] == "groq" else ENGINE, metadata,
                    checkpoint_extra={key: value for key, value in checkpoint.items() if key not in ("completed_units", "engine")} | {"audio_config": config}, stage="Audio interval saved")
                checkpoint["completed_units"] = index + 1
        except ExtractionFailure as error:
            if str(error).startswith("The native document helper exceeded"):
                raise ExtractionFailure("A local audio helper could not finish within its memory/time limits. Check FFmpeg/speech setup or export a shorter audio copy; saved intervals remain.") from error
            if str(error).startswith("The native document helper could not process"):
                raise ExtractionFailure("The local audio helper could not decode or transcribe this source. It may be damaged or unsupported; check FFmpeg/speech setup or import an exported audio copy. Saved intervals remain.") from error
            raise
