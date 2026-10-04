# M1 — Retrieval and grounded answering (design only)

**Status: proposal. No code, no dependency, no migration.** This document exists
to be approved or corrected before any of it is built.

Branch context: `cleanup/architecture-reset`. The contracts this design fills in
are the unimplemented scaffolds in `studylens_service/knowledge/`, `grounding/`,
`providers/` and the top-level `evaluation/` package. Every entry point there
currently raises `NotImplementedError`.

Current behaviour, stated plainly: **there is no retrieval and there are no
grounded answers.** `GET .../content` is an inspection API that returns units
including `needs_ocr`, `suspect`, `unreadable`, `too_large` and `empty`. It is
not a retrieval corpus and M1 must never treat it as one.

---

## 1. Eligibility gate

One function decides what may be indexed and what may be cited:
`knowledge.eligible_source_versions()`. **It is the only place this rule lives.**
Retrieval, grounding, the citation builder and the benchmark all call it.
Nothing re-derives it.

A source version is eligible when **all** hold:

| Condition | Source of truth | Why |
| --- | --- | --- |
| Original integrity verified — a `verify_original` job for this version reached `succeeded` | `jobs`, `source_versions` | An unreadable original cannot support a citation |
| Extraction terminal and not failed — latest `extract_source` job is `succeeded` or `partial` | `jobs` | Mid-extraction content is incomplete by construction |
| At least one **citable** unit (see §1.1) | `content_units` | Otherwise there is nothing to cite |
| Text integrity — unit `text_sha256` matches the stored `text` | `content_units` | A modified unit is not evidence of what was extracted |

A `partial` extraction is eligible; the per-unit rule below filters its bad
units, so the version-level rule does not need to.

### 1.1 Per-unit eligibility: `text` **and** `suspect` are both citable

Both are indexed and both may be cited. Only these are excluded:

| Unit status | Citable? | Reason | Badge on the citation |
| --- | --- | --- | --- |
| `text` | **yes** | Extracted text, integrity checked | none, or "verified" |
| `suspect` | **yes** | Real extracted text that a machine produced and nobody has checked | **per-modality badge, §1.2** |
| `needs_ocr` | no | No text was recognised at all | "Needs OCR" |
| `empty` | no | Nothing to say | — |
| `unreadable` | no | Extraction could not read it | "Not extracted" |
| `too_large` | no | Deliberately skipped | "Not extracted" |

Excluding `suspect` outright was my earlier recommendation and it was wrong. It
would make **video, YouTube captions and scanned material largely unanswerable** —
most of what a student would ask about. The honest arrangement is not to hide
automatic text but to **index it and label every citation derived from it**, so
the student can see exactly what they are trusting.

`suspect` never reaches `VERIFIED`. It enters as `UNVERIFIED` at best, and the
renderer must render the badge. A citation with no badge is a bug.

### 1.2 Confidence differs by modality, and by language for speech

A `suspect` unit is not one thing. The badge must say which kind of machine text
the student is being shown:

| Origin | Badge | Why confidence differs |
| --- | --- | --- |
| ASR transcript of audio or video speech | **"auto-transcript, verify against clip"** | ASR substitutes, drops and splits words; timestamps are approximate |
| ASR of **Hindi or Hinglish** speech | **"auto-transcript (Hindi/Hinglish), verify against clip"** plus an accuracy warning | See below |
| OCR text from a scanned page | **"scanned text, verify against page"** | OCR degrades on low contrast, skew and mixed scripts; glyph confusion is common in Devanagari |
| OCR text from a born-digital page | **"scanned text, verify against page"** | Same origin; the reader should still know it is machine-read |
| Cloud model transcription of a visual | **"model output, not in the source"** | Already `MODEL_DERIVED` in §7; never shown as source text |

**Hindi and Hinglish specifically.** The hinglish pilot
(`docs/archive/ingestion-pilots/hinglish-asr.md`) records materially worse
accuracy for code-switched Hindi/English than for clean English. So for a
`suspect` unit detected as `hi` or as Hinglish:

1. The badge is **longer and explicit**, not a footnote.
2. The citation carries an extra `confidence_hint` the renderer must display:
   `"asr_accuracy_low_for_language"`.
3. Low-confidence ASR must **not** be the sole support for a numerical or
   definitional claim. If the only available evidence is low-confidence ASR, the
   pipeline **refuses**. Refusing is cheap; a wrong formula the student then
   trusts is not.
4. A future milestone may let the student confirm or correct a transcript; a
   confirmed unit becomes a new version with status `text`. M1 does not build
   this path, but the schema leaves room for it.

**One threshold by default (decision 11.9).** The refusal threshold in point 3
is a single value, not a per-language value. If the §4 measurement shows
Hinglish retrieval scoring materially worse than English, a stricter override
for Hinglish-sourced answers may be introduced — but only on the strength of
that measurement, and the numbers must be written down in `DECISIONS.md` at the
time. Absent such evidence, one threshold stands.

How the language is determined for an existing unit: prefer the
`metadata.speech.language` already recorded by `audio.py`; fall back to
`metadata.speech.language_probability`; if neither exists, treat the language as
unknown and apply the long badge. **Never** guess "English" because the app
happens to default to English.

### 1.3 Warnings travel with the citation

Warnings and coverage gaps are carried on every hit and never dropped. A hit from
a source version with warnings always renders that warning alongside the
citation, and `weakest_state()` must not report `VERIFIED` while a warning
applies — even for a `text` unit, because a warning is itself evidence that
something about that unit is not trustworthy.

**No age indicator (decision 11.8).** A `suspect` unit does not display how long
it has been unreviewed. The badge is fixed. What M1 does expose is a
**model/settings fingerprint in a details view** — the embedding model id and
revision, chunker version, index build time and prompt version that produced a
given answer — so a student can inspect provenance on demand without every
citation carrying a date.

**YouTube captions (decision 11.4).** A caption-derived citation is capped at
`UNVERIFIED` for the whole of this hackathon. The citation additionally
distinguishes **manual** from **auto-generated** caption tracks, because the two
carry very different error profiles. Promotion above `UNVERIFIED` happens only
through an explicit student review action — never automatically, and never as a
side effect of a caption refresh.

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
  changes. An index row with an older version is not reused; it is rebuilt.
* Minimum chunk: skip units shorter than ~40 characters unless it is the only
  unit in its source version. Indexing a single word produces noise.

---

## 3. Storage — proposed migration `0006_retrieval`

Alembic head is `0005_youtube_media_links`. M1 adds **`0006_retrieval`**, forward
only, under `BEGIN IMMEDIATE` like every existing migration. No table is altered;
nothing existing is rewritten. Rollback is unsupported, consistent with D6.

**M1 owns `0006_retrieval` (decision 11.7).** No other work is planned for that
slot, so this migration will not have to be renumbered.

Two operational conditions attach to it:

* **Back up the real data directory before the first run.** The migration is
  forward-only and rollback is unsupported, so the only way back from a bad
  first run is a restored copy.
* **Exercise the migration on a copy first.** Run it against a copy of the real
  data directory and check the result before it touches the real one.

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
Deterministic ids mean a rebuild returns the same rows, so a rebuild is
idempotent and a retry cannot duplicate.

**Provenance, per row:** `chunker_version` on every chunk; `model` + `revision` +
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

**Local vs hosted embeddings — decided. M1 is local-only.** Chunk text is the
student's own material; sending it to a hosted embedding API is a new data flow,
and this milestone does not open one. `docs/PRIVACY_AND_DATA_FLOW.md` is
therefore unchanged by M1 and no embedding request is added to its data-flow
table. Revisiting that needs its own DECISIONS entry and a consent answer first.

### 4.1 Who owns tokenizer and ONNX loading

Someone has to own model loading, and "whoever needs retrieval first" is how
duplicated tokenizers and double-loaded 1 GB models appear. The seam:

| Concern | Owner | Where | Tests that must exist |
| --- | --- | --- | --- |
| Model download, hash verification, revision pinning | `scripts/setup-embeddings.py`, mirroring the existing `scripts/setup-audio.py` | `models/` (gitignored) | a download with a wrong hash is refused |
| Tokenizer and ONNX session construction, **one process-wide cache keyed by model + revision** | `studylens_service/knowledge/embedder.py` | new module | a second call does **not** re-load; a different revision **does** re-load |
| Chunking | `studylens_service/knowledge/chunker.py` | new module | per-modality boundary tests (§2) |
| Index write and invalidation | `studylens_service/knowledge/index.py` | new module | invalidation leaves no orphan chunk, vector or FTS row |
| Cosine similarity over the BLOB column | `studylens_service/knowledge/vectors.py` | new module | matches a reference implementation on random vectors |
| HTTP surface | existing `api.py` pattern | `api.py` | the same scope/auth tests every other route has |

**Rules.** The ONNX session is built **once per (model, revision)** and reused;
building it per query would add seconds to every search. Inference runs inside
the existing single heavy worker, never in the API request path. A failed load
degrades to **FTS5-only**, with the UI saying lexical search is in use — the app
must still work with no embedding model present.

### 4.2 fastembed versus hand-rolled ONNX

| | Hand-rolled (`onnxruntime` + `tokenizers`, both already locked) | `fastembed` |
| --- | --- | --- |
| New distributions | **0** | 1 (`fastembed`) plus its own transitive pins |
| Wheel size | 0 | ~15–30 MB plus pins |
| Licence | Apache-2.0 / MIT, already vendored by policy | Apache-2.0 |
| Who maintains the loading code | us | upstream |
| Model download | we write it, pinned and hash-verified | upstream registry, still pinned and hash-verified by us |
| Risk | ~60 lines of loading code we must test and maintain | version conflicts against our pinned `onnxruntime==1.30.0`; a transitive bump is a supply-chain event in a project the audit already flags as unverified |

**Recommendation: hand-rolled ONNX.** The loading code is small, we already own
`huggingface-hub` for the audio model, and it adds **zero new dependencies**.
Revisit `fastembed` only if we end up wanting several embedding models, which is
M1-plus at best.

---

## 5. Index and dependencies — for approval

**Lexical:** SQLite FTS5, `unicode61` tokenizer. Already in the Python `sqlite3`
build. Zero new dependency. Handles Devanagari and romanised Hindi as character
sequences; `remove_diacritics 2` is safe for both. Weakness: no stemming, so
"extraction" and "extract" are distinct terms — acceptable for a first cut.

**Vector:** stock SQLite has no vector type. Options in preference order:

| Option | New dependency | Licence | Size | Maintenance | Notes |
| --- | --- | --- | --- | --- | --- |
| **A. Brute-force cosine over BLOB** | none | — | 0 | — | O(n). **Fine for the demo**; removes every supply-chain question |
| **B. `sqlite-vec`** | 1 | Apache-2.0 | ~1 MB, compiles into SQLite | Active, **pre-v1**, ~1.0/yr | Best quality-of-life; pre-v1 is the risk |
| **C. `hnswlib`** | 1 | Apache-2.0 | ~5 MB | Mature, low recent activity | Fast ANN; hand-rolled index lifecycle |
| **D. LanceDB / Qdrant / Chroma** | 1 (large) | Apache-2.0 and others | 50–500 MB | Active | Overkill: duplicates storage we have, adds a service-shaped thing |
| **E. FAISS** | 1 | MIT | ~30 MB | Active | Linux-first build; awkward on Windows |

**Recommendation: start with A, move to B only if measured latency demands it.**
A needs no new dependency, which matters for a supply chain the audit already
flags as unverified. numpy is already in the lock.

**The chunk-count ceiling for brute force.** Cost is `O(chunks × dims)` float32
reads plus a dot product per chunk, in NumPy on one contiguous buffer. Using the
§4 figures (384-dim, float32 = 1,536 bytes/vector) and the measured ~10–30 ms at
20k chunks on this machine:

| Chunks | Scan per query | Verdict |
| --- | --- | --- |
| 5,000 | ~7.7 MB | **Comfortable.** No thought needed |
| 20,000 | ~31 MB | **Comfortable.** Typical single-student corpus |
| 50,000 | ~77 MB | **Acceptable**, ~40–75 ms/query |
| 100,000 | ~154 MB | **Borderline.** ~80–150 ms/query; the read dominates. Switch to ANN |
| 250,000+ | ~384 MB | **Unacceptable.** Brute force is finished |

With 768-dim (`e5-base`) every figure doubles: **comfortable ceiling ~25,000
chunks**, borderline at ~50,000.

Context: a 500-page PDF at ~1000 chars per chunk is ~500 chunks. Reaching 100,000
chunks means ~100,000 pages, or a large audio/video library at one chunk per
30-second cue. **For one student on an 8 GB laptop, brute force will not be the
bottleneck.** Adopting ANN should be measurement-driven, not triggered by a
chunk-count rule that will not fire in practice.

**Migration path if the ceiling is hit.** `vectors.py` (§4.1) is the only module
that knows how similarity is computed. Swapping to `sqlite-vec` or an ANN index
is a change inside that module plus a rebuild of `embeddings`; `chunks`,
`chunks_fts` and every caller stay untouched.

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
* Model licences must be recorded per model in `index_state` and
  `docs/DECISIONS.md`. Most candidates are MIT or Apache-2.0; some multilingual
  checkpoints carry additional terms. **I have not verified any individual
  model's licence text** — that is a task, not an assumption.
* `sqlite-vec` is **not adopted** (decision 11.3). It would be the first new
  compiled dependency in the project. Brute force is used until the chunk
  ceiling above is actually reached.

**Brute force, not `sqlite-vec` (decision 11.3).** Vector search is a scan over
a BLOB column for the whole of M1. No compiled extension is added. The ceiling
above is the tripwire: if it is reached, §"Migration path if the ceiling is hit"
below is followed, not pre-emptively.

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
      "unit_status": "text",           // or "suspect"; drives the badge
      "text_sha256": "…",
      "snippet": "…",                 // bounded, <= 400 chars
      "locator": { "kind": "page", "page": 4, "width": 612, "height": 792, "rotation": 0 },
      "citation": {
        "label": "Notes.pdf, page 4",
        "badge": null,                 // e.g. "scanned text, verify against page"
        "confidence_hint": null,       // e.g. "asr_accuracy_low_for_language"
        "opens": { "view": "materials", "version_id": "…", "offset": 3 },
        "seek_seconds": null
      },
      "warnings": []
    }
  ],
  "eligibility": { "indexed_versions": 12, "skipped_unverified": 3 }
}
```

`badge` and `confidence_hint` follow §1.2 and are **required** whenever
`unit_status == "suspect"`; the renderer must refuse to render a citation whose
badge is missing for a `suspect` unit.

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

**Ships visible, with badges from day one (decision 11.5).** There is no feature
flag and no dark launch. The answer surface and its evidence badges appear
together in the first M1 demo. Shipping uncited machine text first and
retro-fitting the badges afterwards is precisely the failure this design is
built to avoid.

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
   a `content_units` row whose `text_sha256` matches, and every citation from a
   `suspect` unit carries its badge. A citation that no longer resolves, or a
   badge that is missing, is an error rather than a warning.

**Three-tier refusal (decision 11.2).** Refusal is not a binary. The pipeline
has three behaviours, chosen by the evidence actually retrieved:

| Evidence found | Behaviour |
| --- | --- |
| Strong | Answer normally, with citations. |
| Weak | Short answer labelled **"Partially supported"**, with citations, plus an offer to search the web — taken only with explicit student permission. |
| None | **"Evidence not found"**. No model-knowledge answer unless the student explicitly chooses **"Outside knowledge"**. |

Return `refused: true` with no answer text when:

* the merged hit set is empty, or
* the top hit's score is below a **measured** threshold, or
* after verification, no sentence retains a `VERIFIED` or `UNVERIFIED` citation, or
* the only supporting evidence is low-confidence Hindi/Hinglish ASR (§1.2, rule 3).

Both thresholds are set from the **gold dev split**, not guessed. Until measured,
the honest behaviour is to **refuse more often** — a refusal is recoverable, a
confident wrong answer teaches the student something false.

**The five evidence states** (`grounding.EvidenceState`):

| State | Meaning | UI |
| --- | --- | --- |
| `VERIFIED` | Original integrity checked; locator and text hash match | neutral marker |
| `UNVERIFIED` | Real extracted text, never checked against the original | "Check against source" |
| `MODEL_DERIVED` | Model output, not present in the source | must be visibly distinct |
| `INSUFFICIENT` | Retrieved but does not support the claim | audit panel only |
| `REFUSED` | No eligible evidence | shown instead of an answer |

`weakest_state()` drives the banner. An answer containing one `INSUFFICIENT`
citation is not presented as trustworthy. A citation from a `suspect` unit is
`UNVERIFIED` at best and additionally carries its §1.2 badge.

**Off-material queries.** This is the case most likely to produce a plausible
lie, so it gets an explicit rule: if the best hit is below the refusal
threshold, **refuse**. Do not answer from model knowledge — not silently, and
not as a default. If the student explicitly chooses **"Outside knowledge"**, the
pipeline may answer from model knowledge, and the answer is labelled as such and
carries no citation. Silent fallback to model knowledge is the thing this design
exists to prevent.

**Web search.** M1 does **not** implement web search, and no query text leaves
the device in M1. What M1 does build is the **permission flow stub** (S5): the
weak-evidence tier offers "search the web", and the offer is rendered and
permission is collected, but no search backend is wired up. That keeps the
student-facing contract honest now, and defers the data-flow and consent
decision (a new `DECISIONS.md` entry) to the milestone that would actually
perform the request.

---

## 8. Providers

All model calls go through `providers.Provider` (already scaffolded). M1 routes
**new** M1 calls through it and, where cheap, records provenance for existing ones.

**M1 call sites:** embedding (a local model — not a network call, but the *model*
identity and revision must be recorded exactly as a provider response would be)
and answer composition (if a local Ollama model is configured).

Rules:

* `ProviderResponse.prompt_revision` is **required**. A response without it is a
  bug. This is the seam that closes the D14 gap.
* `ProviderKind.LOCAL` covers Ollama at `127.0.0.1:11434`; `ProviderKind.GROQ`
  covers the cloud path. Embeddings are `LOCAL` only for M1 (§4).
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
| `test_only_verified_terminal_text_units_enter_the_index` | the gate rejects `needs_ocr`, `empty`, `unreadable`, `too_large`, non-terminal and hash-mismatched units, and **accepts `text` and `suspect`** |
| `test_suspect_citations_carry_a_badge_and_never_reach_verified` | every `suspect` citation has the §1.2 badge for its modality and language, and its state is at best `UNVERIFIED` |
| `test_rebuilding_a_source_version_invalidates_its_chunks` | rebuild leaves no orphan chunk, embedding or FTS row |
| `test_answer_refuses_when_no_eligible_evidence_exists` | empty corpus → `refused: true`, empty text |
| `test_answer_refuses_when_only_low_confidence_asr_supports_a_claim` | Hindi/Hinglish ASR alone cannot support a numerical or definitional claim |
| `test_every_claim_carries_an_exact_locator` | no sentence without a resolvable citation |
| `test_answer_is_only_as_strong_as_its_weakest_citation` | `weakest_state()` picks the worst state |
| `test_model_text_never_replaces_content_unit_text` | `content_units.text` unchanged after answering |
| `test_every_response_records_its_prompt_revision` | no provider response without a revision |

Plus chunk-boundary tests per modality, deterministic-id idempotency, FTS and
vector agreeing on a trivial query, `opens` payloads for every locator kind, and
embedder-cache tests per §4.1 (second call does not re-load; different revision
does).

**What `evaluation/` needs from M1:**

1. A **public, callable entry point** — `knowledge.KnowledgeIndex` and
   `grounding.GroundingService` implemented as protocols, not scripts poking at
   `Worker`. Several existing evaluators violate this; M1 must not.
2. A **versioned, scored, offline benchmark suite**: committed cases under
   `tests/fixtures/retrieval/`, deterministic, no network, a pinned
   `BenchmarkSuite.revision`, numeric results per case.
3. **The first slice of the gold set: 45 cases across nine categories**
   (decision 11.6).

   | Category | Count | Labels needed |
   | --- | --- | --- |
   | Direct fact in one chunk | 6 | `supports` / `does_not_support` per chunk |
   | Fact spanning two chunks | 5 | both chunks cited |
   | Answerable only from `page`/`slide`/`time`, including video timestamp | 6 | exact locator expected |
   | **Unanswerable / off-material** | 8 | must refuse |
   | Adversarial: plausible but absent | 7 | must refuse |
   | Answerable, but the only source is `suspect` ASR | 4 | must answer **with the §1.2 badge**, never `VERIFIED` |
   | Answerable, but the only source is OCR of a scan | 4 | must answer **with the scanned-text badge** |
   | Answerable numerically, but only from Hindi/Hinglish ASR | 3 | must **refuse** (§1.2 rule 3) |
   | Hinglish question, English source | 2 | retrieval must find it |
   | **Total** | **45** | |

   Composition floors, both satisfied by the table above: **at least 15
   off-material** cases (8 + 7 = 15) and **at least 10 Hindi/Hinglish or
   video-timestamp** cases (6 + 3 + 2 = 11).

   **Construction rules.** Real course material only — no invented documents.
   Every locator is hand-verified against the actual page, slide or timestamp; a
   locator nobody checked is worse than no locator, because it looks checked.
   The set is split into a **dev** split used for tuning thresholds and choosing
   the embedding model, and a **held-out** split that is never read during
   tuning and is reported once. Borderline questions are kept in the set, not
   dropped for being awkward.

   **Growth.** The slice grows toward ~100 by M4, keeping the same floors.
The refusal and badge cases are the ones that matter. A retrieval benchmark that
only measures recall will happily reward a model that fabricates well, and a
badge-blind one will happily reward hiding machine text.

---

## 10. Cut line

**Minimum for a working demo** (M1-min):

* Eligibility gate (§1) with `text` **and** `suspect` citable, badges, and the
  Hindi/Hinglish refusal rule.
* Chunking for `page`, `slide`, `time`, `lines`.
* Migration `0006_retrieval`: `chunks`, `embeddings`, `chunks_fts`, `index_state`.
* Local ONNX embeddings, single model, revision pinned, hash-verified, cached
  once per (model, revision) per §4.1.
* Hybrid retrieval (FTS5 + brute-force cosine, **no new PyPI dependency**).
* `GET .../search` and the exact citation contract in §6, reusing existing
  renderer navigation.
* Extractive composition with per-sentence citations, the verifier as a lexical
  overlap check, and a **measured** refusal threshold.
* Five evidence states rendered, with the §1.2 badges on every `suspect` citation.
* Invalidation on reprocess.
* A first gold set covering the refusal and badge cases.

Explicitly **not** in the demo: reranker, `sqlite-vec`, fusion beyond RRF, query
rewriting, multi-turn, streaming answers, and migrating existing providers.

**Optional** (M1-plus, each independently approvable): cross-encoder rerank;
`sqlite-vec` if measured latency justifies it; a second embedding model behind
`index_state` so a model swap is a rebuild not a migration; student-corrected
transcripts becoming `text` units; per-subject indexes for large workspaces.

---

## 11. Decisions taken

All nine questions are **answered**. This section is the record; the answers are
also reflected in the sections that depend on them, which are marked
"(decision 11.N)".

1. **Embeddings may send student material off-device.** — **ANSWERED: local
   only.** M1 embeds locally with a pinned, hash-verified ONNX model. No hosted
   embedding provider, no new data flow, and `PRIVACY_AND_DATA_FLOW.md` is
   unchanged. (§4)

2. **Refusal behaviour when the corpus is thin.** — **ANSWERED: three tiers.**

   | Evidence found | Behaviour |
   | --- | --- |
   | Strong | Answer normally, with citations. |
   | Weak | Short answer labelled **"Partially supported"**, with citations, plus an offer to search the web — taken only with explicit student permission. |
   | None | **"Evidence not found"**. No model-knowledge answer unless the student explicitly chooses **"Outside knowledge"**. |

   Both thresholds are set from the gold dev split, not guessed. Borderline
   questions are included in the gold set rather than excluded as inconvenient.

3. **`sqlite-vec`.** — **ANSWERED: no.** Brute force only, until the §5 chunk
   ceiling is actually reached. No new compiled dependency in M1.

4. **Are YouTube captions citable sources?** — **ANSWERED: yes, and permanently
   capped at `UNVERIFIED` for this hackathon.** The citation must additionally
   distinguish **manual** from **auto-generated** caption tracks. Promotion above
   `UNVERIFIED` happens only through an explicit student review action — never
   automatically, and never as a side effect of a refresh.

5. **Gate the answer feature behind a flag?** — **ANSWERED: no.** The answer
   feature ships **visible, with badges from day one**. Shipping uncited machine
   text first and retro-fitting the badges is the mistake this design exists to
   avoid.

6. **Gold-set size.** — **ANSWERED: first slice of 45 across nine categories**,
   growing toward ~100 by M4, with **at least 15 off-material** cases and **at
   least 10 Hindi/Hinglish or video-timestamp** cases. Real course material
   only, hand-verified locators. Split into a **dev** set (for tuning) and a
   **held-out** set (report only).

7. **Migration number.** — **ANSWERED: M1 owns `0006_retrieval`.** No other work
   is planned for that slot.

   Two operational conditions attach: **back up the real data directory before
   the first run**, and **exercise the migration on a copy first** (§3).

8. **Badge age display.** — **ANSWERED: no age indicator.** A fixed badge is
   sufficient. Instead, M1 exposes a **model/settings fingerprint in a details
   view**, so what produced an answer is inspectable without decorating every
   citation.

9. **Should the refusal threshold differ by language?** — **ANSWERED: one
   threshold by default.** A per-language override is permitted **only if the §4
   measurement shows a real gap**, and the numbers behind any override must be
   written down when it is introduced.

---

## 12. Implementation plan

Sequenced so that each slice is independently reviewable and each can be
stopped without leaving the repository in a state that cannot be explained.
Gates run before and after every slice.

**S1 — Retrieval skeleton, no embeddings.** Migration `0006_retrieval`, the §1
eligibility gate, and the §2 chunker, with tests, plus a CLI/dev endpoint that
lists eligible chunks for a source. Deliberately **no embeddings yet**, so the
chunking contract is proven before anything depends on it.

**S2 — Measurement, then the index.** Run the §4 measurement plan on 20–30 real
course pages/segments and report disk, RAM, speed, and Hindi/Hinglish
retrieval. Then choose and implement local embeddings, FTS5, the brute-force
index and the retrieval API. First retrieval-only evaluation: **recall@k and MRR
on the dev split**.

**S3 — Providers and answers.** `providers/` (Groq, Ollama, prompt versions
recorded) and answer composition: per-sentence citations, five evidence states,
three-tier refusal.

**S4 — Verifier. Only if time allows.** Propose approach and cost **first**,
before writing any of it.

**S5 — Renderer.** Tutor screen, citation chips, source viewer that opens the
exact page/slide/timestamp, evidence-state banners, web-search permission flow
stub.

Nothing in this plan starts until the design is approved.

---

## Appendix — what this document does not do

It changes no code, adds no dependency, and creates no migration. Every entry
point in `knowledge/`, `grounding/`, `providers/` and `evaluation/` still raises
`NotImplementedError`. No model was downloaded, benchmarked or evaluated. Model
footprints in §4 are **estimates from published model cards, not measurements on
this machine** — the measurement plan is what turns them into facts, and the
Hinglish accuracy claim in §1.2 is likewise drawn from the archived pilot rather
than from a fresh measurement.