# evaluation — Track D benchmark (reserved, not implemented)

Home of the **scored, repeatable** benchmark. Scaffolded in the B4 architecture
reset with interfaces only; see [`__init__.py`](__init__.py) and
[`contracts.py`](contracts.py).

## Not the same thing

| | Where | What it is |
| --- | --- | --- |
| Ingestion pilots | [`docs/archive/ingestion-pilots/`](../docs/archive/ingestion-pilots/README.md) | Archived evidence of what was measured in Phases 1–7. Historical. |
| Ingestion evaluators | [`scripts/ingestion-evals/`](../scripts/ingestion-evals/README.md) | Runnable standalone runners. Several need a live provider or a model download, and several call `Worker` internals directly. |
| **Track D benchmark** | **this directory** | Scored, committed fixtures, offline, public-interface-only. Not built. |

Do not put pilot reports or evidence here. Do not add a runner here that needs
network access or a model download — that is what made the pilots unrepeatable.

## Status

Every entry point raises `NotImplementedError`. There is no suite, no fixtures,
and no runner yet. When it lands, a suite must pin a `revision` so a score can be
tied to the exact cases that produced it.

Current gaps are recorded in
[`docs/audit/CURRENT_ARCHITECTURE.md`](../docs/audit/CURRENT_ARCHITECTURE.md)
section 12.