"""Automatic queue gate; authored material and mocked HTTP only."""
import json
import os
import threading
import unittest
from unittest.mock import patch

import test_cloud_vision as helpers
from test_storage import BASE, SOURCES
from studylens_service.job_errors import Cancelled, PermanentFailure
from studylens_service.worker import Worker


class AutomaticVisionTests(unittest.TestCase):
    setUp = helpers.CloudTests.setUp
    tearDown = helpers.CloudTests.tearDown
    stop = helpers.CloudTests.stop
    content = helpers.CloudTests.content
    job = helpers.CloudTests.job
    seed = helpers.CloudTests.seed
    provider = helpers.CloudTests.provider

    def complete_local(self, worker, version, error=None):
        worker.connection.execute("UPDATE jobs SET state='queued',available_at=0 WHERE kind='extract_source' AND source_version_id=?", (version,))
        job = worker.claim()
        self.assertEqual(job["kind"], "extract_source")
        with patch("studylens_service.extraction.extract", side_effect=error,
                   return_value={"counts": {"text": 1}, "units": 1, "warnings": 0}):
            worker.execute(job)

    def difficult(self, worker, version):
        row = worker.connection.execute("SELECT id,metadata_json FROM content_units WHERE source_version_id=?", (version,)).fetchone()
        metadata = json.loads(row["metadata_json"])
        metadata["ocr"] = {"words": [{"text": "Retention", "confidence": 35}]}
        worker.connection.execute("UPDATE content_units SET metadata_json=? WHERE id=?", (json.dumps(metadata), row["id"]))

    def test_automatic_completion_restart_and_cache_preserve_local_evidence(self):
        worker, version = self.seed()
        self.difficult(worker, version)
        before = self.content(version)["units"][0]
        calls, provider = self.provider()
        with patch.dict(os.environ, {"GROQ_API_KEY": "authored-key", "STUDYLENS_AUTO_GROQ_VISION": "1"}), provider:
            self.complete_local(worker, version)
            cloud = self.job(version, "cloud_visuals")
            self.assertTrue(cloud["automatic"])
            self.assertEqual(cloud["state"], "queued")
            payload = json.loads(worker.connection.execute("SELECT payload_json FROM jobs WHERE id=?", (cloud["id"],)).fetchone()[0])
            self.assertNotIn("consent", payload)
            self.assertEqual(len(calls), 0)
            restarted = Worker(self.root, threading.Event())
            self.direct_workers.append(restarted)
            restarted.recover()
            restarted.execute(restarted.claim())
            self.assertEqual(self.job(version, "cloud_visuals")["state"], "succeeded")
            self.assertIsNone(restarted.claim())
            # A rerun of cloud processing uses the existing provider cache.
            response = self.client.post(BASE + f"/source-versions/{version}/cloud-visuals", json={})
            self.assertEqual(response.status_code, 202)
            restarted.execute(restarted.claim())
            self.assertEqual(self.job(version, "cloud_visuals")["result"]["cached"], 1)
        self.assertEqual(len(calls), 1)
        after = self.content(version)["units"][0]
        for key in ("text", "text_sha256", "locator", "id"):
            self.assertEqual(before[key], after[key])
        self.assertTrue(after["metadata"]["cloud_visuals"][0]["automatic"])
        self.assertFalse(after["metadata"]["cloud_visuals"][0]["verified"])

    def test_ordinary_text_preview_stays_local_without_http(self):
        worker, version = self.seed()
        calls, provider = self.provider()
        with patch.dict(os.environ, {"GROQ_API_KEY": "authored-key", "STUDYLENS_AUTO_GROQ_VISION": "1"}), provider:
            self.complete_local(worker, version)
            worker.execute(worker.claim())
        self.assertEqual(len(calls), 0)
        self.assertEqual(self.job(version, "cloud_visuals")["result"]["local"], 1)

    def test_missing_key_and_opt_out_do_not_queue(self):
        worker, version = self.seed()
        for key, enabled in (("", "1"), ("authored-key", "0")):
            with self.subTest(key_present=bool(key), enabled=enabled), patch.dict(os.environ, {"GROQ_API_KEY": key, "STUDYLENS_AUTO_GROQ_VISION": enabled}):
                self.complete_local(worker, version)
                self.assertFalse(self.client.get("/vision").json()["automatic"])
                self.assertIsNone(worker.claim())

    def test_failed_or_cancelled_local_work_does_not_queue_cloud(self):
        worker, version = self.seed()
        with patch.dict(os.environ, {"GROQ_API_KEY": "authored-key", "STUDYLENS_AUTO_GROQ_VISION": "1"}):
            for error in (PermanentFailure("Authored extraction failure"), Cancelled()):
                self.complete_local(worker, version, error)
                self.assertIsNone(worker.claim())

    def test_no_preview_or_nonvisual_source_does_not_queue(self):
        worker, version = self.seed()
        with patch.dict(os.environ, {"GROQ_API_KEY": "authored-key", "STUDYLENS_AUTO_GROQ_VISION": "1"}):
            for kind in ("text", "audio", "video"):
                worker.connection.execute("UPDATE sources SET kind=?", (kind,))
                self.complete_local(worker, version)
                self.assertIsNone(worker.claim())
            worker.connection.execute("UPDATE sources SET kind='image'")
            worker.connection.execute("UPDATE content_units SET metadata_json='{}'")
            self.complete_local(worker, version)
            self.assertIsNone(worker.claim())

    def test_cancelled_cloud_job_is_not_duplicated_or_resurrected(self):
        worker, version = self.seed()
        with patch.dict(os.environ, {"GROQ_API_KEY": "authored-key", "STUDYLENS_AUTO_GROQ_VISION": "1"}):
            self.complete_local(worker, version)
            cloud = self.job(version, "cloud_visuals")
            self.assertEqual(self.client.post(BASE + f"/jobs/{cloud['id']}/cancel").status_code, 200)
            self.complete_local(worker, version)
        self.assertEqual(self.job(version, "cloud_visuals")["id"], cloud["id"])
        self.assertEqual(self.job(version, "cloud_visuals")["state"], "cancelled")
        self.assertIsNone(worker.claim())

    def test_opt_out_after_queue_blocks_network(self):
        worker, version = self.seed()
        self.difficult(worker, version)
        calls, provider = self.provider()
        with patch.dict(os.environ, {"GROQ_API_KEY": "authored-key", "STUDYLENS_AUTO_GROQ_VISION": "1"}):
            self.complete_local(worker, version)
        with patch.dict(os.environ, {"GROQ_API_KEY": "authored-key", "STUDYLENS_AUTO_GROQ_VISION": "0"}), provider:
            worker.execute(worker.claim())
        self.assertEqual(len(calls), 0)
        self.assertEqual(self.job(version, "cloud_visuals")["state"], "failed")
        self.assertTrue(self.content(version)["units"][0]["text"])

    def test_new_local_work_takes_priority_over_automatic_cloud(self):
        worker, version = self.seed()
        with patch.dict(os.environ, {"GROQ_API_KEY": "authored-key", "STUDYLENS_AUTO_GROQ_VISION": "1"}):
            self.complete_local(worker, version)
            response = self.client.post(SOURCES, params={"filename": "priority.txt"}, content=b"Authored priority fixture")
            self.assertEqual(response.status_code, 201)
            first = worker.claim()
            self.assertEqual(first["kind"], "verify_original")
            worker.execute(first)
            second = worker.claim()
            self.assertEqual(second["kind"], "extract_source")
            worker.execute(second)
            self.assertEqual(worker.claim()["kind"], "cloud_visuals")

    def test_equal_creation_times_claim_integrity_before_extraction(self):
        worker, version = self.seed()
        worker.connection.execute("DELETE FROM content_units WHERE source_version_id=?", (version,))
        worker.connection.execute("UPDATE jobs SET state='queued',owner=NULL,available_at=0,created_at=1 WHERE source_version_id=?", (version,))
        # An earlier random UUID must not let extraction win a timestamp tie.
        worker.connection.execute("UPDATE jobs SET id='a-extraction' WHERE kind='extract_source' AND source_version_id=?", (version,))
        worker.connection.execute("UPDATE jobs SET id='z-integrity' WHERE kind='verify_original' AND source_version_id=?", (version,))
        first = worker.claim()
        self.assertEqual(first["kind"], "verify_original")
        worker.execute(first)
        self.assertEqual(worker.claim()["kind"], "extract_source")
