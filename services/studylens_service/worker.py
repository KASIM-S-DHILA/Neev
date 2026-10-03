"""One OS-locked worker per data directory. This process uses only the stdlib."""
import argparse
import hashlib
import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


from .job_errors import Cancelled, Interrupted, PermanentFailure

# Deferred cloud quota waits release this worker for local jobs.
from .cloud_vision_wait import Deferred


@contextmanager
def exclusive_worker(root):
    handle = (root / "heavy-worker.lock").open("a+b")
    if handle.seek(0, os.SEEK_END) == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    locked = False
    try:
        if os.name == "nt":
            import msvcrt
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                locked = True
            except OSError:
                pass
        else:
            import fcntl
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
            except BlockingIOError:
                pass
        yield locked
    finally:
        if locked:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


class Worker:
    def __init__(self, root, stop, allow_eval=False):
        self.root = root.resolve()
        self.stop = stop
        self.allow_eval = allow_eval
        self.owner = str(uuid4())
        self.connection = sqlite3.connect(self.root / "studylens.sqlite3", timeout=5, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA busy_timeout=5000")

    def recover(self):
        # The OS lock proves that no previous heavy worker can still write.
        self.connection.execute("""UPDATE jobs SET
            state=CASE WHEN cancel_requested THEN 'cancelled' ELSE 'queued' END,
            stage=CASE WHEN cancel_requested THEN 'Cancelled after restart' ELSE 'Resuming after restart' END,
            owner=NULL, recoveries=recoveries+1, available_at=?, updated_at=? WHERE state='running'""", (time.time(), time.time()))

    def audit_orphans(self):
        # Report old, unreferenced files. Never delete originals or an active upload.
        referenced = {row[0] for row in self.connection.execute("SELECT relative_path FROM source_versions")}
        cutoff = time.time() - 3600
        paths = []
        count = 0
        for folder in ("staging", "originals"):
            for path in (self.root / folder).rglob("*"):
                try:
                    if not path.is_file() or path.stat().st_mtime > cutoff:
                        continue
                    relative = path.relative_to(self.root).as_posix()
                    if relative in referenced:
                        continue
                    count += 1
                    if len(paths) < 100:
                        paths.append(relative)
                except FileNotFoundError:
                    continue
        report = {"checked_at": time.time(), "old_unreferenced_files": count, "paths": paths, "action": "retained_for_review"}
        temporary = self.root / ("reconciliation." + self.owner + ".tmp")
        temporary.write_text(json.dumps(report), encoding="utf-8")
        os.replace(temporary, self.root / "reconciliation.json")

    def claim(self):
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            row = self.connection.execute("SELECT * FROM jobs WHERE state='queued' AND cancel_requested=0 AND available_at<=? ORDER BY (kind='cloud_visuals'),(kind='video_frames'),created_at,(kind='extract_source'),id LIMIT 1", (time.time(),)).fetchone()
            if row:
                self.connection.execute("UPDATE jobs SET state='running', stage='Starting', owner=?, attempts=attempts+1, updated_at=? WHERE id=?", (self.owner, time.time(), row["id"]))
            self.connection.commit()
            return dict(row) if row else None
        except BaseException:
            self.connection.rollback()
            raise

    def check(self, job):
        row = self.connection.execute("SELECT cancel_requested,owner,state FROM jobs WHERE id=?", (job["id"],)).fetchone()
        if not row or row["owner"] != self.owner or row["state"] != "running":
            raise Interrupted()
        if row["cancel_requested"]:
            raise Cancelled()
        if self.stop.is_set():
            raise Interrupted()

    def update(self, job, **values):
        values["updated_at"] = time.time()
        fields = ",".join(key + "=?" for key in values)
        self.connection.execute(f"UPDATE jobs SET {fields} WHERE id=? AND owner=? AND state='running'", (*values.values(), job["id"], self.owner))

    def checkpoint(self, job, done, total, stage, checkpoint):
        self.update(job, done=done, total=total, stage=stage, checkpoint_json=json.dumps(checkpoint))

    def queue_automatic_visuals(self, job):
        from .cloud_vision import automatic_enabled
        if not automatic_enabled():
            return
        source = self.connection.execute("""SELECT s.kind,v.filename FROM source_versions v
            JOIN sources s ON s.id=v.source_id WHERE v.id=?""", (job["source_version_id"],)).fetchone()
        if not source or source["kind"] not in ("pdf", "slides", "image"):
            return
        if not self.connection.execute("""SELECT 1 FROM content_units WHERE source_version_id=?
            AND json_array_length(metadata_json,'$.assets')>0 LIMIT 1""", (job["source_version_id"],)).fetchone():
            return
        from .jobs import job_values
        values = job_values(job["workspace_id"], job["subject_id"], job["source_version_id"],
            "cloud_visuals", source["filename"] + " · Automatic Groq", 0,
            {"provider": "groq", "automatic": True, "run_id": str(uuid4())})
        # Called inside extraction completion's transaction. A crash cannot leave
        # a completed local job without its queued fallback. Existing/cancelled
        # cloud jobs are not silently replaced or restarted.
        fields = ",".join(values)
        placeholders = ",".join("?" for _ in values)
        self.connection.execute(f"INSERT INTO jobs ({fields}) VALUES ({placeholders}) ON CONFLICT(kind,source_version_id) DO NOTHING", tuple(values.values()))

    def verify(self, job):
        row = self.connection.execute("SELECT * FROM source_versions WHERE id=?", (job["source_version_id"],)).fetchone()
        if not row:
            raise PermanentFailure("The saved original version is missing.")
        target = (self.root / row["relative_path"]).resolve()
        if not target.is_relative_to((self.root / "originals").resolve()):
            raise PermanentFailure("The original path is outside the material store.")
        if not target.is_file() or target.stat().st_size != row["size_bytes"]:
            raise PermanentFailure("The original is missing or its size changed. Restore the original or import a new version.")
        digest = hashlib.sha256()
        done = 0
        last_write = 0.0
        # hashlib states are not serializable. Restart the hash stage safely.
        self.checkpoint(job, 0, row["size_bytes"], "Checking original bytes", {"bytes_hashed": 0})
        with target.open("rb") as stream:
            while True:
                self.check(job)
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                done += len(chunk)
                if time.monotonic() - last_write >= .2:
                    self.checkpoint(job, done, row["size_bytes"], "Checking original bytes", {"bytes_hashed": done})
                    last_write = time.monotonic()
        if done != row["size_bytes"] or digest.hexdigest() != row["sha256"]:
            raise PermanentFailure("The original failed its integrity check. Restore it or import a new version.")
        self.checkpoint(job, done, done, "Original checked", {"bytes_hashed": done})
        return {"sha256": digest.hexdigest(), "bytes": done, "integrity_verified": True}

    def fixture(self, job):
        if not self.allow_eval:
            raise PermanentFailure("Queue test jobs require explicit evaluation mode.")
        payload = json.loads(job["payload_json"])
        checkpoint = json.loads(job["checkpoint_json"])
        completed = checkpoint.get("completed_steps", [])
        total = payload["steps"]
        for step in range(len(completed), total):
            cpu_deadline = time.monotonic() + payload.get("cpu_ms", 0) / 1000
            scratch = b"Authored queue CPU fixture" * 1000
            while time.monotonic() < cpu_deadline:
                hashlib.sha256(scratch).digest()
                self.check(job)
            deadline = time.monotonic() + payload["delay_ms"] / 1000
            while time.monotonic() < deadline:
                self.check(job)
                self.stop.wait(min(.05, max(0, deadline - time.monotonic())))
            self.check(job)
            if job["failures"] < payload.get("fail_until", 0):
                raise OSError("Injected transient failure in queue evaluation")
            if payload.get("permanent_failure"):
                raise PermanentFailure("Injected permanent failure in queue evaluation")
            completed.append(step)
            self.checkpoint(job, len(completed), total, "Queue test · no course processing", {"completed_steps": completed})
        return {"completed_steps": completed, "evaluation_only": True}

    def execute(self, job):
        try:
            self.check(job)
            if job["kind"] == "verify_original":
                result = self.verify(job)
            elif job["kind"] == "queue_fixture":
                result = self.fixture(job)
            elif job["kind"] == "extract_source":
                from .extraction import extract
                from .resource_guard import ParserGuard
                with ParserGuard(self, job) as guard:
                    result = extract(self, job, guard)
            elif job["kind"] == "cloud_visuals":
                from .cloud_vision import process
                from .resource_guard import ParserGuard
                with ParserGuard(self, job) as guard:
                    result = process(self, job, guard)
            elif job["kind"] == "video_frames":
                from .video_frames import process
                from .resource_guard import ParserGuard
                with ParserGuard(self, job) as guard:
                    result = process(self, job, guard)
            elif job["kind"] == "youtube_import":
                from .youtube import process
                from .resource_guard import ParserGuard
                with ParserGuard(self, job) as guard:
                    result = process(self, job, guard)
            else:
                raise PermanentFailure("No processor is installed for this job type.")
            # Commit completion and cancellation atomically. A racing cancel wins.
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                self.check(job)
                if job["kind"] == "youtube_import":
                    from .youtube import publish
                    result = publish(self, job, result)
                partial = job["kind"] == "extract_source" and (result["counts"]["text"] < result["units"] or result["warnings"] or not result["units"])
                partial = partial or (job["kind"] == "cloud_visuals" and bool(result["needs_review"]))
                partial = partial or (job["kind"] == "video_frames" and (bool(result["omitted_candidates"]) or bool(result["empty_windows"]) or not result["selected_frames"]))
                partial = partial or (job["kind"] == "youtube_import" and bool(result["issue"]))
                self.update(job, state="partial" if partial else "succeeded", stage="Some content needs attention" if partial else "Complete", owner=None, result_json=json.dumps(result), error=None)
                if job["kind"] == "extract_source":
                    self.queue_automatic_visuals(job)
                self.connection.commit()
            except BaseException:
                self.connection.rollback()
                raise
        except Cancelled:
            self.update(job, state="cancelled", stage="Cancelled", owner=None)
        except Interrupted:
            self.update(job, state="queued", stage="Paused for restart", owner=None, recoveries=job["recoveries"] + 1)
        except Deferred as wait:
            self.update(job, state="queued", stage=wait.stage, owner=None, available_at=time.time() + wait.seconds)
        except Exception as error:
            failures = job["failures"] + 1
            permanent = isinstance(error, (PermanentFailure, FileNotFoundError, ValueError, KeyError))
            retry = not permanent and failures < job["max_attempts"]
            self.update(job, state="queued" if retry else "failed", stage="Retry scheduled" if retry else "Needs attention",
                owner=None, failures=failures, error=str(error)[:1000], available_at=time.time() + min(4, .3 * 2 ** (failures - 1)))

    def run(self):
        try:
            self.recover()
            self.audit_orphans()
            while not self.stop.is_set():
                job = self.claim()
                if job:
                    self.execute(job)
                else:
                    self.stop.wait(.1)
        finally:
            self.connection.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--allow-eval", action="store_true")
    args = parser.parse_args()
    stop = threading.Event()
    def parent_pipe():
        import sys
        sys.stdin.buffer.read(1)
        stop.set()
    threading.Thread(target=parent_pipe, daemon=True).start()
    root = Path(args.data_dir)
    while not stop.is_set():
        with exclusive_worker(root) as locked:
            if locked:
                Worker(root, stop, args.allow_eval).run()
                return
        stop.wait(.1)


if __name__ == "__main__":
    main()
