"""Independent Phase 7C gate: real local OCR, labeled provider fixture."""
import hashlib
import json
import threading
import unittest
from uuid import uuid4
from unittest.mock import patch

import test_extraction as helpers
from test_storage import BASE
from test_video_frames import FIXTURES, TOOLS
from studylens_service import video_frame_visuals as visuals
from studylens_service.cloud_vision_wait import Deferred
from studylens_service.jobs import JobStore
from studylens_service.worker import Worker


@unittest.skipUnless(TOOLS, "Install pinned frame dependencies and FFmpeg")
class FrameVisualTests(unittest.TestCase):
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
    def seed(self, name="slides.mp4"):
        value = self.upload(name, (FIXTURES / name).read_bytes())
        version = value["version_id"]
        self.worker.execute(self.worker.claim())
        self.client.post(BASE + "/jobs/" + self.job(version)["id"] + "/cancel").raise_for_status()
        if not any(job["kind"] == "video_frames" and job["source_version_id"] == version
                   for job in self.client.get(BASE + "/jobs").json()):
            self.client.post(BASE + "/source-versions/" + version + "/process-video-frames").raise_for_status()
        return version

    def page(self, version):
        response = self.client.get(BASE + "/source-versions/" + version + "/video-frames")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def run_frames(self, version):
        self.worker.execute(self.worker.claim())
        self.assertIn(self.job(version, "video_frames")["state"], ("succeeded", "partial"))
        return self.page(version)

    def run_visuals(self, version):
        queued = self.job(version, "video_frame_visuals")
        self.assertEqual(queued["state"], "queued")
        self.worker.execute(self.worker.claim())
        return self.page(version)

    def test_real_ocr_keeps_version_timestamp_and_separate_audio(self):
        version = self.seed()
        self.run_frames(version)
        with patch.object(visuals, "groq_enabled", return_value=False):
            page = self.run_visuals(version)
        self.assertEqual(page["visual_job"]["state"], "succeeded")
        self.assertEqual(page["total"], 3)
        for frame in page["frames"]:
            value = frame["visual"]
            self.assertEqual(value["source_version_id"], version)
            self.assertEqual(value["source_sha256"], page["source_sha256"])
            self.assertEqual(value["seconds"], frame["seconds"])
            self.assertEqual(value["asset_sha256"], frame["asset"]["sha256"])
            self.assertTrue(value["ocr"]["available"])
            self.assertTrue(value["ocr"]["text"])
            self.assertEqual(value["cloud"]["status"], "not_configured" if value["routing"]["decision"] == "cloud" else "local")
            self.assertTrue(value["review_required"])
        self.assertEqual(self.content(version)["state"], "cancelled")
        self.assertEqual(page["frames"][0]["nearby_audio"], [])
        self.assertNotIn("results", page["visual_job"]["checkpoint"])
        spoken = "Authored speech fixture"
        self.worker.connection.execute("""INSERT INTO content_units
            (id,source_version_id,job_id,ordinal,locator_json,text,text_sha256,status,warning,engine,metadata_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (str(uuid4()), version, self.job(version)["id"], 1,
            json.dumps({"kind": "time", "start_seconds": 0, "end_seconds": 3}), spoken,
            hashlib.sha256(spoken.encode()).hexdigest(), "suspect", "Fixture only", "fixture",
            json.dumps({"segments": [{"start_seconds": 0, "end_seconds": 1, "text": spoken}],
                "speech": {"provider": "local"}})))
        aligned = self.page(version)["frames"][0]
        self.assertEqual(aligned["nearby_audio"][0]["text"], spoken)
        self.assertEqual(aligned["nearby_audio"][0]["source_version_id"], version)
        self.assertEqual(aligned["visual"]["ocr"], page["frames"][0]["visual"]["ocr"])

    def test_selective_cloud_uses_one_frame_per_window_and_labels_fixture(self):
        version = self.seed()
        self.run_frames(version)
        calls = []
        async def provider(worker, job, raw, *, fallback=False):
            calls.append((len(raw), fallback))
            return {"is_blank": False, "text_lines": ["Fixture diagram"], "tables": [], "equations": [],
                "diagram_nodes": [], "diagram_edges": [], "uncertainties": []}
        with patch.object(visuals, "groq_enabled", return_value=True), patch.object(visuals, "route",
                return_value={"decision": "cloud", "reasons": ["Fixture routing"]}), patch.object(
                visuals, "reserve"), patch.object(visuals, "request_image", side_effect=provider):
            page = self.run_visuals(version)
        self.assertEqual(len(calls), 1)
        self.assertEqual(page["visual_job"]["result"]["cloud_sent"], 1)
        self.assertEqual(page["visual_job"]["result"]["cloud_not_selected"], 2)
        self.assertEqual(page["frames"][0]["visual"]["cloud"]["provider"], "groq")
        self.assertFalse(page["frames"][0]["visual"]["cloud"]["verified"])
        self.assertEqual(page["frames"][1]["visual"]["cloud"]["status"], "not_selected")

    def test_cancel_restart_preserves_committed_frame_and_scope(self):
        version = self.seed()
        self.run_frames(version)
        original = visuals.ocr
        calls = 0
        def cancelling(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.client.post(BASE + "/jobs/" + self.job(version, "video_frame_visuals")["id"] + "/cancel")
            return original(*args)
        with patch.object(visuals, "ocr", side_effect=cancelling), patch.object(visuals, "groq_enabled", return_value=False):
            self.worker.execute(self.worker.claim())
        before = self.page(version)
        self.assertEqual(before["visual_job"]["state"], "cancelled")
        self.assertIsNotNone(before["frames"][0]["visual"])
        self.assertIsNone(before["frames"][1]["visual"])
        self.assertEqual(self.client.post(BASE + "/jobs/" + before["visual_job"]["id"] + "/retry").status_code, 202)
        restarted = Worker(self.root, threading.Event())
        try:
            with patch.object(visuals, "groq_enabled", return_value=False):
                restarted.execute(restarted.claim())
        finally:
            restarted.connection.close()
        after = self.page(version)
        self.assertEqual(after["visual_job"]["state"], "succeeded")
        self.assertEqual(after["frames"][0]["visual"]["ocr"], before["frames"][0]["visual"]["ocr"])
        self.assertEqual(after["frames"][0]["visual"]["seconds"], before["frames"][0]["visual"]["seconds"])
        self.assertEqual(self.client.post(BASE.replace("semester-3", "other") +
            "/source-versions/" + version + "/process-frame-visuals").status_code, 404)
        self.assertEqual(self.client.post(BASE + "/source-versions/" + version + "/process-frame-visuals").status_code, 202)

    def test_damaged_preview_fails_closed_without_cloud_send(self):
        version = self.seed()
        page = self.run_frames(version)
        row = self.worker.connection.execute("SELECT checkpoint_json FROM jobs WHERE kind='video_frames' AND source_version_id=?", (version,)).fetchone()
        asset = json.loads(row[0])["frames"][0]["asset"]
        (self.root / asset["path"]).write_bytes(b"damaged")
        with patch.object(visuals, "request_image", side_effect=AssertionError("No send")):
            self.worker.execute(self.worker.claim())
        self.assertEqual(self.job(version, "video_frame_visuals")["state"], "failed")
        self.assertIsNone(self.page(version)["frames"][0]["visual"])

    def test_reselection_invalidates_prior_visual_results(self):
        version = self.seed()
        self.run_frames(version)
        with patch.object(visuals, "groq_enabled", return_value=False):
            self.run_visuals(version)
        self.client.post(BASE + "/source-versions/" + version + "/process-video-frames").raise_for_status()
        page = self.page(version)
        self.assertIsNone(page["visual_job"])
        self.assertEqual(page["total"], 0)
        self.worker.execute(self.worker.claim())
        rebuilt = self.page(version)
        self.assertEqual(rebuilt["total"], 3)
        self.assertIsNone(rebuilt["frames"][0]["visual"])
        self.assertEqual(rebuilt["visual_job"]["state"], "queued")

    def test_cloud_quota_pause_restarts_without_resending_saved_frame(self):
        version = self.seed("static.mp4")
        self.run_frames(version)
        sends, reserves = [], 0
        async def provider(worker, job, raw, *, fallback=False):
            sends.append(len(raw))
            return {"is_blank": False, "text_lines": ["Fixture text"], "tables": [], "equations": [],
                "diagram_nodes": [], "diagram_edges": [], "uncertainties": []}
        def pace(_worker):
            nonlocal reserves
            reserves += 1
            if reserves == 2:
                raise Deferred(.01)
        with patch.object(visuals, "groq_enabled", return_value=True), patch.object(visuals, "route",
                return_value={"decision": "cloud", "reasons": ["Fixture routing"]}), patch.object(
                visuals, "reserve", side_effect=pace), patch.object(visuals, "request_image", side_effect=provider):
            self.worker.execute(self.worker.claim())
            paused = self.page(version)
            self.assertEqual(paused["visual_job"]["state"], "queued")
            self.assertEqual(paused["frames"][0]["visual"]["cloud"]["status"], "complete")
            self.assertIsNone(paused["frames"][1]["visual"]["cloud"])
            restarted = Worker(self.root, threading.Event())
            try:
                restarted.connection.execute("UPDATE jobs SET available_at=0 WHERE id=?", (paused["visual_job"]["id"],))
                restarted.execute(restarted.claim())
            finally:
                restarted.connection.close()
        after = self.page(version)
        self.assertEqual(after["visual_job"]["state"], "succeeded")
        self.assertEqual(after["frames"][0]["visual"], paused["frames"][0]["visual"])
        self.assertEqual(len(sends), 2)

    def test_existing_selected_video_backfills_visual_job_once(self):
        version = self.seed()
        self.run_frames(version)
        self.worker.connection.execute("DELETE FROM jobs WHERE kind='video_frame_visuals' AND source_version_id=?", (version,))
        with patch.dict("os.environ", {"STUDYLENS_AUTO_VIDEO_VISUALS": "1"}):
            self.client.portal.call(JobStore(self.client.app.state.database).backfill)
            self.client.portal.call(JobStore(self.client.app.state.database).backfill)
        jobs = [job for job in self.client.get(BASE + "/jobs").json()
            if job["source_version_id"] == version and job["kind"] == "video_frame_visuals"]
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["state"], "queued")


if __name__ == "__main__":
    unittest.main()
