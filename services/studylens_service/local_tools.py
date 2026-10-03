"""Bound native helper processes; never invoke a shell or put them on the API loop."""
import os
import shutil
import subprocess
import time
from pathlib import Path
from .job_errors import ExtractionFailure


def find_tool(name):
    override = os.environ.get("STUDYLENS_" + name.upper())
    if override:
        return str(Path(override).resolve()) if Path(override).is_file() else None
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        choices = {"tesseract": "Tesseract-OCR/tesseract.exe", "soffice": "LibreOffice/program/soffice.exe"}
        candidate = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / choices.get(name, "__missing_tool__")
        if candidate.is_file():
            return str(candidate)
    return None


class ChildBoundary:
    """Windows job: child tree dies if its worker exits; cap native private memory."""
    def __init__(self, process, memory_limit=512 * 1024**2):
        self.handle = None
        if os.name != "nt":
            return
        import ctypes
        from ctypes import wintypes
        class Basic(ctypes.Structure):
            _fields_ = [("time1", ctypes.c_longlong), ("time2", ctypes.c_longlong), ("flags", wintypes.DWORD),
                ("min", ctypes.c_size_t), ("max", ctypes.c_size_t), ("active", wintypes.DWORD),
                ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD), ("scheduling", wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [("a" + str(i), ctypes.c_ulonglong) for i in range(6)]
        class Extended(ctypes.Structure):
            _fields_ = [("basic", Basic), ("io", IO), ("process_memory", ctypes.c_size_t),
                ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t), ("peak_job", ctypes.c_size_t)]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel.CreateJobObjectW.restype = wintypes.HANDLE
        kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel = kernel
        handle = kernel.CreateJobObjectW(None, None)
        limits = Extended()
        limits.basic.flags = 0x2000 | 0x200  # KILL_ON_JOB_CLOSE | JOB_MEMORY
        limits.job_memory = memory_limit
        if not handle or not kernel.SetInformationJobObject(handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(handle, wintypes.HANDLE(int(process._handle))):
            if handle:
                kernel.CloseHandle(handle)
            process.kill()
            process.wait()
            raise ExtractionFailure("Could not isolate the document helper. Check native tool permissions.")
        self.handle = handle

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def run_tool(args, worker, job, guard, folder, timeout=20, allowed_codes=(0,), *, memory_limit=512 * 1024**2):
    # Files avoid unbounded PIPE buffers and allow cancellation while a helper runs.
    output, errors = folder / "helper-out.log", folder / "helper-error.log"
    boundary = None
    helper_env = {**os.environ, "OMP_THREAD_LIMIT": "1"}
    for name in ("GROQ_API_KEY", "STUDYLENS_API_TOKEN"):
        helper_env.pop(name, None)
    with output.open("wb") as stdout, errors.open("wb") as stderr:
        process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
            env=helper_env,
            **({"creationflags": 0x08000000} if os.name == "nt" else {"start_new_session": True}))
        try:
            boundary = ChildBoundary(process, memory_limit)
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                worker.check(job)
                guard.touch()
                if time.monotonic() > deadline or max(output.stat().st_size, errors.stat().st_size) > 4 * 1024**2:
                    raise ExtractionFailure("The native document helper exceeded its time/output limit. Export a smaller or clearer source.")
                worker.stop.wait(.05)
            if process.returncode not in allowed_codes:
                raise ExtractionFailure("The native document helper could not process this source. Check its installation/language data or export a clearer copy.")
            return output.read_text(encoding="utf-8", errors="replace"), process.returncode
        finally:
            if process.poll() is None:
                if os.name == "nt":
                    process.kill()
                else:
                    import signal
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
            if boundary:
                boundary.close()
