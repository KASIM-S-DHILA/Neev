"""Cloud speech contract gate: real FFmpeg, authored HTTP fixtures, no real key."""
import asyncio
import json
import os
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
import test_audio as helpers
from test_storage import BASE
from studylens_service import audio, cloud_audio
from studylens_service.cloud_vision_wait import Deferred
from studylens_service.job_errors import ExtractionFailure
from studylens_service.local_tools import find_tool
from studylens_service.worker import Worker


def response(text="हिन्दी English fixture"):
    return {"text": text, "language": "hindi", "segments": [{"start": 1, "end": 3, "text": text,
        "avg_logprob": -.2, "no_speech_prob": .01, "compression_ratio": 1.2}]}


@unittest.skipUnless(find_tool("ffmpeg") and find_tool("ffprobe"), "Install FFmpeg for the audio contract gate")
class CloudAudioTests(unittest.TestCase):
    def setUp(self):
        helpers.AudioTests.setUp(self)
        audio.capability.return_value["cloud_enabled"] = True
        environment = patch.dict(os.environ, {"GROQ_API_KEY": "authored-test-key", "STUDYLENS_AUTO_GROQ_AUDIO": "1"})
        environment.start()
        self.addCleanup(environment.stop)
        vad = patch.object(audio, "detect_speech", return_value={"method": "authored-vad-fixture", "speech_detected": True,
            "regions": [{"start": 1, "end": 3}]})
        vad.start()
        self.addCleanup(vad.stop)
        self.asr = patch.object(audio, "transcribe", side_effect=helpers.speech)
        self.local = self.asr.start()
        self.addCleanup(self.asr.stop)
        self.requests = []

    tearDown = helpers.AudioTests.tearDown
    seed = helpers.AudioTests.seed
    upload = helpers.AudioTests.upload
    job = helpers.AudioTests.job
    content = helpers.AudioTests.content
    stop = helpers.AudioTests.stop

    def transport(self, handler=None):
        original = httpx.AsyncClient
        def receive(request):
            self.requests.append(request)
            return handler(request) if handler else httpx.Response(200, json=response())
        return patch.object(cloud_audio.httpx, "AsyncClient", side_effect=lambda **kw: original(
            transport=httpx.MockTransport(receive), **kw))

    def run_job(self):
        job = self.worker.claim()
        self.assertIsNotNone(job)
        self.worker.execute(job)

    def release(self, version):
        self.worker.connection.execute("UPDATE jobs SET available_at=0 WHERE id=?", (self.job(version)["id"],))
        value = cloud_audio.ledger(self.worker)
        value["next_request_at"] = 0
        cloud_audio.save_ledger(self.worker, value)

    def test_cloud_transcript_provenance_original_and_multipart_contract(self):
        version = self.seed()
        with patch.dict(os.environ, {"STUDYLENS_AUDIO_LANGUAGE": "hi"}), self.transport():
            self.run_job()
        unit = self.content(version)["units"][0]
        self.assertEqual(unit["text"], "हिन्दी English fixture")
        self.assertEqual(unit["status"], "suspect")
        self.assertEqual(unit["metadata"]["speech"]["provider"], "groq")
        self.assertEqual(unit["metadata"]["speech"]["model"], cloud_audio.MODEL)
        self.assertEqual(unit["metadata"]["speech"]["diagnostics"][0]["no_speech_prob"], .01)
        self.assertEqual(self.job(version)["checkpoint"]["completed_units"], 1)
        self.assertFalse(self.local.called)
        request = self.requests[0]
        self.assertEqual(str(request.url), cloud_audio.ENDPOINT)
        for field in (b'filename="source-interval.wav"', b'verbose_json', b'whisper-large-v3-turbo', b'name="language"\r\n\r\nhi'):
            self.assertIn(field, request.content)
        self.assertEqual(self.client.get("/source-versions/" + version + "/file").content, (helpers.FIXTURES / "clean.wav").read_bytes())
        self.assertEqual(self.client.get("/workspaces/other/source-versions/" + version + "/content").status_code, 404)

    def test_cloud_without_local_model_and_cache_reused_after_reprocess(self):
        audio.capability.return_value["model_ready"] = False
        version = self.seed()
        with self.transport():
            self.run_job()
            self.assertEqual(self.content(version)["state"], "partial")
            self.client.post(BASE + "/source-versions/" + version + "/process-audio").raise_for_status()
            self.run_job()
        self.assertEqual(len(self.requests), 1)
        self.assertTrue(self.content(version)["units"][0]["metadata"]["speech"]["cached"])
        self.assertIsNone(self.content(version)["units"][0]["metadata"]["speech"]["model_sha256"])

    def test_silence_and_vad_negative_do_not_upload_or_invent_speech(self):
        with self.transport():
            silent = self.seed("silence.wav")
            self.run_job()
            tone = self.seed("tone.wav")
            with patch.object(audio, "detect_speech", return_value={"method": "authored-vad-fixture", "speech_detected": False, "regions": []}):
                self.run_job()
        self.assertFalse(self.requests)
        self.assertFalse(self.local.called)
        for version in (silent, tone):
            self.assertEqual(self.content(version)["units"][0]["text"], "")

    def test_uncertain_vad_transcribes_full_interval(self):
        version = self.seed()
        with patch.object(audio, "detect_speech", side_effect=ExtractionFailure("unavailable")), self.transport():
            self.run_job()
        self.assertEqual(len(self.requests), 1)
        self.assertIn("full interval", self.content(version)["units"][0]["warning"])

    def test_bad_key_falls_back_once_for_remaining_intervals_without_response_body(self):
        version = self.seed("intervals.wav")
        with self.transport(lambda _: httpx.Response(401, text="SECRET provider body")):
            self.run_job()
        units = self.content(version)["units"]
        self.assertEqual(len(units), 3)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.local.call_count, 2)
        self.assertEqual(units[1]["metadata"]["speech"]["provider"], "local")
        self.assertNotIn("SECRET", json.dumps(units))
        self.assertEqual(self.job(version)["checkpoint"]["completed_units"], 3)

    def test_malformed_text_timestamps_diagnostics_and_large_responses_use_local(self):
        invalid = [response() | {"text": "different"}, response() | {"segments": [{"start": -1, "end": 3, "text": "bad"}]},
            response() | {"segments": [{"start": 1, "end": 3, "text": "bad", "avg_logprob": float("nan")}]},
            response() | {"segments": [{"start": 1, "end": 3, "text": "bad", "no_speech_prob": 2}]},
            {"text": "bad", "segments": []}]
        version = self.seed()
        for index, data in enumerate(invalid + [None]):
            with self.subTest(data=data):
                if index:
                    self.client.post(BASE + "/source-versions/" + version + "/process-audio").raise_for_status()
                self.release(version)
                raw = json.dumps(data).encode() if data is not None else b"x" * (2 * 1024**2 + 1)
                with self.transport(lambda _: httpx.Response(200, content=raw)):
                    self.run_job()
                self.assertEqual(self.content(version)["units"][0]["metadata"]["speech"]["provider"], "local")
                self.assertFalse(list((self.root / "derived/audio-transcripts").glob("*.json")))

    def test_quota_uses_ready_local_fallback(self):
        version = self.seed()
        with self.transport(lambda _: httpx.Response(429, headers={"retry-after": "65"})):
            self.run_job()
        self.assertEqual(self.content(version)["units"][0]["metadata"]["speech"]["provider"], "local")
        self.assertEqual(cloud_audio.ledger(self.worker)["day_requests"], 1)

    def test_network_error_uses_local_without_exposing_error_details(self):
        version = self.seed()
        def unavailable(request):
            raise httpx.ReadTimeout("SECRET network details", request=request)
        with self.transport(unavailable):
            self.run_job()
        unit = self.content(version)["units"][0]
        self.assertEqual(unit["metadata"]["speech"]["provider"], "local")
        self.assertNotIn("SECRET", json.dumps(unit))

    def test_cancel_after_cache_before_unit_save_reuses_response_on_resume(self):
        version = self.seed()
        save = audio.save_audio
        def cancel_before_commit(*args):
            result = save(*args)
            self.client.post(BASE + "/jobs/" + self.job(version)["id"] + "/cancel").raise_for_status()
            return result
        with self.transport():
            with patch.object(audio, "save_audio", side_effect=cancel_before_commit):
                self.run_job()
            self.assertEqual(self.job(version)["state"], "cancelled")
            self.assertEqual(self.content(version)["units"], [])
            self.client.post(BASE + "/jobs/" + self.job(version)["id"] + "/retry").raise_for_status()
            self.run_job()
        self.assertEqual(len(self.requests), 1)
        self.assertTrue(self.content(version)["units"][0]["metadata"]["speech"]["cached"])

    def test_opt_out_with_key_uses_local_without_http(self):
        version = self.seed()
        audio.capability.return_value["cloud_enabled"] = False
        with patch.dict(os.environ, {"STUDYLENS_AUTO_GROQ_AUDIO": "0"}), self.transport():
            self.assertFalse(cloud_audio.enabled())
            self.run_job()
        self.assertFalse(self.requests)
        self.assertEqual(self.content(version)["units"][0]["metadata"]["speech"]["provider"], "local")

    def test_quota_without_local_releases_worker_and_has_bounded_waits(self):
        audio.capability.return_value["model_ready"] = False
        version = self.seed()
        with self.transport(lambda _: httpx.Response(429, headers={"retry-after": "65"})):
            for _ in range(3):
                self.release(version)
                self.run_job()
                self.assertEqual(self.job(version)["state"], "queued")
                self.assertEqual(self.job(version)["failures"], 0)
                self.assertEqual(self.job(version)["stage"], cloud_audio.WAIT_STAGE)
            other = self.upload("other.txt", b"Local work can proceed while cloud audio waits")
            self.run_job()
            self.run_job()
            self.assertEqual(self.content(other["version_id"])["state"], "succeeded")
            self.release(version)
            self.run_job()
        self.assertEqual(self.job(version)["state"], "failed")
        self.assertEqual(self.content(version)["units"], [])

    def test_normal_pacing_does_not_trigger_local_fallback(self):
        version = self.seed("intervals.wav")
        with self.transport():
            self.run_job()
            self.assertEqual(self.job(version)["stage"], "Pacing Groq audio requests")
            self.assertEqual(self.job(version)["checkpoint"]["completed_units"], 1)
            self.release(version)
            self.run_job()
        self.assertEqual(self.job(version)["checkpoint"]["completed_units"], 3)
        self.assertFalse(self.local.called)
        self.assertEqual(self.content(version)["units"][1]["metadata"]["segments"][0]["start_seconds"], 31)

    def test_cancel_inflight_request_never_commits_cache_or_transcript(self):
        version = self.seed()
        async def cancelled(request):
            self.worker.connection.execute("UPDATE jobs SET cancel_requested=1 WHERE id=?", (self.job(version)["id"],))
            await asyncio.sleep(10)
            return httpx.Response(200, json=response())
        with self.transport(cancelled):
            self.run_job()
        self.assertEqual(self.job(version)["state"], "cancelled")
        self.assertEqual(self.content(version)["units"], [])
        self.assertFalse(list((self.root / "derived/audio-transcripts").glob("*.json")))

    def test_restart_preserves_first_interval_and_resumes_absolute_location(self):
        version = self.seed("intervals.wav")
        with self.transport():
            self.run_job()
            first = self.content(version)["units"][0]
            self.client.post(BASE + "/jobs/" + self.job(version)["id"] + "/cancel").raise_for_status()
            self.client.post(BASE + "/jobs/" + self.job(version)["id"] + "/retry").raise_for_status()
            self.release(version)
            old = self.worker
            self.worker = Worker(self.root, threading.Event())
            old.connection.close()
            self.run_job()
        units = self.content(version)["units"]
        self.assertEqual(len(units), 3)
        self.assertEqual(first, units[0])
        self.assertEqual(units[1]["metadata"]["segments"][0]["start_seconds"], 31)
        self.assertEqual(len(self.requests), 2)

    def test_corrupt_cache_fails_closed_to_local_without_resending(self):
        version = self.seed()
        with self.transport():
            self.run_job()
            cache = next((self.root / "derived/audio-transcripts").glob("*.json"))
            saved = json.loads(cache.read_text("utf-8"))
            saved["data"]["text"] = "tampered"
            cache.write_text(json.dumps(saved), encoding="utf-8")
            self.client.post(BASE + "/source-versions/" + version + "/process-audio").raise_for_status()
            self.run_job()
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.content(version)["units"][0]["metadata"]["speech"]["provider"], "local")

    def test_ledger_corruption_cannot_bypass_limits(self):
        version = self.seed()
        (self.root / "groq-audio-budget.json").write_text("broken", encoding="utf-8")
        with self.transport():
            self.run_job()
        self.assertFalse(self.requests)
        self.assertEqual(self.content(version)["units"][0]["metadata"]["speech"]["provider"], "local")

    def test_original_corruption_prevents_cloud_upload(self):
        version = self.seed()
        row = self.worker.connection.execute("SELECT relative_path FROM source_versions WHERE id=?", (version,)).fetchone()
        source = self.root / row[0]
        raw = bytearray(source.read_bytes())
        raw[-1] ^= 1
        source.write_bytes(raw)
        with self.transport():
            self.run_job()
        self.assertFalse(self.requests)
        self.assertEqual(self.content(version)["state"], "failed")

    def test_budget_caps_and_bucket_reset(self):
        now = time.time()
        value = dict(hour=int(now // 3600), day=int(now // 86400), hour_seconds=0, day_seconds=0, day_requests=0, next_request_at=0)
        for name, limit in (("hour_seconds", 7000), ("day_seconds", 28000), ("day_requests", 1900)):
            cloud_audio.save_ledger(self.worker, value | {name: limit})
            with self.assertRaises(Deferred):
                cloud_audio.reserve(self.worker, 9)
        cloud_audio.save_ledger(self.worker, value | {"hour": 0, "day": 0, "hour_seconds": 7000, "day_seconds": 28000, "day_requests": 1900})
        cloud_audio.reserve(self.worker, 1)
        self.assertEqual(cloud_audio.ledger(self.worker)["day_seconds"], 10)
        self.assertEqual(cloud_audio.ledger(self.worker)["day_requests"], 1)


if __name__ == "__main__":
    unittest.main()
