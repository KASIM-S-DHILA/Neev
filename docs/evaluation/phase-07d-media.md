# Phase 7D-2 — student-supplied local media and YouTube review

October 3, 2026. This is an independently evaluated checkpoint after [caption import](phase-07d-youtube.md) and [uploaded-video frame extraction](phase-07c.md). It adds a route for a video file the student can use without acquiring YouTube audiovisual bytes inside Neev.

## Student flow and data

1. Import a YouTube link and its available captions in Materials.
2. Add a permitted local video file as a separate Material in the same subject. Its original, SHA-256, source version and background audio/frame/visual jobs use the existing uploaded-video pipeline.
3. Open **Review YouTube source → Local video copy**, choose the saved video version, and enter the YouTube time that corresponds to local 00:00. The example offset 60 maps a caption at 01:05.5 to local 00:05.5.
4. Review caption cues in the on-demand YouTube player or the browser fallback, and open the local copy at mapped times. The player iframe is created only after a click and removed on Close.

The association is append-only in `youtube_media_links`. It records the selected caption version, video version, offset and creation time. The latest association applies to the YouTube source across caption refreshes. Detaching appends a new null association; it does not delete the video original or previous association rows. Its provenance is `student_supplied_local_copy` with `match_verified: false`. Caption text and local video output stay separate and unverified. The interface does not call them combined visual coverage.

The stored original remains in the existing `originals` tree under the existing `%APPDATA%/StudyLens` profile. The API rehashes the local video before association. Scope checks require the same workspace and subject and a video source version. A link-only caption source can still be associated without inventing caption text. The existing worker owns video processing, cancellation and restart; the link has no new heavy job and does not alter those checkpoints.

## Evaluation

| Gate | Result |
| --- | --- |
| `npm.cmd run youtube:media:test` | 2 focused contracts passed: immutable originals, caption versions, cold restart, offset/provenance, idempotent attach/detach history, workspace/type/offset/integrity rejection. |
| `npm.cmd run youtube:test` | Earlier 13 caption-import contracts passed after this change. |
| `npm.cmd run check` | 15 JavaScript checks and TypeScript/Vite production build passed. |
| Production Electron | `node_modules\\.bin\\electron.cmd scripts\\evaluate-youtube-media-desktop.cjs tmp\\youtube-integration-20261003-083018` passed using authored caption/video fixtures. It verified click-to-create iframe URL, iframe removal, browser fallback, UI attachment and 01:05.5 → 00:05.5 local playback seek. See `youtube-media-desktop.json` and `screenshots/youtube-media-desktop.png`. |
| `npm.cmd run api:test` | 165 service tests passed in 160.097 s. Disposable retrograde-migration fixtures were updated to drop the new table before replaying old migrations. Log: `tmp/phase-07d-media-service-tests.log`. |
| `npm.cmd run smoke:desktop` | Built Electron started with SQLite WAL, schema `0005_youtube_media_links`, supervised single heavy worker, isolated IPC bridge and existing source-review checks. |

All test inputs were authored or saved evaluation fixtures. The native check did not treat an iframe URL as proof that YouTube delivered playable video. It captured external browser launches rather than opening a real browser. No YouTube audiovisual bytes were downloaded by the implementation or these tests. No Groq call was needed for the association checkpoint; linked local copies use the already evaluated uploaded-video OCR/vision job.

## Policy and remaining checks

[YouTube API Services Developer Policies](https://developers.google.com/youtube/terms/developer-policies) restrict downloading or caching audiovisual content without prior written approval. Downloading it temporarily and deleting it after extraction still performs the download. Neev therefore accepts a student-supplied permitted local file and offers on-demand online viewing through an embedded YouTube player with a canonical browser fallback. This checkpoint does not claim that a student declaration alone verifies acquisition permission or media identity.

Student manual checks remain: play an embeddable video in the built Electron app, try a video with embedding disabled or removed, compare local/remote timing and visual events on a natural lecture, cancel/restart local video frame/visual processing, and observe responsiveness on an 8 GB laptop. Browser fallback should be checked in a real browser. A source-aware combined citation/retrieval view is a later checkpoint.

The first full run exposed the outdated retrograde-migration fixtures and failed 3 test bodies (plus their teardown errors). After correcting those fixtures, the full 165-test run passed. The two focused contracts were rerun after the final cold-restart assertion. These automated results do not establish student acceptance or 8 GB performance.
