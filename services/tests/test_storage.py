import copy
import hashlib
import tempfile
import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from alembic.operations import Operations
from studylens_service.api import create_app

TOKEN = "test-only-local-service-token-123456"
AUTH = {"Authorization": "Bearer " + TOKEN}
SESSION = {
    "version": 1, "tabs": [{"id": "tab-1", "view": "ask", "subjectId": "probability", "topicId": "conditional", "draft": "समझाइए"}],
    "activeTabId": "tab-1", "sidebarCollapsed": False,
    "subjects": [{"id": "probability", "name": "Probability", "icon": "probability", "demo": True,
        "topics": [{"id": "conditional", "title": "Conditional Probability", "description": "Fixture topic", "unit": "Fundamentals", "read": True, "lesson": "conditional", "readMinutes": 8}]}],
}
BASE = "/workspaces/semester-3"
SOURCES = BASE + "/subjects/probability/sources"


class StorageTests(unittest.TestCase):
    def test_failed_migration_rolls_back_and_can_restart(self):
        with tempfile.TemporaryDirectory(prefix="studylens-migration-") as folder:
            root = Path(folder)
            original = Operations.create_table
            calls = 0
            def fail_after_first(operation, *args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise RuntimeError("injected migration failure")
                return original(operation, *args, **kwargs)
            with patch.object(Operations, "create_table", fail_after_first):
                with self.assertRaisesRegex(RuntimeError, "injected migration failure"):
                    with TestClient(create_app(root, TOKEN), headers=AUTH):
                        pass
            with closing(sqlite3.connect(root / "studylens.sqlite3")) as connection:
                self.assertEqual(connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(), [])
            with TestClient(create_app(root, TOKEN), headers=AUTH) as client:
                self.assertEqual(client.get("/health").json()["schema_version"], "0005_youtube_media_links")

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="studylens-storage-")
        self.root = Path(self.directory.name)
        self.client = TestClient(create_app(self.root, TOKEN), headers=AUTH)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.directory.cleanup()

    def seed(self):
        response = self.client.put(BASE + "/session", json={"base_revision": 0, "session": SESSION})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["revision"]

    def upload(self, payload=b"Original notes", filename="notes.txt", source_id=None):
        params = {"filename": filename}
        if source_id:
            params["source_id"] = source_id
        return self.client.post(SOURCES, params=params, content=payload, headers={"Content-Type": "application/octet-stream"})

    def test_migration_wal_restart_and_unicode_snapshot(self):
        self.assertEqual(self.client.get("/health").json()["journal_mode"], "wal")
        self.assertEqual(self.client.get("/health").json()["schema_version"], "0005_youtube_media_links")
        self.seed()
        self.client.__exit__(None, None, None)
        self.client = TestClient(create_app(self.root, TOKEN), headers=AUTH)
        self.client.__enter__()
        record = self.client.get(BASE + "/session").json()
        self.assertEqual(record["revision"], 1)
        self.assertEqual(record["session"], SESSION)

    def test_revision_conflict_never_overwrites_saved_work(self):
        self.seed()
        edited = copy.deepcopy(SESSION)
        edited["tabs"][0]["draft"] = "Stale content"
        response = self.client.put(BASE + "/session", json={"base_revision": 0, "session": edited})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.get(BASE + "/session").json()["session"]["tabs"][0]["draft"], "समझाइए")

    def test_workspaces_are_isolated_and_names_are_unique(self):
        self.seed()
        response = self.client.post("/workspaces", json={"name": "Exam revision"})
        self.assertEqual(response.status_code, 201)
        identifier = response.json()["id"]
        self.assertIsNone(self.client.get(f"/workspaces/{identifier}/session").json()["session"])
        second = copy.deepcopy(SESSION)
        second["subjects"][0]["name"] = "Another course"
        result = self.client.put(f"/workspaces/{identifier}/session", json={"base_revision": 0, "session": second})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(self.client.get(BASE + "/session").json()["session"]["subjects"][0]["name"], "Probability")
        self.assertEqual(self.client.post("/workspaces", json={"name": " exam REVISION "}).status_code, 409)

    def test_update_and_remove_topic_roundtrip(self):
        self.seed()
        updated = copy.deepcopy(SESSION)
        updated["subjects"][0]["topics"].append({"id": "bayes", "title": "Bayes", "description": "", "unit": "Advanced", "read": False})
        updated["subjects"][0]["name"] = "Probability 101"
        self.assertEqual(self.client.put(BASE + "/session", json={"base_revision": 1, "session": updated}).status_code, 200)
        updated["subjects"][0]["topics"] = updated["subjects"][0]["topics"][1:]
        updated["tabs"][0].pop("topicId")
        updated["tabs"][0]["draft"] = ""
        response = self.client.put(BASE + "/session", json={"base_revision": 2, "session": updated})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.get(BASE + "/session").json()["session"], updated)

    def test_original_duplicate_and_version_history_are_exact(self):
        self.seed()
        first = self.upload().json()
        duplicate = self.upload().json()
        second = self.upload(b"Changed notes", "updated.txt", first["source_id"]).json()
        self.assertFalse(first["duplicate"])
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["version_id"], first["version_id"])
        self.assertEqual(second["version"], 2)
        rows = self.client.get(SOURCES).json()
        self.assertEqual(len(rows), 1)
        self.assertEqual([version["version"] for version in rows[0]["versions"]], [2, 1])
        self.assertEqual(rows[0]["versions"][1]["sha256"], hashlib.sha256(b"Original notes").hexdigest())
        self.assertEqual(self.client.get(f'/source-versions/{first["version_id"]}/file').content, b"Original notes")
        self.assertEqual(self.client.get(f'/source-versions/{second["version_id"]}/file').content, b"Changed notes")
        self.assertEqual(list((self.root / "staging").iterdir()), [])

    def test_parallel_versions_get_distinct_monotonic_numbers(self):
        self.seed()
        source = self.upload().json()["source_id"]
        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda data: self.upload(data, "notes.txt", source), [b"Version A", b"Version B"]))
        self.assertTrue(all(response.status_code == 201 for response in responses))
        self.assertEqual(sorted(response.json()["version"] for response in responses), [2, 3])

    def test_invalid_scope_and_dangling_refs_do_not_change_database(self):
        self.seed()
        bad = copy.deepcopy(SESSION)
        bad["tabs"][0]["topicId"] = "does-not-exist"
        self.assertEqual(self.client.put(BASE + "/session", json={"base_revision": 1, "session": bad}).status_code, 422)
        bad = copy.deepcopy(SESSION)
        bad["subjects"][0]["topics"].append(copy.deepcopy(bad["subjects"][0]["topics"][0]))
        self.assertEqual(self.client.put(BASE + "/session", json={"base_revision": 1, "session": bad}).status_code, 422)
        self.assertEqual(self.client.get(BASE + "/session").json()["revision"], 1)

    def test_source_foreign_key_blocks_inconsistent_subject_removal(self):
        self.seed()
        self.upload()
        bad = {"version": 1, "tabs": [{"id": "tab-1", "view": "workspace", "draft": ""}], "activeTabId": "tab-1", "sidebarCollapsed": False, "subjects": []}
        self.assertEqual(self.client.put(BASE + "/session", json={"base_revision": 1, "session": bad}).status_code, 409)
        self.assertEqual(self.client.get(BASE + "/session").json()["session"], SESSION)
        self.assertEqual(self.client.get(BASE + "/session").json()["revision"], 1)

    def test_auth_and_cross_origin_access_are_rejected(self):
        self.assertEqual(self.client.get("/health", headers={"Authorization": ""}).status_code, 401)
        self.assertEqual(self.client.get("/health", headers={"Origin": "https://unrelated.example"}).status_code, 403)

    def test_bad_filename_type_and_empty_file_leave_no_metadata(self):
        self.seed()
        self.assertEqual(self.upload(filename="../notes.txt").status_code, 422)
        self.assertEqual(self.upload(filename="program.exe").status_code, 415)
        self.assertEqual(self.upload(payload=b"").status_code, 422)
        self.assertEqual(self.client.get(SOURCES).json(), [])
        self.assertEqual(list((self.root / "staging").iterdir()), [])

    def test_oversize_and_disk_failure_are_actionable(self):
        with TestClient(create_app(self.root, TOKEN, max_file_bytes=4), headers=AUTH) as limited:
            response = limited.post(SOURCES, params={"filename": "large.txt"}, content=b"12345")
            self.assertEqual(response.status_code, 413)
        self.seed()
        original_open = Path.open
        def failed_open(path, *args, **kwargs):
            if path.suffix == ".part":
                raise OSError("Injected disk-full fixture")
            return original_open(path, *args, **kwargs)
        with patch.object(Path, "open", failed_open):
            self.assertEqual(self.upload().status_code, 507)
        self.assertEqual(self.client.get(SOURCES).json(), [])

    def test_same_size_tampering_is_detected_on_download(self):
        self.seed()
        first = self.upload().json()
        digest = hashlib.sha256(b"Original notes").hexdigest()
        (self.root / "originals" / digest[:2] / digest).write_bytes(b"x" * len(b"Original notes"))
        response = self.client.get(f'/source-versions/{first["version_id"]}/file')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.upload().status_code, 500)


if __name__ == "__main__":
    unittest.main()

