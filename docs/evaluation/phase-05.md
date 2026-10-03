# Phase 5 acceptance — OCR, slides and visual source preservation

Date: October 1, 2026. Version: 0.5.0. Scope: local OCR, still images/multipage TIFF, PDF page previews, native PPTX text/pictures/equations, optional office/vision adapters, explicit reprocessing, source/version locators and partial-content warnings. Student manual acceptance is confirmed for the implemented workflow; broad extraction quality and whole-app 8 GB measurements remain pending.

## Manual acceptance update

On October 1, 2026, the student supplied a screenshot confirming the native slide-12 table, including `4.2` and `4.5`, then reported all remaining requested checks passed. This records student acceptance of the Phase 5 workflow and its [cloud extension](phase-05-cloud-vision.md), including cloud consent, cache reuse and cancellation. It does not replace held-out quality evaluation or measured 8 GB performance.

## Independent gate

```powershell
npm.cmd run api:install
npm.cmd run visual:test
npm.cmd run api:test
npm.cmd run check
npm.cmd run smoke:desktop
```

New pinned libraries: Pillow 12.3.0, pypdfium2 5.13.0, defusedxml 0.7.1. Tesseract 5 with English traineddata is required for the real OCR gate. It is already installed on this laptop; Hindi traineddata is not installed. No model, cloud key or external search is required. The test suite uses disposable databases and actual worker/native processes; fault injection and office/provider responses are explicitly test-only fixtures.

## Fixtures and reviewed truth

`fixtures/phase-05/generate.py` authors readable scan/branching figure/fraction images, an EXIF-oriented JPEG, blank/corrupt images, two-page TIFF, a three-page scanned PDF and a minimal OpenXML extraction package with deliberately non-filename slide order, a linked resource and OMML fraction. This PPTX is an extraction fixture, not a rendered PowerPoint quality sample. `gold.json` records locations, literal needles, graph/fraction truth and an off-material topic. All three PDF pages were rendered with Poppler and visually reviewed: text is legible, branching arrows point to Heads/Tails, and the fraction denominator is P(B). No generated OCR is presumed to verify that fraction structure.

The generator needs reportlab/Pillow for authoring, not as additional app runtime requirements. It was run with the project Pillow and bundled reportlab. The linked resource points to a closed loopback port and must never be fetched. Vision and office adapter tests use labeled responses/conversions; they do not count as live model/LibreOffice quality evidence.

Implementation APIs were checked against [Tesseract's official command-line documentation](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html) and [PDFium's Python API](https://pypdfium2.readthedocs.io/en/stable/python_api.html). OCR stores TSV confidence/word boxes; rendering runs serially and closes native handles.

## Recorded results

| Check                                           | Result                                                                                                                |
| ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Independent visual gate                         | 16 passed                                                                                                             |
| Full Python regression gate                     | 62 passed                                                                                                             |
| JS session/save/import checks                   | 13 passed                                                                                                             |
| TypeScript and production build                 | Passed                                                                                                                |
| Hidden Electron boundary and visual IPC         | Passed: OCR partial/review state, image preview, original integrity, reprocessing action                              |
| Real CPU image/PDF OCR                          | Authored literal text recovered; physical pages/word geometry retained                                                |
| EXIF JPEG/TIFF order                            | Upright OCR and exact image page order; originals retained                                                            |
| Native PPTX order/pictures/equation XML         | Correct presentation order; picture OCR and OMML separate from native text                                            |
| Blank/corrupt/animated/huge images              | No invented text or claimed success for invalid input                                                                 |
| Missing OCR executable/language data            | Preview retained with actionable warning                                                                              |
| ZIP limits/unsafe XML/external links/legacy PPT | Refused or explicitly partial/export required; no linked resource fetch                                               |
| Cancellation/reprocessing/migration             | Responsive service; cancelled native helper; stable IDs; damaged preview repaired; older units preserved on migration |
| Office adapter/count mismatch                   | Labeled converter fixture passed; mismatched full-slide previews withheld                                             |
| Optional vision adapter                         | Labeled response/offline fixtures passed; fixed local URL, unverified notes, unload request                           |
| Live LibreOffice fidelity                       | User's deck converted to 13 pages; title-slide preview confirmed by student. General layout/font fidelity still needs review. |
| Live diagram/formula interpretation             | Not run: no live vision model was evaluated                                                                           |
| Target 8 GB memory/latency                      | Not measured; Phase 19 gate                                                                                           |

Browser review covers PDF OCR warning, Visuals navigation and slide/equation inspection. Evidence: [visual source viewer](screenshots/phase-05-visual-browser.png), [slide/equation viewer](screenshots/phase-05-slide-browser.png). Native smoke ran outside Windows AppContainer with renderer sandboxing and Node isolation enabled. The service test suite does not establish general OCR accuracy or learning effectiveness.

The full regression run passed 62 tests before the final equation-preview addition. The subsequent independent visual run passed all 16 tests, including the added unsupported/deep-equation check, followed by a successful JS/build gate. These counts overlap; they are not separate benchmark samples.

## Student laptop checks

Close/reopen **StudyLens.lnk** to load 0.5.0. Keep the default tools/model configuration for these checks.

1. **Scan/image comparison:** Import a scanned PDF or a photo of notes. Review extracted text, switch to **Visuals**, and compare words/numbers and page locations against the original. Expect an OCR review warning, including when confidence is high. You can use `fixtures/phase-05/scanned-visuals.pdf` first. Check a diagram/fraction visually; an inaccurate OCR formula must not look verified.
2. **Slides:** Import one real PPTX. Check slide order/native text and any embedded image review. If full previews are unavailable, export the deck to PDF and check them there. LibreOffice is optional and is now installed here; after installation the user reprocessed their deck and confirmed the full title-slide preview. Legacy PPT must request a PPTX/PDF export. Supported native fractions/superscripts have readable previews. These preserve structure without verifying mathematical correctness; unsupported forms request comparison with the original.
3. **Restart/reprocessing/responsiveness:** Restart and confirm previews/text remain. Use **Process visuals again** on an older scanned PDF or one imported in Phase 4. Navigate while it runs, then inspect the new OCR result. Confirm the original/earlier source versions remain downloadable and unchanged.

Optional: configure an already-installed local vision model and compare its notes with reviewed graph/fraction truth. Do not mark semantic interpretation accepted from adapter fixtures alone. Live conversion/model tests should record model/tool version, material, settings, failures, timing and memory.

The final browser check reprocessed the PPTX, verified original slide order, and visually confirmed the fraction's numerator above P(B). Raw XML is stored as provenance and is no longer displayed in the student workflow. The preview is structural, not a correctness check.

## Limits

- Legacy PPT requires export. Full PPTX fidelity needs a separately installed LibreOffice or PDF export; layout/font/crop changes are possible. Linked resources/macros/embedded objects skip conversion. Presenter notes are not extracted; complex charts, tables, SmartArt and group transforms may be incomplete.
- OCR language selection requires installed traineddata. This run tested English OCR and mixed-language text preservation from Phase 4, not Hindi OCR quality. EXIF orientation is handled; handwriting, skew and arbitrary physical rotation are not automatically corrected.
- OCR/vision uncertainty is retained. No automatic student review approval, verified math parser or proven graph interpretation is claimed. Native text, OCR, equation XML and model notes have separate origins. Retrieval rules and evidence invalidation must honor these distinctions in later phases.
- Original imports remain capped at 2 GB, processing at 64 MiB PDF/slide/image or 16 MiB text; images at 40 million pixels/100 TIFF pages. PDF/slide unit limits remain 500. Bound previews are thumbnails, not original-resolution replacements.
- Worker and Windows native-helper budgets are separate; an optional external Ollama server has its own memory/lifecycle. Tests establish bounded failure/cancellation paths, not end-to-end laptop performance. Derived artifacts are retained on disk; quota/cleanup remains hardening.

Phase 5 implementation has an independently evaluable source-preservation/OCR gate. Manual acceptance and live office/vision fidelity are explicitly separate. Next after acceptance: Phase 6 audio source extraction/transcription. Live audio tutoring remains on hold.
