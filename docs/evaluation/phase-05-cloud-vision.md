# Phase 5 extension — selective cloud visual extraction

Historical gate: the Groq consent flow below was superseded on October 3, 2026 by [automatic selective Groq processing](automatic-groq.md). Google OCR was subsequently removed at the student's request.

Date: October 1, 2026. The student authorized the pilot and then app integration. This gate adds opt-in Groq extraction to the existing local workflow. Student manual acceptance is confirmed: after showing the correct native table, the student reported all remaining requested checks passed.

## Implemented flow

1. Import and local extraction remain unchanged by default: no automatic cloud jobs or requests.
2. In the source viewer, expand **Cloud help for difficult visuals**. Consent is specific to the displayed source version. **Process difficult visuals** runs local selection; **Process this slide/PDF page/image page** overrides selection at that location.
3. Selection considers empty white previews, retained native tables, low Tesseract word confidence, numeric/horizontal layout, mathematical text, diagonal strokes and native chart/SmartArt/connector flags. These are provisional signals, not proof of correctness. Difficult images can be missed, and ordinary content can be selected unnecessarily.
4. A separate durable `cloud_visuals` job sends one bounded image at a time. Full rendered pages include embedded pictures, so they are not also sent separately. Without a full slide rendering, at most four saved picture previews are eligible. These are complete previews, not automatically detected tight crops.
5. Results appear under **Tables & structure**, with source text, native table cells and cloud transcription kept separate. Cloud output remains unverified and is not retrieval evidence. Equations are literal LaTeX; diagram connections are text lists. No answer solving or mathematical verification is implied.

October 2 viewer correction: **Extracted text** now prefers a successful saved Groq transcription for that location, showing text, tables, equations and diagram labels with an **Unverified** label. Original local OCR is available under **Local extraction retained**; its stored text/hash is unchanged. Without a successful cloud result the tab displays local extraction. Starting cloud processing keeps the text tab selected, and the existing job polling updates it when output is saved. Earlier saved Groq output is displayed immediately after reopening; it does not require another request. **Tables & structure** remains available. The [native viewer check](cloud-extracted-text-ui.json) passed for the retained production table, exact local-text comparison and unchanged local hash; [screenshot](screenshots/cloud-extracted-text-desktop.png). JS tests and production build passed.

Native DrawingML tables retain literal grid order, including empty cells and decimals, without guessing which row is a header. Merged cells require comparison with the original. A direct check of the student's deck found native tables on slides 10 and 12; slide 12 retained all ten numeric values, including `4.2` and `4.5`. See [retained native grid](native-table-deck.json). Reprocess an older imported deck to add this metadata.

## Credentials, bounds and recovery

- `GROQ_API_KEY` is read in the backend/worker environment. The renderer sees only configured/not configured and the model ID. No credential is stored in SQLite, reports or model metadata. Native OCR/office helpers do not receive that key.
- Fixed HTTPS endpoint, redirects disabled, environment proxies disabled, normal TLS verification. Model: `qwen/qwen3.8-27b`, selected from the account's available vision models during the preceding live pilot. Its availability and preview behavior can change; unavailable access produces an explicit HTTP error, preserving local results.
- Saved previews are checked against their SHA-256 and store containment. The original is rehashed before each processing attempt. Images are at most 1280 pixels per edge; existing saved previews are at most 512 KiB. Initial requests use JSON object mode, no reasoning, temperature 0 and 1536 output tokens. A JSON generation failure or output-budget truncation schedules one fallback without provider JSON mode, with the same JSON instructions and a 4096-token output bound. Responses are bounded to 2 MiB; transcription text to 50,000 characters with additional collection limits.
- Local validation rejects unknown fields, malformed/truncated output, ragged tables, contradictory blank claims, dangling diagram connections, and suspected duplicate or partial tables. Overlap detection can also flag legitimate repeated tables; it requests review instead of silently merging them. Successful format checks do not establish factual accuracy.
- Text-mode fallback can return one complete JSON object inside a Markdown code fence. Only that whole wrapper is removed before the same validation. Extra prose, multiple objects and broken JSON remain rejected. Persistent invalid output marks the visual for review and preserves local extraction. Other HTTP 400 errors do not trigger this format fallback; key/access/request errors have distinct messages without publishing raw provider output.
- One image request per 65 seconds per data directory is the conservative default for the observed 8,000 TPM account. Low remaining-token/request headers can extend the delay. HTTP 429 honors a bounded provider wait and permits three quota waits before marking the affected visual for attention. Requests from other data directories/apps still share provider quotas.
- Quota waits persist through `available_at` and a tiny atomic budget file, releasing the heavy worker for local jobs. No long sleep holds the worker. Connect timeout is 5 seconds, read timeout 20 seconds, total request budget 23 seconds, with cancellation checks about every 100 ms. Existing worker memory/time guards remain active.
- Format recovery uses the same durable scheduling and 65-second spacing, with the stage **Retrying visual output**. A checkpoint records the fallback mode so restarting does not reset its one-fallback limit.
- Each completed visual commits separately. Results are reused within the same source version/unit using sent-image hash, model and prompt revision. Cancellation or restart retains saved results; local reprocessing deletes derived units and the old cloud job. Cloud permission does not carry to a new source version. A cancelled job can be resumed under its original consent.
- Cancellation stops local receiving/saving and future sends; it cannot recall an image already transferred. A crash between transfer and local commit can require another request. No exactly-once provider billing guarantee is claimed.

## Independent checks

```powershell
npm.cmd run vision:test
npm.cmd run api:test
npm.cmd run check
npm.cmd run smoke:desktop
```

`vision:test` uses labeled provider responses and disposable databases: no actual external requests. It covers absent/false/non-boolean consent, workspace/location scope, missing credentials, active-job conflicts, original/preview corruption, duplicate output, native table extraction, cache reuse, cancellation during a pending request, quota scheduling with continued local work, and invalidation on reprocessing. The retained initial pilot's partial duplicate tables are explicitly rejected.

Observed results:

| Gate | Result |
|---|---|
| Service regression | 75 tests passed, including the first 12 cloud tests |
| Final independent cloud gate | 14 tests passed after adding retained duplicates and cumulative counts across quota pauses |
| JS session/import tests | 13 passed |
| TypeScript/build | Passed |
| Hidden native Electron | Passed: storage/visual IPC, vision capability, cloud request without consent rejected |
| Native viewer rendering | All 20 data cells present; unverified label visible; processing details collapsed |
| Live production table extraction | One correctly structured table; all headers, rows and ten numeric values exact; 1.172 seconds for selection, transfer, validation and persistence |
| Live repeat | Cached result reused, zero new sends |
| Original/local text/locator preservation | Passed in the live gate |
| Whole-app 8 GB performance and broad routing/semantic quality | Not established |

### October 2: HTTP 400 recovery regression

The student's failing `numbers_gs150.jpg` request was reproduced on its already-approved preview. Groq returned HTTP 400 with `error.code=json_validate_failed`. The earlier generic key/access/quota message misidentified this generation failure. Groq documents response format validation failures separately from authentication and rate limits: [errors](https://console.groq.com/docs/errors), [structured outputs](https://console.groq.com/docs/structured-outputs).

The first text-mode fallback at 3072 tokens failed local validation. A diagnostic at 4096 tokens returned HTTP 200, `finish_reason=stop`, and 2128 completion tokens, but its JSON was wrapped in a Markdown code fence. This was a parsing failure rather than truncation. After allowing only the whole fence wrapper, the production fallback returned one schema-valid table with 29 rows, 96 text lines and three uncertainties in 4.828 seconds. [Live recovery evidence](groq-format-fallback-20261002-034941.json). No app database was mutated by this diagnostic, and no additional source was transmitted.

This establishes request recovery and structural validation on this image. Every handwritten cell and completeness of transcription still need comparison with the original; no semantic accuracy claim is made. Earlier failed attempts remain recorded in [first fallback evidence](groq-format-fallback-20261001-181237.json). Successful cached outputs remain reusable.

Final regression results for this fix: 19 cloud tests, 16 durable queue tests and 13 JS tests passed; TypeScript and production build passed. Fixtures cover one bounded fallback after JSON generation failure, restart persistence, repeated failure ending in partial results, rejecting invalid fallback output, distinct non-generation HTTP 400 handling, and accepting a single fenced object while rejecting surrounding prose/fragments. These are software behavior checks, not OCR accuracy measurements.

For an existing failed job: restart StudyLens to load the corrected worker, then use **Background work → Resume** on the cloud visual job. Format recovery can display **Retrying visual output** for about 65 seconds; local navigation and jobs remain available during that wait.

The overlapping test counts are not separate accuracy samples. The first standalone visual regression exposed malformed PPTX reaching LibreOffice before XML validation, causing a timeout and a Windows profile cleanup error. XML preflight now precedes rendering; the full regression passed afterwards.

The source viewer was reviewed in a hidden native Electron window using the isolated live fixture database. [Screenshot](screenshots/phase-05-cloud-desktop.png). No additional image was transferred for that visual check.

The [live integration evidence](desktop-vision-20261001-172849.json) came from the app API, real Tesseract and the production worker in an isolated data directory. The local OCR omitted some cells and read `4.5` as `45`; the separate cloud result recovered the correct table. This was one known image, not a held-out quality test or latency distribution. Approximately 70.4 MiB private memory was observed after processing in that evaluation process, not a peak or whole-app measurement.

Reproduce the explicit live gate (sends the retained table image to Groq):

```powershell
node scripts/python.mjs scripts/evaluate-desktop-vision.py --run
```

### Local production routing check

```powershell
node scripts/python.mjs scripts/evaluate-desktop-routing.py
```

This makes no cloud requests and uses actual Tesseract plus the app's Pillow router. See [results](desktop-routing-results.json). It differs from the earlier cached PP-OCR/OpenCV pilot. Local extraction took 0.263–0.474 seconds per fixture; selection took 0.002–0.167 seconds. Clean/degraded English and a blank stayed local; table, equation, diagram and an English-OCR Hindi page became candidates. The first implementation missed the known branching figure. Additional diagonal slopes and a small stroke expansion fixed that case. Rules were adjusted on this known set, so these outcomes are not unbiased routing accuracy.

Tesseract remains the app's current local recognizer. The recommended PP-OCRv6 Small replacement is a separate integration; model benchmark environments are not app dependencies. Hindi quality is not claimed from English Tesseract. Borderless tables, handwriting, photographs, faint text, arbitrary rotation, mixed-language pages, multiple dense tables/diagrams and preview downsampling remain comparison/override cases.

## Student checks

Restart StudyLens to load the updated Python worker and built interface. Use `npm.cmd run dev` or the rebuilt shortcut. If cloud setup says missing, launch from PowerShell after loading your existing user environment key without printing it:

```powershell
$env:GROQ_API_KEY = [Environment]::GetEnvironmentVariable('GROQ_API_KEY', 'User')
npm.cmd run dev
```

1. **Native table:** Open `Presentation 2.pptx`, use **Process visuals again**, go to slide 12, then **Tables & structure**. Compare every cell, especially `4.2` and `4.5`. Native cells should appear without needing cloud permission.
2. **Opt-in difficult image:** Import a table/diagram image. Before consent, cloud processing buttons must be disabled. Give permission and use **Process difficult visuals**. If selection misses it, use **Process this image page**. Compare the unverified result with **Visuals**. Native text/OCR must remain separate.
3. **Cache and queue:** Repeat the same location and confirm the reused count. On a source with several selected pages, expect **Waiting for Groq quota**. Navigate/import local notes during that wait, then cancel cloud processing. Saved results must remain; later previews must not be sent after cancellation. Restart and inspect retained results.

Manual results: the student confirmed the native table, cloud consent/processing, cache reuse and cancellation checks passed on October 1, 2026. Phase 5 is accepted for its implemented scope. Audio ingestion is the next milestone and has not started. Broad OCR correctness, semantic verification, held-out routing quality, learning gains and measured whole-app 8 GB performance remain separate evaluation gates.
