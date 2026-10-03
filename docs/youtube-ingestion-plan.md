# YouTube source ingestion — Phase 7 extension

Research date: October 3, 2026. This document records the original plan. **7D-1 link/caption ingestion is now implemented**, ahead of frame OCR at the student's request; see the [implementation and measured results](evaluation/phase-07d-youtube.md). The pinned caption reader is installed, a live public lecture import passed, and production Electron review was checked. Media acquisition and embedded playback remain planned. Playback currently opens the system browser at a source timestamp.

## Student flow

Materials → Add YouTube link → select subject/topic and available caption language → Import. The import action authorizes access to that submitted source. It does not authorize searching for more videos, crawling related videos or importing a playlist. Start with one completed video per import; playlist selection and live streams come later.

Show coverage explicitly: **Transcript available**, **Visuals processed**, or **Link only**. Captions alone do not establish what is shown in slides, tables or demonstrations. Do not mark caption-only ingestion as fully multimodal.

## Caption path

Candidate: the free, unofficial [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api/blob/master/README.md). It retrieves manual/generated caption tracks, language metadata and timed snippets without a headless browser. Prefer an original-language manual track when available, otherwise clearly label generated captions. Keep source-language captions separate from any translated explanation. The library documents RequestBlocked/IpBlocked failures; desktop operation is not a guarantee against blocking. Do not add proxy subscriptions or browser-cookie extraction as an automatic dependency.

Store raw caption snapshot plus normalized timed segments, video ID/canonical URL, language, manual/generated/translated flags, import time and extraction version. Normalize rolling caption duplicates without losing words/times; caption overlaps are not automatically invalid. Preserve original timings and any selected-range offset. Hash caption snapshots and create new versions on refresh; a caption hash is not a video-file hash. Remote video edits can make old timestamps differ from current playback.

The [official captions.download API](https://developers.google.com/youtube/v3/docs/captions/download) requires OAuth and permission to edit the video. An API key alone does not provide arbitrary public-lecture transcripts. Official authorized caption export or student-supplied SRT/VTT remains an alternative when public fetching is unavailable or unsuitable.

## Full media path

Candidate: [yt-dlp](https://github.com/yt-dlp/yt-dlp), a free open source adapter supporting subtitles and audio/video acquisition. Use only an appropriate permitted source route. Technically, acquired media could enter our existing FFprobe/FFmpeg audio pipeline and the planned scene/frame pipeline. Choose bounded processing quality, preserve original timestamps and recover partial downloads, then publish a saved version only after integrity checks. Size estimates are not a substitute for enforcing actual byte/duration/disk limits.

Current full YouTube support needs yt-dlp-ejs plus a supported JavaScript runtime. [The EJS guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS) supports Node >=22 when explicitly enabled. The development checkout has Node 24; installer packaging must supply or discover a compatible executable. Electron's embedded Node runtime is not automatically a standalone Node executable. Pin and update yt-dlp/EJS together; downloading never silently updates runtime code.

Technical downloader availability does not establish permission to download. [YouTube API developer policies](https://developers.google.com/youtube/terms/developer-policies) restrict audiovisual downloading/caching without prior written approval, separation of components, and scraping YouTube applications. Evaluate the acquisition route before shipping an automatic downloader. A public URL or a student's ownership declaration alone does not settle platform permission. Creator-provided media from a permitted source, uploaded by the student, is the straightforward full-ingestion fallback. The unofficial caption path also needs platform-policy review; it is not an official API integration.

## Playback and citations

Use the [official IFrame Player API](https://developers.google.com/youtube/iframe_api_reference) for online playback and seeking to source timestamps; provide an Open on YouTube timestamp link when embedding fails. The official player supports seekTo and reports embedding/unavailable errors, including 153 for missing Referer/equivalent client identification. Test Electron's production origin/client identity, not only Vite. Keep third-party playback isolated from the privileged preload bridge. Embedding does not supply decoded frames to our OCR pipeline.

Caption-derived knowledge can be stored locally, subject to applicable retention requirements, while online video playback requires network access. Saved transcript availability must not imply offline video playback or permanent remote-video availability. Missing captions can leave a link-only source until the student adds a transcript or permitted media copy. There is no automatic Groq transcription without an acquired audio source.

## Backend design

- Parse only supported YouTube HTTPS URL forms; canonicalize the video ID and strip unrelated tracking parameters. Do not turn the importer into an arbitrary URL fetcher.
- Run fetching/downloading in background workers with time/output/disk bounds and cancellation. Cache legitimate completed caption snapshots; cap retries on transient errors.
- Deduplicate by video ID, track/language and workspace source association. Sharing an identical cache payload must not expose another workspace's source records.
- Track independent fetch, transcript, frames and visual-extraction checkpoints. A failure in one path preserves completed results in the others.
- Retain external-source provenance; generated captions and ASR are unverified and are not promoted to reliable grounding by successful import.

## Independently evaluable checkpoints

**7D-1: Link and transcript.** Fixtures for URL forms, generated/manual captions, Hindi/English tracks, overlapping/rolling captions, missing captions, blocked requests, invalid timings, duplicates, workspace isolation and cancellation. Online playback/seek checked separately with a public lecture; never fabricate success for unavailable captions.

**7D-2: Permitted media acquisition.** Small controlled source with explicit availability/permission; check partial download, expired media links, byte limits, cancellation/restart, original integrity and timestamp offsets before connecting to Groq.

**7D-3: Full review.** Connect the acquired media to Phase 7 audio/frame extraction. Compare against manually marked lecture events and preserve a visible distinction between transcript-only and visual coverage. Test production Electron embedding and remote deletion/embedding-disabled failures.

Recommended prototype sequence: finish uploaded-video checkpoints 7A–7C, then implement the YouTube link/transcript checkpoint. Treat the caption reader and downloader as replaceable acquisition adapters; the downstream content-unit contracts remain shared.
