import hashlib
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import closing
from pathlib import Path

from fastapi.testclient import TestClient
from studylens_service.api import create_app
from test_storage import AUTH, BASE, SESSION, SOURCES, TOKEN


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="studylens-queue-")
        self.root = Path(self.directory.name)
        self.workers = []
        self.client = TestClient(create_app(self.root, TOKEN, allow_eval=True), headers=AUTH)
        self.client.__enter__()
        self.assertEqual(self.client.put(BASE + "/session", json={"base_revision": 0, "session": SESSION}).status_code, 200)

    def tearDown(self):
        for worker in self.workers:
            self.stop_worker(worker)
        self.client.__exit__(None, None, None)
        self.directory.cleanup()

    def start_worker(self):
        worker = subprocess.Popen([sys.executable, "-m", "studylens_service.worker", "--data-dir", str(self.root), "--allow-eval"],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            **({"creationflags": 0x08000000} if os.name == "nt" else {}))
        self.workers.append(worker)
        return worker

    def stop_worker(self, worker, abrupt=False):
        if worker.poll() is None:
            if abrupt:
                worker.kill()
            else:
                worker.stdin.close()
            worker.wait(timeout=5)
        if worker.stdin and not worker.stdin.closed:
            worker.stdin.close()
        if worker.stderr and not worker.stderr.closed:
            output = worker.stderr.read().decode()
            worker.stderr.close()
            self.assertEqual(output, "", output)

    def fixture(self, **payload):
        response = self.client.post(BASE + "/queue-test", json={"steps": 12, "delay_ms": 30, **payload})
        self.assertEqual(response.status_code, 202, response.text)
        return response.json()["id"]

    def job(self, job_id):
        response = self.client.get(BASE + "/jobs/" + job_id)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def wait(self, job_id, predicate, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            job = self.job(job_id)
            if predicate(job):
                return job
            time.sleep(.02)
        self.fail(f"Queue condition timed out: {self.job(job_id)}")

    def upload(self, payload=b"Authored original fixture"):
        response = self.client.post(SOURCES, params={"filename": "notes.txt"}, content=payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_duplicate_import_has_one_durable_job_and_correct_result(self):
        original = self.upload()
        self.assertTrue(self.upload()["duplicate"])
        jobs = self.client.get(BASE + "/jobs").json()
        self.assertEqual(len(jobs), 2)
        jobs = [job for job in jobs if job["kind"] == "verify_original"]
        self.assertEqual(jobs[0]["source_version_id"], original["version_id"])
        self.start_worker()
        complete = self.wait(jobs[0]["id"], lambda job: job["state"] == "succeeded")
        self.assertEqual(complete["result"]["sha256"], hashlib.sha256(b"Authored original fixture").hexdigest())
        self.assertTrue(complete["result"]["integrity_verified"])

    def test_queue_cancel_before_claim_does_not_run(self):
        job_id = self.fixture()
        self.assertEqual(self.client.post(BASE + "/jobs/" + job_id + "/cancel").json()["state"], "cancelled")
        self.start_worker()
        next_id = self.fixture(steps=1)
        self.wait(next_id, lambda job: job["state"] == "succeeded")
        cancelled = self.job(job_id)
        self.assertEqual(cancelled["attempts"], 0)
        self.assertEqual(cancelled["done"], 0)

    def test_running_cancel_then_manual_retry_resumes_exact_units(self):
        job_id = self.fixture(steps=30, delay_ms=30)
        self.start_worker()
        self.wait(job_id, lambda job: job["done"] >= 2)
        self.client.post(BASE + "/jobs/" + job_id + "/cancel")
        cancelled = self.wait(job_id, lambda job: job["state"] == "cancelled")
        self.assertLess(cancelled["done"], cancelled["total"])
        self.assertGreaterEqual(cancelled["done"], 2)
        self.assertEqual(self.client.post(BASE + "/jobs/" + job_id + "/retry").status_code, 202)
        complete = self.wait(job_id, lambda job: job["state"] == "succeeded")
        self.assertEqual(complete["result"]["completed_steps"], list(range(30)))

    def test_killed_worker_recovers_checkpoint_without_repeating_units(self):
        job_id = self.fixture(steps=24, delay_ms=35)
        worker = self.start_worker()
        before = self.wait(job_id, lambda job: job["done"] >= 3)
        self.stop_worker(worker, abrupt=True)
        checkpoint = self.job(job_id)
        self.assertEqual(checkpoint["state"], "running")
        self.assertGreaterEqual(checkpoint["done"], before["done"])
        self.start_worker()
        complete = self.wait(job_id, lambda job: job["state"] == "succeeded")
        self.assertEqual(complete["recoveries"], 1)
        self.assertEqual(complete["attempts"], 2)
        self.assertEqual(complete["result"]["completed_steps"], list(range(24)))

    def test_clean_parent_eof_pauses_and_restart_resumes(self):
        job_id = self.fixture(steps=24, delay_ms=35)
        worker = self.start_worker()
        self.wait(job_id, lambda job: job["done"] >= 2)
        self.stop_worker(worker)
        paused = self.job(job_id)
        self.assertEqual(paused["state"], "queued")
        self.assertEqual(paused["stage"], "Paused for restart")
        self.start_worker()
        complete = self.wait(job_id, lambda job: job["state"] == "succeeded")
        self.assertEqual(complete["result"]["completed_steps"], list(range(24)))

    def test_two_worker_processes_never_run_two_heavy_jobs(self):
        ids = [self.fixture(steps=8, delay_ms=40) for _ in range(3)]
        self.start_worker()
        self.start_worker()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            rows = self.client.get(BASE + "/jobs").json()
            self.assertLessEqual(sum(row["state"] == "running" for row in rows), 1)
            if all(self.job(job_id)["state"] == "succeeded" for job_id in ids):
                break
            time.sleep(.02)
        else:
            self.fail("Queue did not complete")

    def test_transient_failures_retry_with_bound_and_succeed(self):
        job_id = self.fixture(steps=2, fail_until=2)
        self.start_worker()
        complete = self.wait(job_id, lambda job: job["state"] == "succeeded")
        self.assertEqual(complete["attempts"], 3)
        self.assertEqual(complete["failures"], 2)
        self.assertEqual(complete["result"]["completed_steps"], [0, 1])

    def test_transient_failures_stop_after_three_attempts(self):
        job_id = self.fixture(steps=1, fail_until=3)
        self.start_worker()
        failed = self.wait(job_id, lambda job: job["state"] == "failed")
        self.assertEqual(failed["attempts"], 3)
        self.assertEqual(failed["failures"], 3)
        self.assertEqual(self.client.post(BASE + "/jobs/" + job_id + "/retry").status_code, 202)

    def test_permanent_failures_and_damaged_originals_do_not_retry(self):
        job_id = self.fixture(permanent_failure=True)
        original = self.upload()
        with closing(sqlite3.connect(self.root / "studylens.sqlite3")) as connection:
            relative = connection.execute("SELECT relative_path FROM source_versions WHERE id=?", (original["version_id"],)).fetchone()[0]
        (self.root / relative).write_bytes(b"x" * len(b"Authored original fixture"))
        self.start_worker()
        failed = self.wait(job_id, lambda job: job["state"] == "failed")
        self.assertEqual(failed["attempts"], 1)
        version_job = next(row for row in self.client.get(BASE + "/jobs").json() if row["source_version_id"] == original["version_id"] and row["kind"] == "verify_original")
        failed = self.wait(version_job["id"], lambda job: job["state"] == "failed")
        self.assertEqual(failed["attempts"], 1)
        self.assertIn("integrity", failed["error"])

    def test_workspace_scope_and_running_retry_are_rejected(self):
        job_id = self.fixture(steps=30)
        other = self.client.post("/workspaces", json={"name": "Other workspace"}).json()["id"]
        for suffix in ("", "/cancel", "/retry"):
            response = self.client.get(f"/workspaces/{other}/jobs/{job_id}") if not suffix else self.client.post(f"/workspaces/{other}/jobs/{job_id}{suffix}")
            self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get(f"/workspaces/{other}/jobs").json(), [])
        self.assertEqual(self.client.get(BASE + "/jobs?limit=1000").status_code, 422)
        self.start_worker()
        self.wait(job_id, lambda job: job["state"] == "running")
        self.assertEqual(self.client.post(BASE + "/jobs/" + job_id + "/retry").status_code, 409)

    def test_service_remains_responsive_while_worker_runs(self):
        job_id = self.fixture(steps=100, delay_ms=35, cpu_ms=30)
        self.start_worker()
        self.wait(job_id, lambda job: job["state"] == "running")
        durations = []
        for _ in range(10):
            start = time.monotonic()
            self.assertEqual(self.client.get("/health").status_code, 200)
            self.assertEqual(self.client.get(BASE + "/session").status_code, 200)
            durations.append(time.monotonic() - start)
        self.assertLess(max(durations), 2, durations)
        self.assertEqual(self.job(job_id)["state"], "running")

    def test_supervisor_lifecycle_and_evaluation_default_off(self):
        with tempfile.TemporaryDirectory(prefix="studylens-supervisor-") as folder:
            with TestClient(create_app(Path(folder), TOKEN, start_worker=True), headers=AUTH) as client:
                status = client.get("/queue").json()
                self.assertTrue(status["available"])
                self.assertFalse(status["evaluation_enabled"])
                self.assertEqual(client.post(BASE + "/queue-test", json={}).status_code, 404)

    def test_orphan_audit_reports_old_files_without_deleting(self):
        orphan = self.root / "staging" / "old-unfinished.part"
        orphan.write_bytes(b"Unfinished fixture")
        old = time.time() - 7200
        os.utime(orphan, (old, old))
        fresh = self.root / "staging" / "active-upload.part"
        fresh.write_bytes(b"Fresh fixture")
        self.start_worker()
        job_id = self.fixture(steps=1)
        self.wait(job_id, lambda job: job["state"] == "succeeded")
        import json
        report = json.loads((self.root / "reconciliation.json").read_text())
        self.assertEqual(report["old_unreferenced_files"], 1)
        self.assertTrue(orphan.exists())
        self.assertTrue(fresh.exists())

    def test_completed_original_can_be_checked_again(self):
        original = self.upload()
        job = next(row for row in self.client.get(BASE + "/jobs").json() if row["kind"] == "verify_original")
        self.start_worker()
        self.wait(job["id"], lambda row: row["state"] == "succeeded")
        response = self.client.post(BASE + "/source-versions/" + original["version_id"] + "/verify")
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["id"], job["id"])
        completed = self.wait(job["id"], lambda row: row["state"] == "succeeded" and row["attempts"] == 2)
        self.assertTrue(completed["result"]["integrity_verified"])

    def test_phase_two_upgrade_preserves_session_and_original_and_backfills_job(self):
        original = self.upload()
        before = self.client.get(BASE + "/session").json()
        self.client.__exit__(None, None, None)
        # Reconstruct the previous schema within this disposable test directory.
        with closing(sqlite3.connect(self.root / "studylens.sqlite3")) as connection:
            connection.execute("DROP TABLE youtube_media_links")
            connection.execute("DROP TABLE content_units")
            connection.execute("DROP TABLE jobs")
            connection.execute("UPDATE alembic_version SET version_num='0001_local_storage'")
            connection.commit()
        self.client = TestClient(create_app(self.root, TOKEN, allow_eval=True), headers=AUTH)
        self.client.__enter__()
        self.assertEqual(self.client.get(BASE + "/session").json(), before)
        self.assertEqual(self.client.get("/source-versions/" + original["version_id"] + "/file").content, b"Authored original fixture")
        rows = self.client.get(BASE + "/jobs").json()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["source_version_id"], original["version_id"])

    def test_supervisor_restarts_killed_process_and_recovers_job(self):
        with tempfile.TemporaryDirectory(prefix="studylens-supervised-recovery-") as folder:
            app = create_app(Path(folder), TOKEN, start_worker=True, allow_eval=True)
            with TestClient(app, headers=AUTH) as client:
                job_id = client.post(BASE + "/queue-test", json={"steps": 30, "delay_ms": 30}).json()["id"]
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    row = client.get(BASE + "/jobs/" + job_id).json()
                    if row["done"] >= 2:
                        break
                    time.sleep(.02)
                else:
                    self.fail("Supervised job did not start")
                client.portal.call(app.state.worker_supervisor.process.kill)
                while time.monotonic() < deadline:
                    row = client.get(BASE + "/jobs/" + job_id).json()
                    if row["state"] == "succeeded":
                        break
                    time.sleep(.02)
                else:
                    self.fail("Supervised job did not recover")
                self.assertEqual(row["result"]["completed_steps"], list(range(30)))
                self.assertEqual(row["recoveries"], 1)
                self.assertEqual(client.get("/queue").json()["restarts"], 1)
