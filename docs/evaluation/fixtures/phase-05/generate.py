"""Authored extraction fixtures; not a student course or presentation template."""
import io
import json
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader

ROOT = Path(__file__).resolve().parent
ROOT.mkdir(parents=True, exist_ok=True)
font_path = "C:/Windows/Fonts/arial.ttf"
font = ImageFont.truetype(font_path, 42)
small = ImageFont.truetype(font_path, 30)
scan = Image.new("RGB", (1500, 1000), "white")
draw = ImageDraw.Draw(scan)
for y, line in zip((100, 200, 300, 400), (
        "Conditional probability", "The sample space contains 100 outcomes.",
        "Event A contains 25 outcomes.", "The probability of A is 0.25.")):
    draw.text((90, y), line, font=font, fill="black")
scan.save(ROOT / "scan.png")
figure = Image.new("RGB", (1500, 1000), "white")
draw = ImageDraw.Draw(figure)
draw.text((80, 70), "A branching experiment", font=font, fill="black")
for box, label in (((100, 350, 430, 500), "Start"), ((940, 180, 1370, 330), "Heads 0.5"), ((940, 650, 1370, 800), "Tails 0.5")):
    draw.rectangle(box, outline="black", width=4)
    draw.text((box[0] + 22, box[1] + 42), label, font=font, fill="black")
draw.line((430, 425, 940, 255), fill="black", width=5)
draw.line((430, 425, 940, 725), fill="black", width=5)
draw.polygon(((940, 255), (910, 248), (922, 279)), fill="black")
draw.polygon(((940, 725), (908, 715), (923, 693)), fill="black")
draw.text((80, 900), "OCR labels alone do not prove graph relationships.", font=small, fill="black")
figure.save(ROOT / "figure.png")
equation = Image.new("RGB", (1500, 1000), "white")
draw = ImageDraw.Draw(equation)
draw.text((90, 90), "Bayes rule - compare fraction structure", font=font, fill="black")
draw.text((140, 430), "P(A|B) =", font=font, fill="black")
draw.text((530, 350), "P(B|A) P(A)", font=font, fill="black")
draw.line((510, 440, 1090, 440), fill="black", width=4)
draw.text((730, 480), "P(B)", font=font, fill="black")
draw.text((90, 850), "Do not treat OCR as a verified mathematical formula.", font=small, fill="black")
equation.save(ROOT / "equation.png")

rotated = scan.rotate(90, expand=True)
exif = rotated.getexif()
exif[274] = 6  # The physical JPEG is rotated; its EXIF maps it back to upright.
rotated.save(ROOT / "oriented-scan.jpg", exif=exif)
blank = Image.new("RGB", (600, 500), "white")
blank.save(ROOT / "blank.png")
scan.copy().save(ROOT / "two-pages.tiff", save_all=True, append_images=[figure.copy()], compression="tiff_lzw")
(ROOT / "corrupt.png").write_bytes(b"Intentionally invalid authored image fixture")

canvas = Canvas(str(ROOT / "scanned-visuals.pdf"), pagesize=(750, 500), invariant=1)
for image in (scan, figure, equation):
    canvas.drawImage(ImageReader(image), 0, 0, width=750, height=500)
    canvas.showPage()
canvas.save()

# Minimal OpenXML package deliberately authored to test order, images and OMML,
# not a general-purpose presentation. The PDF/images above provide reviewed truth.
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
parts = {
    "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/><Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/><Override PartName="/ppt/slides/slide2.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/></Types>',
    "_rels/.rels": f'<Relationships xmlns="{RELS}"><Relationship Id="rId1" Type="{R}/officeDocument" Target="ppt/presentation.xml"/></Relationships>',
    "ppt/presentation.xml": f'<p:presentation xmlns:p="{P}" xmlns:r="{R}"><p:sldIdLst><p:sldId id="256" r:id="rId2"/><p:sldId id="257" r:id="rId1"/></p:sldIdLst><p:sldSz cx="9144000" cy="6096000"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>',
    "ppt/_rels/presentation.xml.rels": f'<Relationships xmlns="{RELS}"><Relationship Id="rId1" Type="{R}/slide" Target="slides/slide1.xml"/><Relationship Id="rId2" Type="{R}/slide" Target="slides/slide2.xml"/></Relationships>',
    "ppt/slides/_rels/slide2.xml.rels": f'<Relationships xmlns="{RELS}"><Relationship Id="image1" Type="{R}/image" Target="../media/figure.png"/><Relationship Id="external1" Type="{R}/image" Target="http://127.0.0.1:9/never-fetch" TargetMode="External"/></Relationships>',
    "ppt/media/figure.png": (ROOT / "figure.png").read_bytes(),
}
def slide(title, picture=False, math=False):
    body = f'<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>{title}</a:t></a:r></a:p></p:txBody></p:sp>'
    if picture:
        body += '<p:pic><p:nvPicPr><p:cNvPr id="3" name="Authored branch figure"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="image1"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="9144000" cy="6096000"/></a:xfrm></p:spPr></p:pic>'
    if math:
        body += '<p:sp><p:spPr/><p:txBody><a:bodyPr/><a:p><m:oMath><m:f><m:num><m:r><m:t>P(B|A) P(A)</m:t></m:r></m:num><m:den><m:r><m:t>P(B)</m:t></m:r></m:den></m:f></m:oMath></a:p></p:txBody></p:sp>'
    return f'<p:sld xmlns:p="{P}" xmlns:a="{A}" xmlns:r="{R}" xmlns:m="{M}"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>{body}</p:spTree></p:cSld></p:sld>'
parts["ppt/slides/slide1.xml"] = slide("Second slide: Bayes fraction", math=True)
parts["ppt/slides/slide2.xml"] = slide("First slide: branching experiment", picture=True)
with zipfile.ZipFile(ROOT / "ordered-visuals.pptx", "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for name, value in parts.items():
        archive.writestr(name, value)

(ROOT / "gold.json").write_text(json.dumps({"provenance": "Authored Phase 5 fixtures; manually inspect images and rendered PDF pages.",
    "ocr": [{"source": "scan.png", "needle": "100 outcomes"}, {"source": "oriented-scan.jpg", "needle": "100 outcomes"}],
    "pdf": [{"page": 1, "needle": "100 outcomes"}, {"page": 2, "needle": "Heads"}, {"page": 3, "math_review_required": True}],
    "slides": [{"slide": 1, "part": "ppt/slides/slide2.xml", "needle": "First slide", "picture": 1},
        {"slide": 2, "part": "ppt/slides/slide1.xml", "needle": "Second slide", "equation_denominator": "P(B)"}],
    "off_material": "No extracted source describes entropy; do not invent it.",
    "semantic_truth": {"figure": "Start has two outgoing arrows to Heads 0.5 and Tails 0.5.",
        "equation": "P(A|B) = P(B|A) P(A) / P(B). OCR is not assumed to preserve this."}}, indent=2), encoding="utf-8")
print("Authored visual fixtures generated")
