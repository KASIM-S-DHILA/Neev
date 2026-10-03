import { useRef, useState } from "react";
import { AudioTranscript, timestamp } from "./AudioTranscript";
import type { ContentUnit } from "./storage/client";
import { VideoFrames } from "./VideoFrames";

export function VideoTranscript({ unit, workspaceId, versionId }: { unit?: ContentUnit; workspaceId: string; versionId: string }) {
  const player = useRef<HTMLVideoElement>(null);
  const pendingSeek = useRef<number | null>(null);
  const [failed, setFailed] = useState(false);
  const start = unit?.locator.kind === "time" ? unit.locator.start_seconds : 0;
  const source = window.studyLens?.storage
    ? `studylens-media://original/${encodeURIComponent(workspaceId)}/${encodeURIComponent(versionId)}`
    : `/api/workspaces/${encodeURIComponent(workspaceId)}/source-versions/${encodeURIComponent(versionId)}/playback`;
  const seek = (seconds: number) => {
    pendingSeek.current = seconds;
    if (player.current) player.current.currentTime = seconds;
  };
  return <div className="video-transcript">
    <p className="small-text">{unit ? "Audio transcript only · Visual extraction is pending" : "Video playback · Transcript unavailable"}</p>
    {failed ? <>
      <p className="content-warning">Video playback is unavailable for this file. Save the original to open in another player, or export an H.264 MP4 copy.</p>
      {unit?.metadata.audio && <AudioTranscript unit={unit} />}
    </> : <>
      <video ref={player} controls preload="metadata" src={source} aria-label="Original source video"
        onLoadedMetadata={() => { if (player.current) player.current.currentTime = pendingSeek.current ?? start; }}
        onError={() => setFailed(true)} />
      {unit?.metadata.speech && <p className="small-text">{unit.metadata.speech.provider === "groq" ? "Transcribed by Groq" : unit.metadata.speech.provider === "none" ? "No speech detected" : "Transcribed on this device"} · Unverified</p>}
      {unit?.metadata.segments?.map((segment, index) => <div className="audio-segment" key={index}>
        <button className="text-button" aria-label={`Seek video to ${timestamp(segment.start_seconds)}`}
          onClick={() => seek(segment.start_seconds)}>{timestamp(segment.start_seconds)}</button>
        <p>{segment.text}</p>
      </div>)}
    </>}
    {unit?.metadata.video?.audio_present === false
      ? <p className="content-no-text">This video has no audio stream. You can watch the original; there is no audio transcript.</p>
      : !unit?.metadata.segments?.length && <p className="content-no-text">No saved speech in this interval. Review the video for missed speech.</p>}
    <VideoFrames key={`${workspaceId}:${versionId}`} workspaceId={workspaceId} versionId={versionId} seek={seek} seekAvailable={!failed} />
  </div>;
}
