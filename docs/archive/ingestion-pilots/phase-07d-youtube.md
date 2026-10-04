# Phase 7D-1 — YouTube links and timed captions

Date: October 3, 2026. Implemented at the student's request ahead of video-frame OCR. This checkpoint imports link/caption sources into Materials; full YouTube media acquisition is not implemented.

## Student flow

1. **Materials → Add YouTube link**. Paste one HTTPS video link, optionally name it, and enter a caption language: `en`, `hi`, or another track code.
2. **Import captions** queues background work. Manual captions in that language are preferred over auto-generated captions. The submitted video is the only source accessed; related videos and playlists are not crawled.
3. Expand the saved source and choose **Review YouTube source**. Read saved intervals and use timestamps or **Watch on YouTube** to open the system browser. Watching requires internet; saved text does not.
4. **Available caption languages** lets the student import another original track. No automatic translation is applied. **Refresh captions** requests a new snapshot; changed captions become a new version while identical snapshots reuse the saved version.
5. **Save snapshot** exports the immutable JSON, rather than implying that the video itself is stored. **Check snapshot** verifies its bytes.

Caption-only material is explicitly labelled **Transcript only · Visuals not processed**. All caption units are unverified (`suspect`, review required), including manual tracks. This preserves the distinction between byte integrity and content correctness. Missing/blocked captions produce **Link only**, with a reason and zero knowledge units. Earlier caption versions stay accessible if a later fetch is unavailable.

## Implementation

- `youtube-transcript-api==1.2.4`, with pinned requests dependencies in the project virtual environment. No API key, proxy subscription, browser-cookie extraction, new speech/vision weights or media downloader.
- A `youtube_import` job runs in the existing single worker. The network helper is a cancellable, bounded child; it never runs on the Electron renderer/main event loop or API event loop.
- Supported input forms: `/watch?v=`, `youtu.be/`, `/shorts/`, `/embed/`, `/live/`, plus the standard/mobile YouTube hosts. Canonicalization strips tracking, timestamps and playlist parameters when an individual video ID is present. Channel/playlist-only links, duplicate `v` parameters, arbitrary hosts, HTTP, credentials and explicit ports are rejected.
- Network requests/redirects are restricted to HTTPS YouTube/consent endpoints. Per-request connect/read limits are 5/10 seconds; each response is capped at 8 MB decompressed. Child runtime/output bounds are 45 seconds/4 MB; Windows child and parent worker memory guards remain 512 MiB each. These are safety limits, not whole-app peak-memory measurements.
- Snapshot bounds: 4 MB UTF-8, 30,000 cues, 200 language tracks, 4,000 characters per cue, ordered finite nonnegative times, and four-hour timeline. Returned video identity and selected-track provenance must match.
- Snapshot SHA-256 describes caption/link JSON, not remote video bytes. Import time is the version creation time. No changing fetch timestamp is included in the hashed snapshot, allowing identical caption snapshots to deduplicate.
- Worker completion publishes source/version records and the verify/extract jobs in one transaction, after its cancellation check. A restart after saving a snapshot reuses its checksum-validated bytes without another network fetch. Cancelled unpublished imports cannot create a material record.
- Source association is scoped to workspace, subject, **case-sensitive** video ID and requested language. Caption content may reuse identical stored bytes, while source records remain scoped. Up to ten active YouTube imports wait per subject; repeated active requests reuse their queued job.
- The original verifier and extraction path recheck saved bytes. Offline extraction groups cues into bounded intervals, preserving overlapping/rolling timings and words. Only adjacent exact duplicate cues within a group are dropped; recurring speech remains.
- Native timestamp opening uses a restricted IPC action that accepts only canonical YouTube watch URLs and bounded numeric times. Third-party content is never loaded into a page with the privileged preload bridge. The original content-security policy remains in place.

## Evidence

| Gate | Result |
|---|---|
| Offline YouTube/adaptor contracts | 13 passed; URL boundaries, manual/generated language selection, overlap locations, Hindi, missing/blocked captions, snapshot dedup/versioning, case-sensitive IDs, workspace isolation, cancellation and snapshot/extraction restart |
| Service regression | 156 passed in 259.970 seconds; the final case-sensitive-ID refinement was checked again by the focused YouTube gate |
| JavaScript/TypeScript/Vite | 15 checks passed; includes native URL boundaries and distinct browser/API versus desktop/IPC request bodies; build passed |
| Dependencies | `pip check`: no broken requirements |
| Live import | Public lecture captions available, immutable snapshot verified; 16 source-time intervals |
| Production Electron | Import form and invalid-link error, live caption review, coverage labels, Hindi pagination, native timestamp URL and rejection of arbitrary external URLs passed |

The [live report](youtube-20261003-083018.json) records a real caption fetch for [The essence of calculus](https://www.youtube.com/watch?v=WUvTyaaNkzM). English manual captions were available; fetch, snapshot publication, verification and interval extraction took **2.828 seconds** on this developer laptop. This is one observed import, not a general speed guarantee or caption-accuracy benchmark. No video/audio was downloaded and Groq credentials were cleared for evaluation.

The [native report](youtube-desktop.json) and [visually inspected screenshot](screenshots/youtube-desktop.png) show production Electron review. The Hindi UI fixture is explicitly authored, not claimed to be actual captions of that lecture. The timestamp check captured the system-browser launch URL `https://www.youtube.com/watch?v=WUvTyaaNkzM&t=65`; it did not open a browser or prove remote-player seeking/playback. Actual browser opening/playback remains a manual check.

Initial focused testing exposed a test-cleanup handle ordering error on Windows, corrected by closing the SQLite worker before deleting temporary test data. The native harness initially attempted to serialize a DOM element from a wait expression; boolean wait results corrected it. Neither failure was a successful caption import claim.

## Remaining boundaries

YouTube may block access, disable captions, remove videos or change remote timing. No authentication/proxy workaround is installed. Playlists, real-time live-stream capture, automatic translation, embedded IFrame playback, media downloading, Groq ASR for captionless links and visual-frame extraction of linked videos are not part of this checkpoint. Use an uploaded permitted media copy for the existing audio/frame pipeline.

The [caption reader documentation](https://github.com/jdepoix/youtube-transcript-api/blob/master/README.md) describes this unofficial acquisition method and its blocking/authentication limitations. The [original plan](../../youtube-ingestion-plan.md) retains the official API/platform-policy considerations for shipping and media acquisition. Successful retrieval does not constitute a policy review.

No reliable Hindi/Hinglish transcription claim, natural-video visual coverage claim, learning-gain claim or whole-app 8 GB measurement follows from these gates.

## Reproduce

```powershell
npm.cmd run api:install
npm.cmd run youtube:test
npm.cmd run check
npm.cmd run api:test
node scripts/python.mjs scripts/evaluate-youtube.py
node_modules/.bin/electron.cmd scripts/evaluate-youtube-desktop.cjs tmp/youtube-integration-20261003-083018
```

The live script creates fresh isolated data; pass its returned directory to the native script. Offline tests make no real network/Groq calls. Saved pilot data is retained under `tmp/` and excluded from source control.

## Manual checkpoint

Restart Electron. Import a video with available captions in your subject, review a few intervals and click a timestamp. Confirm the system browser opens the intended video near that time. Refresh and confirm unchanged captions reuse the version. Close/reopen the app and read saved captions. Try a captionless/inaccessible video and confirm the link-only status, no invented text, and preserved earlier versions. Continue navigating during fetching on the target 8 GB laptop.
