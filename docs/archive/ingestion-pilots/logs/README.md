# Logs (archived)

Retained run logs. `.gitignore` ignores `*.log` globally, so these are
force-added to the repository on purpose: they are evidence, not transient
output.

## `phase-07b-service-first.log`

Test-run output recorded during the Phase 7B "service-first" run.

- **2 failures were recorded at that time**, out of 143 tests.
- **Both of those tests pass as of the audit commit** (`24e82f7`); the full
  `api:test` gate passes 165 tests.
- **Root cause UNVERIFIED.** The log was never compared against the current
  implementation to explain why the failures disappeared. Treat this as an
  unresolved discrepancy, not a fixed bug.

Recorded failures (143 tests, `FAILED (failures=2)`):

| Test | Recorded symptom |
| --- | --- |
| `test_jobs.QueueTests.test_two_worker_processes_never_run_two_heavy_jobs` | queue completion timed out; never reached `succeeded`/`partial` |
| `test_video_frames.FrameTests.test_video_track_can_end_before_container_audio` | `AssertionError: 'failed' not found in ('succeeded', 'partial')` — native document helper could not process the source |

The discrepancy is also recorded in
[`docs/audit/CURRENT_ARCHITECTURE.md`](../../audit/CURRENT_ARCHITECTURE.md)
sections 9 and 13. Do not discard this file.