"""Isolated CPU OCR comparison. Assets/cache in tmp; never writes student data.

Run using tmp/ocr-benchmark/venv/Scripts/python.exe. --fixtures, then --run.
Every candidate gets a fresh process; results retain failures and exact weights.
"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "tmp/ocr-benchmark"
LIMIT = 500_000_000  # decimal MB, total required weights per configuration
FILES = []
os.environ.update(ONNXTR_CACHE_DIR=str(WORK / "onnxtr"), HF_HOME=str(WORK / "hf"),
                  HF_MODULES_CACHE=str(WORK / "hf-modules"),
                  HF_HUB_DISABLE_XET="1", OMP_NUM_THREADS="4", MKL_NUM_THREADS="4",
                  OPENBLAS_NUM_THREADS="4", HF_HUB_DISABLE_SYMLINKS_WARNING="1")


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    def encode(v):
        if hasattr(v, "tolist"): return v.tolist()
        if hasattr(v, "item"): return v.item()
        raise TypeError(type(v).__name__)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=encode), encoding="utf-8")


def register(path, url=None, expected=None):
    path = Path(path)
    if path in [Path(x["path"]) for x in FILES]:
        return path
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if expected and not digest.startswith(expected):
        raise ValueError("Weight integrity mismatch: " + str(path))
    FILES.append({"path": str(path), "bytes": path.stat().st_size, "sha256": digest,
                  "url": url, "publisher_hash_checked": bool(expected)})
    if sum(x["bytes"] for x in FILES) > LIMIT:
        raise ValueError("Combined model weights exceed 500 MB")
    return path


def download(url, path, expected=None):
    path = Path(path)
    if path.is_file():
        return register(path, url, expected)
    path.parent.mkdir(parents=True, exist_ok=True)
    catalog = WORK / "onnx-asset-sizes.json"
    if catalog.exists():
        asset = json.loads(catalog.read_text()).get(url)
        if asset and asset["bytes"] > LIMIT - sum(x["bytes"] for x in FILES):
            raise ValueError(f"Combined model weights exceed 500 MB: published next file {asset['bytes']} bytes")
    req = urllib.request.Request(url, headers={"User-Agent": "StudyLens-local-OCR-benchmark"})
    with urllib.request.urlopen(req, timeout=90) as response:
        remaining = LIMIT - sum(x["bytes"] for x in FILES)
        size = int(response.headers.get("Content-Length", "0"))
        if size > remaining:
            raise ValueError(f"Combined weights exceed 500 MB: next file {size} bytes")
        print("Downloading", path.name, size or "streamed", flush=True)
        part = path.with_suffix(path.suffix + ".part")
        total = 0
        with part.open("wb") as output:
            while chunk := response.read(1024**2):
                total += len(chunk)
                if total > remaining:
                    raise ValueError("Combined weights exceed 500 MB while downloading")
                output.write(chunk)
        part.replace(path)
    return register(path, url, expected)


def candidates():
    rows = []
    def rapid(name, version, det, rec):
        rows.append(dict(name=name, family="rapid", version=version, det=det, rec=rec))
    rapid("pp-v4-en", "PP-OCRv4", "en_PP-OCRv3_det_mobile", "en_PP-OCRv4_rec_mobile")
    for variant in ("mobile", "server"):
        rapid("pp-v4-" + variant, "PP-OCRv4", "ch_PP-OCRv4_det_" + variant, "ch_PP-OCRv4_rec_" + variant)
    rapid("pp-v4-document", "PP-OCRv4", "ch_PP-OCRv4_det_server", "ch_doc_PP-OCRv4_rec_server")
    rapid("pp-v4-hi", "PP-OCRv4", "multi_PP-OCRv3_det_mobile", "devanagari_PP-OCRv4_rec_mobile")
    for rec in ("en", "ch", "latin", "devanagari"):
        rapid("pp-v5-" + rec, "PP-OCRv5", "ch_PP-OCRv5_det_mobile", rec + "_PP-OCRv5_rec_mobile")
    rapid("pp-v5-server", "PP-OCRv5", "ch_PP-OCRv5_det_server", "ch_PP-OCRv5_rec_server")
    for size in ("tiny", "small", "medium"):
        rapid("pp-v6-" + size, "PP-OCRv6", "multi_PP-OCRv6_det_" + size, "multi_PP-OCRv6_rec_" + size)
    dets = ("db_mobilenet_v3_large", "db_resnet34", "db_resnet50", "linknet_resnet18",
            "linknet_resnet34", "linknet_resnet50", "fast_tiny", "fast_small", "fast_base")
    recs = ("crnn_mobilenet_v3_small", "crnn_mobilenet_v3_large", "crnn_vgg16_bn", "sar_resnet31",
            "master", "vitstr_small", "vitstr_base", "parseq", "viptr_tiny")
    for det in dets:
        rows.append(dict(name="doctr-det-" + det, family="doctr", det=det, rec="crnn_vgg16_bn", int8=False))
    for rec in recs:
        rows.append(dict(name="doctr-rec-" + rec, family="doctr", det="db_mobilenet_v3_large", rec=rec, int8=False))
    for rec in recs:
        if rec != "viptr_tiny":
            rows.append(dict(name="doctr-int8-rec-" + rec, family="doctr", det="db_mobilenet_v3_large", rec=rec, int8=True))
    for det in dets:
        if not det.startswith("fast") and det != "db_mobilenet_v3_large":
            rows.append(dict(name="doctr-int8-det-" + det, family="doctr", det=det, rec="crnn_vgg16_bn", int8=True))
    rows.append(dict(name="doctr-400mb-combination", family="doctr", det="linknet_resnet50", rec="vitstr_base", int8=False))
    rows.append(dict(name="doctr-tables", family="doctr", det="fast_base", rec="crnn_vgg16_bn", int8=False, tables=True))
    for det, langs in (("craft", ["en"]), ("dbnet18", ["en"]), ("craft", ["hi", "en"])):
        rows.append(dict(name="easyocr-" + det + "-" + "-".join(langs), family="easy", det=det, langs=langs))
    for kind in ("printed", "handwritten"):
        rows.append(dict(name="trocr-small-" + kind, family="trocr", repo="microsoft/trocr-small-" + kind))
    for name in ("base", "base-ft"):
        rows.append(dict(name="florence2-" + name, family="florence", repo="microsoft/Florence-2-" + name))
    for kind in ("installed", "fast", "best"):
        rows.append(dict(name="tesseract-" + kind, family="tesseract", kind=kind))
    for kind in ("fast", "best"):
        rows.append(dict(name="tesseract-" + kind + "-en-hi", family="tesseract", kind=kind, langs="eng+hin"))
    for psm in (6,11):
        rows.append(dict(name="tesseract-installed-psm" + str(psm), family="tesseract", kind="installed", psm=psm))
    for quant, projector in (("q4_k_m", "f16"), ("q8_0", "f16"), ("f16_q8_0", "f16"), ("q4_k_m", "f32"), ("bf16", "q8_0")):
        rows.append(dict(name="smoldocling-" + quant + "-vision-" + projector, family="smol", quant=quant, projector=projector))
    return rows


def rapid_engine(row):
    import rapidocr
    import yaml
    configs = yaml.safe_load((Path(rapidocr.__file__).parent / "default_models.yaml").read_text("utf-8"))["onnxruntime"]
    params = {"Global.log_level": "error", "EngineConfig.onnxruntime.intra_op_num_threads": 4,
              "EngineConfig.onnxruntime.inter_op_num_threads": 1, "Det.limit_type": "max", "Det.limit_side_len": 1280}
    for part, name, version in (("Det", row["det"], row["version"]), ("Rec", row["rec"], row["version"]),
                               ("Cls", "ch_ppocr_mobile_v2.0_cls_mobile", "PP-OCRv4")):
        info = configs[version][part.lower()][name]
        target = WORK / "rapid" / (name + ".onnx")
        bundled = Path(rapidocr.__file__).parent / "models" / Path(info["model_dir"]).name
        if bundled.exists():
            target = register(bundled, info["model_dir"], info["SHA256"])
        else:
            target = download(info["model_dir"], target, info["SHA256"])
        params[part + ".model_path"] = str(target)
    return rapidocr.RapidOCR(params=params)


def build(row):
    family = row["family"]
    if family == "smol":
        import atexit, base64, io, secrets, socket
        repo = "Mungert/SmolDocling-256M-preview-GGUF"
        revision = "80cce50dda2be7b01b78ca7213d9acd92ba87d51"
        tree = json.load(urllib.request.urlopen(f"https://huggingface.co/api/models/{repo}/tree/{revision}?recursive=true", timeout=30))
        paths = []
        for name in (f"SmolDocling-256M-preview-{row['quant']}.gguf", f"SmolDocling-256M-preview-{row['projector']}.mmproj"):
            entry = next(x for x in tree if x["path"] == name)
            paths.append(download(f"https://huggingface.co/{repo}/resolve/{revision}/{name}", WORK / "smol" / name, entry["lfs"]["oid"]))
        row["revision"] = revision
        binary = next((ROOT / "tmp/hunyuan-ocr/bin").rglob("llama-server.exe"))
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1",0)); port = reservation.getsockname()[1]
        key = secrets.token_urlsafe(24); base = f"http://127.0.0.1:{port}"
        log = (WORK / "logs" / (row["name"] + "-server.log")).open("w", encoding="utf-8")
        process = subprocess.Popen([str(binary),"--model",str(paths[0]),"--mmproj",str(paths[1]),"--host","127.0.0.1",
            "--port",str(port),"--api-key",key,"--alias","ocr-trial","--ctx-size","8192","--parallel","1",
            "--threads","4","--threads-batch","4","--batch-size","512","--ubatch-size","128",
            "--n-gpu-layers","0","--no-mmproj-offload","--jinja","--special"],stdout=log,stderr=log,creationflags=0x08000000)
        def stop():
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait()
            log.close()
        atexit.register(stop)
        def request(endpoint,payload=None,timeout=180):
            req=urllib.request.Request(base+endpoint,data=json.dumps(payload).encode() if payload is not None else None,
                 headers={"Content-Type":"application/json","Authorization":"Bearer "+key})
            with urllib.request.urlopen(req,timeout=timeout) as response:return json.load(response)
        started=time.monotonic()
        while time.monotonic()-started<90:
            if process.poll() is not None:raise ValueError("SmolDocling server exited during startup")
            try:
                if request("/health",timeout=2).get("status")=="ok":break
            except (OSError,TimeoutError):pass
            time.sleep(.25)
        else:raise TimeoutError("SmolDocling startup timed out")
        def infer(image):
            buffer=io.BytesIO();image.save(buffer,format="PNG")
            result=request("/v1/chat/completions",{"model":"ocr-trial","messages":[{"role":"user","content":[
                {"type":"image_url","image_url":{"url":"data:image/png;base64,"+base64.b64encode(buffer.getvalue()).decode()}},
                {"type":"text","text":"Convert this page to docling."}]}],"temperature":0,"top_p":1,"top_k":-1,
                "repeat_penalty":1,"max_tokens":2048,"stream":False})
            choice=result["choices"][0]
            return {"text":choice["message"]["content"],"finish_reason":choice["finish_reason"],"timings":result.get("timings"),
                    "usage":result.get("usage"),"format":"raw DocTags", "special_tokens_enabled":True,"runtime":"llama.cpp b11303 CPU"}
        return infer
    if family == "rapid":
        engine = rapid_engine(row)
        def infer(image):
            import numpy as np
            out = engine(np.asarray(image))
            return {"text": "\n".join(out.txts or []), "boxes": out.boxes.tolist() if out.boxes is not None else [],
                    "confidence": list(out.scores or [])}
        return infer
    if family == "doctr":
        import onnxtr.models.engine as module
        def bounded_download(url, **kw):
            name = kw.get("file_name") or url.rsplit("/", 1)[-1]
            import re
            match = re.search(r"-([a-f0-9]+)\.", name)
            return download(url, WORK / "onnxtr/models" / name, kw.get("hash_prefix") or (match.group(1) if match else None))
        module.download_from_url = bounded_download
        from onnxruntime import SessionOptions
        from onnxtr.models import ocr_predictor, EngineConfig
        opts = SessionOptions(); opts.intra_op_num_threads = 4; opts.inter_op_num_threads = 1
        opts.enable_cpu_mem_arena = False
        cfg = EngineConfig(session_options=opts, providers=["CPUExecutionProvider"])
        model = ocr_predictor(det_arch=row["det"], reco_arch=row["rec"], load_in_8_bit=row["int8"],
            det_bs=1, reco_bs=8, det_engine_cfg=cfg, reco_engine_cfg=cfg, layout_engine_cfg=cfg, table_engine_cfg=cfg,
            detect_tables=row.get("tables", False), keep_reading_order=True)
        def infer(image):
            import numpy as np
            result = model([np.asarray(image)])
            return {"text": result.render(), "document": result.export()}
        return infer
    if family == "easy":
        import torch
        torch.set_num_threads(4); torch.set_num_interop_threads(1)
        import easyocr
        model = easyocr.Reader(row["langs"], gpu=False, model_storage_directory=str(WORK / "easy"),
                               user_network_directory=str(WORK / "easy-network"), detect_network=row["det"], verbose=False)
        detector = easyocr.config.detection_models[row["det"]]
        register(WORK / "easy" / detector["filename"], detector["url"])
        for generation in easyocr.config.recognition_models.values():
            for info in generation.values():
                if info["model_script"] == model.model_lang or info["model_script"] == model.model_lang.removesuffix("_sim"):
                    path = WORK / "easy" / info["filename"]
                    if path.exists(): register(path, info["url"])
        # Determine the recognizer filename from the actual reader's language choice.
        if len(FILES) == 1:
            filename = "english_g2.pth" if row["langs"] == ["en"] else "devanagari.pth"
            register(WORK / "easy" / filename)
        def infer(image):
            import numpy as np
            out = model.readtext(np.asarray(image), batch_size=1, workers=0)
            return {"text": "\n".join(x[1] for x in out), "boxes": [x[0] for x in out], "confidence": [float(x[2]) for x in out]}
        return infer
    if family == "florence":
        import torch
        torch.set_num_threads(4); torch.set_num_interop_threads(1)
        from huggingface_hub import HfApi, snapshot_download
        info = HfApi().model_info(row["repo"], files_metadata=True)
        weight = next((x for x in info.siblings if x.rfilename == "model.safetensors"), None)
        if weight is None:weight = next(x for x in info.siblings if x.rfilename == "pytorch_model.bin")
        if weight.size > LIMIT: raise ValueError("Florence weights exceed 500 MB")
        folder = Path(snapshot_download(row["repo"],revision=info.sha,
            allow_patterns=["*.json","*.txt","*.safetensors","*.py"],local_dir=WORK / "florence" / row["name"]))
        register(folder / "model.safetensors", f"https://huggingface.co/{row['repo']}/resolve/{info.sha}/model.safetensors")
        row["revision"] = info.sha
        row["source_files"] = [{"name":p.name,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in folder.glob("*.py")]
        from transformers import AutoModelForCausalLM, AutoProcessor
        processor = AutoProcessor.from_pretrained(folder,local_files_only=True,trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(folder,local_files_only=True,trust_remote_code=True,torch_dtype=torch.float32,
                                                    attn_implementation="eager").eval()
        # Publisher implementation uses tuple KV caches, predating Transformers DynamicCache.
        model.language_model._supports_default_dynamic_cache = lambda: False
        row["compatibility_adapter"] = "Disable automatic DynamicCache; retain publisher legacy tuple cache"
        def infer(image):
            task = "<OCR_WITH_REGION>"
            inputs = processor(text=task,images=image,return_tensors="pt")
            with torch.inference_mode(): output = model.generate(**inputs,max_new_tokens=1024,num_beams=1,do_sample=False)
            raw = processor.batch_decode(output,skip_special_tokens=False)[0]
            parsed = processor.post_process_generation(raw,task=task,image_size=image.size)[task]
            return {"text":"\n".join(parsed["labels"]),"boxes":parsed["quad_boxes"],"raw":raw}
        return infer
    if family == "trocr":
        import torch
        torch.set_num_threads(4); torch.set_num_interop_threads(1)
        from huggingface_hub import HfApi, snapshot_download
        info = HfApi().model_info(row["repo"], files_metadata=True)
        revision = info.sha
        weight = next((x for x in info.siblings if x.rfilename == "model.safetensors"), None)
        if weight is None:weight = next(x for x in info.siblings if x.rfilename == "pytorch_model.bin")
        if weight.size > LIMIT - 20_000_000: raise ValueError("TrOCR weights plus detector exceed budget")
        folder = Path(snapshot_download(row["repo"], revision=revision,
            allow_patterns=["*.json", "*.txt", "*.model", weight.rfilename], local_dir=WORK / "trocr" / row["name"]))
        register(folder / weight.rfilename, f"https://huggingface.co/{row['repo']}/resolve/{revision}/{weight.rfilename}")
        row["revision"] = revision
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        processor = TrOCRProcessor.from_pretrained(folder, local_files_only=True)
        model = VisionEncoderDecoderModel.from_pretrained(folder, local_files_only=True).eval()
        detector = rapid_engine(dict(version="PP-OCRv5", det="ch_PP-OCRv5_det_mobile", rec="en_PP-OCRv5_rec_mobile"))
        def infer(image):
            import numpy as np
            detected = detector(np.asarray(image), use_rec=False, use_cls=False)
            texts, boxes = [], []
            for quad in detected.boxes if detected.boxes is not None else []:
                x0, y0 = np.floor(quad.min(axis=0)).astype(int); x1, y1 = np.ceil(quad.max(axis=0)).astype(int)
                crop = image.crop((max(0,x0-3), max(0,y0-3), min(image.width,x1+3), min(image.height,y1+3)))
                pixels = processor(images=crop, return_tensors="pt").pixel_values
                with torch.inference_mode(): output = model.generate(pixels, max_new_tokens=128)
                texts.extend(processor.batch_decode(output, skip_special_tokens=True)); boxes.append(quad.tolist())
            return {"text": "\n".join(texts), "boxes": boxes, "pipeline": "PP-v5 detection + TrOCR line recognition"}
        return infer
    if family == "tesseract":
        binary = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
        tessdata = binary.parent / "tessdata"
        language = row.get("langs", "eng")
        if row["kind"] != "installed":
            tessdata = WORK / "tess" / row["kind"]
            for lang in language.split("+"):
                url = f"https://raw.githubusercontent.com/tesseract-ocr/tessdata_{row['kind']}/main/{lang}.traineddata"
                download(url, tessdata / (lang + ".traineddata"))
        else: register(tessdata / "eng.traineddata")
        def infer(image):
            image.save(WORK / "tess-input.png")
            result = subprocess.run([str(binary), str(WORK / "tess-input.png"), "stdout", "--tessdata-dir", str(tessdata),
                "-l", language, "--psm", str(row.get("psm",3))], capture_output=True, timeout=90, creationflags=0x08000000)
            if result.returncode: raise ValueError(result.stderr.decode("utf-8", "replace"))
            return {"text": result.stdout.decode("utf-8", "replace")}
        return infer
    raise ValueError(family)


def fixtures():
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, features
    work = WORK / "fixtures"; work.mkdir(parents=True, exist_ok=True)
    original = ROOT / "docs/evaluation/fixtures/phase-05"
    for name in ("scan", "equation", "figure", "blank"):
        image = Image.open(original / (name + ".png")).convert("RGB")
        image.thumbnail((1280,1280)); image.save(work / (name + ".png"))
    image = Image.open(ROOT / "tmp/hunyuan-ocr/slide-12.png").convert("RGB")
    image.thumbnail((1280,1280)); image.save(work / "table-slide-12.png")
    image = Image.open(original / "scan.png").convert("RGB")
    image.thumbnail((900,900)); image = image.filter(ImageFilter.GaussianBlur(0.7))
    image.save(work / "scan-degraded.jpg", quality=45)
    image = Image.new("RGB", (1280,800), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("C:/Windows/Fonts/Nirmala.ttc", 40)
    lines = ["प्रायिकता का परिचय", "कुल परिणामों की संख्या 100 है।", "घटना A में 25 परिणाम हैं।", "Probability of A = 0.25"]
    for i,line in enumerate(lines): draw.text((70,80+i*125),line,font=font,fill="black")
    image.save(work / "hindi-mixed.png")
    save(work / "manifest.json", {"hindi_lines":lines,"raqm":features.check_feature("raqm"),"max_edge":1280})
    print("Fixtures ready", flush=True)


def worker(row):
    from PIL import Image, ImageOps
    target = WORK / "results" / (row["name"] + ".json")
    report = {"config":row,"samples":[],"weight_files":FILES,"status":"initializing"}
    save(target, report)
    try:
        started = time.perf_counter(); infer = build(row)
        report["cached_or_download_init_seconds"] = time.perf_counter() - started
        report["weight_bytes"] = sum(x["bytes"] for x in FILES)
        report["status"] = "running"; save(target,report)
        for path in sorted((WORK / "fixtures").glob("*")):
            if path.suffix not in (".png", ".jpg"): continue
            image = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
            reps = 1 if row["family"] in ("trocr", "smol", "florence") else 2
            times, outputs = [], []
            for _ in range(reps):
                started = time.perf_counter(); out = infer(image); times.append(time.perf_counter()-started); outputs.append(out)
            report["samples"].append({"sample":path.stem,"times_seconds":times,"median_seconds":statistics.median(times),
                                       "output":outputs[-1],"repeat_text_equal":len(outputs)==1 or outputs[0]["text"]==outputs[1]["text"]})
            save(target,report)
            print(row["name"], path.stem, round(times[-1],3), flush=True)
            if row["family"] in ("rapid", "doctr", "easy") and statistics.median(times) > 20:
                report["status"] = "complete" if len(report["samples"]) == 7 else "stopped-slow"
                report["slow_warning"] = "Stop rule: >20 seconds/page on a non-generative candidate"
                if report["status"] == "stopped-slow":report["error"] = report["slow_warning"] + "; partial results retained"
                break
        else:
            report["status"] = "complete"
    except Exception as exc:
        import traceback
        report["status"] = "excluded-storage" if "500 MB" in str(exc) or "budget" in str(exc) else "failed"
        report["error"] = str(exc); report["traceback"] = traceback.format_exc()
    finally:
        report["weight_files"] = FILES; save(target,report)


def run(names):
    import psutil
    rows = [x for x in candidates() if not names or x["name"] in names]
    save(WORK / "catalog.json", candidates())
    for row in rows:
        target = WORK / "results" / (row["name"] + ".json")
        if target.exists():
            previous = json.loads(target.read_text("utf-8"))
            if (previous.get("status") == "complete" and len(previous.get("samples", [])) == 7) or previous.get("status") in ("stopped-slow", "excluded-storage", "aborted"):
                print("Already evaluated",row["name"],flush=True);continue
        print("Starting",row["name"],flush=True)
        logpath = WORK / "logs" / (row["name"] + ".log");logpath.parent.mkdir(parents=True,exist_ok=True)
        with logpath.open("w",encoding="utf-8") as log:
            proc = subprocess.Popen([sys.executable,str(Path(__file__).resolve()),"--worker",row["name"]],stdout=log,stderr=log,
                creationflags=0x08000000, env={**os.environ,"PYTHONIOENCODING":"utf-8"})
            started = time.monotonic();peak_rss=peak_private=0; abort=None
            while proc.poll() is None:
                try:
                    tree=[psutil.Process(proc.pid)]+psutil.Process(proc.pid).children(recursive=True)
                    counters=[p.memory_info() for p in tree]
                    rss=sum(x.rss for x in counters);private=sum(getattr(x,"private",x.vms) for x in counters)
                    peak_rss=max(peak_rss,rss);peak_private=max(peak_private,private)
                    if private > 3*1024**3:abort="Trial stopped above 3 GiB sampled private memory"
                    if time.monotonic()-started>900:abort="Trial stopped after 900 seconds"
                    if abort:
                        for p in reversed(tree):
                            try:p.kill()
                            except psutil.Error:pass
                        break
                except psutil.Error:pass
                time.sleep(0.1)
            proc.wait()
        report=json.loads(target.read_text("utf-8")) if target.exists() else {"config":row,"samples":[],"status":"failed"}
        report.update(peak_process_tree_resident_bytes=peak_rss,peak_process_tree_private_bytes=peak_private,
                      exit_code=proc.returncode,total_worker_seconds=time.monotonic()-started)
        if abort:report.update(status="aborted",error=abort)
        elif proc.returncode:report.update(status="failed",error=report.get("error", "Worker exited with code " + str(proc.returncode)))
        save(target,report)
        print(row["name"],report["status"],round(report.get("weight_bytes",0)/1e6,2),"MB",round(peak_rss/1024**2),"MiB peak RSS",flush=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--fixtures",action="store_true");parser.add_argument("--run",action="store_true")
    parser.add_argument("--only",nargs="*");parser.add_argument("--worker");args=parser.parse_args()
    WORK.mkdir(parents=True,exist_ok=True)
    if args.fixtures:fixtures()
    if args.worker:worker(next(x for x in candidates() if x["name"]==args.worker))
    if args.run:run(args.only)
