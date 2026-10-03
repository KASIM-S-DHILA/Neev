# LlamaIndex capacity check for Neev Phase 8

October 3, 2026. This is a documentation review plus an isolated offline pilot. It is **not** a Phase 8 implementation or a student-material quality benchmark.

## What the official documentation supports

| Need | Documentation finding | Neev implication |
| --- | --- | --- |
| Local keyword retrieval | [BM25Retriever](https://developers.llamaindex.ai/python/framework/integrations/retrievers/bm25_retriever/) accepts nodes/docstores, metadata filters and disk persistence. | Can index Neev content units while retaining source/version/locator metadata. Backend scoping still needs its own enforcement. |
| Hybrid retrieval | The [BM25 guide](https://developers.llamaindex.ai/python/framework/integrations/retrievers/bm25_retriever/) combines BM25 with a vector index using `QueryFusionRetriever`; the [fusion guide](https://developers.llamaindex.ai/python/framework/integrations/retrievers/reciprocal_rerank_fusion/) describes reciprocal rank fusion. | API capacity exists, but this pilot did not run a vector model or validate hybrid ranking. |
| Local persistence | [Document stores](https://developers.llamaindex.ai/python/framework/module_guides/storing/docstores/) and [storage contexts](https://developers.llamaindex.ai/python/framework/module_guides/storing/save_load/) can persist/reload nodes and indexes. | A prototype can rebuild or reload retrieval state after restart. Neev must still invalidate stale versions atomically. |
| Evaluation | The [evaluation guide](https://developers.llamaindex.ai/python/framework/module_guides/evaluating/) names hit rate, MRR and precision for retrievers. | Use fixed source-location gold questions before integration. These metrics do not measure answer faithfulness. |
| Local embeddings | [HuggingFace embeddings](https://developers.llamaindex.ai/python/framework/integrations/embeddings/huggingface/) support local sentence-transformer models. | A specific model, download size, multilingual quality and 8 GB behavior need a separate test. |
| Package choice | The [installation guide](https://developers.llamaindex.ai/python/framework/getting_started/installation/) says the `llama-index` starter bundle includes OpenAI integrations/defaults and supports selective installation of packages. | This pilot installed only core plus BM25 in an ignored isolated environment; Neev's service requirements and cloud configuration were untouched. |

## Offline pilot

Inputs were the current `docs/PHASES.md` and `docs/CONTEXT_HANDOFF.md`. Each substantive line became a node with stable ID, source path, line number, file SHA-256, workspace and `local_documentation` provenance. An authored conflicting node in a second workspace tested filtering. Eight fixed questions targeted exact documented lines. No model, provider key, remote content, app search or user data was used. Network connects were blocked during BM25 indexing and retrieval.

Environment: Windows, Python 3.12.14, `llama-index-core==0.14.25`, `llama-index-retrievers-bm25==0.8.0`; `pip check` passed. The isolated environment occupies **195.4 MB** on disk. It is under ignored `tmp/llamaindex-eval/.venv`, outside the app's dependency lock.

| Measure | Result |
| --- | ---: |
| Nodes | 93, including one foreign-workspace distractor |
| Exact gold line at rank 1 | 3/8 (37.5%) |
| Exact gold line within top 3 | 5/8 (62.5%) |
| MRR@5 | 0.55 |
| Workspace scope | Passed for all returned scored nodes |
| Restart | Rebuilt from persisted docstore and directly reloaded saved BM25 index; first result and scope checks passed |
| Unrelated question | Returned 5 nodes; no abstention decision |
| Build and query timing | 0.154 s build; 4.48 ms median, 5.74 ms maximum query on this tiny corpus |
| Memory and index size | 115.7 MB process working set after run; 275,326 persisted bytes |

The complete question ranks, locators, version hashes, scores and measurements are in [the JSON result](llamaindex-docs-pilot.json). Line-level indexing makes exact citations easy but is a deliberately small, narrow input. The Phase 8 deliverable requires source-version correctness, irrelevant-query handling, cross-source ranking and a larger reviewed gold set. This pilot missed the Phase 8 target line entirely in the top five and placed the YouTube-offset and learner-method targets fifth. It cannot establish that LlamaIndex improves on a simpler SQLite FTS5 baseline.

The process working-set number is one point after the run, not peak RSS, and the 1.87 MB Python `tracemalloc` peak omits native allocator usage. Timing and memory from 93 documentation lines do not establish performance on an 8 GB laptop or a course-sized corpus. No student manual check was performed.

## Reproduce

From the repository root in PowerShell, using the existing project Python only to create an isolated environment:

```powershell
.\.venv\Scripts\python.exe -m venv tmp\llamaindex-eval\.venv
tmp\llamaindex-eval\.venv\Scripts\python.exe -m pip install --disable-pip-version-check --no-input llama-index-core==0.14.25 llama-index-retrievers-bm25==0.8.0
tmp\llamaindex-eval\.venv\Scripts\python.exe -m pip check
tmp\llamaindex-eval\.venv\Scripts\python.exe scripts\evaluate-llamaindex-docs.py
```

Next independent gate: compare BM25, SQLite FTS5 and a selected local embedding plus fusion on the **same** reviewed student-material questions, enforce workspace/source-version filters before ranking, check off-material refusal, and measure peak process memory and restart behavior on the target laptop. Until then, LlamaIndex remains an evaluated option rather than an app dependency.
