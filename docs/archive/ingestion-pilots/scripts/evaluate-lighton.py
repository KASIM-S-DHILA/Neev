"""Exact community Ollama LightOnOCR-2 benchmark in a private local server/model store."""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request

import psutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "tmp/lighton-ocr"
MODEL = "maternion/LightOnOCR-2:1b"
sys.path.insert(0, str(ROOT / "services"))
from studylens_service.local_tools import ChildBoundary

spec = importlib.util.spec_from_file_location("ocr_helpers", ROOT / "scripts/evaluate-hunyuan.py")
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def post(base, route, payload, timeout=30):
    return helpers.request_json(base + route, payload, timeout=timeout)


def prepare():
    original = json.loads((ROOT / "tmp/gemma4-omni/vision-pilot-samples.json").read_text("utf-8"))
    pages = json.loads((ROOT / "tmp/gemma4-omni/document-samples.json").read_text("utf-8"))
    save(WORK / "documents-1280.json", pages)
    for edge in (1280, 1540):
        output = []
        for sample in original:
            source = ROOT / sample["path"]
            if sample.get("source") == "opendatalab/OmniDocBench":
                source = ROOT / "tmp/omnidocbench/images" / sample["source_image"]
            target = WORK / f"pilot-images-{edge}" / (sample["id"] + ".png")
            target.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(source) as image:
                converted = image.convert("RGB")
                converted.thumbnail((edge, edge))
                converted.save(target)
                size = list(converted.size)
                converted.close()
            output.append(sample | {"path": str(target.relative_to(ROOT)), "dimensions": size,
                "input_sha256": digest(target), "prompt": "", "preprocessing_max_edge": edge})
        save(WORK / f"pilot-{edge}.json", output)
    print("Prepared two eight-image pilots and exact paired 50-page inputs", flush=True)


def verify_manifest(base):
    tags = helpers.request_json(base + "/api/tags")
    assert len(tags["models"]) == 1, "Private store contains unexpected models"
    candidates = [p for p in (WORK / "models/manifests").rglob("*") if p.is_file()]
    assert len(candidates) == 1
    manifest_path = candidates[0]
    manifest = json.loads(manifest_path.read_text())
    manifest_hash = "sha256:" + digest(manifest_path)
    assert manifest_hash.removeprefix("sha256:") == tags["models"][0]["digest"].removeprefix("sha256:"), "Tag manifest digest differs"
    assets = []
    for layer in [manifest["config"]] + manifest["layers"]:
        path = WORK / "models/blobs" / layer["digest"].replace(":", "-")
        assert path.stat().st_size == layer["size"] and "sha256:" + digest(path) == layer["digest"], "Blob integrity failed"
        assets.append({"media_type": layer["mediaType"], "bytes": layer["size"], "sha256": layer["digest"],
            "path": str(path.relative_to(ROOT))})
    info = post(base, "/api/show", {"model": MODEL})
    save(WORK / "show.json", info)
    frozen = {"model": MODEL, "manifest_digest": manifest_hash, "runtime": helpers.request_json(base + "/api/version"),
        "assets": assets, "details": info.get("details"), "template": info.get("template"),
        "parameters": info.get("parameters"), "capabilities": info.get("capabilities")}
    previous = WORK / "manifest.json"
    if previous.exists():
        assert json.loads(previous.read_text()) == frozen, "Pinned model/runtime changed"
    save(previous, frozen)
    print("Verified", frozen["manifest_digest"], flush=True)
    return frozen


class RequestFailure(Exception):
    def __init__(self, message, partial="", reason="error"):
        super().__init__(message)
        self.partial, self.reason = partial, reason


def generate(base, sample, num_gpu):
    payload = {"model": MODEL, "messages": [{"role": "user", "content": "", "images": [
        base64.b64encode((ROOT / sample["path"]).read_bytes()).decode()]}], "stream": True,
        "keep_alive": "30m", "options": {"num_gpu": num_gpu, "num_thread": 4, "num_ctx": 4096,
            "num_predict": sample.get("max_tokens", 2048), "temperature": 0, "seed": 42, "repeat_penalty": 1.0}}
    request = urllib.request.Request(base + "/api/chat", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    started, output, final = time.monotonic(), "", None
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            for line in response:
                if time.monotonic() - started > 120:
                    raise RequestFailure("Request exceeded 120-second budget", output, "deadline")
                event = json.loads(line)
                if event.get("error"):
                    raise RequestFailure(event["error"], output)
                output += event.get("message", {}).get("content") or ""
                if event.get("done"):
                    final = event
                    break
        if not final:
            raise RequestFailure("Stream ended without a completion marker", output)
        return {"prediction": output, "finish_reason": final.get("done_reason"),
            "timings": {k: v for k, v in final.items() if k.endswith("_duration") or k.endswith("_count")}}
    except RequestFailure:
        raise
    except Exception as error:
        raise RequestFailure(str(error), output, "deadline" if isinstance(error, TimeoutError) else "error") from error


def run(args):
    WORK.mkdir(parents=True, exist_ok=True)
    if args.prepare:
        prepare()
        return
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    env = {k: v for k, v in os.environ.items() if not any(x in k.upper() for x in ("TOKEN", "API_KEY", "SECRET"))}
    env.update(OLLAMA_HOST=f"127.0.0.1:{port}", OLLAMA_MODELS=str(WORK / "models"), OLLAMA_NO_CLOUD="1",
        OLLAMA_NUM_PARALLEL="1", OLLAMA_MAX_LOADED_MODELS="1", OLLAMA_CONTEXT_LENGTH="4096", LLAMA_ARG_CACHE_RAM="0")
    report_path = ROOT / f"docs/evaluation/lighton-{'setup' if args.setup else args.tag}.json"
    num_gpu = -1 if args.gpu else 0
    report = {"status": "running", "samples": [], "mode": "Automatic GPU offload" if args.gpu else "CPU only", "threads": 4, "context": 4096,
        "num_gpu": num_gpu, "prompt_cache_ram_mib": 0,
        "hardware": json.loads((ROOT / "docs/evaluation/hinglish-hardware.json").read_text()),
        "available_ram_at_start_bytes": psutil.virtual_memory().available,
        "request_timeout_seconds": 120, "memory_cap_gib": 5.5, "peak_private_bytes": 0, "peak_resident_bytes": 0,
        "cloud_inference_requests": 0, "method": "Exact community package; image-only /api/chat, empty text; private Ollama server/store; unchanged app recognizers."}
    done = threading.Event()
    log_name = "server-setup.log" if args.setup else f"server-{args.tag}.log"
    with (WORK / log_name).open("wb") as log:
        process = subprocess.Popen([shutil.which("ollama"), "serve"], env=env, stdin=subprocess.DEVNULL,
            stdout=log, stderr=log, creationflags=0x08000000)
        boundary = ChildBoundary(process, int(5.5 * 1024**3))
        def monitor():
            while not done.wait(.2) and process.poll() is None:
                try:
                    tree = [psutil.Process(process.pid)] + psutil.Process(process.pid).children(recursive=True)
                    usages = [helpers.memory(p.pid) for p in tree]
                    for field in ("private", "resident"):
                        total = sum(u[field] for u in usages)
                        report[f"peak_{field}_bytes"] = max(report[f"peak_{field}_bytes"], total)
                        if total > 5.5 * 1024**3:
                            report["resource_error"] = "Private Ollama process tree exceeded 5.5 GiB budget"
                            process.kill()
                except psutil.Error:
                    pass
        watcher = threading.Thread(target=monitor, daemon=True)
        watcher.start()
        try:
            started = time.monotonic()
            while time.monotonic() - started < 30:
                if process.poll() is not None:
                    raise RuntimeError("Private Ollama server exited during startup")
                try:
                    helpers.request_json(base + "/api/version", timeout=2)
                    break
                except OSError:
                    time.sleep(.25)
            else:
                raise TimeoutError("Private server did not become ready")
            if args.setup:
                print("Pulling", MODEL, "into private benchmark store", flush=True)
                request = urllib.request.Request(base + "/api/pull", data=json.dumps({"model": MODEL, "stream": True}).encode(),
                    headers={"Content-Type": "application/json"})
                last, download_start = 0, time.monotonic()
                with urllib.request.urlopen(request, timeout=60) as response:
                    for line in response:
                        event = json.loads(line)
                        if event.get("error"):
                            raise RuntimeError(event["error"])
                        if time.monotonic() - download_start > 3600:
                            raise TimeoutError("Model pull exceeded one-hour download limit")
                        if time.monotonic() - last > 20 or event["status"] == "success":
                            print(json.dumps(event), flush=True)
                            last = time.monotonic()
                report["model"] = verify_manifest(base)
                report["status"] = "completed"
                return
            report["model"] = verify_manifest(base)
            samples = json.loads(args.samples.read_text("utf-8"))
            if args.resume and report_path.exists():
                previous = json.loads(report_path.read_text("utf-8"))
                for field in ("model", "threads", "context", "request_timeout_seconds", "mode", "num_gpu", "prompt_cache_ram_mib"):
                    assert previous[field] == report[field], "Resume configuration differs"
                report = previous
                report["status"] = "running"
            completed = {s["id"] for s in report["samples"]}
            # Empty /api/generate explicitly preloads without generating text; /api/chat is used for images.
            started = time.monotonic()
            post(base, "/api/generate", {"model": MODEL, "prompt": "", "keep_alive": "30m",
                "options": {"num_gpu": num_gpu, "num_thread": 4, "num_ctx": 4096}}, timeout=120)
            report["load_seconds"] = round(time.monotonic() - started, 3)
            devices = helpers.request_json(base + "/api/ps")
            report["loaded_model"] = devices
            if not args.gpu:
                assert all(m.get("size_vram", 0) == 0 for m in devices["models"]), "Unexpected GPU offload"
            print("Ready", report["load_seconds"], "seconds", flush=True)
            for sample in samples:
                if sample["id"] in completed:
                    continue
                assert digest(ROOT / sample["path"]) == sample["input_sha256"], "Input changed"
                print("Processing", sample["id"], flush=True)
                started = time.monotonic()
                try:
                    item = sample | generate(base, sample, num_gpu) | {"seconds": round(time.monotonic() - started, 3), "prompt": ""}
                except Exception as error:
                    item = sample | {"prediction": getattr(error, "partial", ""), "error": str(error),
                        "finish_reason": getattr(error, "reason", "error"), "seconds": round(time.monotonic() - started, 3), "prompt": ""}
                report["samples"].append(item)
                save(report_path, report)
                print(sample["id"], item["seconds"], item["finish_reason"], flush=True)
                if process.poll() is not None:
                    raise RuntimeError("Private server exited; inspect saved log")
                if item.get("error") and item["finish_reason"] != "deadline":
                    raise RuntimeError("Request failed; inspect compatibility before continuing")
            report["status"] = "completed"
        except Exception as error:
            report["status"] = "failed"
            report["error"] = str(error)
            print("Failed", str(error), flush=True)
        finally:
            done.set()
            watcher.join(timeout=2)
            boundary.close()
            if process.poll() is None:
                process.wait(timeout=10)
            report["server_exit_code"] = process.returncode
            save(report_path, report)
    print("Saved", report_path, flush=True)
    if report["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--samples", type=Path)
    parser.add_argument("--tag", default="pilot-1280")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--gpu", action="store_true")
    args = parser.parse_args()
    if not (args.setup or args.prepare or args.samples):
        parser.error("Choose --setup, --prepare or --samples")
    run(args)
