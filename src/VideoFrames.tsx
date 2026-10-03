import { useEffect, useState } from "react";
import { timestamp } from "./AudioTranscript";
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
        if (["queued", "running"].includes(value.job?.state ?? "")) timer = setTimeout(() => void load(), 2000);
      } catch (cause) {
        if (!cancelled) setError(cause instanceof Error ? cause.message : "Frames could not be loaded.");
      }
    };
    void load();
    return () => {cancelled = true; clearTimeout(timer);};
  }, [open, workspaceId, versionId, offset, refresh]);
  const busy = working || ["queued", "running"].includes(page?.job?.state ?? "");
  async function process() {
    setWorking(true);
    try {
      await storageClient.processVideoFrames(workspaceId, versionId);
      setOffset(0);
      setRefresh(value => value + 1);
    } catch (cause) {setError(cause instanceof Error ? cause.message : "Frame selection could not start.");}
    finally {setWorking(false);}
  }
  return <details className="video-frames" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Selected frames{page ? ` · ${page.total}` : ""}</summary>
    {open && <>
      <p className="small-text">From the entire video · Click a timestamp to seek. On-screen text has not been extracted. One-second sampling can miss brief changes.</p>
      {!seekAvailable && <p className="small-text">In-app playback is unavailable; open the saved original at these timestamps.</p>}
      {error && <p className="material-message error" role="alert">{error}</p>}
      {page?.job?.error && <p className="material-message error">{page.job.error}</p>}
      {busy && <p className="small-text" role="status">{page?.job?.stage ?? "Starting frame selection…"} · Saved frame windows remain available.</p>}
      {Number(page?.job?.result?.omitted_candidates ?? page?.job?.checkpoint?.omitted ?? 0) > 0 && <p className="content-warning">The frame budget skipped some changed candidates. Review the original for missing steps.</p>}
      {Number(page?.job?.result?.empty_windows ?? page?.job?.checkpoint?.empty_windows ?? 0) > 0 && <p className="content-warning">Some video intervals had no decoded frames. The video track may end before its audio; compare with the original.</p>}
      {!page && !error && <p className="small-text">Loading selected frames…</p>}
      {!!page && !page.frames.length && <p className="small-text">No saved frames on this page yet.</p>}
      <div className="video-frame-grid">
        {page?.frames.map(frame => <figure key={frame.id}>
          {frame.asset.data_url ? <img src={frame.asset.data_url} alt={`Selected source frame at ${timestamp(frame.seconds)}`} /> : <p className="content-warning">{frame.asset.error}</p>}
          <figcaption><button className="text-button" disabled={!seekAvailable} onClick={() => seek(frame.seconds)} aria-label={`Seek frame at ${timestamp(frame.seconds)}`}>{timestamp(frame.seconds)}</button>
            <span className="small-text">{frame.reasons.includes("sampled_scene_change") ? "Scene change" : frame.reasons.includes("visual_change") ? "Visual update" : "Reference frame"} · OCR pending</span></figcaption>
        </figure>)}
      </div>
      <div className="video-frame-actions">
        <button className="text-button" disabled={!offset} onClick={() => setOffset(value => Math.max(0, value - 4))}>Previous frames</button>
        <span className="small-text">{page?.total ? `${offset + 1}–${Math.min(offset + 4, page.total)} of ${page.total}` : "0 frames"}</span>
        <button className="text-button" disabled={!page || offset + 4 >= page.total} onClick={() => setOffset(value => value + 4)}>Next frames</button>
        <button className="text-button" disabled={busy} onClick={() => void process()}>{page?.job ? "Select frames again" : "Select frames"}</button>
        <button className="text-button" onClick={() => setRefresh(value => value + 1)}>Refresh frames</button>
      </div>
      {!!page?.job && ["cancelled", "failed"].includes(page.job.state) && <button className="text-button" onClick={() => { void storageClient.retryJob(workspaceId, page.job!.id).then(() => setRefresh(value => value + 1)).catch(cause => setError(cause.message)); }}>Resume frame selection</button>}
    </>}
  </details>;
}
