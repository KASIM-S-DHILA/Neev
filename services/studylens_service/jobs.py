import json
import time
from uuid import uuid4

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .database import Conflict, Missing
from .schema import content_units, jobs, sources, source_versions, workspaces


def job_values(workspace_id, subject_id, version_id, kind, label, total, payload=None):
    stamp = time.time()
    return dict(id=str(uuid4()), workspace_id=workspace_id, subject_id=subject_id,
        source_version_id=version_id, kind=kind, label=label, state="queued", stage="Waiting",
        done=0, total=total, checkpoint_json="{}", payload_json=json.dumps(payload or {}),
        result_json=None, error=None, cancel_requested=False, attempts=0, failures=0,
        max_attempts=3, recoveries=0, owner=None, available_at=stamp, created_at=stamp, updated_at=stamp)


def public_job(row):
    return {key: row[key] for key in ("id", "workspace_id", "subject_id", "source_version_id", "kind",
        "label", "state", "stage", "done", "total", "error", "cancel_requested", "attempts", "failures",
        "max_attempts", "recoveries", "created_at", "updated_at")} | {
        "checkpoint": {key: value for key, value in json.loads(row["checkpoint_json"]).items() if key not in ("frames", "video", "results")}, "result": json.loads(row["result_json"]) if row["result_json"] else None,
        **({"provider": json.loads(row["payload_json"]).get("provider", "groq"),
            "automatic": bool(json.loads(row["payload_json"]).get("automatic"))} if row["kind"] == "cloud_visuals" else {})}


class JobStore:
    def __init__(self, database):
        self.db = database

    async def require_workspace(self, workspace_id):
        async with self.db.engine.connect() as connection:
            if not (await connection.execute(select(workspaces.c.id).where(workspaces.c.id == workspace_id))).scalar_one_or_none():
                raise Missing("Workspace not found")

    async def backfill(self):
        # Give originals saved before Phase 3 the same durable verification job.
        async with self.db.engine.begin() as connection:
            rows = (await connection.execute(select(source_versions, sources.c.workspace_id, sources.c.subject_id, sources.c.kind)
                .join(sources, sources.c.id == source_versions.c.source_id))).mappings()
            for row in rows:
                values = job_values(row["workspace_id"], row["subject_id"], row["id"], "verify_original", row["filename"], row["size_bytes"])
                await connection.execute(sqlite_insert(jobs).values(**values).on_conflict_do_nothing(index_elements=["kind", "source_version_id"]))
                if row["kind"] in ("pdf", "text", "image", "slides", "audio", "video", "youtube"):
                    values = job_values(row["workspace_id"], row["subject_id"], row["id"], "extract_source", row["filename"], 0)
                    await connection.execute(sqlite_insert(jobs).values(**values).on_conflict_do_nothing(index_elements=["kind", "source_version_id"]))
                from .video_frames import automatic_enabled
                if row["kind"] == "video" and automatic_enabled():
                    values = job_values(row["workspace_id"], row["subject_id"], row["id"], "video_frames", row["filename"] + " · Frames", 0)
                    await connection.execute(sqlite_insert(jobs).values(**values).on_conflict_do_nothing(index_elements=["kind", "source_version_id"]))
                if row["kind"] == "video":
                    from .video_frame_visuals import automatic_enabled as frame_visuals_enabled
                    selected = (await connection.execute(select(jobs).where(jobs.c.kind == "video_frames",
                        jobs.c.source_version_id == row["id"]))).mappings().first()
                    if frame_visuals_enabled() and selected and selected["state"] in ("succeeded", "partial"):
                        count = len(json.loads(selected["checkpoint_json"]).get("frames", []))
                        if count:
                            values = job_values(row["workspace_id"], row["subject_id"], row["id"],
                                "video_frame_visuals", row["filename"] + " · Frame text", count)
                            await connection.execute(sqlite_insert(jobs).values(**values).on_conflict_do_nothing(index_elements=["kind", "source_version_id"]))

    async def import_youtube(self, workspace_id, subject_id, body):
        from .youtube import parse_url
        from sqlalchemy import text
        _, url = parse_url(body.url)
        await self.db.require_subject(workspace_id, subject_id)
        payload = {"url": url, "language": body.language, "title": body.title.strip()}
        async with self.db.engine.connect() as connection:
            await connection.execute(text("BEGIN IMMEDIATE"))
            try:
                active = (await connection.execute(select(jobs).where(jobs.c.workspace_id == workspace_id,
                    jobs.c.subject_id == subject_id, jobs.c.kind == "youtube_import", jobs.c.state.in_(["queued", "running"])))).mappings().all()
                for row in active:
                    previous = json.loads(row["payload_json"])
                    if previous["url"] == url and previous["language"] == body.language:
                        await connection.commit()
                        return public_job(row)
                if len(active) >= 10:
                    raise Conflict("Up to ten YouTube imports can wait per subject. Finish or cancel an import first.")
                values = job_values(workspace_id, subject_id, None, "youtube_import", (payload["title"] or "YouTube · " + url[-11:]) + " · Captions", 1, payload)
                await connection.execute(insert(jobs).values(**values))
                await connection.commit()
            except BaseException:
                await connection.rollback()
                raise
        return await self.get(workspace_id, values["id"])

    async def process_frames(self, workspace_id, version_id):
        async with self.db.engine.connect() as connection:
            from sqlalchemy import text
            await connection.execute(text("BEGIN IMMEDIATE"))
            try:
                source = (await connection.execute(select(source_versions, sources.c.kind, sources.c.subject_id).join(sources, sources.c.id == source_versions.c.source_id)
                    .where(sources.c.workspace_id == workspace_id, source_versions.c.id == version_id))).mappings().first()
                if not source:
                    raise Missing("Original version not found in this workspace")
                if source["kind"] != "video":
                    raise Conflict("Frame selection supports video sources.")
                current = (await connection.execute(select(jobs).where(jobs.c.kind == "video_frames", jobs.c.source_version_id == version_id))).mappings().first()
                if current and current["state"] in ("queued", "running"):
                    raise Conflict("Frame selection is already active. Cancel it before rebuilding.")
                visual = (await connection.execute(select(jobs).where(jobs.c.kind == "video_frame_visuals",
                    jobs.c.source_version_id == version_id))).mappings().first()
                if visual and visual["state"] == "running":
                    raise Conflict("Cancel frame visual processing before selecting frames again.")
                await connection.execute(delete(jobs).where(jobs.c.kind == "video_frame_visuals", jobs.c.source_version_id == version_id))
                if current:
                    job_id = current["id"]
                    await connection.execute(update(jobs).where(jobs.c.id == job_id).values(state="queued", stage="Selecting frames again", done=0, total=0,
                        checkpoint_json="{}", result_json=None, error=None, cancel_requested=False, failures=0, owner=None, available_at=time.time(), updated_at=time.time()))
                else:
                    values = job_values(workspace_id, source["subject_id"], version_id, "video_frames", source["filename"] + " · Frames", 0)
                    job_id = values["id"]
                    await connection.execute(insert(jobs).values(**values))
                await connection.commit()
            except BaseException:
                await connection.rollback()
                raise
        return await self.get(workspace_id, job_id)

    async def process_frame_visuals(self, workspace_id, version_id):
        async with self.db.engine.connect() as connection:
            from sqlalchemy import text
            await connection.execute(text("BEGIN IMMEDIATE"))
            try:
                source = (await connection.execute(select(source_versions, sources.c.kind, sources.c.subject_id)
                    .join(sources, sources.c.id == source_versions.c.source_id)
                    .where(sources.c.workspace_id == workspace_id, source_versions.c.id == version_id))).mappings().first()
                if not source or source["kind"] != "video":
                    raise Missing("Video version not found in this workspace")
                frames = (await connection.execute(select(jobs).where(jobs.c.kind == "video_frames",
                    jobs.c.source_version_id == version_id))).mappings().first()
                if not frames or frames["state"] not in ("succeeded", "partial") or not json.loads(frames["checkpoint_json"]).get("frames"):
                    raise Conflict("Finish selecting video frames before visual extraction.")
                current = (await connection.execute(select(jobs).where(jobs.c.kind == "video_frame_visuals",
                    jobs.c.source_version_id == version_id))).mappings().first()
                if current and current["state"] in ("queued", "running"):
                    raise Conflict("Frame visual processing is already active.")
                count = len(json.loads(frames["checkpoint_json"])["frames"])
                if current:
                    job_id = current["id"]
                    await connection.execute(update(jobs).where(jobs.c.id == job_id).values(state="queued",
                        stage="Reading selected frames again", done=0, total=count, checkpoint_json="{}",
                        result_json=None, error=None, cancel_requested=False, failures=0, owner=None,
                        available_at=time.time(), updated_at=time.time()))
                else:
                    values = job_values(workspace_id, source["subject_id"], version_id, "video_frame_visuals",
                        source["filename"] + " · Frame text", count)
                    job_id = values["id"]
                    await connection.execute(insert(jobs).values(**values))
                await connection.commit()
            except BaseException:
                await connection.rollback()
                raise
        return await self.get(workspace_id, job_id)

    async def frames(self, workspace_id, version_id, offset=0):
        async with self.db.engine.connect() as connection:
            source = (await connection.execute(select(source_versions.c.sha256, sources.c.kind).join(sources, sources.c.id == source_versions.c.source_id)
                .where(sources.c.workspace_id == workspace_id, source_versions.c.id == version_id))).mappings().first()
            if not source or source["kind"] != "video":
                raise Missing("Video version not found in this workspace")
            job = (await connection.execute(select(jobs).where(jobs.c.kind == "video_frames", jobs.c.source_version_id == version_id))).mappings().first()
            checkpoint = json.loads(job["checkpoint_json"]) if job else {}
            visual_job = (await connection.execute(select(jobs).where(jobs.c.kind == "video_frame_visuals",
                jobs.c.source_version_id == version_id))).mappings().first()
            visual_checkpoint = json.loads(visual_job["checkpoint_json"]) if visual_job else {}
            visible = checkpoint.get("frames", [])[offset:offset + 4]
            if visible:
                first, last = min(frame["seconds"] for frame in visible), max(frame["seconds"] for frame in visible)
                audio_rows = (await connection.execute(select(content_units.c.id, content_units.c.metadata_json)
                    .where(content_units.c.source_version_id == version_id,
                        func.json_extract(content_units.c.locator_json, "$.kind") == "time",
                        func.json_extract(content_units.c.locator_json, "$.start_seconds") <= last + 8,
                        func.json_extract(content_units.c.locator_json, "$.end_seconds") >= first - 8))).mappings().all()
            else:
                audio_rows = []
        values = checkpoint.get("frames", [])
        if values and checkpoint.get("source_sha256") != source["sha256"]:
            raise Conflict("Frame source fingerprint changed. Select frames again.")
        from .visual_assets import public_assets
        from .video_frame_visuals import manifest
        import asyncio
        valid_visuals = (visual_checkpoint.get("manifest") == manifest(checkpoint)
            and visual_checkpoint.get("source_sha256") == source["sha256"])
        visual_results = visual_checkpoint.get("results", {}) if valid_visuals else {}
        def nearby_audio(seconds):
            matches = []
            for row in audio_rows:
                metadata = json.loads(row["metadata_json"])
                speech = metadata.get("speech", {})
                for segment in metadata.get("segments", []):
                    if segment["start_seconds"] - 8 <= seconds <= segment["end_seconds"] + 8:
                        matches.append({"unit_id": row["id"], "source_version_id": version_id,
                            "start_seconds": segment["start_seconds"], "end_seconds": segment["end_seconds"],
                            "text": segment["text"][:500], "provider": speech.get("provider", "local"),
                            "review_required": True})
            return sorted(matches, key=lambda item: min(abs(seconds-item["start_seconds"]), abs(seconds-item["end_seconds"])))[:2]
        async def publish(frame):
            asset = (await asyncio.to_thread(public_assets, self.db.root, {"assets": [frame["asset"]]}))["assets"][0]
            if asset.get("error"):
                asset["error"] = "Frame preview missing or damaged. Select frames again; the original is retained."
            return {key: value for key, value in frame.items() if key != "asset"} | {
                "asset": asset, "visual": visual_results.get(frame["id"]),
                "nearby_audio": nearby_audio(frame["seconds"])}
        return {"version_id": version_id, "source_sha256": source["sha256"], "job": public_job(job) if job else None,
            "visual_job": public_job(visual_job) if visual_job else None,
            "total": len(values), "offset": offset, "frames": await asyncio.gather(*(publish(frame) for frame in values[offset:offset + 4]))}

    async def list(self, workspace_id, subject_id=None, limit=50):
        await self.require_workspace(workspace_id)
        query = select(jobs).where(jobs.c.workspace_id == workspace_id)
        if subject_id:
            query = query.where(jobs.c.subject_id == subject_id)
        # Show pending work first; completed history is bounded.
        query = query.order_by(jobs.c.state.in_(["queued", "running"]).desc(), jobs.c.created_at.desc()).limit(limit)
        async with self.db.engine.connect() as connection:
            return [public_job(row) for row in (await connection.execute(query)).mappings()]

    async def get(self, workspace_id, job_id):
        async with self.db.engine.connect() as connection:
            row = (await connection.execute(select(jobs).where(jobs.c.workspace_id == workspace_id, jobs.c.id == job_id))).mappings().first()
            if not row:
                raise Missing("Job not found in this workspace")
            return public_job(row)

    async def verify(self, workspace_id, version_id):
        async with self.db.engine.begin() as connection:
            row = (await connection.execute(select(source_versions, sources.c.subject_id).join(sources, sources.c.id == source_versions.c.source_id)
                .where(sources.c.workspace_id == workspace_id, source_versions.c.id == version_id))).mappings().first()
            if not row:
                raise Missing("Original version not found in this workspace")
            values = job_values(workspace_id, row["subject_id"], version_id, "verify_original", row["filename"], row["size_bytes"])
            await connection.execute(sqlite_insert(jobs).values(**values).on_conflict_do_nothing(index_elements=["kind", "source_version_id"]))
            job_id = (await connection.execute(select(jobs.c.id).where(jobs.c.kind == "verify_original", jobs.c.source_version_id == version_id))).scalar_one()
            await connection.execute(update(jobs).where(jobs.c.id == job_id, jobs.c.state.in_(["succeeded", "failed", "cancelled", "partial"]))
                .values(state="queued", stage="Waiting", done=0, checkpoint_json="{}", result_json=None, error=None,
                    cancel_requested=False, failures=0, owner=None, available_at=time.time(), updated_at=time.time()))
        return await self.get(workspace_id, job_id)

    async def fixture(self, workspace_id, body):
        await self.require_workspace(workspace_id)
        values = job_values(workspace_id, None, None, "queue_fixture", "Queue test · no course processing", body.steps, body.model_dump())
        async with self.db.engine.begin() as connection:
            await connection.execute(insert(jobs).values(**values))
        return await self.get(workspace_id, values["id"])

    async def process_visuals(self, workspace_id, version_id, *, audio=False):
        async with self.db.engine.connect() as connection:
            from sqlalchemy import text
            await connection.execute(text("BEGIN IMMEDIATE"))
            try:
                row = (await connection.execute(select(source_versions, sources.c.kind, sources.c.subject_id).join(sources, sources.c.id == source_versions.c.source_id)
                    .where(sources.c.workspace_id == workspace_id, source_versions.c.id == version_id))).mappings().first()
                if not row:
                    raise Missing("Original version not found in this workspace")
                if row["kind"] not in (("audio", "video") if audio else ("pdf", "slides", "image")):
                    raise Conflict("Audio processing supports audio and video sources." if audio else "Visual processing supports PDF, slides and image sources.")
                cloud = (await connection.execute(select(jobs).where(jobs.c.kind == "cloud_visuals", jobs.c.source_version_id == version_id))).mappings().first()
                if cloud and cloud["state"] in ("queued", "running"):
                    raise Conflict("Cancel cloud visual processing before rebuilding this source.")
                await connection.execute(delete(jobs).where(jobs.c.kind == "cloud_visuals", jobs.c.source_version_id == version_id))
                current = (await connection.execute(select(jobs).where(jobs.c.kind == "extract_source", jobs.c.source_version_id == version_id))).mappings().first()
                if current and current["state"] in ("queued", "running"):
                    raise Conflict("This source is already being processed. Cancel it before starting again.")
                if current:
                    await connection.execute(delete(content_units).where(content_units.c.source_version_id == version_id))
                    await connection.execute(update(jobs).where(jobs.c.id == current["id"]).values(state="queued", stage="Processing audio again" if audio else "Processing visuals again", done=0, total=0,
                        checkpoint_json="{}", result_json=None, error=None, cancel_requested=False, failures=0, owner=None, available_at=time.time(), updated_at=time.time()))
                    job_id = current["id"]
                else:
                    values = job_values(workspace_id, row["subject_id"], version_id, "extract_source", row["filename"], 0)
                    await connection.execute(insert(jobs).values(**values))
                    job_id = values["id"]
                await connection.commit()
            except BaseException:
                await connection.rollback()
                raise
        return await self.get(workspace_id, job_id)

    async def cloud_visuals(self, workspace_id, version_id, body):
        async with self.db.engine.connect() as connection:
            from sqlalchemy import text
            await connection.execute(text("BEGIN IMMEDIATE"))
            try:
                row = (await connection.execute(select(source_versions, sources.c.kind, sources.c.subject_id).join(sources, sources.c.id == source_versions.c.source_id)
                    .where(sources.c.workspace_id == workspace_id, source_versions.c.id == version_id))).mappings().first()
                if not row:
                    raise Missing("Original version not found in this workspace")
                from .cloud_vision import capability
                if not capability()["configured"]:
                    raise Conflict("Set GROQ_API_KEY and restart Neev to enable Groq.")
                extraction = (await connection.execute(select(jobs).where(jobs.c.kind == "extract_source", jobs.c.source_version_id == version_id))).mappings().first()
                if row["kind"] not in ("pdf", "slides", "image") or not extraction or extraction["state"] not in ("succeeded", "partial"):
                    raise Conflict("Finish local visual processing before using cloud extraction.")
                if body.ordinal is not None:
                    unit = (await connection.execute(select(content_units.c.id).where(content_units.c.source_version_id == version_id, content_units.c.ordinal == body.ordinal))).first()
                    if not unit:
                        raise Missing("Source location not found")
                current = (await connection.execute(select(jobs).where(jobs.c.kind == "cloud_visuals", jobs.c.source_version_id == version_id))).mappings().first()
                if current and current["state"] in ("queued", "running"):
                    raise Conflict("Cloud visual processing is already active for this version.")
                values = job_values(workspace_id, row["subject_id"], version_id, "cloud_visuals", row["filename"] + " · Cloud visuals", 0,
                    body.model_dump() | {"run_id": str(uuid4())})
                if current:
                    job_id = current["id"]
                    await connection.execute(update(jobs).where(jobs.c.id == job_id).values(state="queued", stage="Choosing difficult visuals", done=0, total=0,
                        payload_json=values["payload_json"], checkpoint_json="{}", result_json=None, error=None, cancel_requested=False, failures=0,
                        owner=None, available_at=time.time(), updated_at=time.time()))
                else:
                    await connection.execute(insert(jobs).values(**values))
                    job_id = values["id"]
                await connection.commit()
            except BaseException:
                await connection.rollback()
                raise
        return await self.get(workspace_id, job_id)

    async def cancel(self, workspace_id, job_id):
        stamp = time.time()
        async with self.db.engine.begin() as connection:
            await connection.execute(update(jobs).where(jobs.c.workspace_id == workspace_id, jobs.c.id == job_id, jobs.c.state == "queued")
                .values(state="cancelled", stage="Cancelled", cancel_requested=True, updated_at=stamp))
            await connection.execute(update(jobs).where(jobs.c.workspace_id == workspace_id, jobs.c.id == job_id, jobs.c.state == "running")
                .values(cancel_requested=True, updated_at=stamp))
        return await self.get(workspace_id, job_id)

    async def retry(self, workspace_id, job_id):
        stamp = time.time()
        async with self.db.engine.begin() as connection:
            result = await connection.execute(update(jobs).where(jobs.c.workspace_id == workspace_id, jobs.c.id == job_id,
                jobs.c.state.in_(["failed", "cancelled", "partial"])).values(state="queued", stage="Waiting to resume",
                cancel_requested=False, failures=0, error=None, owner=None, result_json=None, available_at=stamp, updated_at=stamp))
            if not result.rowcount:
                row = (await connection.execute(select(jobs.c.id).where(jobs.c.workspace_id == workspace_id, jobs.c.id == job_id))).first()
                if not row:
                    raise Missing("Job not found in this workspace")
                raise Conflict("Only failed, cancelled or partial jobs can be retried")
        return await self.get(workspace_id, job_id)
