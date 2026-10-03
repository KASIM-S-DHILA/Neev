"""Page/line-bound extraction. Runs only inside the single heavy worker."""
import hashlib
import json
from uuid import NAMESPACE_URL, uuid5
from .job_errors import Cancelled, Interrupted, ExtractionFailure

PDF_MAX_BYTES = 64 * 1024**2
TEXT_MAX_BYTES = 16 * 1024**2
PAGE_MAX_BYTES = 1024**2
PAGE_MAX_CHARS = 50000
PDF_MAX_PAGES = 500
CHUNK_CHARS = 4000


def text_chunks(text):
    """Exact offsets in decoded Unicode, preserving original CR/LF and line ends."""
    offset = 0
    line = 1
    start = 0
    first_line = 1
    parts = []
    length = 0
    last_line = 1
    for piece in text.splitlines(keepends=True):
        # Long lines remain bounded; adjacent units can refer to the same line.
        for index in range(0, len(piece), CHUNK_CHARS):
            segment = piece[index:index + CHUNK_CHARS]
            if parts and length + len(segment) > CHUNK_CHARS:
                yield "".join(parts), {"kind": "lines", "line_start": first_line, "line_end": last_line,
                    "char_start": start, "char_end": offset}
                parts, length, start, first_line = [], 0, offset, line
            parts.append(segment)
            length += len(segment)
            offset += len(segment)
            last_line = line
        # A unit boundary immediately after a newline belongs to the prior line.
        if piece.endswith(("\n", "\r", "\v", "\f", "\x85", "\u2028", "\u2029")):
            line += 1
        if length >= CHUNK_CHARS or len(parts) >= 80:
            yield "".join(parts), {"kind": "lines", "line_start": first_line,
                "line_end": last_line,
                "char_start": start, "char_end": offset}
            parts, length, start, first_line = [], 0, offset, line
    if parts:
        yield "".join(parts), {"kind": "lines", "line_start": first_line,
            "line_end": last_line, "char_start": start, "char_end": offset}


def image_resources(resources, depth=0, visited=None):
    """Detect image references without decoding their image buffers."""
    if not resources:
        return False
    resources = resources.get_object() if hasattr(resources, "get_object") else resources
    if depth >= 4:
        return True  # Treat overly deep graphics as needing visual review.
    visited = set() if visited is None else visited
    objects = resources.get("/XObject", {})
    objects = objects.get_object() if hasattr(objects, "get_object") else objects
    if len(objects) > 200:
        return True
    for reference in objects.values():
        key = (getattr(reference, "idnum", None), getattr(reference, "generation", None))
        if key[0] is not None and key in visited:
            continue
        visited.add(key)
        item = reference.get_object()
        if item.get("/Subtype") == "/Image":
            return True
        if item.get("/Subtype") == "/Form" and image_resources(item.get("/Resources"), depth + 1, visited):
            return True
    return False


def commit_unit(worker, job, ordinal, total, value, locator, status, warning, engine, metadata=None, *, checkpoint_extra=None, stage="Extracting source text"):
    unit_id = str(uuid5(NAMESPACE_URL, f"studylens:{job['source_version_id']}:{ordinal}"))
    connection = worker.connection
    connection.execute("BEGIN IMMEDIATE")
    try:
        worker.check(job)
        connection.execute("""INSERT INTO content_units
            (id,source_version_id,job_id,ordinal,locator_json,text,text_sha256,status,warning,engine,metadata_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(source_version_id,ordinal) DO UPDATE SET
            locator_json=excluded.locator_json,text=excluded.text,text_sha256=excluded.text_sha256,
            status=excluded.status,warning=excluded.warning,engine=excluded.engine,metadata_json=excluded.metadata_json""",
            (unit_id, job["source_version_id"], job["id"], ordinal, json.dumps(locator), value,
             hashlib.sha256(value.encode("utf-8")).hexdigest(), status, warning, engine, json.dumps(metadata or {})))
        worker.checkpoint(job, ordinal, total, stage, {"completed_units": ordinal, "engine": engine} | (checkpoint_extra or {}))
        connection.commit()
    except BaseException:
        connection.rollback()
        raise


def extract(worker, job, guard):
    row = worker.connection.execute("""SELECT v.*,s.kind FROM source_versions v
        JOIN sources s ON s.id=v.source_id WHERE v.id=?""", (job["source_version_id"],)).fetchone()
    if not row or row["kind"] not in ("pdf", "text", "image", "slides", "audio", "video", "youtube"):
        raise ExtractionFailure("This material type does not have a processor yet.")
    verified = worker.connection.execute("SELECT state FROM jobs WHERE source_version_id=? AND kind='verify_original'",
        (row["id"],)).fetchone()
    if not verified or verified[0] != "succeeded":
        raise ExtractionFailure("The original check did not complete. Check or resume the original first, then resume extraction.")
    target = (worker.root / row["relative_path"]).resolve()
    if not target.is_relative_to((worker.root / "originals").resolve()) or not target.is_file():
        raise ExtractionFailure("The original file is missing. Restore it or import a new version.")
    maximum = 2 * 1024**3 if row["kind"] in ("audio", "video") else TEXT_MAX_BYTES if row["kind"] == "text" else PDF_MAX_BYTES
    if row["size_bytes"] > maximum:
        raise ExtractionFailure(f"The original is saved, but processing currently supports {'text files up to 16 MB' if row['kind'] == 'text' else 'PDF, slide and image files up to 64 MB'}. Split it into smaller files.")
    # Verify again: an external edit after the first job must never create source evidence.
    digest = hashlib.sha256()
    with target.open("rb") as stream:
        while chunk := stream.read(1024**2):
            worker.check(job)
            guard.touch()
            digest.update(chunk)
    if target.stat().st_size != row["size_bytes"] or digest.hexdigest() != row["sha256"]:
        raise ExtractionFailure("The original changed after its integrity check. Restore it or import a new version.")
    checkpoint = json.loads(job["checkpoint_json"])
    completed = checkpoint.get("completed_units", 0)
    if row["kind"] == "youtube":
        from .youtube import extract as extract_youtube
        return extract_youtube(worker, job, guard, row, target, completed)
    elif row["kind"] == "video":
        from .video import extract_video
        extract_video(worker, job, guard, row, target, completed)
    elif row["kind"] == "audio":
        from .audio import extract_audio
        extract_audio(worker, job, guard, row, target, completed)
    elif row["kind"] in ("image", "slides"):
        from .visual import extract_visual
        extract_visual(worker, job, guard, row, target, completed)
    elif row["kind"] == "text":
        data = target.read_bytes()
        encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
        try:
            value = data.decode(encoding)
        except UnicodeDecodeError as error:
            raise ExtractionFailure("This text file is not UTF-8 or BOM-marked UTF-16. Save an encoded text copy and import it.") from error
        if any(ord(char) < 32 and char not in "\r\n\t\f" for char in value):
            raise ExtractionFailure("This file contains binary/control bytes. Import a plain UTF-8 or UTF-16 text copy.")
        units = list(text_chunks(value))
        total = len(units)
        worker.checkpoint(job, completed, total, "Extracting source text", checkpoint)
        for index, (text, locator) in enumerate(units, 1):
            worker.check(job)
            guard.touch()
            if index <= completed:
                continue
            locator["encoding"] = encoding
            commit_unit(worker, job, index, total, text, locator, "text" if text.strip() else "empty", None, "text-v1")
    else:
        from pypdf import PdfReader, apply_configuration
        from pypdf.errors import LimitReachedError
        import logging
        logging.getLogger("pypdf").setLevel(logging.ERROR)
        with apply_configuration(maximum_declared_stream_length=8 * 1024**2,
                zlib_maximum_output_length=8 * 1024**2, lzw_maximum_output_length=8 * 1024**2,
                run_length_maximum_output_length=8 * 1024**2, array_based_stream_maximum_output_length=8 * 1024**2,
                page_tree_maximum_entries=2000, xform_maximum_invocations_per_extraction=500):
            try:
                reader = PdfReader(target, strict=True)
                if reader.is_encrypted:
                    raise ExtractionFailure("This PDF is encrypted. Import an unencrypted copy; the original stays saved.")
                total = len(reader.pages)
                if total > PDF_MAX_PAGES:
                    raise ExtractionFailure("PDF text extraction currently supports up to 500 pages. Split the PDF into smaller files.")
                if not total:
                    raise ExtractionFailure("This PDF has no pages.")
                worker.checkpoint(job, completed, total, "Extracting source text", checkpoint)
                for index in range(completed, total):
                    worker.check(job)
                    guard.touch()
                    locator = {"kind": "page", "page": index + 1}
                    text, status, warning = "", "text", None
                    try:
                        page = reader.pages[index]
                        locator.update(width=float(page.mediabox.width), height=float(page.mediabox.height), rotation=int(page.rotation))
                        contents = page.get_contents()
                        raw = contents.get_data() if contents is not None else b""
                        if len(raw) > PAGE_MAX_BYTES:
                            status, warning = "too_large", "This page exceeds the extraction limit. Review the original or export a simpler copy."
                        else:
                            text = page.extract_text() or ""
                            images = image_resources(page.get("/Resources")) or b" BI" in raw or raw.startswith(b"BI")
                            if len(text) > PAGE_MAX_CHARS:
                                text, status, warning = "", "too_large", "This page contains too much text for a bounded preview. Review the original."
                            elif images and sum(char.isalnum() for char in text) < 25:
                                status, warning = "needs_ocr", "Image-like page with little extractable text. OCR is needed; this detection is a heuristic."
                            elif not text.strip():
                                status, warning = "empty", "No extractable text found. This may be blank or contain vector graphics; check the original."
                            elif "\ufffd" in text or any(ord(char) < 32 and char not in "\r\n\t\f" for char in text):
                                status, warning = "suspect", "Some characters could not be read reliably. Review the original before using this text."
                            elif images:
                                warning = "Text layer extracted; image and diagram content still needs visual review."
                    except LimitReachedError:
                        status, warning = "too_large", "Page decoding exceeded the resource limit. Review the original or export a simpler copy."
                    except Exception:
                        status, warning = "unreadable", "This page could not be read. Other readable pages are retained."
                    metadata = {}
                    engine = "pypdf-6.19.0"
                    if status not in ("too_large", "unreadable"):
                        from .visual import pdf_visual
                        text, status, warning, metadata = pdf_visual(worker, job, guard, target,
                            index, text, status, warning)
                        if metadata.get("ocr"):
                            engine += "+tesseract"
                    commit_unit(worker, job, index + 1, total, text, locator, status, warning, engine, metadata)
            except (ExtractionFailure, Cancelled, Interrupted):
                raise
            except Exception as error:
                raise ExtractionFailure("Could not read this PDF. It may be corrupt or malformed. Import an unencrypted exported copy.") from error
            finally:
                if "reader" in locals():
                    reader.close()
    rows = worker.connection.execute("SELECT status,warning FROM content_units WHERE source_version_id=? ORDER BY ordinal", (row["id"],)).fetchall()
    counts = {key: sum(unit["status"] == key for unit in rows) for key in ("text", "needs_ocr", "empty", "unreadable", "too_large", "suspect")}
    return {"units": len(rows), "counts": counts, "warnings": sum(bool(unit["warning"]) for unit in rows),
        "text_only": row["kind"] == "text", "processor_revision": 6, "source_sha256": row["sha256"]}
