"""Independent Phase 5 gate: real CPU OCR plus explicit provider/fault fixtures."""
import base64
import io
import json
import os
import sqlite3
import struct
import time
import unittest
import zipfile
import zlib
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from fastapi.testclient import TestClient
import test_extraction as helpers
from test_storage import AUTH, BASE, SOURCES, TOKEN
from studylens_service.api import create_app
from studylens_service.visual import visual_notes

FIXTURES = Path(__file__).resolve().parents[2] / "docs/evaluation/fixtures/phase-05"


class VisualTests(unittest.TestCase):
    setUp = helpers.ExtractionTests.setUp
    tearDown = helpers.ExtractionTests.tearDown
    start = helpers.ExtractionTests.start
    stop = helpers.ExtractionTests.stop
    job = helpers.ExtractionTests.job
    wait = helpers.ExtractionTests.wait
    content = helpers.ExtractionTests.content

    def upload(self, name, data=None):
        response = self.client.post(SOURCES, params={"filename": name}, content=(FIXTURES / name).read_bytes() if data is None else data)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_real_image_ocr_confidence_boxes_original_and_preview(self):
        original = self.upload("scan.png")
        self.start()
        self.assertEqual(self.wait(original["version_id"])["state"], "partial")
        unit = self.content(original["version_id"])["units"][0]
        self.assertEqual(unit["status"], "suspect")
        self.assertIn("100 outcomes", unit["text"])
        self.assertTrue(unit["metadata"]["review_required"])
        result = unit["metadata"]["ocr"]
        self.assertTrue(result["words"])
        self.assertEqual(result["language"], "eng")
        for word in result["words"]:
            left, top, width, height = word["box"]
            self.assertGreaterEqual(left, 0)
            self.assertLessEqual(left + width, result["width"])
            self.assertLessEqual(top + height, result["height"])
        preview = unit["metadata"]["assets"][0]
        self.assertNotIn("path", preview)
        self.assertTrue(preview["data_url"].startswith("data:image/png;base64,"))
        self.assertEqual(self.client.get("/source-versions/" + original["version_id"] + "/file").content, (FIXTURES / "scan.png").read_bytes())

    def test_exif_rotation_keeps_upright_ocr_and_original_unchanged(self):
        original = self.upload("oriented-scan.jpg")
        self.start()
        self.wait(original["version_id"])
        unit = self.content(original["version_id"])["units"][0]
        self.assertIn("100 outcomes", unit["text"])
        self.assertEqual(unit["metadata"]["ocr"]["width"], 1500)
        self.assertEqual(unit["metadata"]["ocr"]["height"], 1000)
        self.assertEqual(unit["metadata"]["original_width"], 1000)

    def test_multi_page_tiff_has_distinct_locations_and_stable_resume(self):
        original = self.upload("two-pages.tiff")
        self.start()
        self.wait(original["version_id"])
        units = self.content(original["version_id"])["units"]
        self.assertEqual([unit["locator"] for unit in units], [{"kind": "image", "page": 1}, {"kind": "image", "page": 2}])
        self.assertIn("100 outcomes", units[0]["text"])
        self.assertIn("Heads", units[1]["text"])
        self.assertNotEqual(units[0]["id"], units[1]["id"])

    def test_scanned_pdf_figure_equation_preserve_pages_without_math_claim(self):
        original = self.upload("scanned-visuals.pdf")
        self.start()
        complete = self.wait(original["version_id"])
        self.assertEqual(complete["state"], "partial")
        units = self.content(original["version_id"])["units"]
        self.assertEqual([unit["locator"]["page"] for unit in units], [1, 2, 3])
        self.assertIn("100 outcomes", units[0]["text"])
        self.assertIn("Heads", units[1]["text"])
        for unit in units:
            self.assertEqual(unit["status"], "suspect")
            self.assertTrue(unit["metadata"]["assets"])
            self.assertEqual(unit["metadata"]["text_origin"], "ocr")
            self.assertIn("equations", unit["warning"])

    def test_slide_order_native_text_picture_ocr_equation_and_no_external_fetch(self):
        original = self.upload("ordered-visuals.pptx")
        self.start()
        self.assertEqual(self.wait(original["version_id"])["state"], "partial")
        units = self.content(original["version_id"])["units"]
        self.assertIn("First slide", units[0]["text"])
        self.assertIn("Second slide", units[1]["text"])
        self.assertEqual([unit["locator"]["slide"] for unit in units], [1, 2])
        self.assertEqual(units[0]["metadata"]["slide_part"], "ppt/slides/slide2.xml")
        self.assertTrue(units[0]["metadata"]["external_links_ignored"])
        self.assertIn("Heads", units[0]["metadata"]["image_text"][0]["text"])
        self.assertNotIn("Heads", units[0]["text"])
        self.assertIn("Embedded images", units[0]["warning"])
        self.assertIn("P(B)", units[1]["metadata"]["equations"][0])
        preview = units[1]["metadata"]["equation_previews"][0]
        self.assertEqual(preview["children"][0]["kind"], "fraction")
        self.assertIn("P(B)", json.dumps(preview["children"][0]["children"][1]))
        self.assertNotIn("P(B)", units[1]["text"])
        self.assertIn("Fractions", units[1]["warning"])

    def test_missing_ocr_keeps_visual_with_actionable_warning(self):
        original = self.upload("scan.png")
        with patch.dict(os.environ, {"STUDYLENS_TESSERACT": str(self.root / "missing.exe")}):
            self.start()
        self.assertEqual(self.wait(original["version_id"])["state"], "partial")
        unit = self.content(original["version_id"])["units"][0]
        self.assertEqual(unit["text"], "")
        self.assertEqual(unit["status"], "needs_ocr")
        self.assertIn("Install Tesseract", unit["warning"])
        self.assertTrue(unit["metadata"]["assets"])
        for process in self.workers:
            self.stop(process)
        self.client.post(BASE + f"/source-versions/{original['version_id']}/process-visuals")
        with patch.dict(os.environ, {"STUDYLENS_OCR_LANG": "eng+missing_language_fixture"}):
            self.start()
        self.assertEqual(self.wait(original["version_id"])["state"], "partial")
        unit = self.content(original["version_id"])["units"][0]
        self.assertEqual(unit["text"], "")
        self.assertIn("language data", unit["warning"])
        self.assertTrue(unit["metadata"]["assets"])

    def test_corrupt_and_huge_dimension_images_fail_without_claimed_text(self):
        header = struct.pack(">IIBBBBB", 50000, 50000, 8, 2, 0, 0, 0)
        huge = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", len(header)) + b"IHDR" + header + struct.pack(">I", zlib.crc32(b"IHDR" + header))
        originals = [self.upload("corrupt.png"), self.upload("huge.png", huge)]
        self.start()
        for original in originals:
            failed = self.wait(original["version_id"])
            self.assertEqual(failed["state"], "failed")
            self.assertEqual(failed["attempts"], 1)
            self.assertEqual(self.content(original["version_id"])["units"], [])

    def test_blank_and_animated_images_do_not_invent_text(self):
        blank = self.upload("blank.png")
        image = Image.new("RGB", (30, 30), "white")
        second = Image.new("RGB", (30, 30), "black")
        buffer = io.BytesIO()
        image.save(buffer, format="WEBP", save_all=True, append_images=[second], duration=100)
        animated = self.upload("animated.webp", buffer.getvalue())
        image.close()
        second.close()
        self.start()
        self.assertEqual(self.wait(blank["version_id"])["state"], "partial")
        self.assertEqual(self.content(blank["version_id"])["units"][0]["text"], "")
        self.assertEqual(self.wait(animated["version_id"])["state"], "failed")

    def test_unsafe_xml_zip_limits_and_corrupt_slides_are_refused(self):
        def package(parts):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                for name, value in parts.items():
                    archive.writestr(name, value)
            return buffer.getvalue()
        unsafe = package({"ppt/presentation.xml": '<!DOCTYPE x [<!ENTITY a SYSTEM "file:///C:/Windows/win.ini">]><x>&a;</x>'})
        large = package({"ppt/presentation.xml": "x" * (10 * 1024**2 + 1)})
        originals = [self.upload("unsafe.pptx", unsafe), self.upload("oversize.pptx", large), self.upload("bad.pptx", b"Invalid authored ZIP")]
        self.start()
        for original in originals:
            self.assertEqual(self.wait(original["version_id"])["state"], "failed")
            self.assertEqual(self.content(original["version_id"])["units"], [])

    def test_legacy_ppt_retained_with_export_instruction(self):
        original = self.upload("legacy.ppt", b"Authored unsupported legacy container")
        self.start()
        failed = self.wait(original["version_id"])
        self.assertEqual(failed["state"], "failed")
        self.assertIn("Export to PPTX/PDF", failed["error"])
        self.assertEqual(self.client.get("/source-versions/" + original["version_id"] + "/file").status_code, 200)

    def test_office_adapter_fixture_and_page_count_mismatch_withhold_bad_citations(self):
        # Remove the deliberate external-link relationship so conversion is eligible.
        buffer = io.BytesIO()
        with zipfile.ZipFile(FIXTURES / "ordered-visuals.pptx") as source, zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as target:
            for name in source.namelist():
                value = source.read(name)
                if name.endswith("slide2.xml.rels"):
                    value = value.decode().split('<Relationship Id="external1"')[0] + '</Relationships>'
                target.writestr(name, value)
        original = self.upload("office-contract.pptx", buffer.getvalue())
        process = self.start("office-good")
        self.wait(original["version_id"])
        unit = self.content(original["version_id"])["units"][0]
        self.assertIn("LibreOffice rendering", unit["metadata"]["assets"][0]["caption"])
        command = json.loads((self.root / "office-fixture-command.json").read_text())
        self.assertIn("--headless", command)
        self.assertTrue(any(value.startswith("-env:UserInstallation=file:") for value in command))
        self.stop(process)
        self.client.post(BASE + f"/source-versions/{original['version_id']}/process-visuals")
        self.start("office-count-mismatch")
        self.wait(original["version_id"])
        unit = self.content(original["version_id"])["units"][0]
        self.assertIn("slide count differs", unit["warning"])
        self.assertNotIn("LibreOffice rendering", unit["metadata"]["assets"][0]["caption"])

    def test_explicit_reprocessing_stable_ids_scope_and_damaged_preview(self):
        original = self.upload("scan.png")
        self.start()
        self.wait(original["version_id"])
        first = self.content(original["version_id"])["units"][0]
        with closing(sqlite3.connect(self.root / "studylens.sqlite3")) as connection:
            metadata = json.loads(connection.execute("SELECT metadata_json FROM content_units WHERE id=?", (first["id"],)).fetchone()[0])
        (self.root / metadata["assets"][0]["path"]).write_bytes(b"damaged")
        self.assertIn("error", self.content(original["version_id"])["units"][0]["metadata"]["assets"][0])
        other = self.client.post("/workspaces", json={"name": "Other"}).json()["id"]
        self.assertEqual(self.client.post(f"/workspaces/{other}/source-versions/{original['version_id']}/process-visuals").status_code, 404)
        self.assertEqual(self.client.post(BASE + f"/source-versions/{original['version_id']}/process-visuals").status_code, 202)
        self.wait(original["version_id"])
        second = self.content(original["version_id"])["units"][0]
        self.assertEqual(second["id"], first["id"])
        self.assertEqual(second["text_sha256"], first["text_sha256"])
        self.assertIn("data_url", second["metadata"]["assets"][0])

    def test_phase_four_migration_preserves_text_and_original(self):
        original = self.upload("scan.png")
        self.start()
        self.wait(original["version_id"])
        before = self.content(original["version_id"])["units"][0]
        for process in self.workers:
            self.stop(process)
        self.client.__exit__(None, None, None)
        with closing(sqlite3.connect(self.root / "studylens.sqlite3")) as connection:
            connection.execute("DROP TABLE youtube_media_links")
            connection.execute("ALTER TABLE content_units DROP COLUMN metadata_json")
            connection.execute("UPDATE alembic_version SET version_num='0003_content_units'")
            connection.commit()
        self.client = TestClient(create_app(self.root, TOKEN), headers=AUTH)
        self.client.__enter__()
        after = self.content(original["version_id"])["units"][0]
        self.assertEqual(after["id"], before["id"])
        self.assertEqual(after["text"], before["text"])
        self.assertEqual(after["metadata"].get("assets"), [])
        self.assertEqual(self.client.get("/health").json()["schema_version"], "0005_youtube_media_links")

    def test_cancel_native_child_keeps_service_responsive_then_resumes(self):
        original = self.upload("scan.png")
        process = self.start("slow-native")
        deadline = time.monotonic() + 6
        marker = self.root / "native-fixture-started"
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertTrue(marker.exists())
        job = self.job(original["version_id"])
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.post(BASE + f"/source-versions/{original['version_id']}/process-visuals").status_code, 409)
        self.client.post(BASE + f"/jobs/{job['id']}/cancel")
        self.assertEqual(self.wait(original["version_id"])["state"], "cancelled")
        self.stop(process)
        self.start()
        self.client.post(BASE + f"/jobs/{job['id']}/retry")
        self.wait(original["version_id"])
        self.assertIn("100 outcomes", self.content(original["version_id"])["units"][0]["text"])

    def test_optional_vision_fixture_is_local_unverified_bounded_and_unloaded(self):
        class Worker:
            def check(self, _job): pass
        class Guard:
            def touch(self): pass
        calls = []
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_args): pass
            def read(self, _size): return json.dumps({"done": True, "response": "Start branches toward Heads and Tails. Unverified."}).encode()
        def respond(request, **kwargs):
            calls.append(request)
            return Response()
        image = Image.open(FIXTURES / "figure.png")
        try:
            with patch.dict(os.environ, {"STUDYLENS_VISION_MODEL": "authored-vision-fixture"}), patch("urllib.request.urlopen", respond):
                notes = visual_notes(image, Worker(), {}, Guard())
            self.assertFalse(notes["verified"])
            self.assertTrue(notes["review_required"])
            self.assertEqual(calls[0].full_url, "http://127.0.0.1:11434/api/generate")
            self.assertEqual(json.loads(calls[0].data)["keep_alive"], 0)
            with patch.dict(os.environ, {"STUDYLENS_VISION_MODEL": "authored-vision-fixture"}), patch("urllib.request.urlopen", side_effect=OSError("offline")):
                self.assertIn("error", visual_notes(image, Worker(), {}, Guard()))
        finally:
            image.close()

    def test_equation_preview_preserves_operands_and_refuses_unknown_or_deep_structure(self):
        from defusedxml.ElementTree import fromstring
        from studylens_service.equations import M, equation_preview, preview_supported
        namespace = M[1:-1]
        known = fromstring(f'<oMath xmlns="{namespace}"><sSubSup><e><r><t>x</t></r></e><sub><r><t>i</t></r></sub><sup><r><t>2</t></r></sup></sSubSup></oMath>')
        self.assertTrue(preview_supported(equation_preview(known)))
        self.assertEqual(equation_preview(known)["children"][0]["kind"], "subsup")
        unknown = fromstring(f'<oMath xmlns="{namespace}"><m><mr><e><r><t>1</t></r></e></mr></m></oMath>')
        self.assertFalse(preview_supported(equation_preview(unknown)))
        self.assertFalse(preview_supported(equation_preview(known, depth=21)))


if __name__ == "__main__":
    unittest.main()
