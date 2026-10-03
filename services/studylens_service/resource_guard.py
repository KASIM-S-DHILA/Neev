"""Bound uncooperative parser work without putting it on the API event loop."""
import os
import sqlite3
import threading
import time

RECYCLE_EXIT = 75


def private_bytes():
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage", "PrivateUsage")]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        process = ctypes.windll.kernel32.GetCurrentProcess
        process.restype = wintypes.HANDLE
        query = ctypes.windll.psapi.GetProcessMemoryInfo
        query.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if query(process(), ctypes.byref(counters), counters.cb):
            return counters.PrivateUsage
    elif os.path.isfile("/proc/self/statm"):
        with open("/proc/self/statm") as stream:
            return int(stream.read().split()[1]) * os.sysconf("SC_PAGE_SIZE")
    return 0


class ParserGuard:
    def __init__(self, worker, job, *, timeout=30, memory_limit=512 * 1024**2):
        self.worker, self.job = worker, job
        self.timeout, self.memory_limit = timeout, memory_limit
        self.finished = threading.Event()
        self.heartbeat = time.monotonic()
        self.thread = threading.Thread(target=self.watch, daemon=True)

    def touch(self):
        self.heartbeat = time.monotonic()

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.finished.set()
        self.thread.join(timeout=.5)

    def watch(self):
        connection = sqlite3.connect(self.worker.root / "studylens.sqlite3", timeout=.1, isolation_level=None)
        stopping_since = None
        try:
            while not self.finished.wait(.1):
                try:
                    row = connection.execute("SELECT state,owner,cancel_requested FROM jobs WHERE id=?", (self.job["id"],)).fetchone()
                    if not row or row[0] != "running" or row[1] != self.worker.owner:
                        return
                    stopping = row[2] or self.worker.stop.is_set()
                    stopping_since = (stopping_since or time.monotonic()) if stopping else None
                    error = None
                    state, stage = "failed", "Needs attention"
                    if stopping_since and time.monotonic() - stopping_since >= 1:
                        state, stage = ("cancelled", "Cancelled") if row[2] else ("queued", "Paused for restart")
                    elif private_bytes() > self.memory_limit:
                        error = "Source processing exceeded its 512 MB worker budget. Split or simplify the file; the original is saved."
                    elif time.monotonic() - self.heartbeat > self.timeout:
                        error = "A source processing step exceeded its 30-second limit. Split or simplify the file; saved units are retained."
                    else:
                        continue
                    # Only recycle after committing this job's terminal/pause state.
                    changed = connection.execute("""UPDATE jobs SET state=?,stage=?,error=?,owner=NULL,updated_at=?,
                        recoveries=recoveries+CASE WHEN ?='queued' THEN 1 ELSE 0 END
                        WHERE id=? AND owner=? AND state='running'""",
                        (state, stage, error, time.time(), state, self.job["id"], self.worker.owner)).rowcount
                    if changed:
                        os._exit(RECYCLE_EXIT)
                    return
                except sqlite3.OperationalError:
                    continue
        finally:
            connection.close()
