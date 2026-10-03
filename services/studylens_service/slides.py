"""Bounded OpenXML extraction; optional isolated LibreOffice slide rendering."""
import io
import posixpath
import tempfile
import zipfile
from pathlib import Path
from defusedxml.ElementTree import fromstring, tostring
from .job_errors import Cancelled, Interrupted, ExtractionFailure
from .local_tools import find_tool, run_tool

NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math"}
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
ENTRY_LIMIT = 10 * 1024**2


def read_part(archive, name):
    if name not in archive.namelist():
        raise ExtractionFailure("Slide package is missing a required part. Export a new PPTX/PDF copy.")
    info = archive.getinfo(name)
    if info.file_size > ENTRY_LIMIT:
        raise ExtractionFailure("A slide package part exceeds 10 MB. Export smaller images or split the deck.")
    return archive.read(name)


def relationships(archive, part):
    name = posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")
    if name not in archive.namelist():
        return {}, False
    root = fromstring(read_part(archive, name))
    result, external = {}, False
    for item in root:
        if item.get("TargetMode") == "External":
            external = True
            continue  # Never request a linked image, hyperlink, or remote resource.
        target = posixpath.normpath(posixpath.join(posixpath.dirname(part), item.get("Target", "")))
        if target.startswith(("../", "/")) or "\\" in target or ":" in target:
            raise ExtractionFailure("Slide package contains an invalid relationship path.")
        result[item.get("Id")] = target
    return result, external


def convert_deck(worker, job, guard, target, folder):
    tool = find_tool("soffice")
    if not tool:
        return None
    # Give LO a named input suffix; stored originals deliberately have hash-only filenames.
    import shutil
    filename = json_filename(worker, job)
    source = folder / ("source" + Path(filename).suffix.lower())
    shutil.copyfile(target, source)
    profile_directory = folder / "office-profile"
    (profile_directory / "user").mkdir(parents=True, exist_ok=True)
    (profile_directory / "user/registrymodifications.xcu").write_text(
        '<?xml version="1.0"?><oor:items xmlns:oor="http://openoffice.org/2001/registry">'
        '<item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop></item>'
        '</oor:items>', encoding="utf-8")
    profile = profile_directory.as_uri()
    run_tool([tool, "-env:UserInstallation=" + profile, "--headless", "--nologo", "--nodefault",
        "--norestore", "--convert-to", "pdf:impress_pdf_Export", "--outdir", str(folder), str(source)],
        worker, job, guard, folder, timeout=30)
    converted = folder / "source.pdf"
    if not converted.is_file() or converted.stat().st_size > 64 * 1024**2:
        raise ExtractionFailure("Slide conversion returned no bounded PDF. Export the deck to PDF manually.")
    return converted


def json_filename(worker, job):
    return worker.connection.execute("SELECT filename FROM source_versions WHERE id=?", (job["source_version_id"],)).fetchone()[0]


def native_tables(tree):
    tables = []
    for table in tree.findall(".//a:tbl", NS):
        rows, notes = [], []
        source_rows = table.findall("a:tr", NS)
        if len(source_rows) > 160 or len(tables) >= 12:
            raise ExtractionFailure("A slide exceeds native table limits. Split the deck or export to PDF.")
        for row in source_rows:
            cells = row.findall("a:tc", NS)
            if len(cells) > 30:
                raise ExtractionFailure("A native table exceeds 30 columns. Split it or export to PDF.")
            rows.append(["\n".join("".join(node.text or "" for node in paragraph.findall(".//a:t", NS))
                for paragraph in cell.findall(".//a:p", NS)) for cell in cells])
            if any(any(cell.get(key) not in (None, "0", "1") for key in ("gridSpan", "rowSpan")) or
                   any(cell.get(key) == "1" for key in ("hMerge", "vMerge")) for cell in cells):
                notes = ["Merged cells are preserved in grid order; compare spans with the original."]
        if rows:
            # Preserve literal grid order; do not guess whether the first row is a header.
            tables.append({"headers": [], "rows": rows, "notes": notes})
    return tables


def extract_slides(worker, job, guard, row, target, completed):
    from .extraction import commit_unit
    from .visual import ocr, prepare, render_pdf, visual_notes
    from .visual_assets import save_preview
    from PIL import Image
    suffix = Path(row["filename"]).suffix.lower()
    with tempfile.TemporaryDirectory(prefix="slides-", dir=worker.root / "staging") as directory:
        folder = Path(directory)
        converted, conversion_warning = None, None
        try:
            safe_to_render = suffix == ".pptx"
            if safe_to_render:
                with zipfile.ZipFile(target) as package:
                    entries = package.infolist()
                    if len(entries) > 5000 or len({entry.filename for entry in entries}) != len(entries) or sum(entry.file_size for entry in entries) > 100 * 1024**2:
                        raise ExtractionFailure("Slide package exceeds decompressed limits.")
                    for entry in entries:
                        worker.check(job)
                        guard.touch()
                        if "vbaproject" in entry.filename.lower() or "/embeddings/" in entry.filename.lower():
                            safe_to_render = False
                        if entry.filename.endswith((".xml", ".rels")):
                            # Reject unsafe/malformed XML before handing it to the converter.
                            rels = fromstring(read_part(package, entry.filename))
                        if entry.filename.endswith(".rels"):
                            if any(item.get("TargetMode") == "External" for item in rels):
                                safe_to_render = False
            if safe_to_render:
                converted = convert_deck(worker, job, guard, target, folder)
            else:
                conversion_warning = "Automatic slide rendering was skipped for a legacy or externally linked deck. Export to PDF for a full preview."
        except (Cancelled, Interrupted):
            raise
        except Exception:
            conversion_warning = "Full slide rendering failed. Native text and embedded pictures are retained; export a PDF for a faithful page preview."
        if suffix == ".ppt":
            raise ExtractionFailure("Legacy PPT is retained but cannot be safely processed directly. Export to PPTX/PDF; the original stays saved.")
        try:
            with zipfile.ZipFile(target) as archive:
                entries = archive.infolist()
                if len(entries) > 5000 or len({entry.filename for entry in entries}) != len(entries) or sum(entry.file_size for entry in entries) > 100 * 1024**2:
                    raise ExtractionFailure("Slide package exceeds its entry/decompressed size limits. Split or export it to PDF.")
                # No unpacking, macros, scripts, DTDs, or external URL resolution.
                part = "ppt/presentation.xml"
                presentation = fromstring(read_part(archive, part))
                links, _ = relationships(archive, part)
                slides = presentation.findall("p:sldIdLst/p:sldId", NS)
                total = len(slides)
                if not 1 <= total <= 500:
                    raise ExtractionFailure("Slide extraction supports 1–500 slides.")
                rendered_count = None
                if converted:
                    import pypdfium2 as pdfium
                    with pdfium.PdfDocument(converted) as document:
                        rendered_count = len(document)
                    if rendered_count != total:
                        converted = None
                        conversion_warning = "Rendered slide count differs from the original. Previews were withheld to avoid incorrect citations; export PDF manually."
                worker.checkpoint(job, completed, total, "Reading slides and images", {"completed_units": completed})
                for index in range(completed, total):
                    worker.check(job)
                    guard.touch()
                    slide_part = links.get(slides[index].get("{" + NS["r"] + "}id"))
                    if not slide_part or not slide_part.startswith("ppt/slides/"):
                        raise ExtractionFailure("Invalid slide order/relationship. Export a new PPTX/PDF copy.")
                    tree = fromstring(read_part(archive, slide_part))
                    slide_links, external = relationships(archive, slide_part)
                    # Only DrawingML a:t nodes are text; do not include property XML whitespace.
                    text = "\n".join("".join(node.text or "" for node in paragraph.findall(".//a:t", NS)) for paragraph in tree.findall(".//a:p", NS)).strip()
                    if len(text) > 50000:
                        raise ExtractionFailure("A slide exceeds the text limit. Split or simplify the deck.")
                    equations = tree.findall(".//m:oMath", NS)
                    if len(equations) > 100:
                        raise ExtractionFailure("A slide contains too many equations for a bounded preview.")
                    equation_xml = [tostring(equation, encoding="unicode") for equation in equations]
                    from .equations import equation_preview, preview_supported
                    previews = [equation_preview(equation) for equation in equations]
                    previews = [preview if preview_supported(preview) else {"kind": "unsupported"} for preview in previews]
                    if sum(len(value) for value in equation_xml) > 100000:
                        raise ExtractionFailure("Slide equation XML exceeds the bounded preview limit. Export to PDF.")
                    metadata = {"assets": [], "text_origin": "pptx_native_text", "review_required": True, "hidden_slide": tree.get("show") == "0",
                        "slide_part": slide_part, "equations": equation_xml, "equation_previews": previews,
                        "equation_format": "OMML source XML; not a verified linear transcription", "image_text": [], "external_links_ignored": external}
                    metadata["native_tables"] = native_tables(tree)
                    metadata["non_table_graphics"] = bool(tree.findall(".//p:cxnSp", NS)) or any(
                        graphic.get("uri") != "http://schemas.openxmlformats.org/drawingml/2006/table" for graphic in tree.findall(".//a:graphicData", NS))
                    warnings = [conversion_warning] if conversion_warning else []
                    if metadata["hidden_slide"]:
                        warnings.append("This slide is marked hidden in the original; its original-order location is retained.")
                    if not converted:
                        warnings.append("Full slide preview requires LibreOffice or a PDF export. Embedded images below are not a reconstruction of the slide.")
                    else:
                        image = render_pdf(converted, index)
                        try:
                            metadata["assets"].append(save_preview(worker.root, image, f"Slide {index + 1} · LibreOffice rendering"))
                            metadata["visual_notes"] = visual_notes(image, worker, job, guard)
                        finally:
                            image.close()
                    pictures = tree.findall(".//p:pic", NS)
                    if len(pictures) > 8:
                        warnings.append("Only the first eight embedded pictures were processed. Review the original for remaining visuals.")
                    for picture_index, picture in enumerate(pictures[:8], 1):
                        worker.check(job)
                        guard.touch()
                        blip = picture.find(".//a:blip", NS)
                        linked = blip.get("{" + NS["r"] + "}embed") if blip is not None else None
                        asset_part = slide_links.get(linked)
                        if not asset_part:
                            warnings.append("A linked or missing image was not fetched.")
                            continue
                        try:
                            data = read_part(archive, asset_part)
                            with Image.open(io.BytesIO(data)) as original:
                                image, scale = prepare(original)
                            try:
                                value, result = ocr(image, worker, job, guard)
                                if len(metadata["assets"]) < 4:
                                    metadata["assets"].append(save_preview(worker.root, image, f"Slide {index + 1} · Picture {picture_index}"))
                                metadata["image_text"].append({"picture": picture_index, "part": asset_part, "text": value, "ocr": result})
                            finally:
                                image.close()
                        except (Cancelled, Interrupted):
                            raise
                        except Exception:
                            warnings.append(f"Picture {picture_index} could not be decoded/OCRed. It remains in the original deck.")
                    if equations:
                        warnings.append("Native equation XML is preserved. Fractions, superscripts and matrices need visual review; OCR does not verify mathematics.")
                    if pictures:
                        warnings.append("Image OCR is separate and unverified. Diagram relationships, cropping and placement need comparison with the original.")
                    if tree.findall(".//a:graphicData", NS):
                        warnings.append("Tables/charts/SmartArt may have incomplete structure. Review the original slide.")
                    if external:
                        warnings.append("External linked resources were ignored.")
                    if not text:
                        text = "\n\n".join(item["text"] for item in metadata["image_text"] if item["text"])
                        metadata["text_origin"] = "embedded_image_ocr"
                    warning = " ".join(dict.fromkeys(warnings)) or None
                    status = "text" if text and metadata["text_origin"] == "pptx_native_text" else "suspect" if text else "empty"
                    commit_unit(worker, job, index + 1, total, text, {"kind": "slide", "slide": index + 1}, status, warning,
                        "openxml+tesseract-v1", metadata)
        except (Cancelled, Interrupted, ExtractionFailure):
            raise
        except Exception as error:
            raise ExtractionFailure("Could not read this PPTX. It may be corrupt, encrypted or contain unsafe XML. Export a new PPTX/PDF copy.") from error
