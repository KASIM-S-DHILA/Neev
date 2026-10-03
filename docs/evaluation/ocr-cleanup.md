# OCR benchmark cleanup

On 2026-10-03, the student requested removal of the downloaded alternative OCR models and cleanup. Removed the isolated HunyuanOCR, LightOnOCR, small OCR comparison, Gemma multimodal and OmniDocBench evaluation directories under `tmp/`.

The six directories contained 17,483,128,608 bytes of files, including weights, projectors, benchmark-only Python environments, runtime binaries, caches and evaluation dataset downloads. Logical file sizes include hard-linked copies and do not equal physical disk space recovered. [Cleanup inventory](ocr-cleanup.json) records the exact targets and drive free-space readings.

Benchmark reports under `docs/evaluation` and source scripts remain available. Raw results, manifests, logs, authored OCR fixtures and scoring outputs were retained in the verified [7.7 MB evidence archive](retired-ocr-evidence.zip). Paths inside those historical records refer to the removed working directories. Re-running those experiments requires explicitly restoring inputs and downloading their dependencies/models again; cleanup does not launch benchmarks.

Production Tesseract, LibreOffice, Groq, the Tiny speech model, student originals and SQLite data remain intact. Google Cloud Vision was subsequently removed at the student's request on the same date, including its adapter, controls, tests and setup documentation. Pre-existing shared Hugging Face and Ollama models were not downloaded by these OCR trials and were excluded. The production Python environment contains no EasyOCR, RapidOCR, OnnxTR, Transformers or Torch installations requiring removal.

Verification: all six cleanup targets are absent, no alternative OCR weight files remain in the workspace, active tool executables and the speech model are present, and the Electron desktop smoke check passes.
