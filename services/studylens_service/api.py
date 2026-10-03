import asyncio
import hashlib
import hmac
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.requests import ClientDisconnect

from .database import Conflict, Database, Missing, file_checksum
from .schema import CloudVisualRequest, CreateWorkspace, QueueFixture, SaveSession, YouTubeImport
from .jobs import JobStore
from .supervisor import WorkerSupervisor

TYPES = {
    ".pdf": "pdf", ".txt": "text", ".md": "text",
    ".ppt": "slides", ".pptx": "slides",
    ".mp4": "video", ".mkv": "video", ".mov": "video", ".webm": "video",
    ".mp3": "audio", ".wav": "audio", ".m4a": "audio", ".ogg": "audio", ".flac": "audio",
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image", ".tif": "image", ".tiff": "image", ".bmp": "image",
}


def create_app(root: Path, token: str, *, max_file_bytes=2 * 1024**3, ready=None, shutdown=None, start_worker=False, allow_eval=False):
    if len(token) < 24:
        raise ValueError("A fresh local service token is required")
    db = Database(root)
    queue = JobStore(db)
    worker = WorkerSupervisor(db.root, allow_eval)

    @asynccontextmanager
    async def lifespan(_app):
        await db.initialize()
        await asyncio.to_thread((db.root / "staging").mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread((db.root / "originals").mkdir, parents=True, exist_ok=True)
        await queue.backfill()
        if start_worker:
            await worker.start()
        if ready:
            ready()
        try:
            yield
        finally:
            await worker.stop()
            await db.close()

    app = FastAPI(title="Neev local service", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.database = db
    app.state.worker_supervisor = worker
    media_checks = {}
    media_lock = asyncio.Lock()

    @app.middleware("http")
    async def local_auth(request: Request, call_next):
        expected = "Bearer " + token
        if not hmac.compare_digest(request.headers.get("authorization", ""), expected):
            return JSONResponse({"detail": "Local service authorization required"}, status_code=401)
        origin = request.headers.get("origin")
        if origin and origin not in ("http://127.0.0.1:5173", "http://localhost:5173"):
            return JSONResponse({"detail": "Origin is not allowed"}, status_code=403)
        length = request.headers.get("content-length")
        limit = max_file_bytes if "/sources" in request.url.path else 1_000_000
        if length and (not length.isdigit() or int(length) > limit):
            return JSONResponse({"detail": "This request is too large"}, status_code=413)
        return await call_next(request)

    @app.exception_handler(Missing)
    async def missing(_request, error):
        return JSONResponse({"detail": str(error)}, status_code=404)

    @app.exception_handler(Conflict)
    async def conflict(_request, error):
        return JSONResponse({"detail": str(error)}, status_code=409)

    @app.get("/health")
    async def health():
        return await db.health() | {"queue": worker.status()}

    @app.get("/queue")
    async def queue_status():
        return worker.status()

    @app.get("/vision")
    async def vision_status():
        from .cloud_vision import capability
        return capability()

    @app.get("/audio")
    async def audio_status():
        from .audio import capability
        return await asyncio.to_thread(capability)

    @app.post("/workspaces/{workspace_id}/source-versions/{version_id}/process-audio", status_code=202)
    async def process_audio(workspace_id: str, version_id: str):
        return await queue.process_visuals(workspace_id, version_id, audio=True)

    @app.post("/workspaces/{workspace_id}/source-versions/{version_id}/process-video-frames", status_code=202)
    async def process_frames(workspace_id: str, version_id: str):
        return await queue.process_frames(workspace_id, version_id)

    @app.get("/workspaces/{workspace_id}/source-versions/{version_id}/video-frames")
    async def video_frames(workspace_id: str, version_id: str, offset: int = 0):
        if not 0 <= offset <= 600:
            raise HTTPException(422, "Choose a frame offset from 0 to 600")
        return await queue.frames(workspace_id, version_id, offset)

    @app.post("/workspaces/{workspace_id}/source-versions/{version_id}/cloud-visuals", status_code=202)
    async def cloud_visuals(workspace_id: str, version_id: str, body: CloudVisualRequest):
        return await queue.cloud_visuals(workspace_id, version_id, body)

    @app.get("/workspaces/{workspace_id}/jobs")
    async def list_jobs(workspace_id: str, subject_id: str | None = None, limit: int = 50):
        if not 1 <= limit <= 100:
            raise HTTPException(422, "Choose a job page size between 1 and 100")
        return await queue.list(workspace_id, subject_id, limit)

    @app.get("/workspaces/{workspace_id}/jobs/{job_id}")
    async def get_job(workspace_id: str, job_id: str):
        return await queue.get(workspace_id, job_id)

    @app.get("/workspaces/{workspace_id}/source-versions/{version_id}/content")
    async def content(workspace_id: str, version_id: str, offset: int = 0, limit: int = 1):
        if not 0 <= offset <= 10000 or not 1 <= limit <= 10:
            raise HTTPException(422, "Choose a content offset from 0 to 10000 and a page size from 1 to 10")
        return await db.content(workspace_id, version_id, offset, limit)

    @app.post("/workspaces/{workspace_id}/source-versions/{version_id}/verify", status_code=202)
    async def verify_original(workspace_id: str, version_id: str):
        return await queue.verify(workspace_id, version_id)

    @app.post("/workspaces/{workspace_id}/source-versions/{version_id}/process-visuals", status_code=202)
    async def process_visuals(workspace_id: str, version_id: str):
        return await queue.process_visuals(workspace_id, version_id)

    @app.post("/workspaces/{workspace_id}/jobs/{job_id}/cancel")
    async def cancel_job(workspace_id: str, job_id: str):
        return await queue.cancel(workspace_id, job_id)

    @app.post("/workspaces/{workspace_id}/jobs/{job_id}/retry", status_code=202)
    async def retry_job(workspace_id: str, job_id: str):
        return await queue.retry(workspace_id, job_id)

    @app.post("/workspaces/{workspace_id}/queue-test", status_code=202)
    async def test_queue(workspace_id: str, body: QueueFixture):
        if not allow_eval:
            raise HTTPException(404, "Queue evaluation is disabled")
        return await queue.fixture(workspace_id, body)

    @app.get("/workspaces")
    async def list_workspaces():
        return await db.list_workspaces()

    @app.post("/workspaces", status_code=201)
    async def create_workspace(body: CreateWorkspace):
        try:
            return await db.create_workspace(body.name)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @app.get("/workspaces/{workspace_id}/session")
    async def load_session(workspace_id: str):
        return await db.load_session(workspace_id)

    @app.put("/workspaces/{workspace_id}/session")
    async def save_session(workspace_id: str, body: SaveSession):
        return await db.save_session(workspace_id, body.base_revision, body.session)

    @app.get("/workspaces/{workspace_id}/subjects/{subject_id}/sources")
    async def list_sources(workspace_id: str, subject_id: str):
        return await db.list_sources(workspace_id, subject_id)

    @app.post("/workspaces/{workspace_id}/subjects/{subject_id}/youtube", status_code=202)
    async def import_youtube(workspace_id: str, subject_id: str, body: YouTubeImport):
        try:
            return await queue.import_youtube(workspace_id, subject_id, body)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @app.post("/workspaces/{workspace_id}/subjects/{subject_id}/sources", status_code=201)
    async def upload(request: Request, workspace_id: str, subject_id: str, filename: str, source_id: str | None = None):
        if not filename or len(filename) > 255 or any(char in filename for char in ("\\", "/", "\0", ":")) or filename in (".", ".."):
            raise HTTPException(422, "Choose a valid original filename")
        kind = TYPES.get(Path(filename).suffix.lower())
        if not kind:
            raise HTTPException(415, "This file type is not supported")
        await db.require_subject(workspace_id, subject_id)
        staging = db.root / "staging" / (str(uuid4()) + ".part")
        digest = hashlib.sha256()
        size = 0
        handle = None
        try:
            handle = await asyncio.to_thread(staging.open, "xb")
            async for chunk in request.stream():
                size += len(chunk)
                if size > max_file_bytes:
                    raise HTTPException(413, "File exceeds the 2 GB import limit")
                digest.update(chunk)
                await asyncio.to_thread(handle.write, chunk)
            if size == 0:
                raise HTTPException(422, "The file is empty")
            await asyncio.to_thread(handle.flush)
            await asyncio.to_thread(os.fsync, handle.fileno())
            await asyncio.to_thread(handle.close)
            checksum = digest.hexdigest()
            relative = f"originals/{checksum[:2]}/{checksum}"
            blob = db.root / relative
            await asyncio.to_thread(blob.parent.mkdir, parents=True, exist_ok=True)
            try:
                await asyncio.to_thread(os.link, staging, blob)
            except FileExistsError:
                if blob.stat().st_size != size or await asyncio.to_thread(file_checksum, blob) != checksum:
                    raise HTTPException(500, "The existing original file needs integrity review")
            return await db.register_source(workspace_id, subject_id, filename, kind, checksum, size, relative, source_id)
        except ClientDisconnect as error:
            raise HTTPException(400, "Upload was interrupted") from error
        except OSError as error:
            raise HTTPException(507, "Original file could not be saved. Check available disk space.") from error
        finally:
            if handle is not None and not handle.closed:
                await asyncio.to_thread(handle.close)
            await asyncio.to_thread(staging.unlink, missing_ok=True)

    @app.get("/source-versions/{version_id}/file")
    async def original(version_id: str):
        target, filename = await db.version_file(version_id)
        return FileResponse(target, media_type="application/octet-stream", filename=filename)

    @app.api_route("/workspaces/{workspace_id}/source-versions/{version_id}/playback", methods=["GET", "HEAD"])
    async def video_playback(workspace_id: str, version_id: str, request: Request):
        selected_range = request.headers.get("range")
        if selected_range and (len(selected_range) > 100 or not re.fullmatch(r"bytes=(?:\d+-\d*|-\d+)", selected_range)):
            raise HTTPException(416, "Choose one valid byte range")
        if selected_range:
            left, right = selected_range[6:].split("-")
            if left and right and int(right) < int(left):
                raise HTTPException(416, "Byte range end precedes its start")
        # Hash once per unchanged file signature, not once per browser seek. The
        # workspace/type/path/size boundary is still checked on every request.
        async with media_lock:
            target, filename = await db.version_file(version_id, workspace_id, video_only=True, checksum_cache=media_checks)
        mime = {".mp4": "video/mp4", ".mov": "video/quicktime", ".mkv": "video/x-matroska", ".webm": "video/webm"}
        return FileResponse(target, media_type=mime.get(Path(filename).suffix.lower(), "application/octet-stream"),
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})

    @app.get("/storage")
    async def storage():
        return {"data_directory": str(db.root), "database_path": str(db.path), "originals_directory": str(db.root / "originals"), "max_file_bytes": max_file_bytes}

    @app.post("/shutdown")
    async def stop():
        if shutdown:
            shutdown()
        return {"ok": True}

    return app
