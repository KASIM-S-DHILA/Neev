"""Live, caption-only import smoke test plus clearly labelled authored UI data."""
import copy
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "services/tests"))
os.environ["GROQ_API_KEY"]=""
from fastapi.testclient import TestClient
from studylens_service.api import create_app
from studylens_service.worker import Worker
from test_storage import AUTH, BASE, SESSION, SOURCES, TOKEN
from test_youtube import snapshot, ROUTE, URL

tag=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
root=ROOT / "tmp" / ("youtube-integration-"+tag)
report={"date_utc":tag,"data_directory":str(root),"live_url":URL,"checks":{},"live_caption_fetch":"pending"}
with TestClient(create_app(root,TOKEN),headers=AUTH) as client:
    session=copy.deepcopy(SESSION);session["tabs"][0]["view"]="materials"
    client.put(BASE+"/session",json={"base_revision":0,"session":session}).raise_for_status()
    queued=client.post(ROUTE,json={"url":URL,"title":"The essence of calculus (live import)"})
    queued.raise_for_status()
    worker=Worker(root,threading.Event())
    try:
        start=time.monotonic()
        while job:=worker.claim(): worker.execute(job)
        live=client.get(BASE+"/jobs/"+queued.json()["id"]).json()
        report["live_seconds"]=round(time.monotonic()-start,3)
        report["live_job"]=live
        result=live.get("result")
        if result:
            content=client.get(BASE+"/source-versions/"+result["version_id"]+"/content").json()
            report["live_caption_fetch"]="available" if result["coverage"]=="captions_only" else "unavailable"
            report["live_extraction"]={key:content.get(key) for key in ("state","total","completed","integrity_verified","result")}
            report["checks"]["live_snapshot_integrity"]=content["integrity_verified"]
            report["checks"]["coverage_honest"]= bool(content["units"]) if result["coverage"]=="captions_only" else not content["units"]
        else:
            report["checks"]["live_snapshot_integrity"]=False
        # Native visual test uses authored cues, never misrepresents them as
        # text from the real lecture. A separate language/source keeps live
        # import evidence and originals intact.
        fixture=client.post(ROUTE,json={"url":URL,"language":"hi","title":"Authored caption fixture · UI test"})
        fixture.raise_for_status()
        with patch("studylens_service.local_tools.run_tool",return_value=(json.dumps(snapshot(True,"hi")),0)):
            while job:=worker.claim():worker.execute(job)
        value=client.get(BASE+"/jobs/"+fixture.json()["id"]).json()
        report["authored_ui_fixture"]={"label":"Authored cues, not actual video captions", "version_id":value["result"]["version_id"]}
        report["checks"]["authored_fixture_published"]=value["state"]=="succeeded"
    finally:worker.connection.close()
report["status"]="passed" if all(report["checks"].values()) else "needs-review"
target=ROOT / "docs/evaluation" / ("youtube-"+tag+".json")
target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"status":report["status"],"live_caption_fetch":report["live_caption_fetch"],"live_seconds":report["live_seconds"],"issue":report["live_job"].get("result",{}).get("issue"),"report":str(target),"data_directory":str(root)}))
