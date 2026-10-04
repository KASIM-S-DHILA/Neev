import type { Job } from "./storage/client";

/**
 * Human-readable job state.
 *
 * Kept free of JSX and in its own module so it is unit-testable: `node --test`
 * cannot load a `.tsx` file, and this is the wording a student reads when a job
 * is waiting on the cloud provider.
 *
 * A Deferred quota or pacing wait leaves the job `queued` with the wait stage
 * carried in `stage`. That stage must reach the student rather than collapsing
 * into a bare "Waiting", or a throttled job looks like a silent stall. Unknown
 * stages do collapse, so internal text never leaks into the UI.
 */
export function jobStatus(job: Job): string {
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

/** Stages that mean "waiting on a provider", shown verbatim to the student. */
export const VISIBLE_WAIT_STAGES = [
  "Waiting for Groq quota",
  "Waiting for Groq audio quota",
  "Pacing Groq audio requests",
  "Retrying visual output",
  "Retry scheduled",
] as const;