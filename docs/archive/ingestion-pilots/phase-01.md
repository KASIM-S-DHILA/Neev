# Phase 1: Desktop workspace

## Scope and independence

This is the historical Phase 1 report. After Phase 2 integration, launching the app or desktop smoke also requires the Python environment described in README. Pure session tests remain independently runnable. SQLite now owns persistence; Materials now imports originals. Use the Phase 2 guide for current storage/recovery acceptance checks.

Run entirely offline after dependencies are installed. No service, upload, inference provider, database, or search engine is required. Probability, Linear Algebra and Data Structures are explicitly demo curriculum. Conditional Probability has authored demo content, not uploaded-source evidence.

## Automated checks

```sh
npm run check
npm run smoke:desktop
```

`check` runs session behavior checks, TypeScript validation and a production bundle. `smoke:desktop` starts a hidden production Electron window and requires the Workspace renderer, no renderer `require`, and the restricted window bridge. Native window interaction is also checked manually below.

## Manual acceptance checklist

1. Start with `npm run dev`. The Workspace and one New Tab appear.
2. Open Probability, then Conditional Probability. Compare the header, tabs, sidebar, spacing, formula panel and reading surface to PDF pages 1 and 2. No lock icons or fabricated mastery progress should appear.
3. Open Ask; type a draft. Press Ctrl+T. A quiet Workspace opens; return to the old tab and confirm the topic and draft are intact.
4. Close an inactive tab, then the active tab. Close the final tab: a new Workspace tab remains. Try opening more than 12 tabs: a clear limit notice appears.
5. Create a subject and a topic. Blank and duplicate names are rejected; Enter submits, Escape closes, and keyboard focus remains visible.
6. Mark the sample lesson as read. Its reading count changes, but mastery remains Not assessed. Every other topic remains accessible.
7. Close/reopen the app. Subjects, tabs, reading flags, sidebar preference and drafts return. Browser preview has a separate session.
8. Toggle the sidebar; inspect at 1366x768 and around 800x600. Main content scrolls internally; ordinary text is not horizontally clipped.
9. Check window minimize/maximize/restore/close in Electron. These controls are disabled in the browser preview.
10. Open Materials, Practice and Today. They must disclose future availability and must not fake upload, AI, grading or scheduling success.
11. Inspect the question draft view against PDF page 3 and Workspace against page 4. One composer, no permanent support drawer, and consistent contextual navigation.

## Recovery check

In a browser preview's developer tools, set `studylens.session.v1` to invalid JSON and reload. A recovery notice and fresh Workspace should appear without a crash. The automated tests also cover duplicate/dangling references and unsupported sessions.

## Results

Verified on September 30, 2026:

- 7/7 automated session checks passed, including tab isolation, closing the final tab, corruption recovery, reference validation, Unicode drafts and the tab cap.
- TypeScript validation and production Vite build passed.
- Dependency lockfile validation passed with `npm ci --dry-run --ignore-scripts --offline --cache .npm-cache`; no reinstall was performed by this check.
- Hidden production Electron startup passed: Workspace rendered, Node `require` was absent from the renderer, and the restricted preload bridge was present.
- Browser interaction checks passed: new tabs open Workspace; drafts survive tab switching/reload; duplicate subject names are rejected; custom subjects and topics survive reload; reading completion changes without changing mastery.
- Workspace and subject views were visually inspected in the in-app browser at its available viewport (approximately 899x505, then 841x505). The viewport override did not take effect in this browser; exact 1366x768 desktop comparison remains a manual acceptance item.
- Browser screenshot: [Workspace preview](screenshots/phase-01-workspace-browser.jpg).

Native drag/minimize/maximize/restore and keyboard-shortcut interaction still require manual desktop verification. The environment's hidden-window screenshot compositor returned `UnknownVizError`; this is recorded separately from the passing renderer startup/isolation checks. Browser screenshots provide the available visual evidence. No 8 GB performance claim has been made.

## Limits

Session storage is a Phase 1 cache, not durable source storage. No real ingestion, generated answers, assessments, mastery estimates or schedules exist yet. A packaged installer and 8 GB performance qualification belong to Phase 19. No native GPU acceleration is required by this phase.
