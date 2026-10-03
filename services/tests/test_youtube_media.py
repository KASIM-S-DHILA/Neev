"""Independent local-media association checks; no YouTube video is downloaded."""
import json
import sqlite3
import threading
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from studylens_service.api import create_app
from studylens_service.worker import Worker

import test_extraction as extraction_fixtures
from test_storage import AUTH, BASE, SOURCES, TOKEN
from test_youtube import ROUTE, URL, snapshot


VIDEO = Path(__file__).resolve().parents[2] / "docs/evaluation/fixtures/phase-07b/slides.mp4"


class YouTubeMediaTests(unittest.TestCase):
    setUp = extraction_fixtures.ExtractionTests.setUp

    def tearDown(self):
        if hasattr(self, "worker"):
            self.worker.connection.close()
        extraction_fixtures.ExtractionTests.tearDown(self)

    def captions(self, changed=False):
        if not hasattr(self, "worker"):
            self.worker = Worker(self.root, threading.Event())
        queued = self.client.post(ROUTE, json={"url": URL, "language": "en"})
        self.assertEqual(queued.status_code, 202, queued.text)
        value = snapshot()
        if changed:
            value["snippets"][0]["text"] = "A changed lecture caption."
        with patch("studylens_service.local_tools.run_tool", return_value=(json.dumps(value), 0)):
            while job := self.worker.claim():
                self.worker.execute(job)
        result = self.client.get(BASE + "/jobs/" + queued.json()["id"]).json()
        self.assertEqual(result["state"], "succeeded", result)
        return result["result"]["version_id"]

    def video(self):
        uploaded = self.client.post(SOURCES, params={"filename": "slides.mp4"}, content=VIDEO.read_bytes())
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        return uploaded.json()["version_id"]

    def route(self, caption_version):
        return f"{BASE}/source-versions/{caption_version}/local-media"

    def test_association_uses_local_original_and_source_versions_without_merging_them(self):
        first = self.captions()
        refreshed = self.captions(changed=True)
        media_version = self.video()
        route = self.route(first)
        initial = self.client.get(route).json()
        self.assertIsNone(initial["media"])
        payload = {"media_version_id": media_version, "youtube_start_seconds": 60}
        attached = self.client.post(route, json=payload)
        self.assertEqual(attached.status_code, 200, attached.text)
        media = attached.json()["media"]
        self.assertEqual(media["caption_version_id_at_link"], first)
        self.assertEqual(media["media_version_id"], media_version)
        self.assertEqual(media["youtube_start_seconds"], 60)
        self.assertEqual(media["provenance"], "student_supplied_local_copy")
        self.assertFalse(media["match_verified"])
        self.assertEqual(self.client.get(self.route(refreshed)).json()["media"], media)
        self.client.__exit__(None, None, None)
        self.client = TestClient(create_app(self.root, TOKEN), headers=AUTH)
        self.client.__enter__()
        self.assertEqual(self.client.get(self.route(refreshed)).json()["media"], media)
        source = next(row for row in self.client.get(SOURCES).json() if row["kind"] == "youtube")
        self.assertEqual(source["media_link"], media)
        self.assertEqual(len(source["versions"]), 2)
        self.assertEqual(self.client.get("/source-versions/" + media_version + "/file").content, VIDEO.read_bytes())
        self.assertEqual(self.client.get("/source-versions/" + first + "/file").json(), snapshot())
        self.assertEqual(self.client.post(route, json=payload).status_code, 200)
        with closing(sqlite3.connect(self.root / "studylens.sqlite3")) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM youtube_media_links").fetchone()[0], 1)
        self.assertEqual(self.client.delete(self.route(refreshed)).status_code, 200)
        self.assertIsNone(self.client.get(route).json()["media"])
        with closing(sqlite3.connect(self.root / "studylens.sqlite3")) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM youtube_media_links").fetchone()[0], 2)
        self.assertEqual(self.client.get("/source-versions/" + media_version + "/file").content, VIDEO.read_bytes())

    def test_scope_type_offset_and_original_integrity_are_enforced(self):
        caption = self.captions()
        media_version = self.video()
        route = self.route(caption)
        other = self.client.post("/workspaces", json={"name": "Other"}).json()["id"]
        self.assertEqual(self.client.post(self.route(media_version), json={"media_version_id": media_version}).status_code, 404)
        self.assertEqual(self.client.post(f"/workspaces/{other}/source-versions/{caption}/local-media",
            json={"media_version_id": media_version}).status_code, 404)
        self.assertEqual(self.client.post(route, json={"media_version_id": caption}).status_code, 409)
        for offset in (-1, 14401, "NaN"):
            self.assertEqual(self.client.post(route, json={"media_version_id": media_version,
                "youtube_start_seconds": offset}).status_code, 422)
        with closing(sqlite3.connect(self.root / "studylens.sqlite3")) as connection:
            relative = connection.execute("SELECT relative_path FROM source_versions WHERE id=?", (media_version,)).fetchone()[0]
        original = self.root / relative
        data = original.read_bytes()
        original.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
        self.assertEqual(self.client.post(route, json={"media_version_id": media_version}).status_code, 404)
        self.assertIsNone(self.client.get(route).json()["media"])


if __name__ == "__main__":
    unittest.main()
