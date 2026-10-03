"""Local routing pilot from retained PP-OCRv6 Small outputs; no cloud requests.

Heuristics are provisional, uncalibrated, and are not installed in the app.
"""
import hashlib
import json
from pathlib import Path
import re
import time

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "tmp/ocr-benchmark"


def inspect(path, output, requested_language="en", native_structure_available=False):
    if native_structure_available:
        return {"decision":"local-native","reasons":["Usable native source structure available"]}
    started=time.perf_counter()
    image=np.asarray(Image.open(path).convert("RGB"));height,width=image.shape[:2]
    gray=cv2.cvtColor(image,cv2.COLOR_RGB2GRAY)
    text=output["text"];boxes=output.get("boxes",[]);confidence=output.get("confidence",[])
    foreground=float(np.mean(np.min(image,axis=2)<245))
    pure_white=bool(np.all(image==255))
    edges=cv2.Canny(gray,60,150)
    detected=cv2.HoughLinesP(edges,1,np.pi/180,threshold=50,minLineLength=max(50,int(width*.08)),maxLineGap=10)
    lines=[] if detected is None else detected.reshape(-1,4).tolist()
    horizontal=sum(abs(y1-y0)<=3 and abs(x1-x0)>=width*.08 for x0,y0,x1,y1 in lines)
    diagonal=sum(abs(y1-y0)>height*.08 and abs(x1-x0)>width*.08 for x0,y0,x1,y1 in lines)
    numbers=re.findall(r"(?<!\w)\d+(?:\.\d+)?(?!\w)",text)
    math_expressions=re.findall(r"[A-Za-z]\([^)]*\)",text)
    low_fraction=float(np.mean(np.asarray(confidence)<.8)) if confidence else None
    reasons=[]
    if pure_white and not text.strip() and not boxes:
        decision="skip-blank";reasons=["Pure-white fixture and no detected text"]
    else:
        if len(numbers)>=6 and horizontal>=3:
            reasons.append("Table candidate: repeated numeric values and long horizontal boundaries")
        if len(math_expressions)>=2 and "=" in text and horizontal>=1:
            reasons.append("Stacked-math candidate: mathematical expressions and long horizontal stroke")
        if diagonal>=2:
            reasons.append("Diagram candidate: multiple long diagonal connections")
        if not pure_white and not text.strip():
            reasons.append("Non-white pixels but no OCR text; cannot assume blank")
        if low_fraction is not None and low_fraction>.25:
            reasons.append("More than 25% of recognized lines below provisional 0.8 confidence")
        if requested_language=="hi":
            reasons.append("Selected Hindi language is outside this recognizer's supported scripts; try a capable local recognizer first")
        decision="local-language-retry" if requested_language=="hi" else "vision-candidate" if reasons else "local-ocr"
        if not reasons:reasons=["No structural or low-quality trigger in this pilot"]
    return {"decision":decision,"reasons":reasons,"seconds":round(time.perf_counter()-started,4),
        "signals":{"foreground_fraction":round(foreground,4),"ocr_box_count":len(boxes),
            "mean_ocr_confidence":float(np.mean(confidence)) if confidence else None,
            "low_confidence_fraction":low_fraction,"numeric_tokens":len(numbers),
            "long_horizontal_segments":horizontal,"long_diagonal_segments":diagonal}}


def run():
    cv2.setNumThreads(1)
    source=json.loads((WORK/"results/pp-v6-small.json").read_text("utf-8"))
    report={"method":"Known seven-image pilot, fixed provisional heuristics; not a calibrated routing accuracy benchmark.",
        "cloud_calls":0,"opencv_version":cv2.__version__,"samples":[],
        "limitations":["Uses cached OCR; timings exclude initial OCR.","Hindi is an explicit selected-language input in its fixture, not inferred from its filename in the router.",
            "Only pure-white blank detection is validated.","Borderless tables, photographs, handwriting, faint content, rotated pages and densely packed diagrams remain untested.",
            "These fixture rules must be evaluated on held-out course pages before enabling automatic routing."]}
    for sample in source["samples"]:
        name=sample["sample"];path=WORK/"fixtures"/(name+(".jpg" if name=="scan-degraded" else ".png"))
        result=inspect(path,sample["output"],requested_language="hi" if name=="hindi-mixed" else "en")
        report["samples"].append({"sample":name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),**result})
    (ROOT/"docs/evaluation/vision-routing-results.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print([(s["sample"],s["decision"],s["seconds"]) for s in report["samples"]])


if __name__=="__main__":run()
