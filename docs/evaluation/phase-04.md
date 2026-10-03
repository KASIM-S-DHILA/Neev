# Phase 4 acceptance — PDF/text ingestion

Date: October 1, 2026. Scope: local PDF/TXT/Markdown extraction, immutable version-bound text, exact page/line locators, scanned/blank/unreadable page flags, bounded resource handling and a source-text viewer. No AI model or OCR engine is required.

## Independent gate

With the README setup complete:

```powershell
npm.cmd run api:install
npm.cmd run ingest:test
npm.cmd run api:test
npm.cmd run check
npm.cmd run smoke:desktop
```

The only new runtime package is `pypdf==6.19.0`. `ingest:test` uses disposable databases, authored fixtures and real worker subprocesses. Test-only helpers inject a stalled parser or slow unit commits; they are never used by the student app. `api:test` also runs queue/storage regressions. The hidden desktop check imports an authored PDF into isolated smoke data and reads physical page 2 through the native IPC bridge.

## Fixture provenance and reviewed truth

`fixtures/phase-04/generate.py` creates authored digital, mixed scanned/blank and encrypted PDFs, an intentionally invalid PDF, UTF-16 notes and `gold.json`. The generator uses the bundled document runtime, not an app dependency. All six readable digital/mixed PDF pages were rendered with Poppler and visually inspected. Three gold questions map to reviewed physical pages; scan/off-material entries deliberately contain no invented answer. Retrieval and refusal metrics on these entries belong to later phases.

The raster scan contains text only in an image. Its extracted unit must be empty and flagged `needs_ocr`. The mixed file's blank third page must retain page number 3 and status `empty`. Encryption uses an authored fixture password solely to test refusal; the app has no password entry or decryption workflow.

Library rationale/limitations were checked against the [official pypdf extraction documentation](https://pypdf.readthedocs.io/en/latest/user/extract-text.html): PDF text extraction reads an existing text layer, cannot OCR images, and can consume substantial memory on dense streams. Hence the bounded parser process and explicit partial-content flags.

## Recorded results

| Check                                                 | Result                                                                  |
| ----------------------------------------------------- | ----------------------------------------------------------------------- |
| Independent ingestion suite                           | 18 passed                                                               |
| Full service/storage/queue suite                      | 47 passed                                                               |
| JS session/save/import suite                          | 13 passed                                                               |
| TypeScript and production build                       | Passed                                                                  |
| Hidden Electron + content IPC                         | Passed; page 2 of 3, matching reviewed text                             |
| Reviewed gold page locators and extracted-text hashes | Passed                                                                  |
| Mixed digital/scan/blank PDF                          | Readable text retained; scan/blank units correctly flagged              |
| Encrypted/corrupt PDF                                 | One failed attempt, actionable error, original retained                 |
| UTF-16 Hindi/English and long CRLF lines              | Exact text and decoded offsets preserved                                |
| Invalid encoding/binary text                          | Declined without guessing content                                       |
| Duplicate/new version/workspace isolation             | No duplicate job/units; old text remains separate; wrong scope rejected |
| Running cancellation and killed PDF worker            | Stable completed units retained; resumed without duplicates             |
| Stalled parser cancellation                           | API stayed responsive; parser recycled after cancellation               |
| Timeout and memory guard                              | Actual process aborted with persisted failure; no fake success          |
| Intentional recycle then another job                  | Supervisor remained available; crash budget unchanged                   |
| File/page/stream limits and pagination bounds         | Declined or flagged before unsafe/truncated evidence                    |
| Phase 3 database upgrade                              | Session/original preserved; extraction backfilled                       |
| Unimplemented media                                   | Integrity only; no extracted-text claim                                 |
| Browser import, review, Next and direct page jump     | Passed on authored PDF                                                  |
| Browser scanned page                                  | Correct physical page and OCR warning; no fabricated text               |

Evidence: [PDF page viewer](screenshots/phase-04-text-browser.png), [scanned-page warning](screenshots/phase-04-ocr-browser.png), [native startup](screenshots/phase-04-workspace-desktop.png). The native smoke ran outside the Windows AppContainer sandbox with renderer sandboxing and Node isolation enabled.

The memory test uses the actual private-memory sampling path with a deliberately tiny test budget. The timeout test uses a deliberately short deadline. These establish abort/recovery behavior; they are not a measured 512 MiB worst-case bound or an 8 GB end-to-end benchmark. Synthetic oversize bytes test admission limits, not real textbook extraction quality.

## Student laptop checks — completed

On October 1, 2026, the student confirmed the three requested laptop checks were complete, with no issues reported. This records student-reported manual acceptance; it adds no hardware resource measurements or confirmation of optional checks. Keep the checklist below for regression checks.

Close/reopen **StudyLens.lnk** to load the built 0.4.0 interface. No queue evaluation flag is needed.

1. **Real text PDF:** Add one of your PDFs in Materials. Expand its original/version and click **Review extracted text**. Compare a couple of pages with the original, including a cover page if present. Use Next/Previous and the page-number Go control. References use physical PDF pages, not the book's printed page numbers.
2. **Scanned/partial content:** Add `fixtures/phase-04/mixed-notes.pdf`. Page 1 should contain readable text, page 2 should ask for OCR without invented words, and page 3 should say no text was found. The source remains partly extracted. You can also check one of your scanned PDFs; scan detection is a heuristic.
3. **Restart and versions:** Close/reopen the app. Confirm extracted text is still available. If you add a changed version of a PDF/text source, open each version's review and confirm each retains its own text/location and downloadable original.

Optional repeatable failure check: import `corrupt-notes.pdf` or `encrypted-notes.pdf`; expect **Extraction needs attention**, never **Text extracted**. Originals should remain downloadable.

To keep evaluation files separate, set `STUDYLENS_DATA_DIR` to a project `tmp/phase04-manual` path before `npm.cmd start`; do not use the shortcut for a terminal-only override. A large file is unnecessary for this gate.

## Practical limits

- Original storage cap remains 2 GB. Extraction caps are PDF 64 MiB/500 pages and text 16 MiB. Dense pages above 1 MiB of uncompressed content or 50,000 extracted characters are flagged, not truncated into evidence.
- UTF-8/BOM-marked UTF-16 are supported; other encodings need an exported text copy. Line/character locators refer to decoded Unicode, with preserved line endings; character end is exclusive.
- OCR, full table/equation/diagram interpretation and geometric highlight anchors are not implemented. Text plus images carries a visual-review warning. Wrong hidden OCR/font mapping and complex reading order can escape detection.
- A cancelled/failed job can Resume from saved units. A completed partial job may require OCR or a corrected new original; repeatedly pressing Resume does not repair the source. The drawer directs these results to Materials for review.
- Per-page parsing uses sampled memory/time/cancellation guards. Resource use on the target laptop and larger course collections still needs Phase 19 benchmarking. Huge-library source-list pagination remains later hardening.
- Existing supported originals are automatically queued on service startup. Multiple windows share one heavy execution slot. Tutor retrieval/indexing and learning evidence are not generated by this phase.

Phase 4 is accepted: automated checks, reviewed fixtures and student-reported manual checks are complete. Next: Phase 5 OCR, slides/images and visual content.
