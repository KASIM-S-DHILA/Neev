"""Independent frames gate: actual FFmpeg/PySceneDetect, no ASR/cloud calls."""
import hashlib
import importlib.util
import json
import os
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import test_extraction as helpers
from test_storage import BASE, SOURCES
from studylens_service import video_frames as frames
from studylens_service.local_tools import find_tool
from studylens_service.worker import Worker

FIXTURES = Path(__file__).resolve().parents[2] / "tests/fixtures/ingestion/phase-07b"
TOOLS = find_tool("ffmpeg") and find_tool("ffprobe") and importlib.util.find_spec("scenedetect") and importlib.util.find_spec("cv2")


@unittest.skipUnless(TOOLS, "Install pinned frame dependencies and FFmpeg")
class FrameTests(unittest.TestCase):
    def setUp(self):
        helpers.ExtractionTests.setUp(self)
        self.worker = Worker(self.root, threading.Event())

    def tearDown(self):
        self.worker.connection.close()
        helpers.ExtractionTests.tearDown(self)

    upload = helpers.ExtractionTests.upload
    job = helpers.ExtractionTests.job
    stop = helpers.ExtractionTests.stop
    content = helpers.ExtractionTests.content

    def seed(self, name="slides.mp4", data=None):
        value = self.upload(name, data if data is not None else (FIXTURES / name).read_bytes())
        version = value["version_id"]
        self.worker.execute(self.worker.claim())
        self.client.post(BASE + "/jobs/" + self.job(version)["id"] + "/cancel").raise_for_status()
        route = BASE + "/source-versions/" + version + "/process-video-frames"
        if not any(j["kind"] == "video_frames" and j["source_version_id"] == version for j in self.client.get(BASE + "/jobs").json()):
            self.client.post(route).raise_for_status()
        return version

    def page(self, version, offset=0):
        response = self.client.get(BASE + "/source-versions/" + version + "/video-frames", params={"offset": offset})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def run_frames(self, version):
        self.worker.execute(self.worker.claim())
        job = self.job(version, "video_frames")
        self.assertIn(job["state"], ("succeeded", "partial"), job["error"])
        return self.page(version)

    def test_slides_locations_previews_independent_of_cancelled_audio(self):
        version = self.seed()
        page = self.run_frames(version)
        self.assertEqual(page["total"], 3)
        self.assertEqual([f["seconds"] for f in page["frames"]], [0, 4, 8])
        self.assertTrue(all(f["asset"].get("data_url") and f["ocr_pending"] and f["review_required"] for f in page["frames"]))
        self.assertNotIn("path", json.dumps(page))
        self.assertNotIn("frames", page["job"]["checkpoint"])
        self.assertEqual(self.content(version)["state"], "cancelled")
        self.assertEqual(self.client.get("/source-versions/" + version + "/file").content, (FIXTURES / "slides.mp4").read_bytes())

    def test_whiteboard_accumulation_and_returned_slides_are_kept(self):
        for name, wanted in (("whiteboard.mp4", [0,3,6,9,12]), ("return-slides.mp4", [0,4,8])):
            with self.subTest(name=name):
                version = self.seed(name)
                page = self.run_frames(version)
                values = []
                for offset in range(0, page["total"], 4):
                    values += self.page(version, offset)["frames"]
                self.assertEqual([f["seconds"] for f in values], wanted)

    def test_static_duplicate_suppression_and_periodic_reference(self):
        version = self.seed("static.mp4")
        page = self.run_frames(version)
        self.assertEqual([f["seconds"] for f in page["frames"]], [0,60])
        self.assertIn("periodic_reference", page["frames"][1]["reasons"])
        self.assertEqual(page["job"]["result"]["sampled_frames"], 65)

    def test_video_track_can_end_before_container_audio(self):
        version = self.seed("video-ends-first.mp4")
        page = self.run_frames(version)
        self.assertEqual([f["seconds"] for f in page["frames"]], [0,4,8])
        self.assertEqual(page["job"]["result"]["empty_windows"], 2)
        self.assertEqual(page["job"]["state"], "partial")

    def test_vfr_uses_presentation_times_and_rotation_is_applied(self):
        version = self.seed("vfr.mp4")
        page = self.run_frames(version)
        self.assertEqual([f["seconds"] for f in page["frames"]], [0,2.4,5.6])
        version = self.seed("rotated.mp4")
        page = self.run_frames(version)
        self.assertEqual((page["frames"][0]["asset"]["width"], page["frames"][0]["asset"]["height"]), (360,640))

    def test_cancel_resume_preserves_only_completed_windows(self):
        version = self.seed("static.mp4")
        original = frames.analyze
        calls = 0
        def cancel_second(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.client.post(BASE + "/jobs/" + self.job(version, "video_frames")["id"] + "/cancel")
            return original(*args)
        with patch.object(frames, "analyze", side_effect=cancel_second):
            self.worker.execute(self.worker.claim())
        before = self.page(version)
        self.assertEqual(before["job"]["state"], "cancelled")
        self.assertEqual(before["job"]["checkpoint"]["completed_windows"], 1)
        self.assertEqual(before["total"], 1)
        self.client.post(BASE + "/jobs/" + before["job"]["id"] + "/retry").raise_for_status()
        with patch.dict(frames.CONFIG, {"pixel_delta": 25}):
            self.worker.execute(self.worker.claim())
        self.assertEqual(self.job(version, "video_frames")["state"], "failed")
        self.assertIn("Frame settings", self.job(version, "video_frames")["error"])
        self.assertEqual(self.page(version)["frames"][0], before["frames"][0])
        self.client.post(BASE + "/jobs/" + before["job"]["id"] + "/retry").raise_for_status()
        restarted = Worker(self.root, threading.Event())
        try:
            restarted.execute(restarted.claim())
        finally:
            restarted.connection.close()
        after = self.page(version)
        self.assertEqual(after["job"]["state"], "succeeded", after["job"]["error"])
        self.assertEqual(after["frames"][0], before["frames"][0])
        self.assertEqual([f["seconds"] for f in after["frames"]], [0,60])

    def test_scope_busy_pagination_rebuild_stable_ids_and_damaged_asset(self):
        version = self.seed()
        route = BASE + "/source-versions/" + version + "/process-video-frames"
        self.assertEqual(self.client.post(route).status_code, 409)
        self.assertEqual(self.client.post(route.replace("semester-3", "other")).status_code, 404)
        first = self.run_frames(version)
        self.assertEqual(self.client.get(route.replace("process-video-frames", "video-frames").replace("semester-3", "other")).status_code, 404)
        self.assertEqual(self.client.get(route.replace("process-video-frames", "video-frames") + "?offset=601").status_code, 422)
        row = self.worker.connection.execute("SELECT checkpoint_json FROM jobs WHERE id=?", (first["job"]["id"],)).fetchone()
        asset = json.loads(row[0])["frames"][0]["asset"]
        (self.root / asset["path"]).write_bytes(b"damaged")
        self.assertIn("error", self.page(version)["frames"][0]["asset"])
        self.assertNotIn("data_url", self.page(version)["frames"][0]["asset"])
        self.client.post(route).raise_for_status()
        second = self.run_frames(version)
        self.assertEqual([f["id"] for f in first["frames"]], [f["id"] for f in second["frames"]])
        self.assertTrue(second["frames"][0]["asset"].get("data_url"))

    def test_modified_original_and_corrupt_source_fail_closed(self):
        version = self.seed()
        target = self.root / self.worker.connection.execute("SELECT relative_path FROM source_versions WHERE id=?", (version,)).fetchone()[0]
        original = target.read_bytes()
        target.write_bytes(bytes([original[0] ^ 1]) + original[1:])
        with patch.object(frames, "candidates", side_effect=AssertionError("No damaged original decode")):
            self.worker.execute(self.worker.claim())
        self.assertEqual(self.job(version, "video_frames")["state"], "failed")
        self.assertEqual(self.page(version)["total"], 0)
        version = self.seed("broken.mp4", b"Authored invalid video")
        self.worker.execute(self.worker.claim())
        self.assertEqual(self.job(version, "video_frames")["state"], "failed")
        self.assertEqual(self.client.get("/source-versions/" + version + "/file").status_code, 200)

    def test_budget_keeps_late_windows_and_reports_omissions(self):
        data = (FIXTURES.parent / "phase-07/intervals.mp4").read_bytes()
        version = self.seed("motion.mp4", data)
        with patch.object(frames, "MAX_FRAMES", 6), patch.dict(frames.CONFIG, {"max_frames":6}):
            page = self.run_frames(version)
        values = page["frames"] + self.page(version,4)["frames"]
        self.assertEqual(page["total"], 6)
        self.assertGreaterEqual(values[-1]["seconds"], 60)
        self.assertGreater(page["job"]["result"]["omitted_candidates"], 0)
        self.assertEqual(page["job"]["state"], "partial")

    def test_automatic_new_and_saved_video_queue_is_idempotent(self):
        with patch.dict(os.environ, {"STUDYLENS_AUTO_VIDEO_FRAMES":"1"}):
            version = self.seed()
            self.run_frames(version)
            self.worker.connection.execute("DELETE FROM jobs WHERE kind='video_frames' AND source_version_id=?", (version,))
            from studylens_service.jobs import JobStore
            self.client.portal.call(JobStore(self.client.app.state.database).backfill)
            self.client.portal.call(JobStore(self.client.app.state.database).backfill)
        jobs = [j for j in self.client.get(BASE + "/jobs").json() if j["source_version_id"] == version and j["kind"] == "video_frames"]
        self.assertEqual(len(jobs), 1)


if __name__ == "__main__":
    unittest.main()
