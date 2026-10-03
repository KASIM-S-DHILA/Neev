"""Bounded Groq speech transcription, durable pacing and validated chunk cache."""
import asyncio
import hashlib
import json
import math
import os
import time

import httpx

from .cloud_vision_wait import Deferred
from .job_errors import ExtractionFailure

MODEL = "whisper-large-v3-turbo"
VERSION = "groq-audio-1"
ENDPOINT = "https://api.groq.com/openai/v1/audio/transcriptions"
WAIT_STAGE = "Waiting for Groq audio quota"


def enabled():
    return bool(os.environ.get("GROQ_API_KEY", "").strip()) and os.environ.get(
        "STUDYLENS_AUTO_GROQ_AUDIO", "1").strip().lower() in ("1", "true", "yes", "on")


def ledger(worker):
    try:
        value = json.loads((worker.root / "groq-audio-budget.json").read_text("utf-8"))
        for name in ("hour", "day", "hour_seconds", "day_seconds", "day_requests", "next_request_at"):
            number = value[name]
            if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) or number < 0:
                raise ValueError
        return value
    except FileNotFoundError:
        return dict(hour=0, day=0, hour_seconds=0, day_seconds=0, day_requests=0, next_request_at=0)
    except (ValueError, KeyError, TypeError):
        raise ExtractionFailure("The Groq audio usage record is unreadable. Local transcription remains available.")


def save_ledger(worker, value):
    temporary = worker.root / "groq-audio-budget.tmp"
    temporary.write_text(json.dumps(value, allow_nan=False), encoding="utf-8")
    os.replace(temporary, worker.root / "groq-audio-budget.json")


def reserve(worker, duration):
    # One OS-locked heavy worker serializes the ledger across app windows.
    value, now = ledger(worker), time.time()
    hour, day = int(now // 3600), int(now // 86400)
    if value["hour"] != hour:
        value.update(hour=hour, hour_seconds=0)
    if value["day"] != day:
        value.update(day=day, day_seconds=0, day_requests=0)
    seconds = max(10, duration)  # Conservative accounting, including short requests.
    if value["hour_seconds"] + seconds > 7000:
        raise Deferred((hour + 1) * 3600 - now, WAIT_STAGE)
    if value["day_seconds"] + seconds > 28000 or value["day_requests"] >= 1900:
        raise Deferred((day + 1) * 86400 - now, WAIT_STAGE)
    if value["next_request_at"] > now:
        stage = "Pacing Groq audio requests" if value["next_request_at"] - now <= 3.3 else WAIT_STAGE
        raise Deferred(value["next_request_at"] - now, stage)
    value.update(hour_seconds=value["hour_seconds"] + seconds, day_seconds=value["day_seconds"] + seconds,
                 day_requests=value["day_requests"] + 1, next_request_at=now + 3.2)
    save_ledger(worker, value)


async def request_audio(worker, job, raw, language):
    if not enabled():
        raise ExtractionFailure("Automatic Groq audio processing is disabled or its key is missing.")
    if len(raw) > 1024**2:
        raise ExtractionFailure("The audio interval exceeds its upload budget.")
    async with httpx.AsyncClient(timeout=httpx.Timeout(20, connect=5), trust_env=False, follow_redirects=False) as client:
        async def transfer():
            fields = {"model": MODEL, "response_format": "verbose_json", "temperature": "0"}
            if language != "auto":
                fields["language"] = language
            async with client.stream("POST", ENDPOINT,
                headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"].strip(), "User-Agent": "Neev/audio-1"},
                files={"file": ("source-interval.wav", raw, "audio/wav")}, data=fields) as response:
                if response.status_code == 429:
                    try:
                        delay = float(response.headers.get("retry-after", "65"))
                        if not math.isfinite(delay):
                            raise ValueError
                    except ValueError:
                        delay = 65
                    wait = max(3.2, min(86400, delay))
                    value = ledger(worker)
                    value["next_request_at"] = time.time() + wait
                    save_ledger(worker, value)
                    raise Deferred(wait, WAIT_STAGE)
                if response.status_code != 200:
                    raise ExtractionFailure(f"Groq audio returned HTTP {response.status_code}. Check access and quota; local transcription remains available.")
                try:
                    remaining = int(response.headers.get("x-ratelimit-remaining-requests", "999999"))
                except ValueError:
                    remaining = 999999
                if remaining < 1:
                    value = ledger(worker)
                    value["next_request_at"] = max(value["next_request_at"], (int(time.time() // 86400) + 1) * 86400)
                    save_ledger(worker, value)
                received = bytearray()
                async for chunk in response.aiter_bytes():
                    worker.check(job)
                    received.extend(chunk)
                    if len(received) > 2 * 1024**2:
                        raise ExtractionFailure("The Groq audio response exceeded its size limit.")
                return json.loads(received)
        task = asyncio.create_task(transfer())
        try:
            deadline = time.monotonic() + 23
            while not task.done():
                worker.check(job)
                if time.monotonic() > deadline:
                    raise ExtractionFailure("The Groq audio request exceeded its time limit.")
                await asyncio.wait({task}, timeout=.1)
            return await task
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)


def transcribe(worker, job, guard, source, language, duration):
    from .audio import validate_segments
    raw = source.read_bytes()
    if len(raw) > 1024**2:
        raise ExtractionFailure("The audio interval exceeds its upload budget.")
    pcm_sha = hashlib.sha256(raw).hexdigest()
    cache_key = hashlib.sha256(f"{pcm_sha}:{MODEL}:{VERSION}:{language}".encode()).hexdigest()
    directory = worker.root / "derived/audio-transcripts"
    directory.mkdir(parents=True, exist_ok=True)
    cache = directory / (cache_key + ".json")
    cached = cache.is_file()
    try:
        if cached:
            if cache.stat().st_size > 2 * 1024**2:
                raise ValueError
            saved = json.loads(cache.read_text("utf-8"))
            data = saved["data"]
            digest = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()).hexdigest()
            if saved["input_sha256"] != pcm_sha or saved["data_sha256"] != digest:
                raise ValueError
        else:
            reserve(worker, duration)
            guard.touch()
            worker.update(job, stage="Transcribing audio with Groq")
            data = asyncio.run(request_audio(worker, job, raw, language))
        if not isinstance(data, dict) or not isinstance(data.get("text"), str) or len(data["text"]) > 12000:
            raise ValueError
        validate_segments(data, 0, duration)
        if " ".join(data["text"].split()) != " ".join(" ".join(s["text"] for s in data["segments"]).split()):
            raise ValueError
        if data.get("language") is not None and (not isinstance(data["language"], str) or len(data["language"]) > 64):
            raise ValueError
        worker.check(job)
        if not cached:
            digest = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()).hexdigest()
            temporary = cache.with_suffix(".tmp")
            temporary.write_text(json.dumps({"input_sha256": pcm_sha, "data_sha256": digest, "data": data}, allow_nan=False), encoding="utf-8")
            os.replace(temporary, cache)
        return data | {"provider": "groq", "model": MODEL, "input_sha256": pcm_sha, "cached": cached}
    except (ValueError, KeyError, TypeError):
        raise ExtractionFailure("The Groq audio response or saved cache failed text/timestamp checks. Local transcription remains available.")
    except httpx.HTTPError:
        raise ExtractionFailure("The Groq audio connection could not finish. Local transcription remains available.")
