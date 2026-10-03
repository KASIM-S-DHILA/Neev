import { useRef } from "react";
import type { ContentUnit } from "./storage/client";

export function timestamp(seconds: number) {
  const whole = Math.floor(seconds);
  const hours = Math.floor(whole / 3600);
  return (hours ? `${hours}:` : "") + `${Math.floor(whole / 60) % 60}`.padStart(2, "0") + ":" + `${whole % 60}`.padStart(2, "0");
}

export function AudioTranscript({ unit }: { unit: ContentUnit }) {
  const player = useRef<HTMLAudioElement>(null);
  const start = unit.locator.kind === "time" ? unit.locator.start_seconds : 0;
  return <div className="audio-transcript">
    <p className="small-text">{unit.metadata.speech?.provider === "groq" ? "Transcribed by Groq" : unit.metadata.speech?.provider === "none" ? "No speech detected" : "Transcribed on this device"}{unit.metadata.speech?.cached ? " · Saved transcript reused" : ""} · Unverified</p>
    {unit.metadata.audio?.data_url ? <audio ref={player} controls preload="metadata" src={unit.metadata.audio.data_url}
      aria-label={`Source audio from ${timestamp(start)}`} /> : <p className="content-warning">{unit.metadata.audio?.error || "Audio preview unavailable."}</p>}
    {unit.metadata.segments?.length ? unit.metadata.segments.map((segment, index) => <div className="audio-segment" key={index}>
      <button className="text-button" disabled={!unit.metadata.audio?.data_url} aria-label={`Seek to ${timestamp(segment.start_seconds)}`}
        onClick={() => { if (player.current) player.current.currentTime = Math.max(0, segment.start_seconds - start); }}>{timestamp(segment.start_seconds)}</button>
      <p>{segment.text}</p>
    </div>) : <p className="content-no-text">No speech recognized. Listen to this interval to check for missed speech.</p>}
  </div>;
}
