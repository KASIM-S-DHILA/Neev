# evaluation — reserved

This directory is intentionally empty. It is reserved for the **Track D
benchmark**: the scored, repeatable evaluation harness (grounding/citation
scoring and the simulated learner) that is specified but not yet built.

Do not put ingestion pilot evidence here. That material is historical and
lives in [`docs/archive/ingestion-pilots/`](../docs/archive/ingestion-pilots/README.md).
Runnable ingestion evaluators live in
[`scripts/ingestion-evals/`](../scripts/ingestion-evals/README.md).

Expected contents once Track D lands: a runnable entry point, its scored
datasets, and a results directory. See
[`docs/audit/CURRENT_ARCHITECTURE.md`](../docs/audit/CURRENT_ARCHITECTURE.md)
section 12 for the current gap.