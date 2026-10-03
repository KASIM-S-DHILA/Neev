# Local OCR pilot — complete candidate matrix

Generated from retained outputs. See `small-ocr.md` for scope, interpretation, and recommendations.

Weights use decimal MB. RAM uses MiB. Times exclude initialization/download. CER ignores whitespace/case. Lower CER is better. Hindi CER is only meaningful for Hindi-capable models.

| Configuration | Status | Weights MB | Peak RSS MiB | Seconds/sample | Clean CER % | Degraded CER % | Hindi CER % | Table numbers /10 | Blank empty |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| doctr-400mb-combination | complete | 456.63 | 1024 | 3.736 | 0.0 | 0.0 | — | 10 | True |
| doctr-det-db_mobilenet_v3_large | complete | 79.29 | 582 | 1.222 | 0.0 | 0.0 | — | 10 | True |
| doctr-det-db_resnet34 | complete | 152.35 | 637 | 2.014 | 0.0 | 0.0 | — | 10 | True |
| doctr-det-db_resnet50 | complete | 164.13 | 644 | 2.433 | 0.0 | 0.0 | — | 10 | True |
| doctr-det-fast_base | complete | 105.56 | 675 | 2.106 | 0.0 | 0.0 | — | 10 | True |
| doctr-det-fast_small | complete | 101.91 | 674 | 1.879 | 0.95 | 0.95 | — | 10 | True |
| doctr-det-fast_tiny | complete | 97.32 | 694 | 1.754 | 0.0 | 0.95 | — | 10 | True |
| doctr-det-linknet_resnet18 | complete | 109.35 | 430 | 1.312 | 0.0 | 0.0 | — | 10 | True |
| doctr-det-linknet_resnet34 | complete | 149.78 | 469 | 1.875 | 0.0 | 0.0 | — | 10 | True |
| doctr-det-linknet_resnet50 | complete | 178.46 | 762 | 2.511 | 0.0 | 0.0 | — | 10 | True |
| doctr-int8-det-db_resnet34 | complete | 41.44 | 487 | 1.485 | 0.0 | 0.95 | — | 10 | True |
| doctr-int8-det-db_resnet50 | complete | 44.47 | 492 | 1.661 | 0.0 | 0.0 | — | 10 | True |
| doctr-int8-det-linknet_resnet18 | complete | 30.65 | 391 | 0.927 | 0.0 | 0.0 | — | 9 | True |
| doctr-int8-det-linknet_resnet34 | complete | 40.8 | 386 | 1.318 | 0.0 | 0.0 | — | 9 | True |
| doctr-int8-det-linknet_resnet50 | complete | 48.07 | 501 | 1.766 | 0.0 | 0.0 | — | 10 | True |
| doctr-int8-rec-crnn_mobilenet_v3_large | complete | 13.63 | 375 | 0.864 | 0.95 | 0.95 | — | 9 | True |
| doctr-int8-rec-crnn_mobilenet_v3_small | complete | 9.97 | 371 | 0.75 | 0.95 | 0.95 | — | 9 | True |
| doctr-int8-rec-crnn_vgg16_bn | complete | 23.33 | 379 | 1.096 | 0.95 | 0.95 | — | 9 | True |
| doctr-int8-rec-master | complete | 121.12 | 564 | 12.103 | 0.95 | 0.95 | — | 9 | True |
| doctr-int8-rec-parseq | complete | 38.85 | 430 | 1.087 | 0.95 | 0.95 | — | 9 | True |
| doctr-int8-rec-sar_resnet31 | complete | 74.36 | 466 | 4.611 | 0.95 | 0.95 | — | 9 | True |
| doctr-int8-rec-vitstr_base | complete | 90.57 | 450 | 2.058 | 0.95 | 0.95 | — | 9 | True |
| doctr-int8-rec-vitstr_small | complete | 26.41 | 387 | 1.014 | 0.95 | 0.95 | — | 9 | True |
| doctr-rec-crnn_mobilenet_v3_large | complete | 34.14 | 544 | 0.743 | 0.0 | 0.0 | — | 10 | True |
| doctr-rec-crnn_mobilenet_v3_small | complete | 24.41 | 526 | 0.757 | 0.0 | 0.0 | — | 10 | True |
| doctr-rec-crnn_vgg16_bn | complete | 79.29 | 574 | 1.096 | 0.0 | 0.0 | — | 10 | True |
| doctr-rec-master | complete | 263.12 | 834 | 8.719 | 0.0 | 0.0 | — | 10 | True |
| doctr-rec-parseq | complete | 112.66 | 645 | 2.278 | 0.0 | 0.0 | — | 10 | True |
| doctr-rec-sar_resnet31 | complete | 238.31 | 747 | 2.537 | 0.0 | 0.0 | — | 10 | True |
| doctr-rec-viptr_tiny | complete | 36.18 | 644 | 1.329 | 0.0 | 0.0 | — | 10 | True |
| doctr-rec-vitstr_base | complete | 357.46 | 850 | 3.94 | 0.0 | 0.0 | — | 10 | True |
| doctr-rec-vitstr_small | complete | 101.93 | 607 | 2.094 | 0.0 | 0.0 | — | 10 | True |
| doctr-tables | complete | 182.23 | 1959 | 3.193 | 0.0 | 0.0 | — | 10 | True |
| easyocr-craft-en | complete | 98.3 | 1453 | 5.718 | 0.95 | 0.95 | — | 9 | True |
| easyocr-craft-hi-en | complete | 298.56 | 1626 | 7.698 | 4.76 | 5.71 | 8.75 | 5 | True |
| easyocr-dbnet18-en | failed | 71.07 | 1979 | — | — | — | — | — | — |
| florence2-base-ft | complete | 463.22 | 1722 | 5.286 | 0.0 | 0.0 | — | 10 | False |
| florence2-base | complete | 463.22 | 1711 | 8.716 | 0.0 | 0.0 | — | 10 | False |
| pp-v4-document | stopped-slow | 208.86 | 1043 | 78.354 | — | — | — | — | True |
| pp-v4-en | complete | 10.66 | 372 | 1.193 | 1.9 | 0.0 | — | 10 | True |
| pp-v4-hi | complete | 10.7 | 349 | 1.582 | 3.81 | 4.76 | 68.75 | 0 | True |
| pp-v4-mobile | complete | 16.19 | 388 | 1.277 | 0.95 | 0.95 | — | 10 | True |
| pp-v4-server | stopped-slow | 204.47 | 1078 | 79.76 | — | — | — | — | True |
| pp-v5-ch | complete | 22.04 | 392 | 1.117 | 0.0 | 0.0 | — | 10 | True |
| pp-v5-devanagari | complete | 13.35 | 391 | 1.26 | 0.0 | 0.0 | 48.75 | 10 | True |
| pp-v5-en | complete | 13.28 | 376 | 1.089 | 0.0 | 0.0 | — | 10 | True |
| pp-v5-latin | complete | 13.31 | 381 | 1.152 | 0.0 | 0.0 | — | 10 | True |
| pp-v5-server | stopped-slow | 173.28 | 936 | 24.718 | — | — | — | — | True |
| pp-v6-medium | complete | 139.33 | 627 | 14.793 | 0.0 | 0.0 | — | 10 | True |
| pp-v6-small | complete | 31.75 | 388 | 0.956 | 0.0 | 0.0 | — | 10 | True |
| pp-v6-tiny | complete | 6.9 | 314 | 0.292 | 0.0 | 0.0 | — | 10 | True |
| smoldocling-bf16-vision-q8_0 | complete | 431.58 | 869 | 19.615 | 0.0 | 100.0 | — | 10 | False |
| smoldocling-f16_q8_0-vision-f16 | complete | 455.63 | 873 | 21.625 | 0.0 | 100.0 | — | 10 | False |
| smoldocling-q4_k_m-vision-f16 | complete | 307.2 | 745 | 17.083 | 0.0 | 100.0 | — | 10 | False |
| smoldocling-q4_k_m-vision-f32 | complete | 491.22 | 916 | 17.577 | 0.0 | 100.0 | — | 10 | False |
| smoldocling-q8_0-vision-f16 | complete | 365.08 | 789 | 18.862 | 0.0 | 100.0 | — | 10 | False |
| tesseract-best-en-hi | complete | 27.3 | 121 | 0.608 | 0.0 | 0.0 | 3.75 | 7 | True |
| tesseract-best | complete | 15.4 | 105 | 0.519 | 0.0 | 0.0 | — | 7 | True |
| tesseract-fast-en-hi | complete | 5.24 | 101 | 0.395 | 0.0 | 0.0 | 3.75 | 7 | True |
| tesseract-fast | complete | 4.11 | 96 | 0.31 | 0.0 | 0.0 | — | 7 | True |
| tesseract-installed-psm11 | complete | 4.11 | 88 | 0.316 | 0.0 | 0.0 | — | 6 | True |
| tesseract-installed-psm6 | complete | 4.11 | 90 | 0.291 | 0.0 | 0.0 | — | 9 | True |
| tesseract-installed | complete | 4.11 | 89 | 0.298 | 0.0 | 0.0 | — | 7 | True |
| trocr-small-handwritten | complete | 259.21 | 862 | 2.001 | 0.0 | 0.0 | — | 4 | True |
| trocr-small-printed | complete | 259.12 | 862 | 2.114 | 0.0 | 0.0 | — | 10 | True |

## Failures, exclusions, and partial trials

- **easyocr-dbnet18-en** (failed): Input type is cpu, but 'deform_conv_cpu.*.so' is not imported successfully..
- **pp-v4-document** (stopped-slow): Stop rule: >20 seconds/page on a non-generative candidate; partial results retained.
- **pp-v4-server** (stopped-slow): Evaluator stopped this specific worker after equation measurements around 80 seconds per call; partial results retained. Exit code 15 is the evaluator termination..
- **pp-v5-server** (stopped-slow): Stop rule: >20 seconds/page on a non-generative candidate; partial results retained.
- **smoldocling-bf16-vision-q8_0 / blank**: generation hit the output-token limit; the worker completed, but this transcript is truncated.
