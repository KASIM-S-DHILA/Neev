import argparse
import json
import os
import socket
import threading
from pathlib import Path

import uvicorn

from .api import create_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    token = os.environ.get("STUDYLENS_API_TOKEN", "")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", args.port))
    port = sock.getsockname()[1]
    server = None
    def shutdown():
        server.should_exit = True
    app = create_app(Path(args.data_dir), token,
        ready=lambda: print(json.dumps({"event": "ready", "port": port}), flush=True),
        shutdown=shutdown, start_worker=True, allow_eval=os.environ.get("STUDYLENS_QUEUE_EVAL") == "1")
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False, timeout_graceful_shutdown=2)
    server = uvicorn.Server(config)
    if os.environ.get("STUDYLENS_PARENT_PIPE") == "1":
        def parent_closed():
            import sys
            sys.stdin.buffer.read(1)
            server.should_exit = True
        threading.Thread(target=parent_closed, daemon=True).start()
    try:
        server.run(sockets=[sock])
    finally:
        sock.close()


if __name__ == "__main__":
    main()
