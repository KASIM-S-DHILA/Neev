# Phase 3 acceptance — background work

Date: October 1, 2026. Scope: a durable queue, one heavy worker, progress, cancellation, bounded retries and recovery. No model, extraction library, internet access or large media file is required.

Manual acceptance update, October 1: the student confirmed the requested manual checks were done, with no issues reported. The checklist covered navigation/scrolling during a slow job, Cancel/Resume, closing/reopening during work, and cancellation of an unfinished import if not already checked. This is student-reported acceptance; no additional timings or memory measurements were supplied.

## Independent automated gate

After the README environment setup:

```powershell
npm.cmd run queue:test
npm.cmd run api:test
npm.cmd run check
npm.cmd run smoke:desktop
```

`queue:test` runs 16 queue checks against disposable databases and real child worker processes. `api:test` includes those 16 plus the 13 storage regression checks. `check` runs 13 JS checks, TypeScript and the production build. The hidden Electron smoke uses isolated data and verifies the production bridge, persisted session, SQLite WAL, migration `0002_background_jobs`, available worker, one-heavy-job limit and evaluation mode off.

Fixtures are authored synthetic byte strings and numbered slow units, including injected transient/permanent failures. They are not AI responses or evidence of student learning. The API responsiveness check uses a separate CPU/delay worker fixture and a broad two-second request bound; it does not establish interactive latency or memory usage on an 8 GB laptop.

## Recorded results

| Check | Result |
| --- | --- |
| Queue suite | 16 passed |
| Full Python suite | 29 passed |
| JS session, save and import coordination | 13 passed |
| TypeScript and production build | Passed |
| Hidden production Electron startup and worker | Passed; evaluation disabled |
| Two worker processes sharing a directory | Never more than one running heavy job |
| Queued/running cancel, explicit resume | Passed; originals retained |
| Abrupt worker kill and supervised restart | Passed; persisted fixture units recovered |
| Clean parent exit and reopen | Passed; unfinished job requeued |
| Transient failures and retry bound | Two failures then success; three failures stop |
| Permanent failure and damaged bytes | Actionable failure; no automatic retry |
| Phase 2 schema upgrade | Session/original preserved; missing job backfilled |
| Old orphan audit | Reported and retained; referenced bytes preserved |
| API responsiveness during worker activity | Passed with CPU/delay fixture |
| Import across component unmount; captured scope | Passed in JS coordination checks |
| Browser slow fixture, tab navigation, Cancel/Resume | Passed; resumed fixture completed |
| Browser notes import and original verification | Passed; Awaiting extraction displayed |
| Browser reload | Saved material and completed job history restored |

Visual evidence: [queue and checked original](screenshots/phase-03-materials-browser.png) and [production desktop](screenshots/phase-03-workspace-desktop.png). Electron needed execution outside the Windows AppContainer sandbox, as in Phase 2. Renderer sandboxing and Node isolation remained enabled.

## Repeat the manual queue flow

Close the app first, then launch an isolated evaluation instance from the project directory:

```powershell
$env:STUDYLENS_DATA_DIR = Join-Path $PWD 'tmp/phase03-manual'
$env:STUDYLENS_QUEUE_EVAL = '1'
npm.cmd start
```

This uses the completed build. For live changes use `npm.cmd run dev`; for a browser use `npm.cmd run dev:web`. Set the variables before launching; the existing desktop shortcut does not inherit variables from this PowerShell session.

1. In Settings, click **Run slow queue test**. It takes roughly ten seconds and is labeled **Queue test · no course processing**.
2. Expand **Background work**. Observe progress while opening a new study tab, navigating subjects and scrolling. The app should remain usable.
3. Start a second test while the first runs. Only one should run; the other waits. Cancel the waiting job, then cancel the running job. Confirm **Cancelled** and **Resume**.
4. Resume a cancelled job and wait for **Test complete**. No assessment or mastery status should change.
5. Start a fresh test and close StudyLens partway through. Reopen with the same environment/data directory. It should resume and finish; the drawer identifies interruption recovery.
6. Import `tests/fixtures/ingestion/phase-02-notes.txt` into a subject. Expect **Original checked · Awaiting extraction**. An unchanged duplicate should reuse its version. Expand the original and use **Check original** to run another integrity check.
7. During a larger file transfer, switch tabs/workspaces. The global import notice should remain, and the file should land in its original subject. Cancel an unfinished transfer; completed earlier files remain, and no partial version should appear.

After evaluation, remove the temporary launch overrides in that terminal:

```powershell
Remove-Item Env:STUDYLENS_QUEUE_EVAL
Remove-Item Env:STUDYLENS_DATA_DIR
```

## Recovery and practical limits

- Slow fixture units resume from saved unit boundaries. Interrupted integrity checking restarts the hashing stage because a SHA-256 digest state is not serialized. Files stay unchanged.
- Saved job progress survives app closure. File transfer before registration is not resumable; keep the app open until the original is saved. Cancelling a job does not remove its saved source.
- Reconciliation writes an audit of unreferenced files older than one hour to `reconciliation.json`; it retains them. Automatic garbage collection and a student-facing repair/export flow are later hardening work.
- The app displays the latest 50 jobs. Large-library pagination/virtualization and resource measurements remain later gates. No multi-GB import or 8 GB peak-memory benchmark was run for this phase.
- Future PDF/OCR/transcription/model work must reuse this worker boundary and demonstrate its own cancellation, unit checkpoints and subprocess cleanup. Current byte integrity success does not prove content can be decoded.
- Live browser cancellation/resume and import were checked. The student has now confirmed completion of the requested native manual checklist. Phase 2 desktop checks and the seamless 200 MB upload were already confirmed by the student. The steps above remain available for regression checks.

Phase 3 is accepted: its automated gate passes and the student has completed the manual checklist. Next: Phase 4 PDF/text ingestion and exact page locators.
