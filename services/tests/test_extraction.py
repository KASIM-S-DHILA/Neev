import hashlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from contextlib import closing
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject
from studylens_service.api import create_app
from studylens_service.extraction import text_chunks
from test_storage import AUTH, BASE, SESSION, SOURCES, TOKEN

FIXTURES = Path(__file__).resolve().parents[2] / "tests/fixtures/ingestion/phase-04"


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        # Extraction tests must never inherit real cloud credentials. Cloud tests
        # explicitly supply authored keys with a mock HTTP transport.
        cloud_environment = patch.dict(os.environ, {"GROQ_API_KEY": "", "STUDYLENS_AUTO_VIDEO_FRAMES": "0"})
        cloud_environment.start()
        self.addCleanup(cloud_environment.stop)
        self.directory = tempfile.TemporaryDirectory(prefix="studylens-extraction-")
        self.root = Path(self.directory.name)
        self.workers = []
        self.client = TestClient(create_app(self.root, TOKEN), headers=AUTH)
        self.client.__enter__()
        self.assertEqual(self.client.put(BASE + "/session", json={"base_revision": 0, "session": SESSION}).status_code, 200)

    def tearDown(self):
        for process in self.workers:
            self.stop(process)
        self.client.__exit__(None, None, None)
        self.directory.cleanup()

    def start(self, mode=None):
        args = [sys.executable]
        args += [str(Path(__file__).with_name("worker_fixture.py")), mode] if mode else ["-m", "studylens_service.worker"]
        args += ["--data-dir", str(self.root)]
        process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            **({"creationflags": 0x08000000} if os.name == "nt" else {}))
        self.workers.append(process)
        return process

    def stop(self, process, abrupt=False):
        if process.poll() is None:
            if abrupt:
                process.kill()
            else:
                process.stdin.close()
            process.wait(timeout=5)
        if not process.stdin.closed:
            process.stdin.close()
        if not process.stderr.closed:
            self.assertEqual(process.stderr.read().decode(), "")
            process.stderr.close()

    def upload(self, name="digital-notes.pdf", data=None, source_id=None):
        response = self.client.post(SOURCES, params={"filename": name, **({"source_id": source_id} if source_id else {})},
            content=(FIXTURES / name).read_bytes() if data is None else data)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def job(self, version_id, kind="extract_source"):
        return next(row for row in self.client.get(BASE + "/jobs?limit=100").json() if row["source_version_id"] == version_id and row["kind"] == kind)

    def wait(self, version_id, predicate=lambda row: row["state"] in ("succeeded", "partial", "failed", "cancelled")):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            row = self.job(version_id)
            if predicate(row):
                return row
            time.sleep(.02)
        self.fail(f"Extraction condition timed out: {self.job(version_id)}")

    def content(self, version_id, offset=0, limit=10):
        response = self.client.get(BASE + f"/source-versions/{version_id}/content", params={"offset": offset, "limit": limit})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_reviewed_pdf_gold_locations_and_immutable_original(self):
        original = self.upload()
        self.start()
        complete = self.wait(original["version_id"])
        self.assertEqual(complete["state"], "succeeded", complete)
        self.assertEqual(complete["result"]["counts"]["text"], 3)
        content = self.content(original["version_id"])
        self.assertTrue(content["integrity_verified"])
        gold = json.loads((FIXTURES / "gold.json").read_text(encoding="utf-8"))
        for question in gold["questions"][:3]:
            unit = content["units"][question["page"] - 1]
            self.assertEqual(unit["locator"]["page"], question["page"])
            self.assertIn(question["needle"], unit["text"])
            self.assertEqual(unit["text_sha256"], hashlib.sha256(unit["text"].encode()).hexdigest())
        self.assertEqual(self.client.get("/source-versions/" + original["version_id"] + "/file").content, (FIXTURES / "digital-notes.pdf").read_bytes())
        versions = self.client.get(SOURCES).json()[0]["versions"]
        self.assertEqual(versions[0]["extraction"]["state"], "succeeded")

    def test_mixed_pdf_preserves_text_scan_and_blank_locations(self):
        original = self.upload("mixed-notes.pdf")
        self.start()
        complete = self.wait(original["version_id"])
        self.assertEqual(complete["state"], "partial", complete)
        units = self.content(original["version_id"])["units"]
        self.assertEqual([unit["status"] for unit in units], ["text", "suspect", "empty"])
        self.assertEqual([unit["locator"]["page"] for unit in units], [1, 2, 3])
        self.assertTrue(units[1]["text"])
        self.assertTrue(units[1]["metadata"]["ocr"]["review_required"])
        self.assertIn("OCR", units[1]["warning"])

    def test_encrypted_pdf_fails_once_and_preserves_original(self):
        original = self.upload("encrypted-notes.pdf")
        self.start()
        failed = self.wait(original["version_id"])
        self.assertEqual(failed["state"], "failed", failed)
        self.assertIn("encrypted", failed["error"])
        self.assertEqual(failed["attempts"], 1)
        self.assertEqual(self.content(original["version_id"])["units"], [])
        self.assertEqual(self.client.get("/source-versions/" + original["version_id"] + "/file").status_code, 200)

    def test_corrupt_pdf_is_not_marked_extracted(self):
        original = self.upload("corrupt-notes.pdf")
        self.start()
        failed = self.wait(original["version_id"])
        self.assertEqual(failed["state"], "failed", failed)
        self.assertEqual(failed["attempts"], 1)
        self.assertIn("corrupt", failed["error"])
        self.assertEqual(self.content(original["version_id"])["units"], [])

    def test_mixed_language_utf16_has_exact_decoded_offsets(self):
        original = self.upload("mixed-language.txt")
        self.start()
        self.assertEqual(self.wait(original["version_id"])["state"], "succeeded")
        unit = self.content(original["version_id"])["units"][0]
        expected = (FIXTURES / "mixed-language.txt").read_bytes().decode("utf-16")
        self.assertEqual(unit["text"], expected)
        self.assertEqual(unit["locator"], {"kind": "lines", "line_start": 1, "line_end": 3,
            "char_start": 0, "char_end": len(expected), "encoding": "utf-16"})

    def test_long_lines_crlf_chunk_boundaries_do_not_drop_or_relabel_text(self):
        value = "A" * 3999 + "\r\n" + "B" * 8001 + "\nfinal line"
        chunks = list(text_chunks(value))
        self.assertEqual("".join(text for text, _ in chunks), value)
        for text, locator in chunks:
            self.assertLessEqual(len(text), 4000)
            self.assertEqual(value[locator["char_start"]:locator["char_end"]], text)
        self.assertEqual(chunks[-1][1]["line_end"], 3)
        self.assertEqual(chunks[0][1]["line_end"], 1)

    def test_invalid_encoding_and_binary_text_decline_without_guessed_content(self):
        first = self.upload("encoding.txt", b"\xffnot utf8")
        second = self.upload("binary.txt", b"binary\x00bytes")
        self.start()
        for original in (first, second):
            failed = self.wait(original["version_id"])
            self.assertEqual(failed["state"], "failed")
            self.assertEqual(failed["attempts"], 1)
            self.assertEqual(self.content(original["version_id"])["units"], [])

    def test_duplicate_and_new_version_units_are_isolated_and_scope_checked(self):
        original = self.upload()
        self.assertTrue(self.upload()["duplicate"])
        writer = PdfWriter()
        writer.append(PdfReader(FIXTURES / "digital-notes.pdf"), pages=(0, 2))
        buffer = io.BytesIO()
        writer.write(buffer)
        second = self.upload("digital-notes.pdf", buffer.getvalue(), original["source_id"])
        self.start()
        self.wait(original["version_id"])
        self.wait(second["version_id"])
        first_units = self.content(original["version_id"])["units"]
        second_units = self.content(second["version_id"])["units"]
        self.assertEqual(len(first_units), 3)
        self.assertEqual(len(second_units), 2)
        self.assertNotEqual(first_units[0]["id"], second_units[0]["id"])
        other = self.client.post("/workspaces", json={"name": "Other"}).json()["id"]
        self.assertEqual(self.client.get(f"/workspaces/{other}/source-versions/{original['version_id']}/content").status_code, 404)
        self.assertEqual(len([row for row in self.client.get(BASE + "/jobs").json() if row["kind"] == "extract_source"]), 2)

    def test_running_cancel_and_resume_retains_stable_units(self):
        original = self.upload()
        process = self.start("slow-units")
        row = self.wait(original["version_id"], lambda job: job["done"] >= 1)
        saved = self.content(original["version_id"])["units"][0]
        self.client.post(BASE + "/jobs/" + row["id"] + "/cancel")
        self.assertEqual(self.wait(original["version_id"])["state"], "cancelled")
        self.stop(process)
        self.client.post(BASE + "/jobs/" + row["id"] + "/retry")
        self.start()
        self.assertEqual(self.wait(original["version_id"])["state"], "succeeded")
        units = self.content(original["version_id"])["units"]
        self.assertEqual(len(units), 3)
        self.assertEqual(units[0], saved)

    def test_killed_pdf_worker_recovers_without_replacing_completed_unit(self):
        original = self.upload()
        process = self.start("slow-units")
        row = self.wait(original["version_id"], lambda job: job["done"] >= 1)
        saved = self.content(original["version_id"])["units"][0]
        self.stop(process, abrupt=True)
        self.start()
        complete = self.wait(original["version_id"])
        self.assertEqual(complete["state"], "succeeded")
        self.assertEqual(complete["recoveries"], 1)
        units = self.content(original["version_id"])["units"]
        self.assertEqual(len(units), 3)
        self.assertEqual(units[0], saved)

    def test_stalled_parser_cancellation_recycles_and_api_remains_responsive(self):
        original = self.upload()
        process = self.start("stall-parser")
        row = self.wait(original["version_id"], lambda job: job["state"] == "running" and job["stage"] == "Extracting source text")
        start = time.monotonic()
        for _ in range(5):
            self.assertEqual(self.client.get("/health").status_code, 200)
            self.assertEqual(self.client.get(BASE + "/session").status_code, 200)
        self.assertLess(time.monotonic() - start, 2)
        self.client.post(BASE + "/jobs/" + row["id"] + "/cancel")
        cancelled = self.wait(original["version_id"])
        self.assertEqual(cancelled["state"], "cancelled", cancelled)
        process.wait(timeout=3)
        self.assertEqual(process.returncode, 75)

    def test_parser_timeout_and_memory_budget_abort_without_fake_success(self):
        for mode, text in (("timeout", "limit"), ("memory", "budget")):
            original = self.upload(mode + ".pdf", (FIXTURES / "digital-notes.pdf").read_bytes())
            process = self.start(mode)
            failed = self.wait(original["version_id"])
            self.assertEqual(failed["state"], "failed", failed)
            self.assertIn(text, failed["error"])
            process.wait(timeout=3)
            self.assertEqual(process.returncode, 75)

    def test_pdf_page_stream_limit_is_partial_and_has_no_truncated_evidence(self):
        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        stream = DecodedStreamObject()
        stream.set_data(b" " * (1024**2 + 1))
        page[NameObject("/Contents")] = writer._add_object(stream)
        buffer = io.BytesIO()
        writer.write(buffer)
        original = self.upload("dense.pdf", buffer.getvalue())
        self.start()
        partial = self.wait(original["version_id"])
        self.assertEqual(partial["state"], "partial", partial)
        unit = self.content(original["version_id"])["units"][0]
        self.assertEqual(unit["status"], "too_large")
        self.assertEqual(unit["text"], "")

    def test_saved_oversize_originals_decline_extraction_before_parsing(self):
        self.start()
        for filename, size, message in (("large.txt", 16 * 1024**2 + 1, "16 MB"), ("large.pdf", 64 * 1024**2 + 1, "64 MB")):
            original = self.upload(filename, b" " * size)
            failed = self.wait(original["version_id"])
            self.assertEqual(failed["state"], "failed", failed)
            self.assertIn(message, failed["error"])
            self.assertEqual(failed["attempts"], 1)
            self.assertEqual(self.content(original["version_id"])["units"], [])

    def test_deliberate_parser_recycle_does_not_exhaust_supervisor_budget(self):
        import asyncio
        real_spawn = asyncio.create_subprocess_exec
        spawns = 0
        async def injected_spawn(*args, **kwargs):
            nonlocal spawns
            spawns += 1
            if spawns == 1:
                args = (args[0], str(Path(__file__).with_name("worker_fixture.py")), "timeout", *args[3:])
            return await real_spawn(*args, **kwargs)
        self.client.__exit__(None, None, None)
        with patch("studylens_service.supervisor.asyncio.create_subprocess_exec", side_effect=injected_spawn):
            self.client = TestClient(create_app(self.root, TOKEN, start_worker=True), headers=AUTH)
            self.client.__enter__()
            original = self.upload()
            self.assertEqual(self.wait(original["version_id"])["state"], "failed")
            following = self.upload("next.txt", b"Authored next job after a parser recycle")
            self.assertEqual(self.wait(following["version_id"])["state"], "succeeded")
            status = self.client.get("/queue").json()
            self.assertTrue(status["available"])
            self.assertEqual(status["restarts"], 0)
            self.assertIsNone(status["error"])
            self.assertEqual(spawns, 2)

    def test_page_count_limit_and_content_pagination_bounds(self):
        writer = PdfWriter()
        for _ in range(501):
            writer.add_blank_page(width=612, height=792)
        buffer = io.BytesIO()
        writer.write(buffer)
        original = self.upload("long.pdf", buffer.getvalue())
        self.start()
        failed = self.wait(original["version_id"])
        self.assertEqual(failed["state"], "failed")
        self.assertIn("500 pages", failed["error"])
        for query in ("offset=-1", "limit=11", "offset=10001"):
            self.assertEqual(self.client.get(BASE + f"/source-versions/{original['version_id']}/content?" + query).status_code, 422)

    def test_phase_three_upgrade_preserves_original_and_backfills_extraction(self):
        original = self.upload()
        before = self.client.get(BASE + "/session").json()
        self.client.__exit__(None, None, None)
        with closing(sqlite3.connect(self.root / "studylens.sqlite3")) as connection:
            connection.execute("DROP TABLE youtube_media_links")
            connection.execute("DROP TABLE content_units")
            connection.execute("DELETE FROM jobs WHERE kind='extract_source'")
            connection.execute("UPDATE alembic_version SET version_num='0002_background_jobs'")
            connection.commit()
        self.client = TestClient(create_app(self.root, TOKEN), headers=AUTH)
        self.client.__enter__()
        self.assertEqual(self.client.get(BASE + "/session").json(), before)
        self.assertEqual(self.client.get("/health").json()["schema_version"], "0005_youtube_media_links")
        self.start()
        self.assertEqual(self.wait(original["version_id"])["state"], "succeeded")
        self.assertEqual(self.client.get("/source-versions/" + original["version_id"] + "/file").content, (FIXTURES / "digital-notes.pdf").read_bytes())

    def test_malformed_video_never_claims_text_extraction(self):
        original = self.upload("lecture.mp4", b"Authored malformed video fixture")
        self.start()
        self.assertEqual(self.wait(original["version_id"])["state"], "failed")
        content = self.content(original["version_id"])
        self.assertEqual(content["state"], "failed")
        self.assertEqual(content["units"], [])
        self.assertEqual(self.client.get("/source-versions/" + original["version_id"] + "/file").status_code, 200)
