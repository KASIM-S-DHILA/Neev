import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Download, FileText, Plus, RefreshCw } from "lucide-react";
import type { Subject } from "./model";
import { storageClient, unwrap, type Source, type VisionStatus } from "./storage/client";
import { formats, formatBytes } from "./storage/files";
import type { useImports } from "./storage/useImports";
import type { useJobs } from "./storage/useJobs";
import { ContentPreview } from "./ContentPreview";
import { YouTubeReview } from "./YouTubeReview";
import type { SourceVersion } from "./storage/client";

export function Materials({
  workspaceId,
  subject,
  ready,
  flush,
  back,
  imports,
  queue,
}: {
  workspaceId: string;
  subject: Subject;
  ready: boolean;
  flush: () => Promise<boolean>;
  back: () => void;
  imports: ReturnType<typeof useImports>;
  queue: ReturnType<typeof useJobs>;
}) {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const target = useRef<string | undefined>(undefined);
  const mounted = useRef(false);
  const busy = imports.state.busy;
  const [preview, setPreview] = useState<SourceVersion | null>(null);
  const [previewSeek,setPreviewSeek] = useState<number|undefined>(undefined);
  const [previewKind,setPreviewKind] = useState("");
  const [linkForm,setLinkForm] = useState(false);
  const [link,setLink] = useState("");
  const [linkTitle,setLinkTitle] = useState("");
  const [language,setLanguage] = useState("en");
  const [linkBusy,setLinkBusy] = useState(false);
  const [vision, setVision] = useState<VisionStatus | null>(null);
  const [audio, setAudio] = useState<Awaited<ReturnType<typeof storageClient.audioStatus>> | null>(null);
  useEffect(() => {
    let disposed = false;
    storageClient.visionStatus().then(value => { if (!disposed) setVision(value); }).catch(() => {});
    storageClient.audioStatus().then(value => { if (!disposed) setAudio(value); }).catch(() => {});
    return () => { disposed = true; };
  }, [workspaceId]);
  const extractionStates = queue.jobs
    .filter(
      (job) => ["extract_source","youtube_import"].includes(job.kind) && job.subject_id === subject.id,
    )
    .map((job) => `${job.id}:${job.state}`)
    .join("|");

  async function refresh() {
    try {
      if (!(await flush()))
        throw new Error("Save the workspace before loading its materials.");
      const items = await storageClient.listSources(workspaceId, subject.id);
      if (mounted.current) {
        setSources(items);
        setError("");
      }
    } catch (cause) {
      if (mounted.current)
        setError(
          cause instanceof Error
            ? cause.message
            : "Materials could not be loaded.",
        );
    } finally {
      if (mounted.current) setLoading(false);
    }
  }
  useEffect(() => {
    mounted.current = true;
    if (ready) void refresh();
    return () => {
      mounted.current = false;
    };
  }, [
    workspaceId,
    subject.id,
    ready,
    imports.state.completed,
    extractionStates,
  ]);

  async function choose(sourceId?: string) {
    target.current = sourceId;
    if (window.studyLens?.storage) {
      try {
        const files = unwrap(
          await window.studyLens.storage.chooseFiles({ multiple: !sourceId }),
        );
        await imports.manager.start(
          { workspaceId, subjectId: subject.id, sourceId },
          files,
          flush,
        );
      } catch (cause) {
        if (mounted.current)
          setError(
            cause instanceof Error ? cause.message : "Could not choose files.",
          );
      }
    } else {
      if (input.current) {
        input.current.multiple = !sourceId;
        input.current.click();
      }
    }
  }
  async function download(versionId: string, filename: string) {
    try {
      if (!window.studyLens?.storage) return;
      const result = unwrap(
        await window.studyLens.storage.download({ versionId, filename }),
      );
      if (!result.canceled && mounted.current)
        setMessage("Original saved to your chosen location.");
    } catch (cause) {
      if (mounted.current)
        setError(
          cause instanceof Error
            ? cause.message
            : "The original could not be saved.",
        );
    }
  }
  async function importLink() {
    setLinkBusy(true);
    setError("");
    try {
      if(!(await flush())) throw new Error("Save your workspace before adding a link.");
      await storageClient.importYouTube(workspaceId,subject.id,link.trim(),language.trim(),linkTitle.trim());
      if(mounted.current) {setMessage("YouTube caption import queued. Follow it in Background work.");setLinkForm(false);setLink("");setLinkTitle("");}
      await queue.refresh();
    } catch(cause) {if(mounted.current)setError(cause instanceof Error?cause.message:"YouTube import could not start.");}
    finally {if(mounted.current)setLinkBusy(false);}
  }
  return (
    <div className="materials-page" data-testid="materials">
      <button className="text-button" onClick={back}>
        <ArrowLeft size={14} /> Topics
      </button>
      <div className="subject-heading">
        <div>
          <p className="eyebrow">{subject.name}</p>
          <h1>Your course materials</h1>
        </div>
        <div className="youtube-source-actions"><button className="secondary" disabled={!ready || linkBusy} onClick={()=>setLinkForm(value=>!value)}>Add YouTube link</button><button
          className="primary"
          disabled={!ready || busy}
          onClick={() => void choose()}
        >
          <Plus size={15} /> Add material
        </button></div>
      </div>
      <p className="materials-intro">
        Keep your original notes, books and lectures together.
      </p>
      {linkForm && <form className="youtube-import-form" onSubmit={event=>{event.preventDefault();void importLink();}}>
        <label>YouTube video link<input autoFocus type="url" required value={link} maxLength={2048} placeholder="https://www.youtube.com/watch?v=…" onChange={event=>setLink(event.target.value)}/></label>
        <div className="youtube-import-options"><label>Name (optional)<input value={linkTitle} maxLength={200} placeholder="Lecture title" onChange={event=>setLinkTitle(event.target.value)}/></label>
          <label>Caption language<input value={language} required maxLength={12} list="caption-languages" onChange={event=>setLanguage(event.target.value)}/>
            <datalist id="caption-languages"><option value="en">English</option><option value="hi">Hindi</option></datalist></label></div>
        <p className="small-text">Import captions from this video only. Manual captions are preferred for your chosen language. Slides and other visuals require a media copy.</p>
        <div className="youtube-source-actions"><button className="primary" disabled={!ready || linkBusy}>{linkBusy?"Adding…":"Import captions"}</button>
          <button type="button" className="text-button" disabled={linkBusy} onClick={()=>setLinkForm(false)}>Cancel</button></div>
      </form>}
      <input
        ref={input}
        type="file"
        accept={formats}
        hidden
        aria-label="Choose course materials"
        onChange={(event) => {
          const files = Array.from(event.currentTarget.files ?? []);
          event.currentTarget.value = "";
          void imports.manager
            .start(
              { workspaceId, subjectId: subject.id, sourceId: target.current },
              files,
              flush,
            )
            .catch((cause) => setError(cause.message));
        }}
      />
      <div className="material-upload-note">
        <FileText size={19} />
        <div>
          <strong>PDF · Slides · Video · Audio · Images · Text</strong>
          <p>
            Originals up to 2 GB. PDF, text, slides, images, audio and video are processed in
            the background. OCR and automatic transcripts need review. Audio supports
            recordings up to four hours. Video frames and local text are processed in the background. PDF/visual files
            support up to 64 MB and 500 pages/slides; text files up to 16 MB.
          </p>
          {vision?.automatic && <p>Difficult page and picture previews are automatically sent to Groq after local processing. Local results are retained.</p>}
          {audio?.cloud_enabled && <p>Audio intervals containing detected speech are automatically sent to Groq, including audio from videos. Local transcription is used when Groq is unavailable and the local speech model is ready.</p>}
        </div>
      </div>
      {error && (
        <div className="material-message error" role="alert">
          <span>{error}</span>
          <button className="text-button" onClick={() => void refresh()}>
            Refresh list
          </button>
        </div>
      )}
      {message && (
        <p className="material-message" role="status">
          {message}
        </p>
      )}
      {preview && previewKind === "youtube" ? <YouTubeReview key={preview.id} workspaceId={workspaceId} subjectId={subject.id} version={preview}
        job={queue.jobs.find(job=>job.kind==="extract_source" && job.source_version_id===preview.id)}
        videos={sources.filter(source=>source.kind==="video").flatMap(source=>source.versions.map(version=>({version,displayName:source.display_name})))}
        onOpenVideo={(versionId,seconds)=>{const found=sources.flatMap(source=>source.versions).find(version=>version.id===versionId);
          if(found){setPreviewKind("video");setPreviewSeek(seconds);setPreview(found);}}}
        onAssociationChange={()=>void refresh()} close={()=>setPreview(null)}/> : preview && (
        <ContentPreview
          key={preview.id}
          workspaceId={workspaceId}
          version={preview}
          initialSeekSeconds={previewSeek}
          job={queue.jobs.find(
            (job) =>
              job.kind === "extract_source" &&
              job.source_version_id === preview.id,
          )}
          close={() => setPreview(null)}
        />
      )}
      <div className="section-heading">
        <h2>Saved materials</h2>
        <button
          className="text-button"
          disabled={busy || !ready}
          onClick={() => void refresh()}
          aria-label="Refresh materials"
        >
          <RefreshCw size={13} />
        </button>
      </div>
      {loading ? (
        <p className="small-text">Loading your materials…</p>
      ) : !sources.length ? (
        <div className="materials-empty">
          <FileText size={28} />
          <h2>Add your first source</h2>
          <p>Choose a textbook, slide deck, recording or a set of notes.</p>
          <button
            className="secondary"
            disabled={!ready || busy}
            onClick={() => void choose()}
          >
            <Plus size={14} /> Choose files
          </button>
        </div>
      ) : (
        <div className="material-list">
          {sources.map((source) => (
            <section className="material-card" key={source.id}>
              <div className="material-card-heading">
                <FileText size={20} />
                <div>
                  <h3>{source.display_name}</h3>
                  <p>
                    {source.kind} · {formatBytes(source.versions[0].size_bytes)}{" "}
                    · Version {source.versions[0].version}
                  </p>
                </div>
                <span className="stored-status">
                    {source.kind === "youtube" ? source.media_link ? "Local copy attached · Review coverage" : source.versions[0].extraction?.result?.youtube?.coverage === "link_only" ? "Link only · Captions unavailable" : source.versions[0].extraction?.result?.youtube?.coverage === "captions_only" ? "Transcript only · Needs review" : "Reading saved captions…" : source.versions[0].extraction
                    ? source.versions[0].extraction.state === "succeeded"
                      ? "Text extracted"
                      : source.versions[0].extraction.state === "partial"
                        ? source.versions[0].extraction.result?.counts.text ||
                          source.versions[0].extraction.result?.counts.suspect
                          ? "Some content needs review"
                          : "No readable text · Needs review"
                        : source.versions[0].extraction.state === "failed"
                          ? "Extraction needs attention"
                          : source.versions[0].extraction.state === "cancelled"
                            ? "Extraction cancelled"
                            : "Extracting text…"
                    : queue.jobs.find(
                          (job) =>
                            job.source_version_id === source.versions[0].id,
                        )?.state === "succeeded"
                      ? "Original checked · Awaiting extraction"
                      : "Saved · Awaiting extraction"}
                </span>
              </div>
              <details>
                <summary>
                  {source.versions.length === 1
                    ? source.kind === "youtube" ? "Saved caption snapshot" : "Original file"
                    : `${source.versions.length} versions`}
                </summary>
                <div className="version-list">
                  {source.versions.map((version) => (
                    <div className="version-row" key={version.id}>
                      <div>
                        <strong>
                          Version {version.version} · {version.filename}
                        </strong>
                        <span>
                          {formatBytes(version.size_bytes)} ·{" "}
                          {new Date(version.created_at).toLocaleString()}
                        </span>
                        {(version.extraction || source.kind === "youtube") && (
                          <button
                            className="text-button"
                            disabled={!ready}
                            onClick={() => {setPreviewKind(source.kind);setPreviewSeek(undefined);setPreview(version);}}
                          >
                            {source.kind === "youtube" ? "Review YouTube source" : source.kind === "video" ? "Review video" : source.kind === "audio" ? "Review transcript" : "Review extracted text"}
                          </button>
                        )}
                        <button
                          className="text-button"
                          disabled={!ready}
                          onClick={() =>
                            void queue.action("verify", version.id)
                          }
                        >
                          {source.kind === "youtube" ? "Check snapshot" : "Check original"}
                        </button>
                      </div>
                      {window.studyLens?.storage ? (
                        <button
                          className="text-button"
                          onClick={() =>
                            void download(version.id, version.filename)
                          }
                        >
                          <Download size={13} /> {source.kind === "youtube" ? "Save snapshot" : "Save original"}
                        </button>
                      ) : (
                        <a
                          className="text-button"
                          href={`/api/source-versions/${encodeURIComponent(version.id)}/file`}
                          download={version.filename}
                        >
                          <Download size={13} /> {source.kind === "youtube" ? "Save snapshot" : "Save original"}
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              </details>
              {source.kind !== "youtube" && <button
                className="text-button add-version"
                disabled={!ready || busy}
                onClick={() => void choose(source.id)}
              >
                <Plus size={13} /> Add new version
              </button>}
            </section>
          ))}
        </div>
      )}
      <p className="small-text material-footnote">
        An identical file under the same source reuses its saved version. New
        versions preserve earlier originals. Imports continue while you use
        other tabs. Keep Neev open until the original is saved. Saved
        background jobs resume after a restart.
      </p>
    </div>
  );
}
