# Phase 2 acceptance — local service and storage

Date: September 30, 2026. Scope: persistence and original files. Evaluate without Ollama, Groq, SearXNG or an extraction pipeline.

Update, October 1: the student confirmed desktop controls, native file/version downloads, persistence/workspace isolation and the two-window conflict flow all worked. A 200 MB import completed seamlessly. These are student-reported manual results, not a measured 8 GB resource benchmark; a 2 GB file is not required to accept this milestone.

## Setup and independent gate

Follow the Python environment setup in the README, then run:

```powershell
npm.cmd run api:test
npm.cmd run check
npm.cmd run smoke:desktop
```

The Python gate creates disposable temporary databases and files. It does not read the student's data or invoke the UI. Tests use authored strings, a Unicode draft, synthetic file bytes and injected failures. The two browser fixtures in `docs/evaluation/fixtures/phase-02-notes*.txt` are authored evaluation notes, not retrieved course content.

## Recorded results

| Check                                                                      | Result                                           |
| -------------------------------------------------------------------------- | ------------------------------------------------ |
| Python storage suite                                                       | 13 passed                                        |
| JS session/save-coordination suite                                         | 10 passed                                        |
| TypeScript and Vite production build                                       | Passed                                           |
| Hidden Electron production startup, preload isolation, real storage health | Passed; WAL, schema `0001_local_storage`         |
| Create workspace and subject; isolation from default curriculum            | Passed in browser preview                        |
| Import original, duplicate upload, renamed file as explicit version 2      | Passed in browser preview                        |
| Original version 1 browser download                                        | Passed; SHA-256 matched fixture exactly          |
| Materials tab and both versions after browser reload                       | Passed after fixing query-before-hydration issue |

Python checks include CRUD, normalized references, Unicode, restart/migration, injected migration failure and recovery, WAL, workspace isolation, stale-save rejection, parallel version-number allocation, immutable originals, duplicate reuse, filename/type rejection, empty/oversize imports, injected disk failure, missing/damaged bytes and referential rollback. JS checks cover tab behavior plus serialized revision writes, coalescing, explicit retry and conflict stopping.

The browser-downloaded version 1 had SHA-256 `1fc6544355a9ca26f99e674bd05df3e32cd62c9c431264d9ed91ccbd0a1b9e98`, matching the checked-in fixture.

The final desktop smoke also confirmed `sessionPersisted: true` before capture. The live preview proxy returned 200 for local health access and 403 for a foreign Origin or `Sec-Fetch-Site: cross-site`.

Visual evidence: [saved original versions](screenshots/phase-02-materials-browser.jpg) and [ready desktop workspace](screenshots/phase-02-workspace-desktop.png). The desktop screenshot was inspected after storage hydration; it is separate from interactive native-window checks.

The initial sandboxed Electron attempt failed because of Windows AppContainer ACL restrictions on the Electron binary. Running the same smoke test outside that sandbox passed. No sandbox or renderer isolation setting was disabled. Starlette currently emits a TestClient/httpx deprecation warning; all assertions pass with the pinned environment.

## Repeat the manual flow

Use an isolated preview data directory as shown in the README. Launch only one Vite preview at a time (port 5173).

1. Create **Phase 2 evaluation** from the workspace selector. It should have zero subjects. Create **Storage lab**.
2. Add a topic and a question draft. Wait for **Saved on this device**, reload and verify both.
3. Open Materials and add `phase-02-notes.txt`. Expect version 1 and **Saved · Awaiting processing**.
4. Add that same file again. Expect one identical version already saved, with no second version.
5. Select **Add new version**, choose `phase-02-notes-v2.txt`. Expect one source with two versions.
6. Expand versions and save version 1. Compare bytes/hash with the fixture. Reload the page and restart the local service: both originals should remain listed.
7. Switch to another workspace. Its subjects/materials should be separate. Switching back should restore study tabs/drafts.
8. Start two app windows on the same data directory. After both load, edit one and then the stale window. Expect a save conflict, preserved recovery cache, and an explicit reload choice; no automatic overwrite.
9. During a large-file import, continue scrolling and cancel. No partial version should be registered. Files completed before cancellation remain. Phase 2 cancelled unfinished imports on leaving Materials; Phase 3 now keeps transfers active across tabs and offers global cancellation.

## Remaining manual checks and limits

- Desktop controls, native picker/version downloads and two-window conflict behavior passed the student's interactive checks. `.recovery` cache export currently requires developer tools.
- The student reported a seamless 200 MB import. Cancellation of an unfinished file transfer remains a manual check; multi-GB media is optional stress testing. No memory/latency benchmark or large-library performance claim is made.
- Service restart is covered by isolated API tests; browser reload was checked live. Phase 3 audits old orphan staging/blobs and retains them for review.
- Files are stored only. Corrupt-content detection, extraction, processing queues, citations and AI are later milestones. No delete API or UI exists yet.

Proceed to Phase 3 using the storage tests as the regression gate and a deterministic slow-job fixture for queue evaluation.
