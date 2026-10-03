import asyncio
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import delete, event, insert, select, text, tuple_, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import IntegrityError

from .schema import SessionInput, content_units, jobs, sessions, source_versions, sources, subjects, topics, workspaces


def now():
    return datetime.now(timezone.utc).isoformat()


def file_checksum(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


class Missing(Exception):
    pass


class Conflict(Exception):
    pass


def migrate(database_path: Path):
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parent.parent / "migrations"))
    config.attributes["database_path"] = database_path
    command.upgrade(config, "head")


class Database:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.path = self.root / "studylens.sqlite3"
        self.engine = create_async_engine(URL.create("sqlite+aiosqlite", database=str(self.path)))

        @event.listens_for(self.engine.sync_engine, "connect")
        def configure(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    async def initialize(self):
        await asyncio.to_thread(self.root.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(migrate, self.path)
        async with self.engine.begin() as connection:
            await connection.execute(sqlite_insert(workspaces).values(
                id="semester-3", name="Semester 3", name_key="semester 3", revision=0, created_at=now()
            ).on_conflict_do_nothing(index_elements=["id"]))

    async def close(self):
        await self.engine.dispose()

    async def health(self):
        async with self.engine.connect() as connection:
            journal = (await connection.execute(text("PRAGMA journal_mode"))).scalar_one()
            revision = (await connection.execute(text("SELECT version_num FROM alembic_version"))).scalar_one()
            return {"ok": True, "database": "sqlite", "journal_mode": journal, "schema_version": revision}

    async def list_workspaces(self):
        async with self.engine.connect() as connection:
            return [dict(row) for row in (await connection.execute(select(workspaces.c.id, workspaces.c.name).order_by(workspaces.c.created_at, workspaces.c.id))).mappings()]

    async def create_workspace(self, name: str):
        name = name.strip()
        if not name:
            raise ValueError("Enter a workspace name")
        row = {"id": str(uuid4()), "name": name, "name_key": name.casefold(), "revision": 0, "created_at": now()}
        try:
            async with self.engine.begin() as connection:
                await connection.execute(insert(workspaces).values(**row))
        except IntegrityError as error:
            raise Conflict("A workspace with this name already exists") from error
        return {"id": row["id"], "name": name}

    async def load_session(self, workspace_id: str):
        async with self.engine.begin() as connection:
            await connection.execute(text("BEGIN"))
            workspace = (await connection.execute(select(workspaces).where(workspaces.c.id == workspace_id))).mappings().first()
            if not workspace:
                raise Missing("Workspace not found")
            layout = (await connection.execute(select(sessions.c.layout_json).where(sessions.c.workspace_id == workspace_id))).scalar_one_or_none()
            snapshot = None
            if layout is not None:
                snapshot = json.loads(layout)
                snapshot["subjects"] = []
                all_topics = (await connection.execute(select(topics).where(topics.c.workspace_id == workspace_id).order_by(topics.c.position))).mappings().all()
                rows = (await connection.execute(select(subjects).where(subjects.c.workspace_id == workspace_id).order_by(subjects.c.position))).mappings()
                for subject in rows:
                    item = {key: subject[key] for key in ("id", "name", "icon", "demo")}
                    item["topics"] = []
                    for topic in all_topics:
                        if topic["subject_id"] != subject["id"]:
                            continue
                        output = {key: topic[key] for key in ("id", "title", "description", "unit", "read")}
                        if topic["read_minutes"] is not None:
                            output["readMinutes"] = topic["read_minutes"]
                        if topic["lesson"] is not None:
                            output["lesson"] = topic["lesson"]
                        item["topics"].append(output)
                    snapshot["subjects"].append(item)
                SessionInput.model_validate(snapshot)
            return {"workspace": {"id": workspace["id"], "name": workspace["name"]}, "revision": workspace["revision"], "session": snapshot}

    async def save_session(self, workspace_id: str, base_revision: int, snapshot: SessionInput):
        try:
            async with self.engine.begin() as connection:
                result = await connection.execute(update(workspaces).where(
                    workspaces.c.id == workspace_id, workspaces.c.revision == base_revision
                ).values(revision=workspaces.c.revision + 1).returning(workspaces.c.revision))
                revision = result.scalar_one_or_none()
                if revision is None:
                    exists = (await connection.execute(select(workspaces.c.id).where(workspaces.c.id == workspace_id))).scalar_one_or_none()
                    if not exists:
                        raise Missing("Workspace not found")
                    raise Conflict("This workspace changed in another window. Load the saved version before saving again.")
                subject_ids = []
                topic_ids = []
                for position, subject in enumerate(snapshot.subjects):
                    subject_ids.append(subject.id)
                    values = {"workspace_id": workspace_id, "id": subject.id, "name": subject.name.strip(), "name_key": subject.name.strip().casefold(), "icon": subject.icon, "demo": subject.demo, "position": position}
                    await connection.execute(sqlite_insert(subjects).values(**values).on_conflict_do_update(index_elements=["workspace_id", "id"], set_=values))
                    for topic_position, topic in enumerate(subject.topics):
                        topic_ids.append((subject.id, topic.id))
                        values = {"workspace_id": workspace_id, "subject_id": subject.id, "id": topic.id, "title": topic.title.strip(), "title_key": topic.title.strip().casefold(), "description": topic.description, "unit": topic.unit, "read": topic.read, "read_minutes": topic.readMinutes, "lesson": topic.lesson, "position": topic_position}
                        await connection.execute(sqlite_insert(topics).values(**values).on_conflict_do_update(index_elements=["workspace_id", "subject_id", "id"], set_=values))
                await connection.execute(delete(topics).where(topics.c.workspace_id == workspace_id, tuple_(topics.c.subject_id, topics.c.id).not_in(topic_ids)))
                await connection.execute(delete(subjects).where(subjects.c.workspace_id == workspace_id, subjects.c.id.not_in(subject_ids)))
                layout = snapshot.model_dump(exclude_none=True, exclude={"subjects"})
                await connection.execute(sqlite_insert(sessions).values(workspace_id=workspace_id, layout_json=json.dumps(layout, ensure_ascii=False)).on_conflict_do_update(index_elements=["workspace_id"], set_={"layout_json": json.dumps(layout, ensure_ascii=False)}))
                return {"revision": revision}
        except IntegrityError as error:
            raise Conflict("The change conflicts with existing topics or saved materials. No changes were saved.") from error

    async def require_subject(self, workspace_id: str, subject_id: str):
        async with self.engine.connect() as connection:
            exists = (await connection.execute(select(subjects.c.id).where(subjects.c.workspace_id == workspace_id, subjects.c.id == subject_id))).scalar_one_or_none()
            if not exists:
                raise Missing("Subject not found")

    async def list_sources(self, workspace_id: str, subject_id: str):
        await self.require_subject(workspace_id, subject_id)
        async with self.engine.begin() as connection:
            await connection.execute(text("BEGIN"))
            result = (await connection.execute(select(sources).where(sources.c.workspace_id == workspace_id, sources.c.subject_id == subject_id).order_by(sources.c.created_at.desc()))).mappings().all()
            output = []
            for source in result:
                versions = (await connection.execute(select(source_versions).where(source_versions.c.source_id == source["id"]).order_by(source_versions.c.version.desc()))).mappings().all()
                version_output = []
                for version in versions:
                    extraction = (await connection.execute(select(jobs).where(jobs.c.source_version_id == version["id"], jobs.c.kind == "extract_source"))).mappings().first()
                    info = None if not extraction else {
                        "job_id": extraction["id"], "state": extraction["state"], "done": extraction["done"],
                        "total": extraction["total"], "error": extraction["error"],
                        "result": json.loads(extraction["result_json"]) if extraction["result_json"] else None}
                    version_output.append({key: version[key] for key in ("id", "version", "filename", "sha256", "size_bytes", "state", "created_at")} | {"extraction": info})
                output.append({key: source[key] for key in ("id", "display_name", "kind")} | {"versions": version_output})
            return output

    async def register_source(self, workspace_id, subject_id, filename, kind, digest, size, relative_path, source_id=None):
        async with self.engine.connect() as connection:
            await connection.execute(text("BEGIN IMMEDIATE"))
            try:
                subject = (await connection.execute(select(subjects.c.id).where(subjects.c.workspace_id == workspace_id, subjects.c.id == subject_id))).scalar_one_or_none()
                if not subject:
                    raise Missing("Subject not found")
                query = select(sources).where(sources.c.workspace_id == workspace_id, sources.c.subject_id == subject_id)
                query = query.where(sources.c.id == source_id) if source_id else query.where(sources.c.name_key == filename.casefold())
                source = (await connection.execute(query)).mappings().first()
                if source_id and not source:
                    raise Missing("Source not found in this subject")
                if not source:
                    source = {"id": str(uuid4()), "workspace_id": workspace_id, "subject_id": subject_id, "display_name": filename, "name_key": filename.casefold(), "kind": kind, "next_version": 1, "created_at": now()}
                    await connection.execute(insert(sources).values(**source))
                elif source["kind"] != kind:
                    raise Conflict("A new version must have the same material type as the original")
                duplicate = (await connection.execute(select(source_versions).where(source_versions.c.source_id == source["id"], source_versions.c.sha256 == digest))).mappings().first()
                if duplicate:
                    await connection.commit()
                    return {"source_id": source["id"], "version_id": duplicate["id"], "version": duplicate["version"], "duplicate": True}
                version = source["next_version"]
                row = {"id": str(uuid4()), "source_id": source["id"], "version": version, "filename": filename, "sha256": digest, "size_bytes": size, "relative_path": relative_path, "state": "stored", "created_at": now()}
                await connection.execute(insert(source_versions).values(**row))
                from .jobs import job_values
                queued = job_values(workspace_id, subject_id, row["id"], "verify_original", filename, size)
                await connection.execute(insert(jobs).values(**queued))
                if kind in ("pdf", "text", "image", "slides", "audio", "video"):
                    queued = job_values(workspace_id, subject_id, row["id"], "extract_source", filename, 0)
                    await connection.execute(insert(jobs).values(**queued))
                from .video_frames import automatic_enabled
                if kind == "video" and automatic_enabled():
                    queued = job_values(workspace_id, subject_id, row["id"], "video_frames", filename + " · Frames", 0)
                    await connection.execute(insert(jobs).values(**queued))
                await connection.execute(update(sources).where(sources.c.id == source["id"]).values(next_version=version + 1))
                await connection.commit()
                return {"source_id": source["id"], "version_id": row["id"], "version": version, "duplicate": False}
            except BaseException:
                await connection.rollback()
                raise

    async def content(self, workspace_id, version_id, offset=0, limit=20):
        async with self.engine.begin() as connection:
            await connection.execute(text("BEGIN"))
            version = (await connection.execute(select(source_versions, sources.c.kind).join(sources, sources.c.id == source_versions.c.source_id)
                .where(sources.c.workspace_id == workspace_id, source_versions.c.id == version_id))).mappings().first()
            if not version:
                raise Missing("Original version not found in this workspace")
            extraction = (await connection.execute(select(jobs).where(jobs.c.source_version_id == version_id, jobs.c.kind == "extract_source"))).mappings().first()
            cloud = (await connection.execute(select(jobs).where(jobs.c.source_version_id == version_id, jobs.c.kind == "cloud_visuals"))).mappings().first()
            integrity = (await connection.execute(select(jobs.c.state).where(jobs.c.source_version_id == version_id, jobs.c.kind == "verify_original"))).scalar_one_or_none()
            rows = (await connection.execute(select(content_units).where(content_units.c.source_version_id == version_id)
                .order_by(content_units.c.ordinal).offset(offset).limit(limit))).mappings().all()
            units = [{"id": row["id"], "ordinal": row["ordinal"], "locator": json.loads(row["locator_json"]),
                "text": row["text"], "text_sha256": row["text_sha256"], "status": row["status"],
                "warning": row["warning"], "engine": row["engine"],
                "metadata": json.loads(row["metadata_json"])} for row in rows]
            from .visual_assets import public_assets
            from .jobs import public_job
            for unit in units:
                unit["metadata"] = await asyncio.to_thread(public_assets, self.root, unit["metadata"])
            return {"version_id": version_id, "filename": version["filename"], "version": version["version"], "kind": version["kind"],
                "sha256": version["sha256"], "integrity_verified": integrity == "succeeded",
                "state": extraction["state"] if extraction else "unsupported", "error": extraction["error"] if extraction else None,
                "total": extraction["total"] if extraction else 0, "completed": extraction["done"] if extraction else 0,
                "result": json.loads(extraction["result_json"]) if extraction and extraction["result_json"] else None,
                "offset": offset, "units": units, "cloud_job": public_job(cloud) if cloud else None}

    async def version_file(self, version_id: str, workspace_id=None, *, video_only=False, checksum_cache=None):
        async with self.engine.connect() as connection:
            query = select(source_versions, sources.c.kind).join(sources, sources.c.id == source_versions.c.source_id).where(source_versions.c.id == version_id)
            if workspace_id is not None:
                query = query.where(sources.c.workspace_id == workspace_id)
            row = (await connection.execute(query)).mappings().first()
            if not row or (video_only and row["kind"] != "video"):
                raise Missing("Source version not found")
            target = (self.root / row["relative_path"]).resolve()
            originals = (self.root / "originals").resolve()
            if not target.is_relative_to(originals) or not target.is_file() or target.stat().st_size != row["size_bytes"]:
                raise Missing("The original file is missing or damaged")
            stat = target.stat()
            signature = (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_ino)
            cache_key = (str(target), row["sha256"])
            if checksum_cache is None or checksum_cache.get(cache_key) != signature:
                if await asyncio.to_thread(file_checksum, target) != row["sha256"]:
                    if checksum_cache is not None:
                        checksum_cache.pop(cache_key, None)
                    raise Missing("The original file failed its integrity check")
                after = target.stat()
                if signature != (after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_ino):
                    raise Missing("The original changed during its integrity check")
                if checksum_cache is not None:
                    if len(checksum_cache) >= 128:
                        checksum_cache.pop(next(iter(checksum_cache)))
                    checksum_cache[cache_key] = signature
            return target, row["filename"]
