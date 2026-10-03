import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { timestamp } from "./AudioTranscript";
import { storageClient, type ExtractedContent, type Job, type SourceVersion, type YouTubeMediaLink } from "./storage/client";

export function YouTubeReview({workspaceId,subjectId,version,job,videos,onOpenVideo,onAssociationChange,close}: {
  workspaceId:string; subjectId:string; version:SourceVersion; job?:Job;
  videos:{version:SourceVersion; displayName:string}[];
  onOpenVideo:(versionId:string,seconds:number)=>void; onAssociationChange:()=>void; close:()=>void;
}) {
  const [content,setContent] = useState<ExtractedContent|null>(null);
  const [offset,setOffset] = useState(0);
  const [error,setError] = useState("");
  const [refreshing,setRefreshing] = useState(false);
  const [media,setMedia] = useState<YouTubeMediaLink|null>(null);
  const [mediaVersion,setMediaVersion] = useState("");
  const [youtubeStart,setYoutubeStart] = useState("0");
  const [linking,setLinking] = useState(false);
  const [playerSeconds,setPlayerSeconds] = useState<number|null>(null);
  useEffect(()=>{
    let disposed=false;
    setContent(null);
    storageClient.content(workspaceId,version.id,offset).then(value=>{if(!disposed){setContent(value);setError("");}})
      .catch(cause=>{if(!disposed)setError(cause.message);});
    return ()=>{disposed=true;};
  },[workspaceId,version.id,offset,job?.state,job?.done]);
  useEffect(()=>{
    let disposed=false;
    storageClient.youtubeMedia(workspaceId,version.id).then(value=>{
      if(!disposed) {setMedia(value.media);setMediaVersion(value.media?.media_version_id ?? "");setYoutubeStart(String(value.media?.youtube_start_seconds ?? 0));}
    }).catch(cause=>{if(!disposed)setError(cause.message);});
    return ()=>{disposed=true;};
  },[workspaceId,version.id]);
  const unit=content?.units[0];
  const source=content?.result?.youtube || unit?.metadata.youtube;
  const embedId=source && /^[A-Za-z0-9_-]{11}$/.test(source.video_id) ? source.video_id : null;
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
  async function attachMedia() {
    if(!mediaVersion) return;
    setLinking(true);
    try {
      const value=await storageClient.attachYouTubeMedia(workspaceId,version.id,mediaVersion,Number(youtubeStart));
      setMedia(value.media);setError("");onAssociationChange();
    } catch(cause) {setError(cause instanceof Error?cause.message:"Could not attach the local video.");}
    finally {setLinking(false);}
  }
  async function detachMedia() {
    setLinking(true);
    try {
      const value=await storageClient.detachYouTubeMedia(workspaceId,version.id);
      setMedia(value.media);setMediaVersion("");setYoutubeStart("0");setError("");onAssociationChange();
    } catch(cause) {setError(cause instanceof Error?cause.message:"Could not detach the local video.");}
    finally {setLinking(false);}
  }
  return <section className="content-preview youtube-review" aria-label="YouTube source review" data-testid="youtube-review">
    <div className="content-preview-heading"><div><p className="eyebrow">YouTube · Version {version.version}</p><h2>Saved captions</h2></div>
      <button className="icon-button" aria-label="Close YouTube review" onClick={close}><X size={16}/></button></div>
    <p className="small-text">Captions are saved locally. Watching the source requires internet. Remote video edits may change timestamps.</p>
    {error && <p className="material-message error" role="alert">{error}</p>}
    {content?.error && <p className="material-message error" role="alert">{content.error}</p>}
    {!content ? <p className="small-text">Loading saved captions…</p> : <>
      <p className="content-warning">{source?.coverage === "link_only" ? "Link only · No captions saved" : "Transcript only · Visuals not processed"}. Captions need comparison with the original video.</p>
      {!content.integrity_verified && <p className="content-warning">The saved snapshot has not passed its integrity check.</p>}
      {source?.issue && <p className="material-message" role="status">{source.issue}</p>}
      {source && <div className="youtube-source-actions">
        {embedId && <button className="secondary" onClick={()=>setPlayerSeconds(0)}>Watch here</button>}
        <button className="text-button" onClick={()=>void open()}>Open on YouTube</button>
        <button className="text-button" disabled={refreshing} onClick={()=>void refresh(source.requested_language)}>Refresh captions</button>
        <span className="small-text">{source.language_code || source.requested_language} · {source.is_generated === true ? "Auto-generated" : source.is_generated === false ? "Manual captions" : "No selected track"}</span>
      </div>}
      {embedId && playerSeconds!==null && <div className="youtube-player">
        <div className="youtube-source-actions"><span className="small-text">YouTube player · {timestamp(playerSeconds)}</span>
          <button className="text-button" onClick={()=>setPlayerSeconds(null)}>Close player</button></div>
        <iframe key={playerSeconds} title="YouTube video player" src={`https://www.youtube-nocookie.com/embed/${embedId}?start=${Math.floor(playerSeconds)}`}
          loading="lazy" referrerPolicy="strict-origin-when-cross-origin" allow="autoplay; encrypted-media; picture-in-picture; web-share" allowFullScreen />
        <p className="small-text">If this video cannot play here, use Open on YouTube.</p>
      </div>}
      <details className="content-provenance">
        <summary>Local video copy{media ? ` · ${media.filename}` : ""}</summary>
        <p className="small-text">Add a video file you are permitted to use through Add material, then attach its saved version here. The file comes from your device. Its match to this YouTube link is for you to check.</p>
        {media && <div className="youtube-source-actions">
          <button className="secondary" onClick={()=>onOpenVideo(media.media_version_id,0)}>Review local video</button>
          <span className="small-text">Local 00:00 matches YouTube {timestamp(media.youtube_start_seconds)} · Audio {media.audio_state || "pending"} · Frames {media.frames_state || "pending"} · Frame text {media.visual_state || "pending"}</span>
          <button className="text-button" disabled={linking} onClick={()=>void detachMedia()}>Detach copy</button>
        </div>}
        <div className="youtube-import-options">
          <label>Saved video version<select value={mediaVersion} onChange={event=>setMediaVersion(event.target.value)}>
            <option value="">Choose a local video</option>
            {videos.map(item=><option key={item.version.id} value={item.version.id}>{item.displayName} · Version {item.version.version}</option>)}
          </select></label>
          <label>YouTube time at local 00:00 (seconds)<input type="number" min="0" max="14400" step="0.1" value={youtubeStart}
            onChange={event=>setYoutubeStart(event.target.value)}/></label>
        </div>
        <button className="text-button" disabled={linking || !mediaVersion || youtubeStart==="" || !Number.isFinite(Number(youtubeStart))}
          onClick={()=>void attachMedia()}>{media ? "Change local copy" : "Attach local copy"}</button>
      </details>
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
          <button className="text-button" aria-label={`Watch YouTube here at ${timestamp(segment.start_seconds)}`}
            onClick={()=>embedId ? setPlayerSeconds(segment.start_seconds) : void open(segment.start_seconds)}>{timestamp(segment.start_seconds)}</button>
          <p>{segment.text}</p>
          {media && segment.start_seconds>=media.youtube_start_seconds &&
            (media.duration_seconds==null || segment.start_seconds-media.youtube_start_seconds<=media.duration_seconds) &&
            <button className="text-button" aria-label={`Review local video at ${timestamp(segment.start_seconds-media.youtube_start_seconds)}`}
              onClick={()=>onOpenVideo(media.media_version_id,segment.start_seconds-media.youtube_start_seconds)}>Review copy</button>}
        </div>)}</div>
      </>}
      {!unit && !source?.issue && <p className="small-text">Captions are still being processed. Saved intervals will appear as background work completes.</p>}
    </>}
  </section>;
}
