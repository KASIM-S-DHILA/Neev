import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowLeft, ArrowRight, RefreshCw, X } from "lucide-react";
import { SourceEquation } from "./EquationPreview";
import { ExtractedText, VisualExtraction } from "./VisualExtraction";
import { AudioTranscript, timestamp } from "./AudioTranscript";
import { VideoTranscript } from "./VideoTranscript";
import {
  storageClient,
  type ExtractedContent,
  type Job,
  type SourceVersion,
  type VisionStatus,
} from "./storage/client";

export function ContentPreview({
  workspaceId,
  version,
  job,
  close,
}: {
  workspaceId: string;
  version: SourceVersion;
  job?: Job;
  close: () => void;
}) {
  const [offset, setOffset] = useState(0);
  const [jump, setJump] = useState("1");
  const [content, setContent] = useState<ExtractedContent | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const [view, setView] = useState<"text" | "visual" | "structure">("text");
  const [processing, setProcessing] = useState(false);
  const [vision, setVision] = useState<VisionStatus | null>(null);
  useEffect(() => {
    let disposed = false;
    storageClient.visionStatus().then((value) => { if (!disposed) {
      setVision(value);
    } })
      .catch(() => { if (!disposed) setVision(null); });
    return () => { disposed = true; };
  }, [workspaceId, version.id]);
  const cloudBusy = content?.cloud_job?.state === "queued" || content?.cloud_job?.state === "running";
  useEffect(() => {
    if (cloudBusy) return;
    let disposed = false;
    storageClient.visionStatus().then(value => { if (!disposed) setVision(value); }).catch(() => {});
    return () => { disposed = true; };
  }, [cloudBusy, workspaceId, version.id]);
  useEffect(() => {
    if (!cloudBusy) return;
    let disposed = false;
    const timer = window.setInterval(() => {
      storageClient.content(workspaceId, version.id, offset).then((data) => { if (!disposed) setContent(data); })
        .catch((cause) => { if (!disposed) setError(cause instanceof Error ? cause.message : "Cloud status could not be loaded."); });
    }, 1500);
    return () => { disposed = true; window.clearInterval(timer); };
  }, [cloudBusy, workspaceId, version.id, offset]);
  const panel = useRef<HTMLElement>(null);
  useEffect(() => {
    panel.current?.scrollIntoView({ block: "start", behavior: "smooth" });
  }, []);
  useEffect(() => {
    let disposed = false;
    setLoading(true);
    setError("");
    setContent(null);
    storageClient
      .content(workspaceId, version.id, offset)
      .then((data) => {
        if (!disposed) setContent(data);
      })
      .catch((cause) => {
        if (!disposed)
          setError(
            cause instanceof Error
              ? cause.message
              : "Extracted text could not be loaded.",
          );
      })
      .finally(() => {
        if (!disposed) setLoading(false);
      });
    return () => {
      disposed = true;
    };
  }, [workspaceId, version.id, offset, refresh, job?.state, job?.done]);
  const unit = content?.units[0];
  const hasCloudText = !!unit?.metadata.cloud_visuals?.some(entry => entry.status === "complete" && entry.extraction);
  const page = content
    ? content.kind === "pdf"
    : version.filename.toLowerCase().endsWith(".pdf");
  const busy = content?.state === "queued" || content?.state === "running";
  const timed = content?.kind === "audio" || content?.kind === "video";
  const label =
    content?.kind === "video" ? "Video interval" : content?.kind === "audio" ? "Audio interval" : content?.kind === "slides"
      ? "Slide"
      : content?.kind === "image"
        ? "Image page"
        : page
          ? "PDF page"
          : "Text section";
  async function processVisuals() {
    setProcessing(true);
    setError("");
    try {
      await storageClient.processVisuals(workspaceId, version.id);
      move(0);
      setRefresh((value) => value + 1);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Visual processing could not start.",
      );
    } finally {
      setProcessing(false);
    }
  }
  async function processAudio() {
    setProcessing(true);
    setError("");
    try {
      await storageClient.processAudio(workspaceId, version.id);
      move(0);
      setRefresh((value) => value + 1);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Audio processing could not start."); }
    finally { setProcessing(false); }
  }
  async function processCloud(ordinal?: number) {
    setProcessing(true);
    setError("");
    try {
      const next = await storageClient.processCloudVisuals(workspaceId, version.id, ordinal);
      setContent((current) => current ? { ...current, cloud_job: next } : current);
      setView("text");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Cloud processing could not start.");
    } finally { setProcessing(false); }
  }
  async function cancelCloud() {
    if (!content?.cloud_job) return;
    try {
      await storageClient.cancelJob(workspaceId, content.cloud_job.id);
      setRefresh((value) => value + 1);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Cloud cancellation failed."); }
  }
  function move(next: number) {
    setOffset(next);
    setJump(String(next + 1));
  }
  function jumpTo(event: FormEvent) {
    event.preventDefault();
    const number = Number(jump);
    if (
      Number.isInteger(number) &&
      number >= 1 &&
      number <= (content?.total ?? 0)
    )
      move(number - 1);
  }
  return (
    <section
      ref={panel}
      className="content-preview"
      aria-label="Extracted source text"
      data-testid="content-preview"
    >
      <div className="content-preview-heading">
        <div>
          <p className="eyebrow">{content?.kind === "video" ? "Video review" : "Source text"} · Version {version.version}</p>
          <h2>{version.filename}</h2>
        </div>
        <button
          className="icon-button"
          aria-label="Close extracted text"
          onClick={close}
        >
          <X size={16} />
        </button>
      </div>
      <p className="small-text">
        {page
          ? "PDF page numbers refer to physical pages, including covers; printed numbering may differ."
          : timed ? "Timestamps refer to the original recording. Automatic speech recognition can miss or mishear words. Listen before using a transcript as evidence."
          : content?.kind === "text"
            ? "Line and character locations refer to the decoded original text."
            : "Locations refer to the original slide order or image page."}{" "}
        {!timed && "OCR and visual interpretations need comparison with the original."}
      </p>
      {error && (
        <p className="material-message error" role="alert">
          {error}
        </p>
      )}
      {!loading && content && !content.integrity_verified && (
        <p className="material-message error">
          The original integrity check is not complete. This text must not be
          used as verified source evidence.
        </p>
      )}
      {content?.error && (
        <p className="material-message error" role="alert">
          {content.error}
        </p>
      )}
      {busy && (
        <p className="small-text" role="status">
          Extraction is in progress. Showing only saved units; remaining content
          is not available yet.
        </p>
      )}
      {(content?.state === "cancelled" || content?.state === "failed") && (
        <p className="small-text">
          Extraction is unfinished. Saved units are retained; use Resume in
          Background work.
        </p>
      )}
      <div className="content-navigation">
        <button
          className="icon-button"
          aria-label="Previous source unit"
          disabled={loading || offset === 0}
          onClick={() => move(offset - 1)}
        >
          <ArrowLeft size={16} />
        </button>
        <form onSubmit={jumpTo}>
          <label htmlFor={`unit-${version.id}`}>{label}</label>
          <input
            id={`unit-${version.id}`}
            type="number"
            min="1"
            max={Math.max(1, content?.total ?? 1)}
            value={jump}
            onChange={(event) => setJump(event.target.value)}
          />
          <span>of {content?.total ?? "…"}</span>
          <button className="text-button" disabled={loading || !content?.total}>
            Go
          </button>
        </form>
        <button
          className="icon-button"
          aria-label="Next source unit"
          disabled={loading || !content?.total || offset + 1 >= content.total}
          onClick={() => move(offset + 1)}
        >
          <ArrowRight size={16} />
        </button>
        <button
          className="icon-button"
          aria-label="Refresh extracted text"
          onClick={() => setRefresh((value) => value + 1)}
        >
          <RefreshCw size={14} />
        </button>
      </div>
      {loading ? (
        <p className="small-text" role="status">
          Loading source text…
        </p>
      ) : unit ? (
        <>
          <p className="source-locator">
            {unit.locator.kind === "page"
              ? `PDF page ${unit.locator.page}`
              : unit.locator.kind === "slide"
                ? `Slide ${unit.locator.slide}`
                : unit.locator.kind === "image"
                  ? `Image page ${unit.locator.page}`
                  : unit.locator.kind === "time" ? `${timestamp(unit.locator.start_seconds)}–${timestamp(unit.locator.end_seconds)}`
                  : `Lines ${unit.locator.line_start}–${unit.locator.line_end} · Characters ${unit.locator.char_start}–${unit.locator.char_end}`}{" "}
            · Version {version.version}
          </p>
          {unit.warning && !(hasCloudText && view === "text") && (
            <p className="content-warning" role="status">
              {unit.warning}
            </p>
          )}
          {!timed && <div
            className="content-view-switch"
            role="group"
            aria-label="Source view"
          >
            <button
              className={view === "text" ? "secondary" : "text-button"}
              onClick={() => setView("text")}
              aria-pressed={view === "text"}
            >
              Extracted text
            </button>
            <button
              className={view === "visual" ? "secondary" : "text-button"}
              onClick={() => setView("visual")}
              aria-pressed={view === "visual"}
            >
              Visuals
            </button>
            <button className={view === "structure" ? "secondary" : "text-button"}
              onClick={() => setView("structure")} aria-pressed={view === "structure"}>Tables &amp; structure</button>
          </div>}
          {content?.kind === "video" ? <VideoTranscript key={unit.id} unit={unit} workspaceId={workspaceId} versionId={version.id} /> : content?.kind === "audio" ? <AudioTranscript key={unit.id} unit={unit} /> : view === "visual" ? (
            <div className="source-visuals">
              {unit.metadata.assets?.length ? (
                unit.metadata.assets.map((asset, index) => (
                  <figure key={index}>
                    {asset.data_url ? (
                      <img src={asset.data_url} alt={asset.caption} />
                    ) : (
                      <p className="content-warning">{asset.error}</p>
                    )}
                    <figcaption>{asset.caption}</figcaption>
                  </figure>
                ))
              ) : (
                <p className="content-no-text">
                  No preview saved. Use Process visuals again for an older PDF,
                  or export slides as PDF for a full slide preview.
                </p>
              )}
              {unit.metadata.visual_notes && (
                <details className="content-provenance">
                  <summary>
                    Unverified visual interpretation ·{" "}
                    {unit.metadata.visual_notes.model}
                  </summary>
                  <p className="content-warning">
                    Model interpretation is separate from source evidence and
                    may be wrong.
                  </p>
                  <pre className="extracted-text">
                    {unit.metadata.visual_notes.text ||
                      unit.metadata.visual_notes.error}
                  </pre>
                </details>
              )}
            </div>
          ) : view === "structure" ? <VisualExtraction unit={unit} /> : <ExtractedText unit={unit} />}
          {!!unit.metadata.image_text?.length && view === "text" && (
            <details className="content-provenance">
              <summary>Embedded picture OCR · Unverified</summary>
              {unit.metadata.image_text.map((image) => (
                <div key={image.picture}>
                  <p className="small-text">Picture {image.picture}</p>
                  <pre className="extracted-text">
                    {image.text || "No readable picture text."}
                  </pre>
                </div>
              ))}
            </details>
          )}
          {!!unit.metadata.equations?.length && (
            <details className="content-provenance">
              <summary>Equations · Compare with the original</summary>
              <p className="small-text">
                Supported equation structure is shown below. Compare symbols
                with the original; no mathematical correctness check has run.
              </p>
              {(
                unit.metadata.equation_previews ??
                unit.metadata.equations.map(() => ({
                  kind: "unsupported" as const,
                }))
              ).map((equation, index) => (
                <SourceEquation key={index} equation={equation} />
              ))}
            </details>
          )}
          <details className="content-provenance">
            <summary>Source details</summary>
            <dl>
              <dt>{hasCloudText && view === "text" ? "Local extraction method" : "Extraction method"}</dt>
              <dd>{unit.engine}</dd>
              <dt>{hasCloudText && view === "text" ? "Local text origin" : "Text origin"}</dt>
              <dd>{unit.metadata.text_origin || "Native text"}</dd>
              {unit.metadata.speech && <><dt>Detected language</dt><dd>{unit.metadata.speech.language || "No speech recognized"} · May vary across intervals</dd>
                {unit.metadata.speech.model && <><dt>Speech model</dt><dd>{unit.metadata.speech.model}</dd></>}
                {unit.metadata.speech.model_sha256 && <><dt>Local model fingerprint</dt><dd>{unit.metadata.speech.model_sha256}</dd></>}
                {unit.metadata.speech.fallback_reason && <><dt>Local fallback</dt><dd>{unit.metadata.speech.fallback_reason}</dd></>}</>}
              {unit.metadata.video && <><dt>Video dimensions</dt><dd>{unit.metadata.video.width} × {unit.metadata.video.height}</dd>
                <dt>Audio starts in source</dt><dd>{unit.metadata.video.audio_start_seconds === null ? "No audio stream" : `${unit.metadata.video.audio_start_seconds.toFixed(3)} seconds`}</dd></>}
              {unit.metadata.ocr && (
                <>
                  <dt>OCR language</dt>
                  <dd>{unit.metadata.ocr.language || "Unavailable"}</dd>
                  <dt>OCR confidence</dt>
                  <dd>
                    {unit.metadata.ocr.mean_confidence ?? "Unavailable"} ·
                    Recognition score, not proof of correctness
                  </dd>
                </>
              )}
              <dt>Original SHA-256</dt>
              <dd>{content?.sha256}</dd>
              <dt>Stable unit ID</dt>
              <dd>{unit.id}</dd>
            </dl>
          </details>
        </>
      ) : (
        !error && (
          <p className="content-no-text">
            {content?.state === "unsupported"
              ? "This material type will be processed in a later ingestion phase."
              : "No extracted unit is available at this location yet."}
          </p>
        )
      )}
      {!loading && content?.kind === "video" && !unit && <VideoTranscript workspaceId={workspaceId} versionId={version.id} />}
      {content && ["pdf", "slides", "image"].includes(content.kind) && (
        <div className="visual-process-action">
          {vision?.automatic && <p className="small-text">Difficult visuals are automatically sent to Groq after local processing. Local results are retained.</p>}
          <details className="cloud-process-action">
            <summary>Cloud help for difficult visuals</summary>
            <p className="small-text">Selected previews from this version are sent to Groq. You can retry processing or request a specific location here. Local results are retained. Selection may miss difficult content.</p>
            <p className="small-text">Groq transcribes tables, equations and diagrams. Results need comparison with the original.</p>
            {vision?.configured ? <>
              <div className="content-view-switch">
                <button className="secondary" disabled={busy || cloudBusy || processing || !content.integrity_verified}
                  onClick={() => void processCloud()}>Process difficult visuals</button>
                <button className="text-button" disabled={busy || cloudBusy || processing || !content.integrity_verified || !unit?.metadata.assets?.length}
                  onClick={() => void processCloud(unit?.ordinal)}>Process this {label.toLowerCase()}</button>
              </div>
            </> : <p className="small-text">Set GROQ_API_KEY in your Windows environment and restart Neev to enable Groq.</p>}
            {content.cloud_job && <div role="status">
              <p className="small-text">{content.cloud_job.provider && content.cloud_job.provider !== "groq" ? "Archived cloud provider" : content.cloud_job.automatic ? "Automatic Groq" : "Groq"} · {content.cloud_job.state === "succeeded" ? "Visual processing complete" : content.cloud_job.stage} · {content.cloud_job.done}/{content.cloud_job.total} locations</p>
              {content.cloud_job.error && <p className="content-warning">{content.cloud_job.error}</p>}
              {content.cloud_job.result && <p className="small-text">{String(content.cloud_job.result.local ?? 0)} retained locally · {String(content.cloud_job.result.sent ?? 0)} newly sent · {String(content.cloud_job.result.cached ?? 0)} reused · {String(content.cloud_job.result.needs_review ?? 0)} need attention. Cloud results remain unverified.</p>}
              {cloudBusy && <button className="text-button" onClick={() => void cancelCloud()}>Cancel cloud processing</button>}
            </div>}
          </details>
          <button
            className="text-button"
            disabled={busy || processing || cloudBusy}
            onClick={() => void processVisuals()}
          >
            Process visuals again
          </button>
          <p className="small-text">
            Rebuilds this version’s extracted units and previews using the
            current local tools. The original file is retained.
          </p>
        </div>
      )}
      {timed && <div className="visual-process-action">
        <button className="text-button" disabled={busy || processing} onClick={() => void processAudio()}>{content?.kind === "video" ? "Reprocess video audio" : "Reprocess audio"}</button>
        <p className="small-text">Rebuilds this version’s transcript and playback intervals using your current speech settings. Saved Groq transcripts can be reused. The original is retained.</p>
      </div>}
    </section>
  );
}
