"""Subprocess-only fault injection for Phase 4 evaluation. Never used by the app."""
import sys
import time
from functools import partial
from studylens_service import extraction, resource_guard, worker

mode = sys.argv.pop(1)
if mode == "slow-units":
    original = extraction.commit_unit
    def slow_commit(*args, **kwargs):
        original(*args, **kwargs)
        time.sleep(.2)
    extraction.commit_unit = slow_commit
elif mode in ("stall-parser", "timeout"):
    from pypdf._page import PageObject
    original = PageObject.extract_text
    def slow_extract(self, *args, **kwargs):
        time.sleep(10)
        return original(self, *args, **kwargs)
    PageObject.extract_text = slow_extract
    if mode == "timeout":
        resource_guard.ParserGuard = partial(resource_guard.ParserGuard, timeout=.4)
elif mode == "memory":
    # Exercise the real private-memory abort path using a deliberately tiny budget.
    resource_guard.ParserGuard = partial(resource_guard.ParserGuard, memory_limit=1)
    from pypdf._page import PageObject
    original = PageObject.extract_text
    def wait_for_guard(self, *args, **kwargs):
        time.sleep(2)
        return original(self, *args, **kwargs)
    PageObject.extract_text = wait_for_guard
elif mode == "slow-native":
    from pathlib import Path
    from studylens_service import local_tools
    original = local_tools.run_tool
    def slow_native(args, instance, job, guard, folder, **kwargs):
        (instance.root / "native-fixture-started").write_text("Explicit native cancellation fixture")
        return original([sys.executable, "-c", "import time; time.sleep(30)"], instance, job, guard, folder)
    local_tools.run_tool = slow_native
elif mode in ("office-good", "office-count-mismatch"):
    from pathlib import Path
    from studylens_service import local_tools
    from pypdf import PdfReader, PdfWriter
    original_run = local_tools.run_tool
    original_find = local_tools.find_tool
    def fixture_find(name):
        return sys.executable if name == "soffice" else original_find(name)
    def fixture_office(args, instance, job, guard, folder, **kwargs):
        if "--convert-to" not in args:
            return original_run(args, instance, job, guard, folder, **kwargs)
        # Explicit converter fixture: checks the adapter, not LibreOffice fidelity.
        writer = PdfWriter()
        path = Path(__file__).resolve().parents[2] / "docs/evaluation/fixtures/phase-04/digital-notes.pdf"
        writer.append(PdfReader(path), pages=(0, 2 if mode == "office-good" else 3))
        writer.write(folder / "source.pdf")
        (instance.root / "office-fixture-command.json").write_text(__import__("json").dumps(args))
        return "Explicit office adapter fixture", 0
    local_tools.find_tool = fixture_find
    local_tools.run_tool = fixture_office
worker.main()
