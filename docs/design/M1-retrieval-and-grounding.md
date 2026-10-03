# M1 — Retrieval and grounded answering (design only)

**Status: proposal. No code, no dependency, no migration.** This document exists
to be approved or corrected before any of it is built.

Branch context: `cleanup/architecture-reset` at `dd18146`. The contracts this
design fills in are the unimplemented scaffolds in
`studylens_service/knowledge/`, `grounding/`, `providers/` and the top-level
`evaluation/` package. Every entry point there currently raises
`NotImplementedError`.

Current behaviour, stated plainly: **there is no retrieval and there are no
grounded answers.** `GET .../content` is an inspection API that returns units
including `needs_ocr`, `suspect`, `unreadable`, `too_large` and `empty`. It is
not a retrieval corpus and M1 must never treat it as one.

---

## 1. Eligibility gate

One function decides what may be indexed and what may be cited:
`knowledge.eligible_source_versions()`. **It is the only place this rule lives.**
Retrieval, grounding, the citation builder and the benchmark all call it. Nothing
re-derives it.

A source version is eligible when **all** hold:

| Condition | Source of truth | Why |
| --- | --- | --- |
| Original integrity verified — a `verify_original` job for this version reached `succeeded` | `jobs`, `source_versions` | An unreadable original cannot support a citation |
| Extraction terminal and not failed — latest `extract_source` job is `succeeded` or `partial` | `jobs` | Mid-extraction content is incomplete by construction |
| For a `partial` extraction, **every** unit must be `text` | `content_units` | A partial extraction with a failed unit is not fully usable |
| At least one unit with `status == "text"` | `content_units` | Otherwise there is nothing to cite |
| Text integrity — unit `text_sha256` matches the stored `text` | `content_units` | A modified unit is not evidence of what was extracted |

A **unit** is eligible only when `status == "text"`. These are never indexed and
never cited, though they stay visible to the student in the content viewer:

| Status | Reason | Student-facing label if it ever surfaces |
| --- | --- | --- |
| `needs_ocr` | no text recognised yet | "Needs OCR" |
| `suspect` | automatic speech, unreviewed | "Automatic transcript — check against the audio" |
| `unreadable` / `too_large` / `empty` | extraction could not or would not proceed | "Not extracted" |

**Suspect units are the interesting case.** They are excluded because an
unreviewed transcript may contain ASR errors, and citing it as fact would be
dishonest. But excluding them entirely would break video and YouTube review,
which are core features today. So:

* `suspect` units are **not indexed** and **not citable as `VERIFIED`**.
* If a future milestone confirms a student's correction, the corrected text is
  stored as a **new unit version** that *is* eligible; the original `suspect`
  unit stays for history. M1 does not build this path, but the schema leaves room.
* A grounded answer about a video or YouTube source will therefore often have
  **no citable transcript**, only frames and captions. That is the correct
  outcome, and the answer must say so rather than guess.

Warnings and coverage gaps are carried through, never dropped. An eligible
version with warnings still yields citations, but `weakest_state()` must not
report `VERIFIED` while a warning applies.
---

## 2. Chunking

Chunking is per modality because the locators differ and the useful span length
differs by an order of magnitude.

| Modality | Unit locator | Chunk size | Overlap | Why |
| --- | --- | --- | --- | --- |
| Document text (`.txt`, `.md`) | `lines` (line_start…line_end, char_start…char_end, encoding) | 1200 chars | 200 chars | Line spans stay meaningful; char offsets keep sub-line precision |
| PDF page | `page` (+ width/height/rotation) | 1000 chars | 150 chars | A citation opens the page; splitting inside a table row is tolerable, inside a sentence is not |
| Slide | `slide` | whole slide, capped at 1500 chars | none | A slide is the student's unit of meaning; a partial slide citation is worse than none |
| Image | `image` (page index) | whole unit | none | Same reason; no text structure to preserve |
| Video frame / caption cue | `time` (start_seconds, end_seconds) | one cue or one retained frame | none | The citation is a timestamp; overlapping time spans would cite one moment twice |
| YouTube caption snapshot | `time` | one cue | none | As above |

Rules:

* **Never chunk across a content unit.** A chunk belongs to exactly one
  `content_unit_id`. This keeps `invalidate(source_version_id)` trivially correct
  and every chunk traceable to one locator.
* **Chunk text is derived, never authoritative.** `chunks.text` is a copy for
  embedding and display. Citations always quote `content_units.text` at the
  recorded locator, never the chunk copy.
* **`text_sha256` on every chunk** is the SHA-256 of the chunk text, so an index
  built from changed text is detectable as stale without re-reading the unit.
* **`chunker_version`** is bumped whenever any size, overlap or boundary rule
---

## 3. Storage — proposed migration `0006_retrieval`

Alembic head is `0005_youtube_media_links`. M1 adds **`0006_retrieval`**, forward
only, under `BEGIN IMMEDIATE` like every existing migration. No table is altered;
nothing existing is rewritten. Rollback is unsupported, consistent with D6.

```sql
-- One row per chunk. Source of truth for retrieval.
CREATE TABLE chunks (
    id                TEXT PRIMARY KEY,      -- deterministic; see below
    workspace_id      TEXT NOT NULL,
    source_version_id TEXT NOT NULL REFERENCES source_versions(id) ON DELETE CASCADE,
    content_unit_id   TEXT NOT NULL REFERENCES content_units(id)   ON DELETE CASCADE,
    ordinal           INTEGER NOT NULL,      -- position within the unit
    modality          TEXT NOT NULL,         -- document|pdf|slide|image|time
    text              TEXT NOT NULL,
    text_sha256       TEXT NOT NULL,
    locator_json      TEXT NOT NULL,         -- exact source locator, verbatim
    chunker_version   INTEGER NOT NULL,
    created_at        TEXT NOT NULL,
    UNIQUE (content_unit_id, ordinal)
);

-- Vectors live apart so a model swap does not rewrite chunk rows.
CREATE TABLE embeddings (
    chunk_id         TEXT PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
    model            TEXT NOT NULL,          -- e.g. "multilingual-e5-small"
    revision         TEXT NOT NULL,          -- immutable model revision hash
    dimensions       INTEGER NOT NULL,
    vector           BLOB NOT NULL,          -- float32 little-endian, row-major
    normalised       INTEGER NOT NULL DEFAULT 0
);

-- Lexical half. FTS5 external-content table; content is read from chunks.
CREATE VIRTUAL TABLE chunks_fts USING fts5(
    text,
    content='chunks',
    content_rowid='rowid',
    tokenize = "unicode61 remove_diacritics 2"
);

CREATE TABLE index_state (
    workspace_id        TEXT PRIMARY KEY,
    chunker_version     INTEGER NOT NULL,
    embedding_model     TEXT,
    embedding_revision  TEXT,
    updated_at          TEXT NOT NULL
);
```

`id` is deterministic:
`uuid5(NAMESPACE_URL, f"{content_unit_id}:{ordinal}:{text_sha256[:16]}:{chunker_version}")`.
Deterministic ids mean a rebuild returns the same rows, so a rebuild is idempotent
and a retry cannot duplicate.

**Provenance, per row:** `chunker_version` on every chunk; `model` + `revision` +
---

## 4. Embeddings and reranker — measurement first, choice after

I am **not** proposing a model as settled. The audit's own standard is that live
quality is unverified, and picking a model from a leaderboard would repeat the
mistake the archive already documents.

Candidates, all multilingual (Hindi + Hinglish + English), with realistic
footprint on an 8 GB laptop:

| Model | Disk (fp16) | Peak RAM to embed | Notes |
| --- | --- | --- | --- |
| `intfloat/multilingual-e5-small` | ~470 MB | ~0.6–1.0 GB | 384-dim, 100+ languages, MIT. Strong default for low-RAM machines |
| `intfloat/multilingual-e5-base` | ~1.1 GB | ~1.5–2.2 GB | 768-dim, better quality, still affordable |
| `BAAI/bge-m3` | ~2.2 GB | ~2.5–3.5 GB | 1024-dim, hybrid retrieval built in. Heavy alongside Electron + Whisper |
| `paraphrase-multilingual-MiniLM-L12-v2` | ~470 MB | ~0.5–0.8 GB | 384-dim, fast, weaker on code-switched Hinglish |
| FastEmbed ONNX build of `multilingual-e5-small` | ~470 MB | ~0.4–0.7 GB | Same weights, ONNX runtime, CPU-only, no torch dependency |

**Hinglish is the risk.** Hinglish is romanised Hindi mixed with English — not a
language any embedding model targets as a first class. A model that scores well
on translated Hindi may embed romanised Hindi poorly. This must be measured.

**Measurement plan, before any model is chosen.** A committed script, later
promoted into `evaluation/`:

1. **Corpus** — existing authored fixtures (phase-04 text, phase-05 slides,
   phase-06 audio text, phase-07 captions) plus ~30 hand-written query/answer
   pairs committed as `tests/fixtures/retrieval/`. Include at least 10
   romanised-Hinglish and 10 English queries about the same material.
2. **Metrics** — Recall@5 and MRR@10 against hand-labelled relevant chunks, with
   lexical-only FTS5 as baseline. A model that does not beat FTS5 on Hinglish is
   not adopted.
3. **Budget** — peak RSS and wall time to embed a 50 MB corpus on this machine,
   repeated while Electron runs. Gate: total app RSS stays under ~2.5 GB,
   because Electron already holds ~300–500 MB and the ASR helper peaks at
   1536 MiB.
4. **Decision rule** — smallest model that beats the FTS5 baseline on Hinglish
   Recall@5 and fits the budget. Prefer ONNX if it matches, to avoid torch.

**Reranker.** A cross-encoder (`bge-reranker-v2-m3` class, ~1.1 GB) is *probably*
out of budget for the demo and is listed as optional in §10. If added it must run
as a bounded top-k pass (k ≤ 20) inside the existing single heavy worker.

---

## 5. Index and dependencies — for approval

**Lexical:** SQLite FTS5, `unicode61` tokenizer. Already in the Python `sqlite3`
build. Zero new dependency. Handles Devanagari and romanised Hindi as character
sequences; `remove_diacritics 2` is safe for both. Weakness: no stemming, so
"extraction" and "extract" are distinct terms — acceptable for a first cut.

**Vector:** stock SQLite has no vector type. Options in preference order:

| Option | New dependency | Licence | Size | Maintenance | Notes |
| --- | --- | --- | --- | --- | --- |
| **A. Brute-force cosine over BLOB** | none | — | 0 | — | O(n). 20k chunks × 384 dims ≈ 30 MB scanned/query, ~10–30 ms in NumPy. **Fine for the demo**; removes every supply-chain question |
| **B. `sqlite-vec`** | 1 | Apache-2.0 | ~1 MB, compiles into SQLite | Active, **pre-v1**, ~1.0/yr | Best quality-of-life; pre-v1 is the risk |
| **C. `hnswlib`** | 1 | Apache-2.0 | ~5 MB | Mature, low recent activity | Fast ANN; hand-rolled index lifecycle |
| **D. LanceDB / Qdrant / Chroma** | 1 (large) | Apache-2.0 and others | 50–500 MB | Active | Overkill: duplicates storage we have, adds a service-shaped thing |
| **E. FAISS** | 1 | MIT | ~30 MB | Active | Linux-first build; awkward on Windows |

**Recommendation: start with A, move to B only if measured latency demands it.**
A needs no new dependency, which matters for a supply chain the audit already
flags as unverified. numpy is already in the lock.

Embedding inference needs a runtime, which is a real dependency decision:

| Requirement | Options | Licence | Size | Maintenance |
| --- | --- | --- | --- | --- |
| Model runtime | `onnxruntime` + FastEmbed, or `sentence-transformers` + torch | Apache-2.0 / MIT | ONNX ~120 MB, no torch; torch **~2.5 GB** | Both active |

**Recommendation: ONNX route.** `onnxruntime==1.30.0` is **already in
`services/requirements-lock.txt`**, so this adds a model download, not a new
wheel. torch at ~2.5 GB is disqualifying on an 8 GB laptop.

**Supply-chain notes, to the audit's standard:**

* No new PyPI distribution is proposed for the demo path (option A +
  onnxruntime already present). The model is a **downloaded artefact with a
  pinned revision hash**, stored under `models/` (already gitignored) and
  verified by hash before use — the pattern `huggingface-hub` already uses in
  `setup-audio.py`.
---

## 6. Retrieval API and citation contract

New read-only route, following the existing auth and scope rules:

```
GET /workspaces/{workspace_id}/subjects/{subject_id}/search?q=<text>&limit=<n>
```

Response shape (exact):

```jsonc
{
  "query": "why does the denominator change",
  "hits": [
    {
      "rank": 1,
      "score": 0.8213,
      "score_kind": "hybrid",          // "lexical" | "vector" | "hybrid"
      "source_version_id": "…",
      "content_unit_id": "…",
      "ordinal": 3,
      "modality": "pdf",
      "text_sha256": "…",
      "snippet": "…",                 // bounded, <= 400 chars
      "locator": { "kind": "page", "page": 4, "width": 612, "height": 792, "rotation": 0 },
      "citation": {
        "label": "Notes.pdf, page 4",
        "opens": { "view": "materials", "version_id": "…", "offset": 3 },
        "seek_seconds": null
      },
      "warnings": []
    }
  ],
  "eligibility": { "indexed_versions": 12, "skipped_unverified": 3 }
}
```

**How a citation opens** — the part that must not be faked:

| Locator | Renderer action |
| --- | --- |
| `page` | Materials tab, that source version, scroll to unit `ordinal`; the preview is already rendered by today's content endpoint |
| `slide` | Same, slide preview at `ordinal` |
| `time` | Video player seeks to `seek_seconds`; for YouTube, seek the embedded player to `locator.start_seconds` **or** the student-entered offset — never both |
| `lines` / `image` | Scroll to the unit and highlight `char_start`/`char_end` |

The renderer already has every one of these affordances today. M1 adds **no new
navigation primitive**, only the `opens` payload saying what to select. If a
locator kind cannot be opened, the UI must disable the link rather than open
something approximate.

`skipped_unverified` is deliberate: the student can see that material exists and
is not being cited. Hiding it would be the dishonest choice.

---

## 7. Answer pipeline

```
question
  → eligibility gate (indexed corpus only)
  → hybrid retrieval (FTS5 ∪ vector, RRF merge)
  → optional rerank (top-k, if budget allows)
  → compose with per-sentence citations
  → verify
  → GroundedAnswer
```

**Per-sentence citation.** The composer emits sentences with an attached citation
id. A sentence with no supporting chunk is **dropped**, not emitted uncited. The
first implementation should be extractive-leaning: prefer quoting and linking over
paraphrasing, because paraphrase is where fabrication enters.

**Verifier.** Two cheap checks:

1. **Groundedness** — does each emitted claim have a chunk that supports it?
   First implementation: embedding similarity above a threshold plus lexical
   overlap. Sentences failing this are removed.
2. **Citation integrity** — every retained citation's `locator` still resolves to
   a `content_units` row whose `text_sha256` matches. A citation that no longer
   resolves is an error, not a warning.

**Refusal threshold.** Refuse (return `refused: true`, no answer text) when:

* the merged hit set is empty, or
* the top hit's score is below a **measured** threshold, or
---

## 8. Providers

All model calls go through `providers.Provider` (already scaffolded). M1 routes
**new** M1 calls through it and, where cheap, records provenance for existing ones.

**M1 call sites:** embedding (local model — not a network call, but the *model*
identity and revision must be recorded exactly as a provider response would be)
and answer composition (if a local Ollama model is configured).

Rules:

* `ProviderResponse.prompt_revision` is **required**. A response without it is a
  bug. This is the seam that closes the D14 gap.
* `ProviderKind.LOCAL` covers Ollama at `127.0.0.1:11434`; `ProviderKind.GROQ`
  covers the cloud path. Embeddings are `LOCAL` only for M1.
* Credentials never enter `ProviderRequest`; they stay in backend env and are
  stripped from helper environments as today.
* Every stored answer, citation and model-derived value records provider, model,
  revision and prompt revision.

**Migrating existing providers is explicitly out of M1's cut line.** Routing
`cloud_vision` and `cloud_audio` through `providers/` is a refactor with real
regression risk against working, tested code, for no M1 benefit. It should be its
own reviewed change. What M1 must not do is *add* another inline client.

---

## 9. Tests, and what the evaluation package needs from M1

**M1 contract tests** (replacing the skips in `test_scaffold.py`, one milestone at
a time):

| Test | Asserts |
| --- | --- |
| `test_only_verified_terminal_text_units_enter_the_index` | the gate rejects `needs_ocr`, `suspect`, non-terminal and hash-mismatched units |
| `test_rebuilding_a_source_version_invalidates_its_chunks` | rebuild leaves no orphan chunk, embedding or FTS row |
| `test_answer_refuses_when_no_eligible_evidence_exists` | empty corpus → `refused: true`, empty text |
| `test_every_claim_carries_an_exact_locator` | no sentence without a resolvable citation |
| `test_answer_is_only_as_strong_as_its_weakest_citation` | `weakest_state()` picks the worst state |
| `test_model_text_never_replaces_content_unit_text` | `content_units.text` unchanged after answering |
| `test_every_response_records_its_prompt_revision` | no provider response without a revision |

Plus chunk-boundary tests per modality, deterministic-id idempotency, FTS and
vector agreeing on a trivial query, and `opens` payloads for every locator kind.

**What `evaluation/` needs from M1:**
---

## 10. Cut line

**Minimum for a working demo** (M1-min):

* Eligibility gate + its tests.
* Chunking for `page`, `slide`, `time`, `lines`.
* Migration `0006_retrieval`: `chunks`, `embeddings`, `chunks_fts`, `index_state`.
* Local ONNX embeddings, single model, revision pinned, hash-verified.
* Hybrid retrieval (FTS5 + brute-force cosine, **no new PyPI dependency**).
* `GET .../search` and the exact citation contract in §6, reusing existing
  renderer navigation.
* Extractive composition with per-sentence citations, the verifier as a lexical
  overlap check, and a **measured** refusal threshold.
* Five evidence states rendered.
* Invalidation on reprocess.
* 20-case gold set, offline, covering the refusal cases.

Explicitly **not** in the demo: reranker, `sqlite-vec`, fusion beyond RRF, query
rewriting, multi-turn, streaming answers, and migrating existing providers.

**Optional** (M1-plus, each independently approvable): cross-encoder rerank;
`sqlite-vec` if measured latency justifies it; a second embedding model behind
`index_state` so a model swap is a rebuild not a migration; student-corrected
transcripts becoming eligible units; per-subject indexes for large workspaces.

---

## 11. Open questions for you

1. **Embeddings may send student material off-device.** §4 proposes local-only.
   Confirm that is the requirement, or tell me a hosted embedding provider is
   acceptable — that is a new data flow, a new DECISIONS entry, and arguably a
   consent question. **This is the biggest decision in M1.**
2. **Which refusal behaviour do you prefer when the corpus is thin?** I propose
   refusing often (correct but frustrating). The alternative is a visible
   "weak evidence" answer.
3. **`sqlite-vec` — approve the pre-v1 compiled dependency now, or start with
   brute force and revisit?** I recommend brute force and no new dependency, and
   would rather not add a compiled C extension without you deciding it.
4. **Should `suspect` transcripts ever be citable?** I propose no, with a path
   for student-corrected text to become eligible. If you want them citable with a
   visible "unverified" badge, that is simpler and changes the eligibility gate.
5. **Is a YouTube caption a citable *source*?** It is an imported course source
   today, so yes — but its provenance is local documentation, not externally
   verifiable (DECISIONS D10). Should caption citations be capped at
   `UNVERIFIED` permanently?
6. **Gate the answer feature behind a flag for the demo?** Ask is currently
   disabled in the UI. M1 could ship dark, or visible with refusal on display.
7. **Gold-set size.** I proposed 30–50 cases. Confirm the budget, or say if you
   want it larger before the model choice is locked.
8. **Migration number.** `0006_retrieval` — confirm M1 owns `0006`, in case
   something else is planned for that slot.

---

## Appendix — what this document does not do

It changes no code, adds no dependency, and creates no migration. Every entry
point in `knowledge/`, `grounding/`, `providers/` and `evaluation/` still raises
`NotImplementedError`. No model was downloaded, benchmarked or evaluated. Model
footprints in §4 are **estimates from published model cards, not measurements on
this machine** — the measurement plan is what turns them into facts.

1. A **public, callable entry point** — `knowledge.KnowledgeIndex` and
   `grounding.GroundingService` implemented as protocols, not scripts poking at
   `Worker`. Several existing evaluators violate this; M1 must not.
2. A **versioned, scored, offline benchmark suite**: committed cases under
   `tests/fixtures/retrieval/`, deterministic, no network, a pinned
   `BenchmarkSuite.revision`, numeric results per case.
3. **The first slice of the gold set**, minimum viable at 30–50 cases:

| Category | Count | Labels needed |
| --- | --- | --- |
| Direct fact in one chunk | 10 | `supports` / `does_not_support` per chunk |
| Fact spanning two chunks | 5 | both chunks cited |
| Answerable only from `page`/`slide`/`time` | 5 | exact locator expected |
| **Unanswerable / off-material** | 10 | must refuse |
| Answerable but source is `suspect` | 5 | must refuse or label `UNVERIFIED`, never `VERIFIED` |
| Hinglish question, English source | 5 | retrieval must find it |
| Adversarial: plausible but absent | 5 | must refuse |

The refusal and `suspect` cases are the ones that matter. A retrieval benchmark
that only measures recall will happily reward a model that fabricates well.
* after verification, no sentence retains a `VERIFIED` or `UNVERIFIED` citation.

The threshold must come from the §4 measurement run, not a round number. Until
measured, the honest behaviour is to **refuse more often** — a refusal is
recoverable, a confident wrong answer teaches the student something false.

**The five evidence states** (`grounding.EvidenceState`):

| State | Meaning | UI |
| --- | --- | --- |
| `VERIFIED` | Original integrity checked; locator and text hash match | neutral marker |
| `UNVERIFIED` | Real extracted text, never checked against the original | "Check against source" |
| `MODEL_DERIVED` | Model output, not present in the source | must be visibly distinct |
| `INSUFFICIENT` | Retrieved but does not support the claim | audit panel only |
| `REFUSED` | No eligible evidence | shown instead of an answer |

`weakest_state()` drives the banner. An answer containing one `INSUFFICIENT`
citation is not presented as trustworthy.

**Off-material queries.** This is the case most likely to produce a plausible
lie, so it gets an explicit rule: if the best hit is below the refusal
threshold, **refuse**. Do not answer from model knowledge. M1 adds no web-search
fallback — search is absent today and would be a new data flow with its own
DECISIONS entry and consent question.
* Model licences must be recorded per model in `index_state` and
  `docs/DECISIONS.md`. Most candidates are MIT or Apache-2.0; some multilingual
  checkpoints carry additional terms. **I have not verified any individual
  model's licence text** — that is a task, not an assumption.
* `sqlite-vec`, if adopted, would be the first new compiled dependency in the
  project and needs a licence and maintenance review before use.
**Local vs hosted embeddings.** Embeddings derive from the student's own
material. Sending chunk text to a hosted embedding API is a **new data flow**
needing its own DECISIONS entry and consent question. **M1 proposes local-only.**
That is a decision, not a default — it is open question 1.
`dimensions` on every embedding. This is the gap DECISIONS D14 calls out — Ollama
currently records model but no prompt/model revision. This table makes that
structurally impossible to omit.

**Invalidation.** `invalidate(source_version_id)`:

1. `DELETE FROM embeddings WHERE chunk_id IN (SELECT id FROM chunks WHERE source_version_id = ?)`
2. `DELETE FROM chunks WHERE source_version_id = ?`
3. FTS5 external-content rows follow the delete; the app issues `'delete'`
   commands against `chunks_fts` for the affected rowids.
4. `index_state` records the last successful full build, not a counter.

Trigger: any `extract_source` rebuild, any `verify_original` failure, any source
version delete. The worker already clears `content_units` and the cloud job on
rebuild, so this hook sits in the same place.

**Known SQLite limits, stated now:** FTS5 external-content tables do **not**
support `UPSERT`, so re-chunk means delete-then-insert. Stock SQLite has no
vector type and no ANN index; vector search is a scan over a BLOB column (§5).
  changes. An index row with an older version is not reused; it is rebuilt.
* Minimum chunk: skip units shorter than ~40 characters unless it is the only
  unit in its source version. Indexing a single word produces noise.