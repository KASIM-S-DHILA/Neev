# Privacy and data flow

What leaves the student's machine, to whom, and under what control. Derived from
the audit's process and external-transfer inventory
([`docs/audit/CURRENT_ARCHITECTURE.md`](audit/CURRENT_ARCHITECTURE.md) §2) and
verified against the code at commit `24e82f7`.

This is a **static** analysis of the shipped code. No network capture was
performed, so third-party library and native-tool behaviour beyond the
boundaries inspected here is **UNVERIFIED**.

## Summary

Neev is a local-first, single-student desktop app. Originals, the database, and
all derived content stay on disk. **Nothing is sent anywhere unless a cloud
provider is configured and the feature that uses it is triggered.** There is no
telemetry client, no analytics, and no crash reporting.

| Destination | Trigger | Sends |
| --- | --- | --- |
| Groq vision | automatic after local extraction, or manual | resized preview PNGs |
| Groq ASR | automatic on detected speech | bounded decoded WAV intervals |
| Ollama (local) | automatic or manual, only if configured | ≤768px image |
| YouTube | student pastes a link; or plays embedded video | video ID, caption requests |
| GitHub | developer runs `git push` | repository contents |
| Hugging Face | explicit setup, or an explicitly run evaluator | model/dataset downloads |

## Local storage

Under the app data directory:

- `studylens.sqlite3` — workspaces, subjects, topics, session, drafts, source
  metadata, jobs, content units, YouTube media associations. WAL enabled.
- `originals/<prefix>/<sha256>` — uploaded originals, byte-identical.
- `staging/` — in-flight imports. Safe to discard when no job is running.
- `derived/` — content-addressed preview images and caches.

Filenames are stored as metadata, never as filesystem paths. No data is written
outside this directory by the application. Removing the directory removes
everything; there is no off-device copy or sync.

### What leaves the device by default

Nothing. `GROQ_API_KEY` unset means every cloud path stays local. Set
`STUDYLENS_AUTO_GROQ_VISION=0`, `STUDYLENS_AUTO_GROQ_AUDIO=0`,
`STUDYLENS_AUTO_VIDEO_FRAMES=0` or `STUDYLENS_AUTO_VIDEO_VISUALS=0` before
launch to disable the corresponding automatic queueing. Jobs that were already
created still run.

## Groq

`https://api.groq.com/openai/v1/chat/completions` and
`https://api.groq.com/openai/v1/audio/transcriptions`. Code:
`cloud_vision.py`, `video_frame_visuals.py`, `cloud_audio.py`.

**Vision.** One resized source preview PNG per difficult unit, base64-encoded,
plus a transcription instruction, schema, model/settings and backend
authentication. **The original filename and the whole document are never placed
in the request.** Local routing means ordinary readable content is not uploaded.

**Retained video frames.** The same instruction and model for selected uploaded
video frames — at most 12 routed frames per pass, one per 30-second window.
Source audio is **not** included in these image requests.

**Speech.** One bounded decoded WAV speech interval, sent under the generic name
`source-interval.wav`, with model/format/temperature and an optional language
hint. Configured automatic speech detection precedes transfer; a local
faster-whisper Tiny model is the fallback when Groq is unavailable.

### Consent

There is **no per-upload consent prompt.** A one-time disclosure is shown at
first run and permanently in Settings. Automatic sending is disabled by
environment flag, not by a user decision.

The wording and the show-once rule live in `src/disclosure.ts`, versioned by the
`studylens.cloud-disclosure.v1` key so a wording change re-notifies rather than
silently reusing an old acknowledgement. Tests: `tests/disclosure.test.ts`.

- `cloud_visuals` jobs carry a `consent` field in the job payload, and the manual
  route requires a literal `{consent:true}` body.
- **Automatic** cloud audio has no consent field at all.
- The tested per-question / per-assessment consent flow **does not exist**.

If a per-upload or per-question consent gate is a requirement, it is new work.

### Once data is sent

A source sent to a provider **cannot be recalled by cancelling the job.** A
transfer interrupted before commit can be repeated, but provider processing that
has already started cannot be undone. Provider-side retention, training use and
quota behaviour are **UNVERIFIED** and governed by the provider's terms.

## Ollama

`http://127.0.0.1:11434/api/generate` — a **local** endpoint, not a remote
service. Code: `visual.py`. Sends one image at ≤768px with a fixed
unverified-description prompt, a configured model, and context/prediction caps
with `keep_alive=0`. No Neev remote URL is configurable here. Ollama's own model
downloads go to its registry when you run `ollama pull`.

## YouTube

Two distinct paths, both student-initiated.

**Caption import** (`youtube_helper.py`). Sends the submitted video ID and
caption-track requests to allowlisted HTTPS hosts — `youtube.com`,
`www.youtube.com`, `consent.youtube.com`, `consent.google.com`. Session proxies
## Credentials

`GROQ_API_KEY` is read from the environment and stays in backend
request headers. Native helper environments have `GROQ_API_KEY` and
`STUDYLENS_API_TOKEN` removed; worker supervision removes the local API token.
Secret values were not read, copied into documentation, or retained during the
audit.

`.env` and `.env.*` are gitignored except `.env.example`.

## Development and evaluation traffic

**Not product behaviour**, but relevant to a privacy review:

- `npm install` / `api:install` contact the npm and PyPI registries.
- `npm.cmd run audio:setup` runs `snapshot_download` from Hugging Face for the
  local speech model. No student audio is uploaded.
- `smoke:desktop` launches a hidden Electron window against an isolated data
  directory. It does not contact external services.
- Evaluators in [`scripts/ingestion-evals/`](../scripts/ingestion-evals/README.md)
  can transfer data or download models **when explicitly run**. None was run
  during the audit.
- `git push` sends repository contents to GitHub.

## Known gaps

- No search/telemetry/voice-tutor component was found, so none is described here.
- Provider-side data retention is **UNVERIFIED** — only the client side was read.
- Consent is disclosure-based, not per-upload.
- Reading-completion counters and any future mastery signal would be sensitive
  by design; they do not exist yet, so nothing is collected.
are disabled. The library may use session/consent cookies it generates itself;
**no user browser-cookie import is implemented.** No course files and no app
token are sent. When captions are blocked, a link-only snapshot is retained and
no text is invented.

**Embedded playback** (`YouTubeReview.tsx`). Loads `youtube-nocookie` on click
with the student-selected video ID and start time. The embedded player contacts
YouTube and its own dependencies as normal browser playback would. Subresource
destinations and retention are **UNVERIFIED**.

**External browser fallback** (`electron/youtube.cjs`). Opens the canonical watch
URL. Browser and account state are entirely outside Neev.

Direct YouTube video downloading is **not implemented**.
Nothing. `GROQ_API_KEY` unset means every cloud path stays local. Set
`STUDYLENS_AUTO_GROQ_VISION=0`, `STUDYLENS_AUTO_GROQ_AUDIO=0`,
`STUDYLENS_AUTO_VIDEO_FRAMES=0` or `STUDYLENS_AUTO_VIDEO_VISUALS=0` before
launch to disable the corresponding automatic queueing. Existing jobs still run.