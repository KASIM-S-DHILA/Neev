"""Video contracts: real FFmpeg, explicitly mocked speech, isolated storage."""
import array
import base64
import io
import json
import threading
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import test_audio as helpers
from test_storage import BASE
from studylens_service import audio, database, video
from studylens_service.local_tools import find_tool
from studylens_service.job_errors import ExtractionFailure
from studylens_service.worker import Worker
from studylens_service.jobs import JobStore

FIXTURES = Path(__file__).resolve().parents[2] / "docs/evaluation/fixtures/phase-07"


@unittest.skipUnless(find_tool("ffmpeg") and find_tool("ffprobe"), "FFmpeg required")
class VideoTests(unittest.TestCase):
    setUp = helpers.AudioTests.setUp
    tearDown = helpers.AudioTests.tearDown
    stop = helpers.AudioTests.stop
    upload = helpers.AudioTests.upload
    content = helpers.AudioTests.content
    job = helpers.AudioTests.job

    def seed(self, name="lecture.mp4", data=None):
        original = self.upload(name, data if data is not None else (FIXTURES / name).read_bytes())
        self.worker.execute(self.worker.claim())
        return original["version_id"]

    def extract(self, version):
        with patch.object(audio, "transcribe", side_effect=helpers.speech):
            self.worker.execute(self.worker.claim())
        return self.content(version)

    def test_original_video_duration_coverage_and_delayed_pcm(self):
        version = self.seed("delayed-audio.mp4")
        unit = self.extract(version)["units"][0]
        self.assertEqual(unit["locator"], {"kind": "time", "start_seconds": 0, "end_seconds": 20})
        self.assertEqual(unit["metadata"]["video"]["coverage"], "audio_only")
        self.assertAlmostEqual(unit["metadata"]["video"]["audio_start_seconds"], 4, delta=.1)
        self.assertTrue(unit["metadata"]["review_required"])
        self.assertEqual(unit["status"], "suspect")
        raw = base64.b64decode(unit["metadata"]["audio"]["data_url"].split(",")[1])
        with wave.open(io.BytesIO(raw)) as wav:
            self.assertEqual(wav.getnframes(), 20 * 16000)
            pcm = array.array("h", wav.readframes(wav.getnframes()))
        first = next(i for i, sample in enumerate(pcm) if abs(sample) > 500) / 16000
        self.assertAlmostEqual(first, 4.11, delta=.15)
        self.assertTrue(all(abs(sample) <= 1 for sample in pcm[15 * 16000:]))
        self.assertEqual(self.client.get("/source-versions/" + version + "/file").content, (FIXTURES / "delayed-audio.mp4").read_bytes())

    def test_no_audio_needs_no_speech_setup_and_never_calls_asr(self):
        version = self.seed("no-audio.mp4")
        with patch.object(audio, "capability", return_value={}), patch.object(audio, "transcribe", side_effect=AssertionError("No audio")):
            self.worker.execute(self.worker.claim())
        content = self.content(version)
        self.assertEqual(content["state"], "partial", content["error"])
        self.assertEqual(content["units"][0]["text"], "")
        self.assertFalse(content["units"][0]["metadata"]["video"]["audio_present"])
        self.assertEqual(content["units"][0]["locator"]["end_seconds"], 5)

    def test_cancel_restart_retains_checkpoint_and_original_time(self):
        version = self.seed("intervals.mp4")
        calls = 0
        def cancel_second(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.client.post(BASE + "/jobs/" + self.job(version)["id"] + "/cancel")
            return helpers.speech()
        with patch.object(audio, "transcribe", side_effect=cancel_second):
            self.worker.execute(self.worker.claim())
        self.assertEqual(self.job(version)["state"], "cancelled")
        first = self.content(version)["units"][0]
        self.client.post(BASE + "/jobs/" + self.job(version)["id"] + "/retry").raise_for_status()
        restarted = Worker(self.root, threading.Event())
        try:
            with patch.object(audio, "transcribe", side_effect=helpers.speech):
                restarted.execute(restarted.claim())
        finally:
            restarted.connection.close()
        units = self.content(version)["units"]
        self.assertEqual([(u["locator"]["start_seconds"], u["locator"]["end_seconds"]) for u in units], [(0, 30), (30, 60), (60, 65)])
        self.assertEqual(first, units[0])
        self.assertAlmostEqual(units[1]["metadata"]["segments"][0]["start_seconds"], units[1]["metadata"]["speech"]["window"]["start_seconds"] + 1, delta=.002)
        self.assertGreaterEqual(units[1]["metadata"]["segments"][0]["start_seconds"], 31)
        self.assertEqual(units[2]["text"], "")

    def test_video_tail_after_audio_ends_is_silent(self):
        version = self.seed("short-audio-long-video.mp4")
        with patch.object(audio, "transcribe", side_effect=helpers.speech) as asr:
            self.worker.execute(self.worker.claim())
        content = self.content(version)
        self.assertEqual(content["state"], "partial", content["error"])
        self.assertEqual(len(content["units"]), 3)
        self.assertEqual(asr.call_count, 1)
        self.assertTrue(all(not u["text"] for u in content["units"][1:]))

    def test_mkv_duration_and_native_stream_metadata(self):
        version = self.seed("lecture.mkv")
        content = self.extract(version)
        self.assertEqual(content["state"], "partial", content["error"])
        unit = content["units"][0]
        self.assertAlmostEqual(unit["locator"]["end_seconds"], 20, delta=.1)
        self.assertEqual(unit["metadata"]["video"]["codec"], "h264")
        self.assertEqual(unit["metadata"]["video"]["width"], 320)

    def test_corrupt_and_audio_disguised_as_video_declined_keep_original(self):
        for name, data in (("corrupt.mp4", (FIXTURES / "corrupt.mp4").read_bytes()),
                           ("disguised.mp4", (helpers.FIXTURES / "clean.wav").read_bytes())):
            with self.subTest(name=name):
                version = self.seed(name, data)
                with patch.object(audio, "transcribe") as asr:
                    self.worker.execute(self.worker.claim())
                self.assertEqual(self.job(version)["state"], "failed")
                self.assertEqual(self.content(version)["units"], [])
                self.assertFalse(asr.called)
                self.assertEqual(self.client.get("/source-versions/" + version + "/file").content, data)

    def test_modified_original_not_decoded(self):
        version = self.seed()
        row = self.worker.connection.execute("SELECT relative_path FROM source_versions WHERE id=?", (version,)).fetchone()
        target = self.root / row[0]
        original = target.read_bytes()
        target.write_bytes(bytes([original[0] ^ 1]) + original[1:])
        with patch.object(audio, "decode", side_effect=AssertionError("Damaged source")):
            self.worker.execute(self.worker.claim())
        self.assertEqual(self.job(version)["state"], "failed")
        self.assertEqual(self.content(version)["units"], [])

    def test_reprocess_scoped_busy_and_stable_ids(self):
        version = self.seed()
        route = BASE + "/source-versions/" + version + "/process-audio"
        self.assertEqual(self.client.post(route).status_code, 409)
        self.assertEqual(self.client.post(route.replace("semester-3", "other")).status_code, 404)
        first = self.extract(version)["units"][0]
        self.assertEqual(self.client.post(route).status_code, 202)
        self.assertEqual(self.extract(version)["units"][0]["id"], first["id"])

    def test_previously_saved_video_backfilled_on_restart(self):
        version = self.seed("no-audio.mp4")
        self.worker.connection.execute("DELETE FROM jobs WHERE kind='extract_source' AND source_version_id=?", (version,))
        with self.client._portal_factory() as portal:
            portal.call(JobStore(self.client.app.state.database).backfill)
            portal.call(JobStore(self.client.app.state.database).backfill)
        self.assertEqual(self.job(version)["state"], "queued")
        self.worker.execute(self.worker.claim())
        self.assertFalse(self.content(version)["units"][0]["metadata"]["video"]["audio_present"])

    def test_video_speech_window_maps_provider_time_and_keeps_internal_gaps(self):
        version = self.seed("delayed-audio.mp4")
        def inspect_window(worker, job, guard, source, *rest):
            with wave.open(str(source)) as wav:
                self.assertEqual(wav.getnframes(), round(9.4 * 16000))
            return {"segments": [{"start": .5, "end": 2, "text": "Authored offset fixture"}]}
        with patch.object(audio, "detect_speech", return_value={"regions": [{"start": 4, "end": 6}, {"start": 9, "end": 13}], "speech_detected": True, "method": "authored fixture"}), patch.object(audio, "transcribe", side_effect=inspect_window):
            self.worker.execute(self.worker.claim())
        unit = self.content(version)["units"][0]
        self.assertEqual(unit["metadata"]["speech"]["window"], {"start_seconds": 3.8, "duration_seconds": 9.4})
        self.assertEqual(unit["metadata"]["segments"][0]["start_seconds"], 4.3)

    def test_playback_authenticated_scoped_ranges_and_checksum_cache(self):
        version = self.seed()
        route = BASE + "/source-versions/" + version + "/playback"
        original = (FIXTURES / "lecture.mp4").read_bytes()
        with patch.object(database, "file_checksum", wraps=database.file_checksum) as checksum:
            self.assertEqual(self.client.head(route).headers["content-length"], str(len(original)))
            response = self.client.get(route, headers={"Range": "bytes=10-99"})
            self.assertEqual(response.status_code, 206)
            self.assertEqual(response.content, original[10:100])
            self.assertEqual(response.headers["content-range"], f"bytes 10-99/{len(original)}")
            self.assertEqual(self.client.get(route, headers={"Range": "bytes=-16"}).content, original[-16:])
            self.assertEqual(checksum.call_count, 1)
            self.assertEqual(self.client.get(route, headers={"Authorization": "Bearer wrong"}).status_code, 401)
            self.assertEqual(self.client.get(route.replace("semester-3", "other")).status_code, 404)
            for selected in ("bytes=0-1,3-4", "bytes=-", "bytes=999999999-", "bytes=9-2"):
                self.assertEqual(self.client.get(route, headers={"Range": selected}).status_code, 416)
            target = self.root / self.worker.connection.execute("SELECT relative_path FROM source_versions WHERE id=?", (version,)).fetchone()[0]
            target.write_bytes(bytes([original[0] ^ 1]) + original[1:])
            self.assertEqual(self.client.get(route).status_code, 404)
            self.assertEqual(checksum.call_count, 2)
        audio_version = self.seed("clean.wav", (helpers.FIXTURES / "clean.wav").read_bytes())
        self.assertEqual(self.client.get(BASE + "/source-versions/" + audio_version + "/playback").status_code, 404)


class VideoValidationTests(unittest.TestCase):
    def test_invalid_timeline_dimensions_and_attached_picture_rejected(self):
        good = {"streams": [{"index": 0, "codec_type": "video", "width": 320, "height": 180, "start_time": "0"},
                            {"index": 1, "codec_type": "audio", "start_time": "4", "channels": 1}],
                "format": {"start_time": "0", "duration": "20"}}
        for field, value in (("duration", "nan"), ("duration", "14401"), ("duration", "0"), ("start_time", "5")):
            broken = json.loads(json.dumps(good))
            broken["format"][field] = value
            with patch.object(video, "run_tool", return_value=(json.dumps(broken), 0)), self.assertRaises(ExtractionFailure):
                video.probe(None, None, None, Path("authored.mp4"), None)
        for modify in (lambda d: d["streams"][1].update(start_time="nan"),
                       lambda d: d["streams"][0].update(width=0),
                       lambda d: d["streams"][0].update(disposition={"attached_pic": 1}),
                       lambda d: d["streams"][0].update(tags={"rotate": "nan"})):
            broken = json.loads(json.dumps(good))
            modify(broken)
            with patch.object(video, "run_tool", return_value=(json.dumps(broken), 0)), self.assertRaises(ExtractionFailure):
                video.probe(None, None, None, Path("authored.mp4"), None)


if __name__ == "__main__":
    unittest.main()
