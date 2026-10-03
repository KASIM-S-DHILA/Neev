"""Authored fixtures only. Run using the bundled document Python runtime."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader, PdfWriter
import json

ROOT = Path(__file__).parent
PAGES = [
    ("Conditional probability", ["P(A | B) = P(A and B) / P(B), provided P(B) > 0.",
        "The conditioning event changes the sample space.", "Example: P(A and B) = 0.12 and P(B) = 0.30.", "Then P(A | B) = 0.40."]),
    ("Bayes' theorem", ["P(A | B) = P(B | A) P(A) / P(B), provided P(B) > 0.",
        "A prior probability is updated after observing evidence.", "This authored evaluation sheet is not an assessment."]),
    ("Independence", ["Events A and B are independent when P(A and B) = P(A) P(B).",
        "If P(B) > 0, independence implies P(A | B) = P(A).", "Do not confuse independence with mutually exclusive events."]),
]


def write_page(pdf, title, lines, page):
    pdf.setFillColorRGB(.15, .24, .32)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(54, 730, title)
    pdf.setFont("Helvetica", 12)
    pdf.setFillColorRGB(.15, .15, .15)
    for index, line in enumerate(lines):
        pdf.drawString(54, 676 - index * 28, line)
    pdf.setFont("Helvetica", 9)
    pdf.setFillColorRGB(.4, .4, .4)
    pdf.drawString(54, 42, f"StudyLens authored source fixture | physical page {page}")
    pdf.showPage()


pdf = canvas.Canvas(str(ROOT / "digital-notes.pdf"), pagesize=(612, 792), invariant=1)
for number, (title, lines) in enumerate(PAGES, 1):
    write_page(pdf, title, lines, number)
pdf.save()

pdf = canvas.Canvas(str(ROOT / "mixed-notes.pdf"), pagesize=(612, 792), invariant=1)
write_page(pdf, *PAGES[0], 1)
image = Image.new("RGB", (1100, 850), "white")
draw = ImageDraw.Draw(image)
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 32)
draw.text((70, 80), "Scanned evaluation page", fill="black", font=font)
draw.text((70, 160), "This sentence exists only in the image.", fill="black", font=font)
draw.text((70, 220), "OCR must read it in a later phase.", fill="black", font=font)
pdf.drawImage(ImageReader(image), 36, 200, width=540, height=417)
pdf.showPage()
pdf.showPage()  # Deliberately blank third page.
pdf.save()

writer = PdfWriter()
writer.append(PdfReader(ROOT / "digital-notes.pdf"))
writer.encrypt("fixture-password")
writer.write(ROOT / "encrypted-notes.pdf")
(ROOT / "corrupt-notes.pdf").write_bytes(b"%PDF-1.4\nAuthored invalid PDF; missing page tree and EOF")
(ROOT / "mixed-language.txt").write_bytes("Probability notes\r\nसंभावना को समझिए।\r\nUse the same source location.\r\n".encode("utf-16"))
(ROOT / "gold.json").write_text(json.dumps({"provenance": "Authored evaluation material; manually review rendered pages.", "questions": [
    {"question": "What denominator appears in conditional probability?", "source": "digital-notes.pdf", "page": 1, "needle": PAGES[0][1][0]},
    {"question": "What is updated after observing evidence?", "source": "digital-notes.pdf", "page": 2, "needle": PAGES[1][1][1]},
    {"question": "How is independence defined?", "source": "digital-notes.pdf", "page": 3, "needle": PAGES[2][1][0]},
    {"question": "What does the scanned page say?", "source": "mixed-notes.pdf", "page": 2, "expected": "needs_ocr; no invented answer"},
    {"question": "Explain photosynthesis.", "source": None, "expected": "off-material; retrieval/refusal evaluation in later phases"},
]}, indent=2, ensure_ascii=False), encoding="utf-8")
