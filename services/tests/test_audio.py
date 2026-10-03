"""Audio contract gate: real FFmpeg, labeled ASR fixtures, disposable databases."""
import hashlib
import json
import os
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import test_extraction as helpers
from test_storage import BASE, SOURCES
from studylens_service import audio
from studylens_service.local_tools import find_tool
from studylens_service.worker import Worker
from studylens_service.job_errors import ExtractionFailure

FIXTURES = Path(__file__).resolve().parents[2] / "docs/evaluation/fixtures/phase-06"


def speech(*args):
    return {"segments": [{"start": 1.0, "end": 3.0, "text": "Authored ASR fixture: triangle has three sides"}],
            "language": "en", "language_probability": .9}


@unittest.skipUnless(find_tool("ffmpeg") and find_tool("ffprobe"), "Install FFmpeg for the audio contract gate")
class AudioTests(unittest.TestCase):
    def setUp(self):
        helpers.ExtractionTests.setUp(self)
        self.worker = Worker(self.root, threading.Event())
        self.model = self.root / "fixture-model"
        self.model.mkdir()
        for name in ("model.bin", "config.json", "tokenizer.json"):
            (self.model / name).write_text("Authored setup fixture, never used for real ASR", encoding="utf-8")
        self.cap = patch.object(audio, "capability", return_value={"ffmpeg": True, "ffprobe": True, "recognizer": True, "model_ready": True})
        self.path = patch.object(audio, "model_directory", return_value=self.model)
        self.cap.start()
        self.path.start()

    def tearDown(self):
        self.cap.stop()
        self.path.stop()
        self.worker.connection.close()
        helpers.ExtractionTests.tearDown(self)

    stop = helpers.ExtractionTests.stop
    content = helpers.ExtractionTests.content
    job = helpers.ExtractionTests.job
    upload = helpers.ExtractionTests.upload

    def seed(self, name="clean.wav"):
        original = self.upload(name, (FIXTURES / name).read_bytes())
        self.worker.execute(self.worker.claim())
        return original["version_id"]

    def test_real_decode_timestamp_and_review_contract_and_original(self):
        version = self.seed()
        with patch.object(audio, "transcribe", side_effect=speech) as asr:
            self.worker.execute(self.worker.claim())
        content = self.content(version)
        unit = content["units"][0]
        self.assertEqual(content["state"], "partial")
        self.assertEqual(unit["status"], "suspect")
        self.assertEqual(unit["locator"]["kind"], "time")
        self.assertEqual(unit["locator"]["start_seconds"], 0)
        self.assertGreater(unit["locator"]["end_seconds"], 8)
        self.assertEqual(unit["metadata"]["segments"][0]["start_seconds"], 1)
        self.assertTrue(unit["metadata"]["review_required"])
        self.assertEqual(unit["metadata"]["audio"]["sample_rate"], 16000)
        self.assertNotIn("path", unit["metadata"]["audio"])
        self.assertTrue(unit["metadata"]["audio"]["data_url"].startswith("data:audio/wav;base64,"))
        self.assertEqual(asr.call_count, 1)
        self.assertEqual(self.client.get("/source-versions/" + version + "/file").content, (FIXTURES / "clean.wav").read_bytes())
        self.assertEqual(self.client.get("/workspaces/other/source-versions/" + version + "/content").status_code, 404)

    def test_silence_never_calls_asr_or_invents_text(self):
        version = self.seed("silence.wav")
        with patch.object(audio, "transcribe", side_effect=AssertionError("Silent PCM must bypass ASR")):
            self.worker.execute(self.worker.claim())
        unit = self.content(version)["units"][0]
        self.assertEqual(unit["text"], "")
        self.assertEqual(unit["status"], "empty")
        self.assertTrue(unit["metadata"]["speech"]["levels"]["near_zero"])

    def test_supported_compressed_formats_decode_and_keep_original_bytes(self):
        for extension in ("mp3", "m4a", "ogg", "flac"):
            with self.subTest(extension=extension):
                name = "clean." + extension
                version = self.seed(name)
                with patch.object(audio, "transcribe", side_effect=speech):
                    self.worker.execute(self.worker.claim())
                content = self.content(version)
                self.assertEqual(content["state"], "partial", content["error"])
                self.assertEqual(content["units"][0]["locator"]["start_seconds"], 0)
                self.assertGreater(content["units"][0]["locator"]["end_seconds"], 8)
                self.assertEqual(self.client.get("/source-versions/" + version + "/file").content, (FIXTURES / name).read_bytes())

    def test_cancel_then_resume_retains_first_interval_and_absolute_times(self):
        version = self.seed("intervals.wav")
        calls = 0
        def cancel_second(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.client.post(BASE + "/jobs/" + self.job(version)["id"] + "/cancel")
            return speech()
        with patch.object(audio, "transcribe", side_effect=cancel_second):
            self.worker.execute(self.worker.claim())
        self.assertEqual(self.job(version)["state"], "cancelled")
        first = self.content(version)["units"][0]
        self.assertEqual(self.job(version)["checkpoint"]["completed_units"], 1)
        self.client.post(BASE + "/jobs/" + self.job(version)["id"] + "/retry")
        restarted = Worker(self.root, threading.Event())
        try:
            with patch.object(audio, "transcribe", side_effect=speech) as asr:
                restarted.execute(restarted.claim())
            self.assertEqual(asr.call_count, 1)  # Third interval is actual silence.
        finally:
            restarted.connection.close()
        units = self.content(version)["units"]
        self.assertEqual(len(units), 3)
        self.assertEqual([(u["locator"]["start_seconds"], u["locator"]["end_seconds"]) for u in units], [(0, 30), (30, 60), (60, 65)])
        self.assertEqual(units[0], first)
        self.assertEqual(units[1]["metadata"]["segments"][0]["start_seconds"], 31)
        self.assertEqual(len({u["id"] for u in units}), 3)

    def test_corrupt_audio_preserves_original_without_saved_transcript(self):
        version = self.seed("corrupt.wav")
        with patch.object(audio, "transcribe") as asr:
            self.worker.execute(self.worker.claim())
        self.assertEqual(self.job(version)["state"], "failed")
        self.assertEqual(self.job(version)["attempts"], 1)
        self.assertEqual(self.content(version)["units"], [])
        self.assertFalse(asr.called)
        self.assertEqual(self.client.get("/source-versions/" + version + "/file").status_code, 200)

    def test_bad_speech_timestamps_are_not_committed(self):
        version = self.seed()
        with patch.object(audio, "transcribe", return_value={"segments": [{"start": -1, "end": 3, "text": "Do not retain"}]}):
            self.worker.execute(self.worker.claim())
        self.assertEqual(self.job(version)["state"], "failed")
        self.assertEqual(self.content(version)["units"], [])

    def test_missing_setup_never_downloads_and_resume_after_setup(self):
        version = self.seed()
        with patch.object(audio, "capability", return_value={"ffmpeg": True, "ffprobe": True, "recognizer": True, "model_ready": False}):
            self.worker.execute(self.worker.claim())
        self.assertIn("audio:setup", self.job(version)["error"])
        self.assertEqual(self.content(version)["units"], [])
        self.client.post(BASE + "/jobs/" + self.job(version)["id"] + "/retry")
        with patch.object(audio, "transcribe", side_effect=speech):
            self.worker.execute(self.worker.claim())
        self.assertEqual(self.job(version)["state"], "partial")

    def test_reprocess_is_scoped_and_rejects_busy_jobs(self):
        version = self.seed()
        route = BASE + "/source-versions/" + version + "/process-audio"
        self.assertEqual(self.client.post(route).status_code, 409)
        self.assertEqual(self.client.post("/workspaces/other/source-versions/" + version + "/process-audio").status_code, 404)
        with patch.object(audio, "transcribe", side_effect=speech):
            self.worker.execute(self.worker.claim())
        first_id = self.content(version)["units"][0]["id"]
        self.assertEqual(self.client.post(route).status_code, 202)
        self.assertEqual(self.content(version)["units"], [])
        with patch.object(audio, "transcribe", side_effect=speech):
            self.worker.execute(self.worker.claim())
        self.assertEqual(self.content(version)["units"][0]["id"], first_id)
        self.assertEqual(self.client.post(BASE + "/source-versions/" + version + "/process-visuals").status_code, 409)

    def test_preview_corruption_is_flagged_and_private_path_is_not_exposed(self):
        version = self.seed()
        with patch.object(audio, "transcribe", side_effect=speech):
            self.worker.execute(self.worker.claim())
        metadata = json.loads(self.worker.connection.execute("SELECT metadata_json FROM content_units WHERE source_version_id=?", (version,)).fetchone()[0])
        (self.root / metadata["audio"]["path"]).write_bytes(b"broken")
        public = self.content(version)["units"][0]["metadata"]["audio"]
        self.assertIn("error", public)
        self.assertNotIn("data_url", public)
        self.assertNotIn("path", public)


class AudioValidationTests(unittest.TestCase):
    def test_duration_limits_and_no_stream(self):
        for duration in ("nan", "inf", "-1", "0", "14401"):
            with patch.object(audio, "run_tool", return_value=(json.dumps({"streams": [{"index": 0, "codec_type": "audio", "duration": duration}]}), 0)):
                with self.assertRaises(ExtractionFailure):
                    audio.probe(None, None, None, Path("fixture.wav"), None)
        with patch.object(audio, "run_tool", return_value=('{"streams": []}', 0)):
            with self.assertRaises(ExtractionFailure):
                audio.probe(None, None, None, Path("fixture.wav"), None)

    def test_out_of_order_overrun_and_nonfinite_segments_are_rejected(self):
        for left, right in ((3, 2), (0, 31), (float("nan"), 2)):
            with self.assertRaises(ExtractionFailure):
                audio.validate_segments({"segments": [{"start": left, "end": right, "text": "bad"}]}, 30, 30)
        self.assertEqual(audio.validate_segments({"segments": [{"start": 0, "end": 1, "text": "हिन्दी English"}]}, 30, 30)[0]["text"], "हिन्दी English")


if __name__ == "__main__":
    unittest.main()
