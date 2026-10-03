"""Student-supplied local video associations for saved YouTube caption sources."""
import json

from sqlalchemy import insert, select, text

from .database import Conflict, Missing, now
from .schema import jobs, youtube_media_links


class YouTubeMediaStore:
    def __init__(self, database):
        self.db = database

    @staticmethod
    async def version(connection, version_id):
        return (await connection.execute(text("""SELECT v.id,v.source_id,v.filename,v.sha256,
            s.kind,s.workspace_id,s.subject_id FROM source_versions v
            JOIN sources s ON s.id=v.source_id WHERE v.id=:version_id"""),
            {"version_id": version_id})).mappings().first()

    async def by_source(self, connection, youtube_source_id):
        latest = (await connection.execute(select(youtube_media_links)
            .where(youtube_media_links.c.youtube_source_id == youtube_source_id)
            .order_by(youtube_media_links.c.id.desc()).limit(1))).mappings().first()
        if not latest or not latest["media_version_id"]:
            return None
        media = await self.version(connection, latest["media_version_id"])
        if not media or media["kind"] != "video":
            return None
        frame = (await connection.execute(select(jobs.c.state, jobs.c.result_json).where(
            jobs.c.source_version_id == media["id"], jobs.c.kind == "video_frames"))).mappings().first()
        visual = (await connection.execute(select(jobs.c.state).where(
            jobs.c.source_version_id == media["id"], jobs.c.kind == "video_frame_visuals"))).mappings().first()
        audio = (await connection.execute(select(jobs.c.state).where(
            jobs.c.source_version_id == media["id"], jobs.c.kind == "extract_source"))).mappings().first()
        frame_result = json.loads(frame["result_json"]) if frame and frame["result_json"] else {}
        return {"media_version_id": media["id"], "filename": media["filename"], "sha256": media["sha256"],
            "caption_version_id_at_link": latest["caption_version_id"],
            "youtube_start_seconds": latest["youtube_start_seconds"], "created_at": latest["created_at"],
            "provenance": "student_supplied_local_copy", "match_verified": False,
            "audio_state": audio["state"] if audio else None,
            "frames_state": frame["state"] if frame else None,
            "visual_state": visual["state"] if visual else None,
            "duration_seconds": frame_result.get("scanned_seconds")}

    async def get(self, workspace_id, caption_version_id):
        async with self.db.engine.connect() as connection:
            caption = await self.version(connection, caption_version_id)
            if not caption or caption["workspace_id"] != workspace_id or caption["kind"] != "youtube":
                raise Missing("Saved YouTube source not found in this workspace")
            return {"caption_version_id": caption_version_id,
                "media": await self.by_source(connection, caption["source_id"])}

    async def attach(self, workspace_id, caption_version_id, body):
        async with self.db.engine.connect() as connection:
            caption = await self.version(connection, caption_version_id)
            media = await self.version(connection, body.media_version_id)
            if not caption or caption["workspace_id"] != workspace_id or caption["kind"] != "youtube":
                raise Missing("Saved YouTube source not found in this workspace")
            if not media or media["workspace_id"] != workspace_id or media["subject_id"] != caption["subject_id"]:
                raise Missing("Local video version not found in this subject")
            if media["kind"] != "video":
                raise Conflict("Choose an uploaded video version.")
        # Rehash outside the write transaction; the normal playback path checks
        # the immutable original again when the student opens it.
        await self.db.version_file(body.media_version_id, workspace_id, video_only=True)
        async with self.db.engine.connect() as connection:
            await connection.execute(text("BEGIN IMMEDIATE"))
            try:
                caption = await self.version(connection, caption_version_id)
                media = await self.version(connection, body.media_version_id)
                if not caption or caption["workspace_id"] != workspace_id or caption["kind"] != "youtube":
                    raise Missing("Saved YouTube source not found in this workspace")
                if not media or media["workspace_id"] != workspace_id or media["subject_id"] != caption["subject_id"]:
                    raise Missing("Local video version not found in this subject")
                if media["kind"] != "video":
                    raise Conflict("Choose an uploaded video version.")
                current = (await connection.execute(select(youtube_media_links)
                    .where(youtube_media_links.c.youtube_source_id == caption["source_id"])
                    .order_by(youtube_media_links.c.id.desc()).limit(1))).mappings().first()
                if not current or current["media_version_id"] != media["id"] or current["youtube_start_seconds"] != body.youtube_start_seconds:
                    await connection.execute(insert(youtube_media_links).values(
                        youtube_source_id=caption["source_id"], caption_version_id=caption_version_id,
                        media_version_id=media["id"], youtube_start_seconds=body.youtube_start_seconds,
                        created_at=now()))
                await connection.commit()
            except BaseException:
                await connection.rollback()
                raise
        return await self.get(workspace_id, caption_version_id)

    async def detach(self, workspace_id, caption_version_id):
        async with self.db.engine.connect() as connection:
            await connection.execute(text("BEGIN IMMEDIATE"))
            try:
                caption = await self.version(connection, caption_version_id)
                if not caption or caption["workspace_id"] != workspace_id or caption["kind"] != "youtube":
                    raise Missing("Saved YouTube source not found in this workspace")
                current = (await connection.execute(select(youtube_media_links)
                    .where(youtube_media_links.c.youtube_source_id == caption["source_id"])
                    .order_by(youtube_media_links.c.id.desc()).limit(1))).mappings().first()
                if current and current["media_version_id"]:
                    await connection.execute(insert(youtube_media_links).values(
                        youtube_source_id=caption["source_id"], caption_version_id=caption_version_id,
                        media_version_id=None, youtube_start_seconds=0, created_at=now()))
                await connection.commit()
            except BaseException:
                await connection.rollback()
                raise
        return await self.get(workspace_id, caption_version_id)
