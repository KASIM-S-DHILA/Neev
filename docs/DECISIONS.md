# Decisions

Architectural decisions that are load-bearing, with the reasoning and the current
status. Read with [`ARCHITECTURE.md`](ARCHITECTURE.md) (what is built) and
[`PRIVACY_AND_DATA_FLOW.md`](PRIVACY_AND_DATA_FLOW.md) (what leaves the machine).

Status values: **Accepted** (in force) · **Provisional** (in force, may change) ·
**Superseded** (kept for history).

---

## D1. Loopback FastAPI service behind an Electron bridge

**Status:** Accepted

The renderer is React and holds no Node access. Rather than giving it filesystem
or database access, a local FastAPI service owns persistence and extraction and
is reached over `127.0.0.1` with a fresh ephemeral bearer token minted at each
launch.

This keeps one implementation of storage/extraction, lets the dev browser reuse
the same code through the Vite `/api` proxy, and means the renderer can only
reach the service through a narrow named-operation IPC bridge.

**Cost:** two serialisation boundaries and a launch handshake. The renderer must
wait for the service; the app opens a window immediately and fills it in.

## D2. One heavy background job at a time

**Status:** Accepted

The worker holds an OS-level lock and the supervisor enforces
`max_active_heavy_jobs: 1`. Extraction is CPU/memory-heavy (native helpers at
512 MiB, Windows ASR helper at 1536 MiB), so concurrency would make memory
unpredictable on an 8 GB target machine.

**Cost:** throughput. Audio and video work queue behind each other.

**Not a claim:** these caps are not a whole-app 8 GB budget, and external
Ollama plus non-Windows helper memory sit outside them.

## D3. Separate offline speech helper process

**Status:** Accepted

Faster-whisper Tiny runs in its own process rather than in the worker. The
parent never holds a decoded full-length buffer or a loaded speech model, so
cancelling or crashing one interval cannot corrupt the service.

**Cost:** an extra process per speech job and IPC round-trips per 30-second
interval.

## D4. Content-addressed, immutable originals

**Status:** Accepted

An import is hashed (SHA-256), fsynced into `staging/`, then linked to
`originals/<prefix>/<sha256>`. Re-importing the same bytes does not duplicate
them, and a source version's identity is content, not a filename.

Filenames are metadata only. **Never** use them as filesystem paths.

**Cost:** an unreferenced blob can survive a crash between the blob write and the
metadata commit. It is never reported as success and can be garbage-collected
later.

## D5. Optimistic concurrency on session saves

**Status:** Accepted

`PUT /workspaces/{id}/session` takes a `base_revision`; a mismatch returns
HTTP 409. Tab context and drafts are saved with the normalised curriculum in one
transaction. The client serialises saves and coalesces pending edits.

**Why not last-write-wins:** silently discarding a student's draft on a race is
worse than making the conflict explicit.

## D6. Alembic forward-only

**Status:** Accepted

Upgrades run under `BEGIN IMMEDIATE`, so DDL and the revision bump commit or roll
back together. Destructive downgrade is deliberately unsupported — the original
upload is always kept, so the data can be recovered without a downgrade path.

## D7. Selective cloud vision, not blanket upload

**Status:** Accepted

`cloud_vision.route` sends only *difficult* units to Groq. Ordinary readable
content stays local. Only a resized preview PNG is sent — never the original
filename, never the whole document. Frame vision is capped at 12 routed frames
per pass, one per 30-second window, and excludes source audio.

**Cost:** routing heuristics can misjudge difficulty, and a misjudged unit is
still a real upload. Cloud results are stored as unverified metadata and never
replace `content_units.text` or change its hash/status.

## D8. Automatic cloud sending with disclosure, not per-upload consent

**Status:** Provisional — see D8a

Automatic Groq vision and speech are disclosed in the UI and controlled by
`STUDYLENS_AUTO_GROQ_*` environment flags. `cloud_visuals` jobs carry a `consent`
field and the manual route requires `{consent:true}`.

**Contradiction, now on the record:** the manual vision route requires explicit
consent, automatic queueing does not ask, and automatic cloud audio carries no
consent field at all. Older documents described per-upload consent; that is not
what the code does. The tested per-question/per-assessment consent flow does not
exist.

### D8a. Consent needs a decision before any cloud feature ships

**Status:** Open

## D10. YouTube captions as an immutable snapshot

**Status:** Accepted

A caption import stores an immutable JSON snapshot with cue times and track
provenance. A refresh creates a new version **only** when the snapshot actually
changes. Blocked captions retain a link-only snapshot; no text is invented.

**Why:** provenance must survive YouTube changing, retracting or re-generating a
track underneath a student.

**Known limitation:** snapshots carry `workspace_id`, `source_path` and `line`
metadata. This is **local documentation provenance, not externally verifiable
citation** — there is no ground truth to check against.

## D11. YouTube media association is student-supplied and unverified

**Status:** Provisional

A student attaches a separately uploaded local video version to a YouTube source
and enters the YouTube time matching local 00:00. Captions can then be reviewed
against the local video while audio, frame selection and OCR/Groq jobs stay
independent.

**Why:** this avoids implementing video downloading and avoids pretending Neev
verified the correspondence. **The match is asserted by the student and is not
checked.** Associations are append-only with detach tombstones; the newest
association wins.

## D12. The content endpoint is inspection, not retrieval

**Status:** Accepted

`GET .../content` returns scoped, ordered units with exact locators, at most 10
per response — **including** units whose status is `needs_ocr`, `suspect`,
`unreadable`, `too_large` or `empty`.

**Why:** the UI needs a faithful view of what extraction actually produced,
including failures, for the student to review. Anything doing retrieval must
apply its own eligibility gate (original integrity, terminal
`succeeded`/`partial` extraction, `text`-only units, warnings preserved). **This
endpoint is not that gate and must not be used as a grounded-answer corpus.**

## D13. No search, no telemetry, no voice tutor

**Status:** Accepted

None of these components exists in tracked runtime source.

**Why it matters:** it keeps the privacy surface small and explicit. Any future
search or telemetry work is a new decision with its own data-flow entry, not an
extension of an existing one.

## D14. Providers are inlined, not abstracted

**Status:** Provisional — a known gap

Groq, Ollama and YouTube clients live inside the modules that use them. There is
no shared provider interface, prompt registry or versioned prompt store.

**Cost, concrete:** Groq vision records `prompt_version` and ASR records
## D16. The smoke screenshot is written to `tmp/`, not to `docs/`

**Status:** Accepted

`electron/main.cjs` previously wrote the desktop smoke screenshot to
`docs/evaluation/screenshots/phase-05-workspace-desktop.png`. When B1 moved the
archived evidence out of `docs/evaluation/`, that write would have recreated the
directory and left an untracked file after **every** gate run — so a passing test
suite would still dirty the working tree, and the "restore it byte-for-byte" step
in the audit procedure would have had nothing to restore.

The smoke test now writes to `tmp/smoke-screenshots/`, which is gitignored.

**Why here and not "restore it afterwards":** a gate that leaves the tree dirty is
a gate that gets skipped or force-restored, and a force-restore is exactly how a
real regression in a generated artifact gets hidden.

**Cost:** the last-known-good desktop screenshot is no longer version-controlled.
It was never evidence — it is regenerated on each run. Historical screenshots are
retained separately in `docs/archive/ingestion-pilots/screenshots/`.

## D17. Windows filename case-insensitivity is a real constraint

**Status:** Accepted — a platform fact, not a preference

On NTFS, `docs/architecture.md` and `docs/ARCHITECTURE.md` are **the same path**.
Git can store both names, but the working tree cannot, and the checkout after a
pull from a case-sensitive machine (Linux CI, a Mac with a case-sensitive volume)
would produce a file that collides on the next Windows checkout.

B1 replaced the stale `docs/architecture.md` with a new document at
`docs/ARCHITECTURE.md`. Both names are now used nowhere in the tree.

**How this is enforced:** nothing enforces it today. `.gitattributes` pins line
endings and binary types but does not address case. The risk returns the moment
someone adds `Readme.md` alongside `README.md`.

**Open risk:** a case-only rename commit can succeed locally on Windows and fail
or silently no-op on a case-sensitive checkout. If CI ever runs on Linux, add a
check that rejects any commit containing two paths that differ only in case.
engine/config/model, but **Ollama records only model and text with no prompt
revision** — a real provenance gap, not a stylistic one.

**Why it held:** there was one consumer per provider, so the abstraction would
have been premature. That reasoning expires as soon as a second consumer appears.

## D15. Evaluation evidence is archived, never deleted

**Status:** Accepted

Phase reports, raw results, screenshots and run logs move to
[`docs/archive/ingestion-pilots/`](archive/ingestion-pilots/README.md) with an
index stating what each file showed and what superseded it. Regression fixtures
live in [`tests/fixtures/ingestion/`](../tests/fixtures/ingestion/README.md).

Scripts whose dependencies were never in `services/requirements-lock.txt` are
archived as **not runnable from this repo** rather than deleted.

**Why:** the evidence is the only record of what was actually measured. It also
records failures — `phase-07b-service-first.log` shows 2 failures out of 143
tests that now both pass, with **root cause unverified**. Deleting it would
destroy an unresolved discrepancy.
Disclosure plus an environment flag is a reasonable default for a private
desktop tool and a poor one for anything assessed. This is unresolved, not
settled. Options, in order of directness: per-upload confirmation, a single
per-workspace opt-in recorded durably, or per-question consent at answer time.

Whichever is chosen needs a durable table; today there is no consent table.

## D9. Automatic transcripts are marked `suspect`

**Status:** Accepted

Every automatic transcript carries `review_required` and a warning. Chunk
boundaries may split words; speakers are not identified; clipping and dropped
audio streams are reported.

**Why:** a confident-looking transcript that silently loses words is worse than
one labelled as needing a listen.