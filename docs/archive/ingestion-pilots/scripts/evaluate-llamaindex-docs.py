"""Isolated Phase 8 LlamaIndex BM25 pilot over Neev's own documentation.

Run with tmp/llamaindex-eval/.venv; do not add these packages to the app runtime.
"""
import hashlib
import importlib.metadata
import json
import os
import socket
import statistics
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path
from unittest.mock import patch

from llama_index.core.schema import TextNode
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.vector_stores.types import FilterOperator, MetadataFilter, MetadataFilters
from llama_index.retrievers.bm25 import BM25Retriever


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp/llamaindex-eval"
DOCS = ("docs/PHASES.md", "docs/CONTEXT_HANDOFF.md")
QUESTIONS = (
    ("What is Phase 8 supposed to build?", "docs/PHASES.md", "Hybrid lexical/vector retrieval"),
    ("When may Neev search the web for outside knowledge?", "docs/CONTEXT_HANDOFF.md", "External web search remains a different feature"),
    ("Where does the renamed desktop app keep saved data?", "docs/CONTEXT_HANDOFF.md", "%APPDATA%/StudyLens"),
    ("How many video frames can be retained?", "docs/CONTEXT_HANDOFF.md", "maximum 600 retained frames"),
    ("How do local copies line up with YouTube captions?", "docs/CONTEXT_HANDOFF.md", "YouTube-to-local time offset"),
    ("Which learner evidence methods are required?", "docs/PHASES.md", "Bayesian knowledge tracing"),
    ("What audio feature is on hold?", "docs/PHASES.md", "Live audio tutoring and speech-model selection remain on hold"),
    ("What permission is needed for Phase 13 search?", "docs/PHASES.md", "Explicit-per-action SearXNG search"),
)


def main():
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("GROQ_API_KEY", None)
    OUT.mkdir(parents=True, exist_ok=True)
    nodes = []
    for relative in DOCS:
        path = ROOT / relative
        version = hashlib.sha256(path.read_bytes()).hexdigest()
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            text = line.strip()
            if len(text) < 45:
                continue
            identifier = hashlib.sha256(f"{relative}:{line_number}:{text}".encode()).hexdigest()[:32]
            nodes.append(TextNode(id_=identifier, text=text, metadata={
                "workspace_id": "semester-3", "source_path": relative, "line": line_number,
                "source_version": version, "provenance": "local_documentation"}))
    # A deliberately conflicting second-workspace hit tests metadata isolation.
    nodes.append(TextNode(id_="other-workspace-distractor", text="Phase 8 Hybrid lexical/vector retrieval must use cloud only.",
        metadata={"workspace_id": "other-workspace", "source_path": "other.md", "line": 1,
            "source_version": "fixture", "provenance": "authored_scope_fixture"}))
    gold = []
    for question, source, phrase in QUESTIONS:
        matches = [node for node in nodes if node.metadata["source_path"] == source and phrase in node.text]
        if len(matches) != 1:
            raise ValueError(f"Gold locator is not unique for {question}: {len(matches)}")
        gold.append((question, matches[0]))
    store = SimpleDocumentStore()
    store.add_documents(nodes)
    filters = MetadataFilters(filters=[MetadataFilter(key="workspace_id", value="semester-3",
        operator=FilterOperator.EQ)])
    tracemalloc.start()
    start = time.perf_counter()
    with patch.object(socket.socket, "connect", side_effect=RuntimeError("Network disabled in LlamaIndex pilot")):
        retriever = BM25Retriever.from_defaults(docstore=store, similarity_top_k=5, filters=filters)
        build_seconds = time.perf_counter() - start
        records, latencies = [], []
        for question, expected in gold:
            began = time.perf_counter()
            hits = retriever.retrieve(question)
            latencies.append((time.perf_counter() - began) * 1000)
            ranked = [hit.node.node_id for hit in hits]
            rank = ranked.index(expected.node_id) + 1 if expected.node_id in ranked else None
            records.append({"question": question, "expected": {"source_path": expected.metadata["source_path"],
                "line": expected.metadata["line"], "source_version": expected.metadata["source_version"]},
                "rank": rank, "top3": [{"source_path": hit.node.metadata["source_path"],
                    "line": hit.node.metadata["line"], "score": hit.score} for hit in hits[:3]],
                "scope_ok": all(hit.node.metadata["workspace_id"] == "semester-3" for hit in hits)})
        unrelated = retriever.retrieve("How many moons does Jupiter have?")
        index_dir = OUT / "bm25"
        retriever.persist(str(index_dir))
        store_path = OUT / "docstore.json"
        store.persist(str(store_path))
        restored_store = SimpleDocumentStore.from_persist_path(str(store_path))
        restored = BM25Retriever.from_defaults(docstore=restored_store, similarity_top_k=5, filters=filters)
        restart_same_top = restored.retrieve(gold[0][0])[0].node.node_id == retriever.retrieve(gold[0][0])[0].node.node_id
        direct = BM25Retriever.from_persist_dir(str(index_dir))
        direct_hits = direct.retrieve(gold[0][0])
        direct_restart_same_top = direct_hits[0].node.node_id == retriever.retrieve(gold[0][0])[0].node.node_id
        direct_restart_scope_ok = all(hit.node.metadata["workspace_id"] == "semester-3" for hit in direct_hits)
    _, python_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    working_set = None
    if os.name == "nt":
        working_set = int(subprocess.check_output(["powershell", "-NoProfile", "-Command",
            f"(Get-Process -Id {os.getpid()}).WorkingSet64"], text=True).strip())
    result = {"status": "completed", "python": sys.version.split()[0],
        "llama_index_core": importlib.metadata.version("llama-index-core"),
        "llama_index_retrievers_bm25": importlib.metadata.version("llama-index-retrievers-bm25"),
        "documents": list(DOCS), "nodes": len(nodes), "questions": records,
        "hit_at_1": sum(row["rank"] == 1 for row in records) / len(records),
        "hit_at_3": sum(row["rank"] is not None and row["rank"] <= 3 for row in records) / len(records),
        "mrr_at_5": sum(1 / row["rank"] if row["rank"] else 0 for row in records) / len(records),
        "scope_ok": all(row["scope_ok"] for row in records),
        "unrelated_query_returned": len(unrelated), "restart_same_top": restart_same_top,
        "direct_restart_same_top": direct_restart_same_top, "direct_restart_scope_ok": direct_restart_scope_ok,
        "build_seconds": build_seconds, "query_ms_median": statistics.median(latencies),
        "query_ms_max": max(latencies), "python_tracemalloc_peak_bytes": python_peak,
        "working_set_bytes_after_run": working_set,
        "persisted_bytes": store_path.stat().st_size + sum(path.stat().st_size for path in index_dir.rglob("*") if path.is_file())}
    (OUT / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["scope_ok"] or not restart_same_top or not direct_restart_same_top or not direct_restart_scope_ok:
        raise SystemExit("Scope or persistence check failed")


if __name__ == "__main__":
    main()
