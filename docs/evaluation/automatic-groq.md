# Automatic selective Groq processing

Date: 2026-10-03. The student requested automatic Groq calls without per-source intervention. This supersedes the earlier Groq consent gate. Google OCR was subsequently removed at the student's request; Groq is the only cloud extraction provider. No live cloud calls were made for these changes.

## Behavior

1. Verify the original and finish local PDF, slide or image extraction first. Read native text and native PowerPoint table cells locally; retain Tesseract output and previews.
2. If `GROQ_API_KEY` is configured and automatic processing is enabled, atomically queue one durable Groq job when local extraction succeeds or finishes partially with saved previews. Failed or cancelled local extraction does not queue it. Audio, video and plain text sources are excluded.
3. The existing conservative router selects difficult previews using OCR confidence, missing readable text, possible table/math/diagram layout and non-table graphics. Ordinary readable content, exact white empty previews and complete native tables can stay local. This is a heuristic, not a calibrated classifier; selection can miss difficult content or send an ordinary preview.
4. Saved results appear in Extracted text with provider/source provenance and remain unverified. Original bytes, local text, hashes and source locations remain unchanged. The job and results record that processing was automatic.

Materials discloses automatic preview sending before upload. The preview shows the automatic policy and cloud job status; Background work shows queue progress and supports cancellation. Groq manual retry/current-location buttons require no checkbox or provider selection.

## Resource and failure behavior

The existing single heavy worker is retained. Ready local jobs take priority over cloud jobs. Quota waits return the cloud job to the queue and release the worker. Existing conservative request spacing, rate-limit handling, bounded retries, cancellation, original/preview integrity checks and model/prompt-specific caching still apply. Errors preserve local results. No additional local model is loaded. Old saved jobs for a removed provider stop before network access, with a message to retry using Groq; they are never silently rerouted. Historical saved results retain their provenance and are displayed as archived cloud extraction.

The automatic job is committed in the same SQLite transaction as local completion. Recovery resumes the saved job. A unique job per version prevents duplicate enqueueing; completion does not restart a cancelled or existing cloud job.

Set `STUDYLENS_AUTO_GROQ_VISION=0` before launching StudyLens to disable automatic sending. A queued automatic job also checks this setting before sending. Manual Groq processing remains available. Missing keys disable automatic queueing. No automatic sweep of the previously processed library occurs: choose **Process visuals again** for an older source to use the new pipeline. Reprocessing rebuilds derived units and invalidates the old cloud job/results as before.

## Verification

- 9 automatic-processing tests passed using authored source fixtures and mocked HTTP: durable completion/restart/cache, local text preservation, ordinary preview staying local, missing key/opt-out, failed/cancelled extraction, unsupported source/no preview, cancelled job deduplication, opt-out after queue, local-job priority and verification before extraction when creation timestamps tie.
- After Google removal, 20 Groq tests and the 8 automatic tests passed, including rejection of removed-provider API requests and saved jobs without network access, quota waits, cancellation and output validation.
- TypeScript/Vite production build and Electron desktop smoke passed.
- Hidden Electron UI check passed: automatic upload disclosure, no checkbox and no provider selector. No processing button was clicked. [UI result](automatic-groq-ui.json), [screenshot](screenshots/automatic-groq-desktop.png).

Run the automatic gate:

```powershell
node scripts/python.mjs -m unittest discover -s services/tests -p test_automatic_vision.py -v
```

Manual check: restart the app with the configured Groq key, import a difficult image/PDF or reprocess an existing one, and watch local extraction followed by **Automatic Groq** in Background work without clicking a cloud button. Compare the returned text/table with the source. Live OCR accuracy and account quota availability remain separate from these mocked regression checks.
