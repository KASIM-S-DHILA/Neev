import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { timestamp } from "./AudioTranscript";
import { storageClient, type ExtractedContent, type Job, type SourceVersion } from "./storage/client";

export function YouTubeReview({workspaceId,subjectId,version,job,close}: {
  workspaceId:string; subjectId:string; version:SourceVersion; job?:Job; close:()=>void;
}) {
  const [content,setContent] = useState<ExtractedContent|null>(null);
  const [offset,setOffset] = useState(0);
  const [error,setError] = useState("");
  const [refreshing,setRefreshing] = useState(false);
  useEffect(()=>{
    let disposed=false;
    setContent(null);
    storageClient.content(workspaceId,version.id,offset).then(value=>{if(!disposed){setContent(value);setError("");}})
      .catch(cause=>{if(!disposed)setError(cause.message);});
    return ()=>{disposed=true;};
  },[workspaceId,version.id,offset,job?.state,job?.done]);
  const unit=content?.units[0];
  const source=content?.result?.youtube || unit?.metadata.youtube;
  async function open(seconds=0) {
    if(!source) return;
    try {await storageClient.openYouTube(source.url+"&t="+Math.floor(seconds));}
    catch(cause){setError(cause instanceof Error?cause.message:"Could not open YouTube.");}
  }
  async function refresh(language:string) {
    if(!source) return;
    setRefreshing(true);
    try {await storageClient.importYouTube(workspaceId,subjectId,source.url,language);setError("");}
    catch(cause){setError(cause instanceof Error?cause.message:"Could not refresh captions.");}
    finally{setRefreshing(false);}
  }
  return <section className="content-preview youtube-review" aria-label="YouTube source review" data-testid="youtube-review">
    <div className="content-preview-heading"><div><p className="eyebrow">YouTube · Version {version.version}</p><h2>Saved captions</h2></div>
      <button className="icon-button" aria-label="Close YouTube review" onClick={close}><X size={16}/></button></div>
    <p className="small-text">Captions are saved locally. Watching the source opens YouTube in your browser and requires internet. Remote video edits may change timestamps.</p>
    {error && <p className="material-message error" role="alert">{error}</p>}
    {content?.error && <p className="material-message error" role="alert">{content.error}</p>}
    {!content ? <p className="small-text">Loading saved captions…</p> : <>
      <p className="content-warning">{source?.coverage === "link_only" ? "Link only · No captions saved" : "Transcript only · Visuals not processed"}. Captions need comparison with the original video.</p>
      {!content.integrity_verified && <p className="content-warning">The saved snapshot has not passed its integrity check.</p>}
      {source?.issue && <p className="material-message" role="status">{source.issue}</p>}
      {source && <div className="youtube-source-actions">
        <button className="secondary" onClick={()=>void open()}>Watch on YouTube</button>
        <button className="text-button" disabled={refreshing} onClick={()=>void refresh(source.requested_language)}>Refresh captions</button>
        <span className="small-text">{source.language_code || source.requested_language} · {source.is_generated === true ? "Auto-generated" : source.is_generated === false ? "Manual captions" : "No selected track"}</span>
      </div>}
      {!!source?.tracks.length && <details className="content-provenance"><summary>Available caption languages</summary>
        <div className="youtube-source-actions">{source.tracks.map(track=><button className="text-button" key={track.language_code+track.is_generated} disabled={refreshing}
          onClick={()=>void refresh(track.language_code)}>{track.language} ({track.language_code}) · {track.is_generated ? "Auto" : "Manual"}</button>)}</div></details>}
      {unit && <>
        <div className="content-navigation">
          <button className="text-button" disabled={offset===0} onClick={()=>setOffset(value=>value-1)}>Previous interval</button>
          <span className="small-text">Interval {offset+1} of {content.total}</span>
          <button className="text-button" disabled={offset+1>=content.total} onClick={()=>setOffset(value=>value+1)}>Next interval</button>
        </div>
        <div className="youtube-captions">{unit.metadata.segments?.map((segment,index)=><div key={index} className="youtube-cue">
          <button className="text-button" aria-label={`Open YouTube at ${timestamp(segment.start_seconds)}`} onClick={()=>void open(segment.start_seconds)}>{timestamp(segment.start_seconds)}</button>
          <p>{segment.text}</p>
        </div>)}</div>
      </>}
      {!unit && !source?.issue && <p className="small-text">Captions are still being processed. Saved intervals will appear as background work completes.</p>}
    </>}
  </section>;
}
