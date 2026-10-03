"""Isolated Gemma 4 E2B CPU evaluation; no application data or settings changes."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import importlib.util

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "tmp/gemma4-omni"
os.environ["HF_HOME"] = str(WORK / "hf-cache")
os.environ["HF_HUB_DISABLE_XET"] = "1"
REPO = "ggml-org/gemma-4-E2B-it-GGUF"
REVISION = "b4243c156154b6dca9324415f8c7ccc098b4aed1"
NAMES = ["gemma-4-E2B-it-Q4_0.gguf", "mmproj-gemma-4-E2B-it-BF16.gguf"]
spec = importlib.util.spec_from_file_location("hunyuan_helpers", ROOT / "scripts/ingestion-evals/evaluate-hunyuan.py")
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


class RequestFailure(Exception):
    def __init__(self, message, partial="", reason="error"):
        super().__init__(message)
        self.partial = partial
        self.reason = reason


def complete(base, payload, key, budget=120):
    payload = payload | {"stream": True, "stream_options": {"include_usage": True}}
    request = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    started = time.monotonic()
    output, finish, usage, timings = "", None, None, None
    try:
        with urllib.request.urlopen(request, timeout=budget) as response:
            for line in response:
                if time.monotonic() - started > budget:
                    raise RequestFailure("Request exceeded 120-second budget", output, "deadline")
                if not line.startswith(b"data: "):
                    continue
                raw = line[6:].strip()
                if raw == b"[DONE]":
                    break
                event = json.loads(raw)
                usage = event.get("usage") or usage
                timings = event.get("timings") or timings
                for choice in event.get("choices", []):
                    output += choice.get("delta", {}).get("content") or ""
                    finish = choice.get("finish_reason") or finish
        if not finish:
            raise RequestFailure("Stream ended without a completion marker", output)
        return {"choices": [{"message": {"content": output}, "finish_reason": finish}], "usage": usage, "timings": timings}
    except RequestFailure:
        raise
    except Exception as error:
        raise RequestFailure(str(error), output, "deadline" if isinstance(error, TimeoutError) else "error") from error


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def download_ranges(url, target, expected_hash, size):
    if target.exists() and target.stat().st_size == size:
        with target.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() == expected_hash:
                print("Already verified", target.name, flush=True)
                return
    # Short ranged transfers avoid stalled full-file CDN responses. Retain chunks for restart.
    chunk_size = 8 * 1024**2
    chunks = WORK / "download-chunks" / target.name
    chunks.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    if partial.exists():
        with partial.open("rb") as stream:
            for index in range(partial.stat().st_size // chunk_size):
                piece = chunks / f"{index:05d}.bin"
                data = stream.read(chunk_size)
                if not piece.exists():
                    piece.write_bytes(data)
    count = (size + chunk_size - 1) // chunk_size
    def fetch(index):
        start = index * chunk_size
        length = min(chunk_size, size - start)
        path = chunks / f"{index:05d}.bin"
        if path.exists() and path.stat().st_size == length:
            return length
        for attempt in range(3):
            try:
                request = urllib.request.Request(url + f"&chunk={index}", headers={"Range": f"bytes={start}-{start+length-1}", "User-Agent": "StudyLens-local-model-evaluation"})
                with urllib.request.urlopen(request, timeout=35) as response:
                    if response.status != 206 or response.headers.get("Content-Range") != f"bytes {start}-{start+length-1}/{size}":
                        raise ValueError("Invalid ranged response")
                    data = response.read(length + 1)
                if len(data) != length:
                    raise ValueError("Incomplete ranged response")
                path.write_bytes(data)
                return length
            except (OSError, ValueError):
                if attempt == 2:
                    raise
                time.sleep(1)
    completed = 0
    last = time.monotonic()
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(fetch, index) for index in range(count)]
        for future in as_completed(futures):
            completed += future.result()
            if time.monotonic() - last > 20:
                print(target.name, round(100 * completed / size), "%", flush=True)
                last = time.monotonic()
    digest = hashlib.sha256()
    with partial.open("wb") as output:
        for index in range(count):
            data = (chunks / f"{index:05d}.bin").read_bytes()
            output.write(data)
            digest.update(data)
    if partial.stat().st_size != size or digest.hexdigest() != expected_hash:
        raise ValueError("Model download integrity mismatch")
    partial.replace(target)
    print("Downloaded and verified", target.name, size, "bytes", flush=True)


def setup():
    from huggingface_hub import HfApi
    WORK.mkdir(parents=True, exist_ok=True)
    info = HfApi().model_info(REPO, revision=REVISION, files_metadata=True)
    manifest = {"repo": REPO, "revision": info.sha, "files": [], "runtime": "llama.cpp b11303 (60e9cf7a7)"}
    for name in NAMES:
        item = next(f for f in info.siblings if f.rfilename == name)
        print("Downloading", name, item.size, "bytes", flush=True)
        path = WORK / name
        download_ranges(f"https://huggingface.co/{REPO}/resolve/{REVISION}/{name}?download=true", path, item.lfs.sha256, item.size)
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != item.lfs.sha256 or path.stat().st_size != item.size:
            raise ValueError("Model integrity mismatch")
        manifest["files"].append({"name": name, "bytes": item.size, "sha256": digest})
        save(WORK / "manifest.json", manifest)
        print("Verified", name, flush=True)
    print("Setup complete", flush=True)


def serve(samples, tag="pilot", image_tokens=0, resume=False):
    WORK.mkdir(parents=True, exist_ok=True)
    report_path = ROOT / f"tmp/ingestion-evals/gemma4-{tag}.json"
    report = {"status": "running", "model": json.loads((WORK / "manifest.json").read_text()),
        "mode": "CPU only", "threads": 4, "context": 4096, "request_timeout_seconds": 120, "image_max_tokens": image_tokens or "runtime default",
        "memory_cap_gib": 5.5, "peak_private_bytes": 0, "peak_resident_bytes": 0,
        "cloud_inference_requests": 0, "samples": [], "method": "Standalone llama.cpp server; unchanged app recognizers. No source references in inference prompts."}
    if resume and report_path.exists():
        previous = json.loads(report_path.read_text("utf-8"))
        for field in ("model", "threads", "context", "image_max_tokens"):
            if previous[field] != report[field]:
                raise ValueError("Resume settings differ from saved benchmark")
        report = previous
        report["status"] = "running"
        report.setdefault("continuations", 0)
        report["continuations"] += 1
    completed_ids = {s["id"] for s in report["samples"]}
    samples = [s for s in samples if s["id"] not in completed_ids]
    if not samples:
        report["status"] = "completed"
        save(report_path, report)
        print("All samples already attempted", flush=True)
        return
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    key = secrets.token_urlsafe(24)
    base = f"http://127.0.0.1:{port}"
    binary = ROOT / "tmp/hunyuan-ocr/bin/llama-server.exe"
    args = [str(binary), "-m", str(WORK / NAMES[0]), "--mmproj", str(WORK / NAMES[1]),
        "--host", "127.0.0.1", "--port", str(port), "--api-key", key, "--alias", "gemma4-eval",
        "--ctx-size", "4096", "--parallel", "1", "--threads", "4", "--threads-batch", "4",
        "--batch-size", "256", "--ubatch-size", "128", "--n-gpu-layers", "0",
        "--no-mmproj-offload", "--jinja", "--reasoning", "off", "--cache-ram", "0"]
    if image_tokens:
        args.extend(["--image-max-tokens", str(image_tokens)])
    done = threading.Event()
    with (WORK / f"server-{tag}.log").open("wb") as log:
        child_env = {k: v for k, v in os.environ.items() if not any(x in k.upper() for x in ("TOKEN", "API_KEY", "SECRET"))}
        process = subprocess.Popen(args, stdout=log, stderr=log, env=child_env, creationflags=0x08000000)
        def monitor():
            while not done.wait(.1) and process.poll() is None:
                usage = helpers.memory(process.pid)
                for field in ("private", "resident"):
                    report[f"peak_{field}_bytes"] = max(report[f"peak_{field}_bytes"], usage[field])
                if max(usage.values()) > 5.5 * 1024**3:
                    report["resource_error"] = "Server exceeded 5.5 GiB private or resident memory budget"
                    process.kill()
                    break
        watcher = threading.Thread(target=monitor, daemon=True)
        watcher.start()
        try:
            started = time.monotonic()
            while time.monotonic() - started < 120:
                if process.poll() is not None:
                    raise RuntimeError("Server exited during loading; inspect saved server log")
                try:
                    if helpers.request_json(base + "/health", timeout=2, api_key=key).get("status") == "ok":
                        break
                except (urllib.error.URLError, TimeoutError):
                    time.sleep(.25)
            else:
                raise TimeoutError("Server did not load in 120 seconds")
            report["load_seconds"] = round(time.monotonic() - started, 3)
            print("Ready", report["load_seconds"], "seconds", flush=True)
            for sample in samples:
                content = [{"type": "text", "text": sample["prompt"]}]
                if sample.get("kind") == "audio":
                    content.append({"type": "input_audio", "input_audio": {
                        "data": base64.b64encode((ROOT / sample["path"]).read_bytes()).decode(), "format": "wav"}})
                elif sample.get("kind") == "image":
                    content.append({"type": "image_url", "image_url": {
                        "url": "data:image/png;base64," + base64.b64encode((ROOT / sample["path"]).read_bytes()).decode()}})
                payload = {"model": "gemma4-eval", "messages": [{"role": "user", "content": content}],
                    "temperature": 0, "max_tokens": sample.get("max_tokens", 512), "stream": False,
                    "cache_prompt": False, "chat_template_kwargs": {"enable_thinking": False}}
                print("Processing", sample["id"], flush=True)
                started = time.monotonic()
                try:
                    response = complete(base, payload, key)
                    choice = response["choices"][0]
                    item = sample | {"prediction": choice["message"]["content"], "finish_reason": choice["finish_reason"],
                        "usage": response.get("usage"), "timings": response.get("timings"), "seconds": round(time.monotonic() - started, 3)}
                except Exception as error:
                    item = sample | {"error": str(error), "prediction": getattr(error, "partial", ""),
                        "finish_reason": getattr(error, "reason", "error"), "seconds": round(time.monotonic() - started, 3)}
                    report["samples"].append(item)
                    save(report_path, report)
                    print(sample["id"], item["seconds"], "seconds", item["finish_reason"], flush=True)
                    if process.poll() is not None:
                        raise
                    continue
                report["samples"].append(item)
                save(report_path, report)
                print(sample["id"], item["seconds"], "seconds", item["finish_reason"], flush=True)
            report["status"] = "completed"
        except Exception as error:
            report["status"] = "failed"
            report["error"] = str(error)
            print("Failed:", str(error), flush=True)
        finally:
            done.set()
            watcher.join(timeout=1)
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            report["server_exit_code"] = process.returncode
            save(report_path, report)
    print("Saved", report_path, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("--samples", type=Path)
    parser.add_argument("--tag", default="pilot")
    parser.add_argument("--image-tokens", type=int, default=0, choices=(0, 280, 560, 1120))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.setup:
        setup()
    elif args.samples:
        serve(json.loads(args.samples.read_text("utf-8")), args.tag, args.image_tokens, args.resume)
    else:
        parser.error("Choose --setup or --samples")
