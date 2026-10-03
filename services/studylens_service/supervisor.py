import asyncio
import os
import sys


class WorkerSupervisor:
    def __init__(self, root, allow_eval=False):
        self.root = root
        self.allow_eval = allow_eval
        self.process = None
        self.task = None
        self.closing = False
        self.error = None
        self.restarts = 0
        self.lock = asyncio.Lock()

    async def spawn(self):
        args = [sys.executable, "-m", "studylens_service.worker", "--data-dir", str(self.root)]
        if self.allow_eval:
            args.append("--allow-eval")
        env = dict(os.environ)
        env.pop("STUDYLENS_API_TOKEN", None)
        async with self.lock:
            if self.closing:
                return
            self.process = await asyncio.create_subprocess_exec(*args, stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL, env=env,
                **({"creationflags": 0x08000000} if os.name == "nt" else {}))

    async def start(self):
        try:
            await self.spawn()
            self.task = asyncio.create_task(self.monitor())
        except OSError:
            self.error = "The background worker could not start. Reopen Neev to retry."

    async def monitor(self):
        while not self.closing:
            await self.process.wait()
            if self.closing:
                return
            # Parser timeout, memory limit or an uncooperative cancellation:
            # that job was checkpointed before a deliberate worker recycle.
            if self.process.returncode == 75:
                await self.spawn()
                continue
            self.restarts += 1
            if self.restarts > 3:
                self.error = "The background worker stopped repeatedly. Saved work is retained; reopen Neev to retry."
                return
            await asyncio.sleep(.2 * self.restarts)
            if self.closing:
                return
            try:
                await self.spawn()
            except OSError:
                self.error = "The background worker could not restart. Reopen Neev to retry."
                return

    def status(self):
        return {"available": bool(self.process and self.process.returncode is None), "error": self.error,
            "restarts": self.restarts, "max_active_heavy_jobs": 1, "evaluation_enabled": self.allow_eval}

    async def stop(self):
        async with self.lock:
            self.closing = True
            process = self.process
            if process and process.returncode is None:
                process.stdin.close()
        if process and process.returncode is None:
            try:
                await asyncio.wait_for(process.wait(), 1.5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        if self.task:
            await self.task
