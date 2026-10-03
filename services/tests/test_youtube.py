import copy
import json
import sqlite3
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from studylens_service.job_errors import Cancelled, ExtractionFailure, Interrupted
from studylens_service.worker import Worker
from studylens_service.youtube import REVISION, caption_groups, parse_url, validate_snapshot
from studylens_service.youtube_helper import fetch
import test_extraction as extraction_fixtures
from test_storage import BASE, SOURCES, SESSION

URL = "https://www.youtube.com/watch?v=WUvTyaaNkzM"
ROUTE = BASE + "/subjects/probability/youtube"


def snapshot(generated=False, language="en", issue=None):
    return {"revision": REVISION, "url": URL, "video_id": "WUvTyaaNkzM", "requested_language": language,
        "language_code": None if issue else language, "is_generated": None if issue else generated,
        "tracks": [{"language": "Hindi" if language == "hi" else "English", "language_code": language, "is_generated": generated}],
        "snippets": [] if issue else [{"text":"Vectors have direction.","start":1.25,"duration":2},
            {"text":"Vectors have direction and magnitude.","start":2,"duration":3},
            {"text":"अगला विषय" if language == "hi" else "The next topic.","start":65.5,"duration":2}], "issue":issue}


class YouTubeTests(unittest.TestCase):
    setUp = extraction_fixtures.ExtractionTests.setUp
    content = extraction_fixtures.ExtractionTests.content
    stop = extraction_fixtures.ExtractionTests.stop

    def tearDown(self):
        if hasattr(self, "worker"):
            self.worker.connection.close()
        extraction_fixtures.ExtractionTests.tearDown(self)

    def enqueue(self, language="en", title="Vector lecture"):
        response=self.client.post(ROUTE,json={"url":URL,"language":language,"title":title})
        self.assertEqual(response.status_code,202,response.text)
        return response.json()

    def drain(self, value):
        with patch("studylens_service.local_tools.run_tool",return_value=(json.dumps(value),0)) as call:
            while job := self.worker.claim():
                self.worker.execute(job)
        return call

    def start_worker(self):
        self.worker=Worker(self.root,threading.Event())

    def test_supported_urls_canonicalize_and_reject_arbitrary_targets(self):
        for value in (URL+"&list=ignored&t=30", "https://youtu.be/WUvTyaaNkzM?si=abc", "https://m.youtube.com/watch?v=WUvTyaaNkzM",
            "https://youtube.com/shorts/WUvTyaaNkzM", "https://www.youtube.com/embed/WUvTyaaNkzM", "https://youtube.com/live/WUvTyaaNkzM"):
            self.assertEqual(parse_url(value),("WUvTyaaNkzM",URL))
        for value in ("http://www.youtube.com/watch?v=WUvTyaaNkzM", "https://youtube.com.evil.test/watch?v=WUvTyaaNkzM",
            "https://user@youtube.com/watch?v=WUvTyaaNkzM", "https://youtube.com:443/watch?v=WUvTyaaNkzM",
            URL+"&v=jNQXAC9IVRw", "https://youtube.com/playlist?list=x", "https://127.0.0.1/watch?v=WUvTyaaNkzM"):
            self.assertEqual(self.client.post(ROUTE,json={"url":value}).status_code,422,value)
        self.assertEqual(self.client.post(ROUTE,json={"url":URL,"language":"en&x=1"}).status_code,422)
        self.assertEqual(self.client.post(ROUTE,json={"url":URL,"download":True}).status_code,422)

    def test_manual_captions_keep_overlap_locations_and_snapshot_integrity(self):
        self.start_worker()
        imported=self.enqueue()
        self.drain(snapshot())
        job=self.client.get(BASE+"/jobs/"+imported["id"]).json()
        self.assertEqual(job["state"],"succeeded",job)
        version=job["result"]["version_id"]
        content=self.content(version)
        self.assertEqual(content["state"],"partial")
        self.assertTrue(content["integrity_verified"])
        self.assertEqual(content["total"],2)
        self.assertEqual(content["units"][0]["locator"],{"kind":"time","start_seconds":1.25,"end_seconds":5})
        self.assertEqual(content["units"][0]["metadata"]["segments"][1]["start_seconds"],2)
        self.assertEqual(content["units"][1]["locator"]["start_seconds"],65.5)
        self.assertEqual(content["units"][0]["status"],"suspect")
        self.assertEqual(content["result"]["youtube"]["coverage"],"captions_only")
        self.assertFalse(content["result"]["youtube"]["is_generated"])
        saved=self.client.get("/source-versions/"+version+"/file")
        self.assertEqual(saved.json(),snapshot())
        sources=self.client.get(SOURCES).json()
        self.assertEqual(sources[0]["display_name"],"Vector lecture")
        self.assertEqual(sources[0]["kind"],"youtube")

    def test_duplicate_queue_duplicate_snapshot_and_changed_caption_versions(self):
        self.start_worker()
        first=self.enqueue()
        self.assertEqual(self.enqueue()["id"],first["id"])
        self.drain(snapshot())
        second=self.enqueue()
        self.drain(snapshot())
        self.assertTrue(self.client.get(BASE+"/jobs/"+second["id"]).json()["result"]["duplicate"])
        changed=snapshot();changed["snippets"][0]["text"]="Vectors have direction and length."
        self.enqueue();self.drain(changed)
        versions=self.client.get(SOURCES).json()[0]["versions"]
        self.assertEqual(len(versions),2)
        self.assertEqual(self.client.get("/source-versions/"+versions[1]["id"]+"/file").json(),snapshot())
        # YouTube IDs are case-sensitive, unlike ordinary filename name keys.
        distinct=snapshot();distinct.update(url=URL.replace("WUv", "wUv"),video_id="wUvTyaaNkzM")
        self.assertEqual(self.client.post(ROUTE,json={"url":distinct["url"]}).status_code,202)
        self.drain(distinct)
        self.assertEqual(len(self.client.get(SOURCES).json()),2)

    def test_generated_hindi_is_separate_and_unverified(self):
        self.start_worker()
        self.enqueue();self.drain(snapshot())
        self.enqueue("hi");self.drain(snapshot(True,"hi"))
        sources=self.client.get(SOURCES).json()
        self.assertEqual(len(sources),2)
        hindi=next(source for source in sources if "-hi." in source["versions"][0]["filename"])
        value=self.content(hindi["versions"][0]["id"])
        self.assertTrue(value["result"]["youtube"]["is_generated"])
        self.assertFalse(value["result"]["youtube"]["translated"])
        self.assertIn("अगला विषय",value["units"][1]["text"])

    def test_link_only_does_not_fabricate_units_and_can_refresh(self):
        self.start_worker()
        imported=self.enqueue()
        self.drain(snapshot(issue="YouTube blocked caption access. The link is saved."))
        value=self.client.get(BASE+"/jobs/"+imported["id"]).json()
        self.assertEqual(value["state"],"partial")
        content=self.content(value["result"]["version_id"])
        self.assertEqual(content["units"],[])
        self.assertEqual(content["result"]["youtube"]["coverage"],"link_only")
        self.enqueue();self.drain(snapshot())
        self.assertEqual(len(self.client.get(SOURCES).json()[0]["versions"]),2)

    def test_wrong_source_or_invalid_times_are_never_published(self):
        self.start_worker()
        for transform in (lambda value:value.update(url="https://www.youtube.com/watch?v=jNQXAC9IVRw"),
            lambda value:value["snippets"][0].update(start=float("nan")),
            lambda value:value["snippets"][0].update(duration=15000),
            lambda value:value["snippets"][1].update(start=0)):
            value=snapshot();transform(value)
            imported=self.enqueue();self.drain(value)
            self.assertEqual(self.client.get(BASE+"/jobs/"+imported["id"]).json()["state"],"failed")
        self.assertEqual(self.client.get(SOURCES).json(),[])

    def test_workspace_scoping_and_atomic_cancel_resume(self):
        self.start_worker()
        imported=self.enqueue()
        other=self.client.post("/workspaces",json={"name":"Other"}).json()["id"]
        self.assertEqual(self.client.post(f"/workspaces/{other}/subjects/probability/youtube",json={"url":URL}).status_code,404)
        job=self.worker.claim()
        def cancel(*args,**kwargs):
            self.worker.connection.execute("UPDATE jobs SET cancel_requested=1 WHERE id=?",(job["id"],))
            raise Cancelled()
        with patch("studylens_service.local_tools.run_tool",side_effect=cancel): self.worker.execute(job)
        self.assertEqual(self.client.get(SOURCES).json(),[])
        self.assertEqual(self.client.post(BASE+"/jobs/"+imported["id"]+"/retry").status_code,202)
        self.drain(snapshot())
        version=self.client.get(SOURCES).json()[0]["versions"][0]["id"]
        self.assertEqual(self.client.get(f"/workspaces/{other}/source-versions/{version}/content").status_code,404)

    def test_saved_snapshot_restarts_without_network_refetch(self):
        self.start_worker(); imported=self.enqueue()
        original=self.worker.checkpoint
        def interrupt(job,done,total,stage,checkpoint):
            original(job,done,total,stage,checkpoint)
            if checkpoint.get("snapshot_sha256"): raise Interrupted()
        with patch.object(self.worker,"checkpoint",side_effect=interrupt), patch("studylens_service.local_tools.run_tool",return_value=(json.dumps(snapshot()),0)):
            self.worker.execute(self.worker.claim())
        self.assertEqual(self.client.get(SOURCES).json(),[])
        call=self.drain(snapshot())
        self.assertEqual(call.call_count,0)
        self.assertEqual(self.client.get(BASE+"/jobs/"+imported["id"]).json()["state"],"succeeded")

    def test_extraction_cancel_resume_uses_saved_caption_snapshot(self):
        self.start_worker();self.enqueue()
        with patch("studylens_service.local_tools.run_tool",return_value=(json.dumps(snapshot()),0)):
            self.worker.execute(self.worker.claim())
        self.worker.execute(self.worker.claim()) # integrity
        job=self.worker.claim(); original=self.worker.checkpoint
        def cancel(job,done,total,stage,checkpoint):
            original(job,done,total,stage,checkpoint)
            if done==1:
                self.worker.connection.execute("UPDATE jobs SET cancel_requested=1 WHERE id=?",(job["id"],))
        with patch.object(self.worker,"checkpoint",side_effect=cancel):self.worker.execute(job)
        self.assertEqual(self.content(job["source_version_id"])["completed"],1)
        self.client.post(BASE+"/jobs/"+job["id"]+"/retry")
        self.drain(snapshot())
        self.assertEqual(self.content(job["source_version_id"])["completed"],2)

    def test_exact_duplicates_only_and_units_are_bounded(self):
        value=snapshot()
        cues=value["snippets"]
        self.assertEqual(len(list(caption_groups([cues[0],cues[0],cues[1]]))[0]),2)
        rolling=[{"text":"same speech", "start":i,"duration":3} for i in range(100)]
        self.assertEqual(sum(len(group) for group in caption_groups(rolling)),100)
        value["snippets"][0]["text"]="x"*4001
        with self.assertRaises(ExtractionFailure):validate_snapshot(value)


class CaptionAdapterTests(unittest.TestCase):
    def track(self, generated=False, language="en"):
        value=snapshot(generated,language)
        fetched=SimpleNamespace(video_id=value["video_id"],language_code=language,is_generated=generated,to_raw_data=lambda:value["snippets"])
        return SimpleNamespace(language="English" if language=="en" else "Hindi",language_code=language,is_generated=generated,fetch=Mock(return_value=fetched))

    def test_select_manual_track_in_requested_language(self):
        generated=self.track(True);manual=self.track();hindi=self.track(True,"hi")
        with patch("youtube_transcript_api.YouTubeTranscriptApi") as api:
            api.return_value.list.return_value=[generated,hindi,manual]
            value=fetch({"url":URL,"video_id":"WUvTyaaNkzM","language":"en"})
        self.assertFalse(value["is_generated"]);manual.fetch.assert_called_once();generated.fetch.assert_not_called();hindi.fetch.assert_not_called()

    def test_missing_language_keeps_available_tracks_and_no_translation(self):
        manual=self.track()
        with patch("youtube_transcript_api.YouTubeTranscriptApi") as api:
            api.return_value.list.return_value=[manual]
            value=fetch({"url":URL,"video_id":"WUvTyaaNkzM","language":"hi"})
        self.assertEqual(value["snippets"],[]);self.assertEqual(value["tracks"][0]["language_code"],"en");manual.fetch.assert_not_called()

    def test_blocked_disabled_and_timeout_return_actionable_link_only(self):
        for name in ("RequestBlocked","TranscriptsDisabled","Timeout"):
            with patch("youtube_transcript_api.YouTubeTranscriptApi") as api:
                api.return_value.list.side_effect=type(name,(Exception,),{})("remote detail should not leak")
                value=fetch({"url":URL,"video_id":"WUvTyaaNkzM","language":"en"})
            self.assertEqual(value["snippets"],[]);self.assertIn("saved",value["issue"]);self.assertNotIn("remote detail",value["issue"])
