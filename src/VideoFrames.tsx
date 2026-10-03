import { useEffect, useState } from "react";
import { timestamp } from "./AudioTranscript";
import { CloudTranscription } from "./VisualExtraction";
import { storageClient, type VideoFramePage } from "./storage/client";

export function VideoFrames({workspaceId, versionId, seek, seekAvailable}: {workspaceId: string; versionId: string; seek: (seconds: number) => void; seekAvailable: boolean}) {
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState<VideoFramePage | null>(null);
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const load = async () => {
      try {
        const value = await storageClient.videoFrames(workspaceId, versionId, offset);
        if (cancelled) return;
        setPage(value);
        setError("");
        if (["queued", "running"].includes(value.job?.state ?? "") || ["queued", "running"].includes(value.visual_job?.state ?? "")) timer = setTimeout(() => void load(), 2000);
      } catch (cause) {
        if (!cancelled) setError(cause instanceof Error ? cause.message : "Frames could not be loaded.");
      }
    };
    void load();
    return () => {cancelled = true; clearTimeout(timer);};
  }, [open, workspaceId, versionId, offset, refresh]);
  const busy = working || ["queued", "running"].includes(page?.job?.state ?? "") || ["queued", "running"].includes(page?.visual_job?.state ?? "");
  async function process() {
    setWorking(true);
    try {
      await storageClient.processVideoFrames(workspaceId, versionId);
      setOffset(0);
      setRefresh(value => value + 1);
    } catch (cause) {setError(cause instanceof Error ? cause.message : "Frame selection could not start.");}
    finally {setWorking(false);}
  }
  async function processVisuals() {
    setWorking(true);
    try {
      await storageClient.processFrameVisuals(workspaceId, versionId);
      setRefresh(value => value + 1);
    } catch (cause) {setError(cause instanceof Error ? cause.message : "Frame text processing could not start.");}
    finally {setWorking(false);}
  }
  return <details className="video-frames" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Selected frames{page ? ` · ${page.total}` : ""}</summary>
    {open && <>
      <p className="small-text">From sampled video frames · Click a timestamp to seek. Text and speech are unverified; compare with the original. One-second sampling can miss brief changes.</p>
      {!seekAvailable && <p className="small-text">In-app playback is unavailable; open the saved original at these timestamps.</p>}
      {error && <p className="material-message error" role="alert">{error}</p>}
      {page?.job?.error && <p className="material-message error">{page.job.error}</p>}
      {page?.visual_job?.error && <p className="material-message error">{page.visual_job.error}</p>}
      {busy && <p className="small-text" role="status">{["queued", "running"].includes(page?.visual_job?.state ?? "") ? page?.visual_job?.stage : page?.job?.stage ?? "Starting frame selection…"} · Saved results remain available.</p>}
      {Number(page?.job?.result?.omitted_candidates ?? page?.job?.checkpoint?.omitted ?? 0) > 0 && <p className="content-warning">The frame budget skipped some changed candidates. Review the original for missing steps.</p>}
      {Number(page?.job?.result?.empty_windows ?? page?.job?.checkpoint?.empty_windows ?? 0) > 0 && <p className="content-warning">Some video intervals had no decoded frames. The video track may end before its audio; compare with the original.</p>}
      {!page && !error && <p className="small-text">Loading selected frames…</p>}
      {!!page && !page.frames.length && <p className="small-text">No saved frames on this page yet.</p>}
      <div className="video-frame-grid">
        {page?.frames.map(frame => <figure key={frame.id}>
          {frame.asset.data_url ? <img src={frame.asset.data_url} alt={`Selected source frame at ${timestamp(frame.seconds)}`} /> : <p className="content-warning">{frame.asset.error}</p>}
          <figcaption><button className="text-button" disabled={!seekAvailable} onClick={() => seek(frame.seconds)} aria-label={`Seek frame at ${timestamp(frame.seconds)}`}>{timestamp(frame.seconds)}</button>
            <span className="small-text">{frame.reasons.includes("sampled_scene_change") ? "Scene change" : frame.reasons.includes("visual_change") ? "Visual update" : "Reference frame"} · {frame.visual ? "Text review" : "OCR pending"}</span></figcaption>
          {frame.visual && <details>
            <summary>Frame text · unverified</summary>
            <p className="small-text">Local Tesseract{frame.visual.ocr.language ? ` · ${frame.visual.ocr.language}` : ""}{frame.visual.ocr.mean_confidence != null ? ` · mean confidence ${Math.round(frame.visual.ocr.mean_confidence)}%` : ""}</p>
            {frame.visual.ocr.text ? <pre className="frame-extracted-text">{frame.visual.ocr.text}</pre> : <p className="small-text">No readable local text saved.</p>}
            {frame.visual.ocr.warning && <p className="content-warning">{frame.visual.ocr.warning}</p>}
            {frame.visual.cloud?.status === "complete" && frame.visual.cloud.extraction && <details>
              <summary>Groq transcription · unverified</summary>
              <CloudTranscription entry={{status: "complete", routing: frame.visual.routing,
                extraction: frame.visual.cloud.extraction}} expandedText />
            </details>}
            {frame.visual.cloud?.reason && <p className="small-text">{frame.visual.cloud.reason}</p>}
            {!!frame.nearby_audio?.length && <details><summary>Speech near this time · separate source</summary>
              {frame.nearby_audio.map(item => <p key={item.unit_id + item.start_seconds} className="small-text">{timestamp(item.start_seconds)}–{timestamp(item.end_seconds)} · {item.provider} · {item.text}</p>)}
            </details>}
          </details>}
        </figure>)}
      </div>
      <div className="video-frame-actions">
        <button className="text-button" disabled={!offset} onClick={() => setOffset(value => Math.max(0, value - 4))}>Previous frames</button>
        <span className="small-text">{page?.total ? `${offset + 1}–${Math.min(offset + 4, page.total)} of ${page.total}` : "0 frames"}</span>
        <button className="text-button" disabled={!page || offset + 4 >= page.total} onClick={() => setOffset(value => value + 4)}>Next frames</button>
        <button className="text-button" disabled={busy} onClick={() => void process()}>{page?.job ? "Select frames again" : "Select frames"}</button>
        <button className="text-button" disabled={busy || !page?.total || !["succeeded","partial"].includes(page.job?.state ?? "")} onClick={() => void processVisuals()}>{page?.visual_job ? "Read frame text again" : "Read frame text"}</button>
        <button className="text-button" onClick={() => setRefresh(value => value + 1)}>Refresh frames</button>
      </div>
      {!!page?.job && ["cancelled", "failed"].includes(page.job.state) && <button className="text-button" onClick={() => { void storageClient.retryJob(workspaceId, page.job!.id).then(() => setRefresh(value => value + 1)).catch(cause => setError(cause.message)); }}>Resume frame selection</button>}
      {!!page?.visual_job && ["cancelled", "failed"].includes(page.visual_job.state) && <button className="text-button" onClick={() => { void storageClient.retryJob(workspaceId, page.visual_job!.id).then(() => setRefresh(value => value + 1)).catch(cause => setError(cause.message)); }}>Resume frame text</button>}
    </>}
  </details>;
}
