import { Check, RefreshCw, X } from "lucide-react";
import type { Job } from "./storage/client";
import type { useImports } from "./storage/useImports";
import type { useJobs } from "./storage/useJobs";

function jobStatus(job: Job) {
  if (job.cancel_requested && job.state === "running") return "Stopping…";
  if (job.state === "succeeded")
    return job.kind === "queue_fixture"
      ? "Test complete"
      : job.kind === "extract_source"
        ? "Text extracted"
        : job.kind === "cloud_visuals" ? "Visuals processed" : job.kind === "video_frames" ? "Frames selected" : job.kind === "video_frame_visuals" ? "Frame text saved · review needed" : job.kind === "youtube_import" ? "YouTube captions saved" : "Original checked";
  if (job.state === "partial") return "Some content needs review";
  if (job.state === "queued")
    return ["Waiting for Groq quota", "Waiting for Groq audio quota", "Pacing Groq audio requests", "Retrying visual output", "Retry scheduled"].includes(job.stage) ? job.stage : "Waiting";
  if (job.state === "cancelled") return "Cancelled";
  if (job.state === "failed") return "Needs attention";
  return job.stage;
}
export function JobPanel({
  queue,
  imports,
}: {
  queue: ReturnType<typeof useJobs>;
  imports: ReturnType<typeof useImports>;
}) {
  const active = queue.jobs.filter(
    (job) => job.state === "running" || job.state === "queued",
  );
  const attention = queue.jobs.some(
    (job) => job.state === "failed" || job.state === "partial",
  );
  const running = active.filter((job) => job.state === "running").length;
  const waiting = active.length - running;
  return (
    <>
      {(imports.state.busy || imports.state.message || imports.state.error) && (
        <div
          className={`notice import-notice ${imports.state.error ? "import-error" : ""}`}
          role="status"
        >
          <span>
            {imports.state.busy
              ? imports.state.progress
              : imports.state.error || imports.state.message}
          </span>
          {imports.state.busy ? (
            <button className="text-button" onClick={imports.manager.cancel}>
              Cancel import
            </button>
          ) : (
            <button
              className="icon-button"
              aria-label="Dismiss import result"
              onClick={imports.manager.dismiss}
            >
              <X size={13} />
            </button>
          )}
        </div>
      )}
      {queue.error && (
        <div className="notice" role="alert">
          <span>{queue.error}</span>
          <button className="text-button" onClick={() => void queue.refresh()}>
            Retry connection
          </button>
        </div>
      )}
      {!!queue.jobs.length && (
        <details className="job-panel" data-testid="job-panel">
          <summary>
            <span>Background work</span>
            <span>
              {active.length
                ? [
                    running ? `${running} running` : "",
                    waiting ? `${waiting} waiting` : "",
                  ]
                    .filter(Boolean)
                    .join(" · ")
                : attention
                  ? "Needs attention"
                  : "Up to date"}
            </span>
          </summary>
          <div className="job-list">
            {queue.jobs.map((job) => (
              <div key={job.id} className={`job-row ${job.state}`}>
                <div className="job-info">
                  <strong>{job.label}</strong>
                  <span>
                    {jobStatus(job)}
                    {job.recoveries ? " · Resumed after interruption" : ""}
                  </span>
                  {(job.state === "running" || job.state === "queued") && (
                    <progress
                      value={job.done}
                      max={Math.max(1, job.total)}
                      aria-label={`Progress for ${job.label}`}
                    />
                  )}{" "}
                  {job.error && <p>{job.error}</p>}
                </div>
                {job.state === "running" || job.state === "queued" ? (
                  <button
                    className="text-button"
                    disabled={job.cancel_requested}
                    onClick={() => void queue.action("cancel", job.id)}
                  >
                    <X size={12} /> Cancel
                  </button>
                ) : ["extract_source", "video_frames", "video_frame_visuals", "youtube_import"].includes(job.kind) && job.state === "partial" ? (
                  <span className="small-text">Review in Materials</span>
                ) : ["failed", "cancelled", "partial"].includes(job.state) ? (
                  <button
                    className="text-button"
                    onClick={() => void queue.action("retry", job.id)}
                  >
                    <RefreshCw size={12} /> Resume
                  </button>
                ) : (
                  <Check size={14} />
                )}
              </div>
            ))}
          </div>
          <p className="small-text">
            One heavy job at a time. Saved jobs resume when you reopen
            Neev. Latest 50 jobs shown.
          </p>
        </details>
      )}
    </>
  );
}
