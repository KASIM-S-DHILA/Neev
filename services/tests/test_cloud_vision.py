"""Independent cloud gate. Provider fixtures never send course material."""
import asyncio
import hashlib
import io
import json
import os
import threading
import time
import unittest
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

import httpx
from PIL import Image, ImageDraw
from defusedxml.ElementTree import fromstring

import test_extraction as helpers
from test_storage import BASE, SOURCES
from studylens_service import cloud_vision as vision
from studylens_service.extraction import commit_unit
from studylens_service.job_errors import Cancelled
from studylens_service.slides import native_tables
from studylens_service.visual_assets import save_preview
from studylens_service.worker import Worker

# Copied from the retained Groq vision pilot
# (docs/archive/ingestion-pilots/groq-vision-results.json). It is a real
# provider result, not authored material, so it is never regenerated and never
# edited. Tests must never read from docs/archive/.
PILOT_RESULTS = (
    Path(__file__).resolve().parents[2]
    / "tests/fixtures/ingestion/pilot/groq-vision-results.json"
)

# SHA256 of the parsed JSON re-serialised canonically, NOT of the raw file.
#
# .gitattributes normalises this JSON to LF in the index, so a Windows working
# copy with CRLF and a clean Linux/clone checkout have different bytes. Hashing
# the raw file made this test pass on the authoring machine and fail in a fresh
# clone. Hashing the normalised content is platform-independent and still catches
# any real edit. See DECISIONS D17.
PILOT_CANONICAL_SHA256 = "17fd8d31749f70644122be3960d9be1288f1e6c7712b21bede79fc6a40d915f2"


def pilot_content_sha256() -> str:
    """Hash the pilot result's content, independent of line endings."""
    data = json.loads(PILOT_RESULTS.read_text("utf-8-sig"))
    canonical = json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def read_pilot_results():
    """Load the retained pilot result, failing loudly if it is absent.

    A silently missing fixture would quietly stop the duplicate-rejection check
    from running, which is worse than a hard failure.
    """
    if not PILOT_RESULTS.is_file():
        raise AssertionError(
            "Missing pilot fixture " + str(PILOT_RESULTS) + ". Restore it from "
            "docs/archive/ingestion-pilots/groq-vision-results.json; do not make "
            "this test skip."
        )
    return json.loads(PILOT_RESULTS.read_text("utf-8"))


def output(**changes):
    return {"is_blank": False, "text_lines": ["Authored table"], "tables": [
        {"headers": ["Metric", "Target", "Achieved"], "rows": [["Retention", "75", "80"]], "notes": []}],
        "equations": [], "diagram_nodes": [], "diagram_edges": [], "uncertainties": []} | changes


class CloudTests(unittest.TestCase):
    def setUp(self):
        helpers.ExtractionTests.setUp(self)
        self.direct_workers = []

    def tearDown(self):
        for worker in self.direct_workers:
            worker.connection.close()
        helpers.ExtractionTests.tearDown(self)
    stop = helpers.ExtractionTests.stop
    content = helpers.ExtractionTests.content
    job = helpers.ExtractionTests.job

    def seed(self):
        image = Image.new("RGB", (360, 240), "white")
        image.putpixel((0, 0), (len(self.direct_workers), 0, 0))
        ImageDraw.Draw(image).rectangle((15, 15, 340, 220), outline="black", width=3)
        data = io.BytesIO()
        image.save(data, "PNG")
        response = self.client.post(SOURCES, params={"filename": f"authored-{len(self.direct_workers)}.png"}, content=data.getvalue())
        self.assertEqual(response.status_code, 201)
        version = response.json()["version_id"]
        worker = Worker(self.root, threading.Event())
        self.direct_workers.append(worker)
        # Run real integrity; retain an explicit authored local extraction fixture.
        first = worker.claim()
        self.assertEqual(first["kind"], "verify_original")
        worker.execute(first)
        job = worker.claim()
        self.assertEqual(job["kind"], "extract_source")
        commit_unit(worker, job, 1, 1, "Metric Target Achieved Retention 75 80", {"kind": "image", "page": 1},
            "suspect", "Authored local fixture", "fixture", {"assets": [save_preview(self.root, image, "Authored image")], "text_origin": "ocr"})
        worker.update(job, state="partial", owner=None)
        image.close()
        return worker, version

    def enqueue(self, version, body=None):
        return self.client.post(BASE + f"/source-versions/{version}/cloud-visuals", json=body or {"ordinal": 1})

    def provider(self, data=None, status=200, headers=None, handler=None):
        calls = []
        async def respond(request):
            calls.append(request)
            if handler:
                return await handler(request)
            return httpx.Response(status, headers=headers, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(data or output())}}]})
        original = httpx.AsyncClient
        return calls, patch.object(httpx, "AsyncClient", side_effect=lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(respond)))

    def test_manual_scope_and_supported_provider_are_enforced(self):
        worker, version = self.seed()
        self.assertFalse(any(row["kind"] == "cloud_visuals" for row in self.client.get(BASE + "/jobs").json()))
        with patch.dict(os.environ, {"GROQ_API_KEY": "authored-secret"}):
            for body in ({"consent": False}, {"consent": True}, {"ordinal": 0}, {"provider": "google"}, {"provider": "google", "consent": True}):
                self.assertEqual(self.client.post(BASE + f"/source-versions/{version}/cloud-visuals", json=body).status_code, 422)
            self.assertEqual(self.client.post(f"/workspaces/other/source-versions/{version}/cloud-visuals", json={}).status_code, 404)
            self.assertEqual(self.enqueue(version, {"ordinal": 9}).status_code, 404)
            self.assertEqual(self.client.post(BASE + f"/source-versions/{version}/cloud-visuals", json={}).status_code, 202)
            self.assertEqual(self.enqueue(version).status_code, 409)
            self.assertEqual(self.client.post(BASE + f"/source-versions/{version}/process-visuals").status_code, 409)

    def test_removed_provider_jobs_stop_without_network_or_provider_switch(self):
        worker, version = self.seed()
        before = self.content(version)["units"][0]
        calls, provider = self.provider()
        with patch.dict(os.environ, {"GROQ_API_KEY": "authored-key", "GOOGLE_CLOUD_VISION_API_KEY": "ignored-key"}), provider:
            status = self.client.get("/vision").json()
            self.assertEqual(status["provider"], "groq")
            self.assertNotIn("providers", status)
            self.assertEqual(self.enqueue(version).status_code, 202)
            worker.connection.execute("UPDATE jobs SET payload_json=? WHERE kind='cloud_visuals'", (json.dumps({"provider": "google", "consent": True}),))
            worker.execute(worker.claim())
        self.assertEqual(len(calls), 0)
        cloud = self.job(version, "cloud_visuals")
        self.assertEqual(cloud["state"], "failed")
        self.assertIn("no longer available", cloud["error"])
        self.assertEqual(before, self.content(version)["units"][0])

    def test_missing_key_and_busy_local_processing_do_not_start_cloud(self):
        worker, version = self.seed()
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            self.assertEqual(self.enqueue(version).status_code, 409)
            self.assertFalse(self.client.get("/vision").json()["configured"])
        worker.connection.execute("UPDATE jobs SET state='queued' WHERE kind='extract_source'")
        with patch.dict(os.environ, {"GROQ_API_KEY": "fixture"}):
            self.assertEqual(self.enqueue(version).status_code, 409)

    def test_structured_result_preserves_text_locations_original_and_cache(self):
        worker, version = self.seed()
        before = self.content(version)["units"][0]
        calls, provider = self.provider()
        with patch.dict(os.environ, {"GROQ_API_KEY": "authored-secret"}), provider:
            self.assertEqual(self.enqueue(version).status_code, 202)
            worker.execute(worker.claim())
            self.assertEqual(self.job(version, "cloud_visuals")["state"], "succeeded")
            self.assertEqual(self.enqueue(version).status_code, 202)
            worker.execute(worker.claim())
        self.assertEqual(len(calls), 1)
        request = json.loads(calls[0].content)
        self.assertEqual(str(calls[0].url), vision.ENDPOINT)
        self.assertEqual(request["response_format"], {"type": "json_object"})
        self.assertEqual(request["max_completion_tokens"], 1536)
        after = self.content(version)["units"][0]
        self.assertEqual(before["text"], after["text"])
        self.assertEqual(before["text_sha256"], after["text_sha256"])
        self.assertEqual(before["locator"], after["locator"])
        entry = after["metadata"]["cloud_visuals"][0]
        self.assertFalse(entry["verified"])
        self.assertEqual(entry["source_version_id"], version)
        self.assertEqual(entry["unit_id"], after["id"])
        self.assertEqual(entry["extraction"]["tables"][0]["rows"], [["Retention", "75", "80"]])
        self.assertNotIn("authored-secret", json.dumps(self.content(version)))
        self.assertNotIn("path", after["metadata"]["assets"][0])
        self.assertEqual(self.job(version, "cloud_visuals")["result"]["cached"], 1)

    def test_json_generation_400_resumes_once_with_local_validation(self):
        worker, version = self.seed()
        requests = []
        async def respond(request):
            payload = json.loads(request.content)
            requests.append(payload)
            if len(requests) == 1:
                return httpx.Response(400, json={"error": {"code": "json_validate_failed", "failed_generation": "authored-private-output"}})
            return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(output())}}]})
        calls, provider = self.provider(handler=respond)
        with patch.dict(os.environ, {"GROQ_API_KEY": "fixture"}), provider:
            self.enqueue(version)
            worker.execute(worker.claim())
            job = self.job(version, "cloud_visuals")
            self.assertEqual(job["state"], "queued")
            self.assertEqual(job["stage"], "Retrying visual output")
            self.assertEqual(job["failures"], 0)
            self.assertEqual(len(calls), 1)
            self.assertNotIn("authored-private-output", json.dumps(job))
            # Resume in a fresh worker; the persisted retry mode must survive restart.
            restarted = Worker(self.root, threading.Event())
            self.direct_workers.append(restarted)
            (self.root / "groq-budget.json").write_text('{"next_request_at":0}', encoding="utf-8")
            restarted.connection.execute("UPDATE jobs SET available_at=0 WHERE id=?", (job["id"],))
            restarted.execute(restarted.claim())
        self.assertEqual(len(calls), 2)
        self.assertEqual(requests[0]["response_format"], {"type": "json_object"})
        self.assertNotIn("response_format", requests[1])
        self.assertEqual(requests[1]["max_completion_tokens"], 4096)
        self.assertEqual(self.job(version, "cloud_visuals")["state"], "succeeded")
        entry = self.content(version)["units"][0]["metadata"]["cloud_visuals"][0]
        self.assertEqual(entry["output_mode"], "text_with_local_validation")
        self.assertFalse(entry["verified"])

    def test_repeated_generation_failure_is_partial_not_an_unbounded_retry(self):
        worker, version = self.seed()
        async def respond(_request):
            return httpx.Response(400, json={"error": {"code": "json_validate_failed"}})
        calls, provider = self.provider(handler=respond)
        with patch.dict(os.environ, {"GROQ_API_KEY": "fixture"}), provider:
            self.enqueue(version)
            worker.execute(worker.claim())
            job = self.job(version, "cloud_visuals")
            (self.root / "groq-budget.json").write_text('{"next_request_at":0}', encoding="utf-8")
            worker.connection.execute("UPDATE jobs SET available_at=0 WHERE id=?", (job["id"],))
            worker.execute(worker.claim())
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.job(version, "cloud_visuals")["state"], "partial")
        self.assertIsNone(worker.claim())
        entry = self.content(version)["units"][0]["metadata"]["cloud_visuals"][0]
        self.assertEqual(entry["status"], "needs_review")
        self.assertNotIn("extraction", entry)

    def test_invalid_fallback_output_is_never_saved_as_transcription(self):
        worker, version = self.seed()
        async def respond(request):
            if "response_format" in json.loads(request.content):
                return httpx.Response(400, json={"error": {"code": "json_validate_failed"}})
            return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": '{"text":"invented wrong shape"}'}}]})
        calls, provider = self.provider(handler=respond)
        with patch.dict(os.environ, {"GROQ_API_KEY": "fixture"}), provider:
            self.enqueue(version)
            worker.execute(worker.claim())
            job = self.job(version, "cloud_visuals")
            (self.root / "groq-budget.json").write_text('{"next_request_at":0}', encoding="utf-8")
            worker.connection.execute("UPDATE jobs SET available_at=0 WHERE id=?", (job["id"],))
            worker.execute(worker.claim())
        self.assertEqual(self.job(version, "cloud_visuals")["state"], "partial")
        self.assertNotIn("invented wrong shape", json.dumps(self.content(version)))

    def test_other_400_errors_do_not_resend_or_echo_provider_body(self):
        worker, version = self.seed()
        async def respond(_request):
            return httpx.Response(400, json={"error": {"code": "invalid_parameter", "param": "reasoning_effort",
                "message": "authored-secret with private source data", "failed_generation": "private response"}})
        calls, provider = self.provider(handler=respond)
        with patch.dict(os.environ, {"GROQ_API_KEY": "authored-secret"}), provider:
            self.enqueue(version)
            worker.execute(worker.claim())
        job = self.job(version, "cloud_visuals")
        self.assertEqual(len(calls), 1)
        self.assertEqual(job["state"], "failed")
        self.assertIn("reasoning_effort", job["error"])
        self.assertNotIn("authored-secret", json.dumps(job))
        self.assertNotIn("private", json.dumps(job))

    def test_quota_wait_releases_worker_and_is_cancellable_without_failure(self):
        worker, version = self.seed()
        calls, provider = self.provider(status=429, headers={"retry-after": "90"})
        with patch.dict(os.environ, {"GROQ_API_KEY": "fixture"}), provider:
            self.enqueue(version)
            started = time.monotonic()
            worker.execute(worker.claim())
        self.assertLess(time.monotonic() - started, 3)
        job = self.job(version, "cloud_visuals")
        self.assertEqual(job["state"], "queued")
        self.assertEqual(job["stage"], "Waiting for Groq quota")
        self.assertEqual(job["failures"], 0)
        self.assertIsNone(worker.claim())
        self.assertEqual(len(calls), 1)
        # Another local import is claimable while this provider is waiting.
        self.client.post(SOURCES, params={"filename": "other.txt"}, content=b"Local work continues")
        self.assertEqual(worker.claim()["kind"], "verify_original")
        self.client.post(BASE + f"/jobs/{job['id']}/cancel")
        self.assertEqual(self.job(version, "cloud_visuals")["state"], "cancelled")

    def test_resume_after_spacing_counts_saved_calls_once(self):
        worker, version = self.seed()
        first = worker.connection.execute("SELECT * FROM content_units WHERE source_version_id=?", (version,)).fetchone()
        metadata = json.loads(first["metadata_json"])
        metadata["non_table_graphics"] = True
        worker.connection.execute("UPDATE content_units SET metadata_json=? WHERE id=?", (json.dumps(metadata), first["id"]))
        # Explicit two-unit scheduling fixture, not a claim about PNG page extraction.
        image = Image.new("RGB", (360, 240), "black")
        second_metadata = {"assets": [save_preview(self.root, image, "Second authored unit")], "non_table_graphics": True}
        image.close()
        worker.connection.execute("""INSERT INTO content_units
            (id,source_version_id,job_id,ordinal,locator_json,text,text_sha256,status,warning,engine,metadata_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (str(uuid4()), version, first["job_id"], 2, json.dumps({"kind": "image", "page": 2}),
            first["text"], first["text_sha256"], "suspect", "Authored scheduling fixture", "fixture", json.dumps(second_metadata)))
        calls, provider = self.provider()
        with patch.dict(os.environ, {"GROQ_API_KEY": "fixture"}), provider:
            self.enqueue(version, {"provider": "groq"})
            worker.execute(worker.claim())
            self.assertEqual(len(calls), 1)
            job = self.job(version, "cloud_visuals")
            self.assertEqual(job["state"], "queued")
            (self.root / "groq-budget.json").write_text('{"next_request_at":0}', encoding="utf-8")
            worker.connection.execute("UPDATE jobs SET available_at=0 WHERE id=?", (job["id"],))
            worker.execute(worker.claim())
        self.assertEqual(len(calls), 2)
        result = self.job(version, "cloud_visuals")["result"]
        self.assertEqual(result["sent"], 2)
        self.assertEqual(result["cached"], 0)

    def test_running_request_cancels_promptly_and_saves_no_response(self):
        worker, version = self.seed()
        async def respond(_request):
            worker.connection.execute("UPDATE jobs SET cancel_requested=1 WHERE kind='cloud_visuals'")
            await asyncio.sleep(10)
            return httpx.Response(200)
        calls, provider = self.provider(handler=respond)
        with patch.dict(os.environ, {"GROQ_API_KEY": "fixture"}), provider:
            self.enqueue(version)
            started = time.monotonic()
            worker.execute(worker.claim())
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual(self.job(version, "cloud_visuals")["state"], "cancelled")
        self.assertNotIn("cloud_visuals", self.content(version)["units"][0]["metadata"])

    def test_invalid_tables_fail_review_without_replacing_local_text(self):
        worker, version = self.seed()
        invalid = output()
        invalid["tables"].append(invalid["tables"][0])
        calls, provider = self.provider(invalid)
        with patch.dict(os.environ, {"GROQ_API_KEY": "fixture"}), provider:
            self.enqueue(version)
            worker.execute(worker.claim())
        self.assertEqual(self.job(version, "cloud_visuals")["state"], "partial")
        unit = self.content(version)["units"][0]
        self.assertIn("Retention 75 80", unit["text"])
        entry = unit["metadata"]["cloud_visuals"][0]
        self.assertEqual(entry["status"], "needs_review")
        self.assertNotIn("extraction", entry)

    def test_corrupt_preview_and_original_prevent_network(self):
        for original in (False, True):
            with self.subTest(original=original):
                worker, version = self.seed()
                row = worker.connection.execute("SELECT * FROM source_versions WHERE id=?", (version,)).fetchone()
                metadata = json.loads(worker.connection.execute("SELECT metadata_json FROM content_units WHERE source_version_id=?", (version,)).fetchone()[0])
                target = self.root / (row["relative_path"] if original else metadata["assets"][0]["path"])
                saved = target.read_bytes()
                target.write_bytes(b"damaged")
                calls, provider = self.provider()
                with patch.dict(os.environ, {"GROQ_API_KEY": "fixture"}), provider:
                    self.enqueue(version)
                    worker.execute(worker.claim())
                self.assertEqual(len(calls), 0)
                self.assertEqual(self.job(version, "cloud_visuals")["state"], "failed")
                target.write_bytes(saved)

    def test_local_rebuild_invalidates_cloud_output_and_job(self):
        worker, version = self.seed()
        calls, provider = self.provider()
        with patch.dict(os.environ, {"GROQ_API_KEY": "fixture"}), provider:
            self.enqueue(version)
            worker.execute(worker.claim())
        self.assertEqual(self.client.post(BASE + f"/source-versions/{version}/process-visuals").status_code, 202)
        content = self.content(version)
        self.assertEqual(content["units"], [])
        self.assertIsNone(content["cloud_job"])


class ShapeAndRoutingTests(unittest.TestCase):
    def test_single_json_fence_is_cosmetic_but_prose_and_fragments_are_rejected(self):
        raw = json.dumps(output())
        for wrapped in ("```json\n" + raw + "\n```", "```\r\n" + raw + "\r\n```"):
            self.assertEqual(vision.validate_output(wrapped), output())
        for invalid in ("Here is the JSON:\n" + raw, raw + "\nExtra text",
                        "```json\n" + raw + "\n```\nExtra text", "```json\n" + raw[:-1] + "\n```",
                        "```json\n" + raw + "\n```\n```json\n" + raw + "\n```"):
            with self.assertRaises(ValueError):
                vision.validate_output(invalid)

    def test_retained_initial_pilot_partial_duplicates_are_rejected(self):
        report = read_pilot_results()
        table = next(sample["extraction"] for sample in report["samples"] if sample["sample"] == "table-slide-12")
        with self.assertRaises(ValueError):
            vision.validate_output(json.dumps(table))

    def test_pilot_fixture_is_present_and_matches_the_retained_original(self):
        # Guards the guard: if this fixture is ever deleted or edited, say so
        # loudly instead of letting the duplicate-rejection test read a
        # different file or silently stop running.
        self.assertTrue(
            PILOT_RESULTS.is_file(),
            "pilot fixture is missing at " + str(PILOT_RESULTS),
        )
        self.assertEqual(
            pilot_content_sha256(),
            PILOT_CANONICAL_SHA256,
            "pilot fixture content changed; restore it from "
            "docs/archive/ingestion-pilots/groq-vision-results.json",
        )
        report = read_pilot_results()
        self.assertIn("samples", report)
        self.assertTrue(
            any(sample["sample"] == "table-slide-12" for sample in report["samples"]),
            "pilot fixture no longer contains the table-slide-12 sample",
        )

    def test_shape_rejects_ragged_dangling_blank_contradiction_and_unknown_fields(self):
        for value in (output(tables=[{"headers": ["a", "b"], "rows": [["1"]], "notes": []}]),
            output(diagram_edges=[{"from": "missing", "to": "node", "label": ""}]),
            output(is_blank=True), output(extra="field")):
            with self.assertRaises(ValueError):
                vision.validate_output(json.dumps(value))
        self.assertEqual(vision.validate_output(json.dumps(output())), output())

    def test_exact_white_only_and_native_table_and_manual_override(self):
        image = Image.new("RGB", (200, 200), "white")
        self.addCleanup(image.close)
        self.assertEqual(vision.route(image, "", {})["decision"], "local")
        image.putpixel((10, 10), (254, 254, 254))
        self.assertEqual(vision.route(image, "", {})["decision"], "cloud")
        metadata = {"native_tables": [{"notes": [], "rows": [["75", "80"]]}]}
        self.assertEqual(vision.route(image, "75 80", metadata)["decision"], "local")
        self.assertEqual(vision.route(image, "75 80", metadata, True)["decision"], "cloud")
        metadata["non_table_graphics"] = True
        self.assertEqual(vision.route(image, "75 80", metadata)["decision"], "cloud")

    def test_native_table_preserves_grid_decimals_and_empty_cells(self):
        xml = '<root xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:tbl><a:tr><a:tc><a:txBody><a:p><a:r><a:t>Rating</a:t></a:r></a:p></a:txBody></a:tc><a:tc><a:txBody><a:p/></a:txBody></a:tc></a:tr><a:tr><a:tc><a:txBody><a:p><a:r><a:t>4.2</a:t></a:r></a:p></a:txBody></a:tc><a:tc><a:txBody><a:p><a:r><a:t>4.5</a:t></a:r></a:p></a:txBody></a:tc></a:tr></a:tbl></root>'
        self.assertEqual(native_tables(fromstring(xml)), [{"headers": [], "rows": [["Rating", ""], ["4.2", "4.5"]], "notes": []}])

    def test_rate_header_duration_units(self):
        self.assertEqual(vision.duration("1m2.5s"), 62.5)
        self.assertEqual(vision.duration("100ms"), .1)
        self.assertEqual(vision.duration("invalid"), 65)


if __name__ == "__main__":
    unittest.main()
