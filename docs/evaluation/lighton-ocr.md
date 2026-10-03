# LightOnOCR test — stopped at user request

The user requested stopping the benchmark on 2026-10-02. The active benchmark and its private Ollama/model server exited. No additional LightOn requests, recommended-resolution pilot, or corpus scoring will run.

## Retained results

- [CPU pilot](lighton-pilot-1280.json): eight requests hit the 120-second deadline without producing text. This is not a usable extraction result or a quality score.
- [GPU pilot at 1280px](lighton-gpu-pilot-1280.json): eight requests attempted. The known table's five rows and Bayes formula were correctly reproduced. The blank image produced explanatory prose; the printed lined note page generated repetitive table markup. Dense maths and the note hit the pilot's output-token limit.
- [Partial GPU document run](lighton-gpu-documents-1280.json): 15 of the planned 50 page attempts are saved, including partial deadline output. Nine ended with a completion marker; six reached the deadline. Page `doc-015` was interrupted while in flight and has no completed prediction in this report. The report is explicitly marked `stopped_by_user`.
- Model manifest, downloaded weights, SHA-256 records and server logs remain under `tmp/lighton-ocr`. The model plus vision projector total 1,468,349,536 bytes, exceeding the earlier 400–500 MB storage budget.

These pilots and partial pages do not establish corpus accuracy. No full 50-page comparison or official metric result is available. The CPU pilot and GPU runs also differ in RAM-cache and repetition-penalty settings; they are not a controlled hardware-only speed comparison. Other development/tests ran during part of the GPU document run.

LightOnOCR was not integrated into StudyLens. The Google Cloud Vision OCR integration requested during this benchmark was subsequently removed at the student's request. Groq is now the only cloud extraction provider.
# Cleanup note

The downloaded model and trial environment were removed at the student's request on October 3, 2026. The cancelled benchmark was not resumed. [Cleanup details and retained raw evidence](ocr-cleanup.md).
