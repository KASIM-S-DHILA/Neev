import { useEffect, useState } from "react";
import { storageClient, type StorageInfo } from "./storage/client";
export function StorageSettings() {
  const [info, setInfo] = useState<StorageInfo | null>(null);
  const [error, setError] = useState("");
  const [audio, setAudio] = useState<Awaited<ReturnType<typeof storageClient.audioStatus>> | null>(null);
  useEffect(() => {
    let alive = true;
    storageClient
      .storageInfo()
      .then((value) => {
        if (alive) setInfo(value);
      })
      .catch((cause) => {
        if (alive) setError(cause.message);
      });
    storageClient.audioStatus().then((value) => { if (alive) setAudio(value); })
      .catch(() => { if (alive) setAudio(null); });
    return () => {
      alive = false;
    };
  }, []);
  return (
    <section className="settings-section">
      <h2>Saved on this device</h2>
      <p>
        Workspaces, subjects, topics, study tabs and drafts are stored in the
        local database. Uploaded originals are kept in their original form.
      </p>
      <div className="info-row">
        <span>Storage</span>
        <span>SQLite · WAL enabled</span>
      </div>
      <div className="info-row">
        <span>Application</span>
        <span>Neev 0.6.0</span>
      </div>
      {info && (
        <div className="storage-paths">
          <label>Data location</label>
          <code>{info.data_directory}</code>
          <label>Database</label>
          <code>{info.database_path}</code>
        </div>
      )}
      {error && <p role="alert">{error}</p>}
      <p className="small-text">
        Keep the entire data directory together when making a backup. Close
        Neev first. PDF, slide and image processing starts locally. OCR uses
        Tesseract; full slide previews use LibreOffice when installed. OCR
        language data must match the source. When configured, Groq processes
        difficult visuals and detected speech. A local speech model provides
        audio fallback. Video audio and selected frame previews are supported; extracting on-screen text comes next.
      </p>
      <details className="content-provenance">
        <summary>Audio processing setup</summary>
        {audio ? <p className="small-text">FFmpeg: {audio.ffmpeg && audio.ffprobe ? "Ready" : "Missing"} · Speech runtime: {audio.recognizer ? "Ready" : "Missing"} · Tiny model: {audio.model_ready ? "Ready" : "Missing"}</p> : <p className="small-text">Audio setup status unavailable.</p>}
        {audio && <p className="small-text">Groq speech: {audio.cloud_enabled ? "Automatic · whisper-large-v3-turbo" : "Not enabled · local transcription"}. Original recordings are retained on this device.</p>}
        <p className="small-text">For local fallback, run <code>npm.cmd run audio:setup</code> from the project folder, then restart Neev. This downloads the local model once. Install FFmpeg separately if needed. Groq uses the configured API key.</p>
      </details>
    </section>
  );
}
