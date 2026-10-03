// Native Electron UI evaluation against a retained, isolated audio fixture database.
const { app, BrowserWindow } = require("electron");
const fs = require("node:fs");
const path = require("node:path");
const { startBackend } = require("../electron/backend.cjs");
const { registerStorage } = require("../electron/storage.cjs");
const project = path.resolve(__dirname, "../..");
const dataRoot = path.resolve(process.argv[2] || "");
const cloudFixture = process.argv.includes("--cloud-fixture");
if (!dataRoot.startsWith(path.join(project, "tmp", "audio-integration-"))) throw new Error("Use the isolated audio evaluation database.");
delete process.env.GROQ_API_KEY;
if (cloudFixture) {
  process.env.GROQ_API_KEY = "authored-ui-status-key"; // Completed fixture data only; no new upload.
  process.env.STUDYLENS_AUTO_GROQ_AUDIO = "1";
}
delete process.env.STUDYLENS_DEV_URL;
app.disableHardwareAcceleration();
app.setPath("userData", path.join(project, "tmp/audio-ui-evaluation"));
let backend, window;
async function evaluate(code) { return window.webContents.executeJavaScript(code, true); }
async function waitFor(expression) {
  const deadline = Date.now() + 10000;
  while (Date.now() < deadline) {
    if (await evaluate(expression)) return;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error("Native UI condition timed out: " + expression);
}
app.whenReady().then(async () => {
  try {
    backend = await startBackend({ dataRoot });
    const saved = await backend.request("/workspaces/semester-3/session");
    saved.session.tabs.find(tab => tab.id === saved.session.activeTabId).view = "materials";
    await backend.request("/workspaces/semester-3/session", { method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ base_revision: saved.revision, session: saved.session }) });
    window = new BrowserWindow({ width: 1366, height: 900, show: false, webPreferences: {
      preload: path.join(project, "electron/preload.cjs"), sandbox: true, contextIsolation: true, nodeIntegration: false, offscreen: true,
    }});
    registerStorage(() => window, async () => backend);
    await window.loadFile(path.join(project, "dist/index.html"));
    await waitFor("!!document.querySelector('[data-testid=materials]') && [...document.querySelectorAll('.material-card')].some(e => e.innerText.includes('clean.wav'))");
    const setup = await evaluate("window.studyLens.storage.request({action:'audioStatus'})");
    if (!setup.ok || !setup.data.model_ready || !setup.data.ffmpeg) throw new Error("Native audio setup IPC failed");
    if (cloudFixture && (!setup.data.cloud_enabled || !await evaluate("document.querySelector('.material-upload-note').innerText.includes('Audio intervals containing detected speech are automatically sent to Groq')"))) throw new Error("Automatic audio disclosure missing");
    await evaluate("document.querySelectorAll('.material-card').forEach(card => { if (card.querySelector('h3')?.textContent === 'clean.wav') { card.querySelector('summary').click(); [...card.querySelectorAll('button')].find(b => b.textContent.includes('Review transcript')).click(); } })");
    await waitFor("!!document.querySelector('audio') && !!document.querySelector('.audio-segment')");
    const media = await evaluate(`new Promise((resolve, reject) => {
      const audio = document.querySelector('audio');
      const inspect = () => audio.readyState >= 1 ? resolve({duration:audio.duration, error:audio.error?.code}) : null;
      if (inspect()) return;
      audio.addEventListener('loadedmetadata', inspect, {once:true});
      audio.addEventListener('error', () => reject(new Error('Audio playback decoding failed')), {once:true});
      setTimeout(() => { if (audio.readyState >= 1) inspect(); else reject(new Error('Audio metadata timed out')); }, 5000);
    })`);
    if (!(media.duration > 8) || media.error) throw new Error("Native PCM playback failed");
    await evaluate("document.querySelectorAll('.audio-segment button')[1].click()");
    const seek = await evaluate("document.querySelector('audio').currentTime");
    if (seek < 2) throw new Error("Timestamp seek failed");
    let absoluteSeek;
    if (cloudFixture) {
      if (!await evaluate("document.querySelector('.audio-transcript').innerText.includes('Transcribed by Groq')")) throw new Error("Cloud transcript provenance missing");
      await evaluate("document.querySelector('[aria-label=\"Close extracted text\"]').click()");
      await evaluate("document.querySelectorAll('.material-card').forEach(card => { if (card.querySelector('h3')?.textContent === 'intervals.wav') { card.querySelector('summary').click(); [...card.querySelectorAll('button')].find(b => b.textContent.includes('Review transcript')).click(); } })");
      await waitFor("!!document.querySelector('audio') && !!document.querySelector('.audio-segment')");
      await evaluate("document.querySelector('[aria-label=\"Next source unit\"]').click()");
      await waitFor("document.querySelector('.source-locator')?.innerText.includes('00:30–01:00') && !!document.querySelector('.audio-segment') && document.querySelector('audio')?.readyState >= 1");
      absoluteSeek = await evaluate(`(() => {
        const buttons = [...document.querySelectorAll('.audio-segment button')];
        const button = buttons.find(b => b.textContent !== '00:30') || buttons[0];
        const parts = button.textContent.split(':').map(Number);
        const seconds = parts.reduce((a, b) => a * 60 + b, 0);
        button.click();
        return {source_seconds:seconds, clip_seconds:document.querySelector('audio').currentTime};
      })()`);
      // Labels show whole seconds; the player keeps the source's fractional timestamp.
      const expected = absoluteSeek.source_seconds - 30;
      if (absoluteSeek.source_seconds < 30 || absoluteSeek.clip_seconds < expected - .05 || absoluteSeek.clip_seconds >= expected + 1.05) throw new Error("Absolute source timestamp seeks to wrong clip time");
    }
    await evaluate("document.fonts.ready.then(() => true)");
    await evaluate("document.querySelector('[data-testid=content-preview]').scrollIntoView({block:'start'})");
    const screenshot = await window.webContents.capturePage(undefined, { stayHidden: true });
    const screenshotPath = path.join(project, `tmp/ingestion-evals/screenshots/${cloudFixture ? "cloud-audio" : "phase-06-audio"}-desktop.png`);
    fs.writeFileSync(screenshotPath, screenshot.toPNG());
    const report = { status: "passed", checks: { native_audio_ipc: true, transcript_visible: true, pcm_playback_metadata: true, timestamp_seek: true,
      ...(cloudFixture ? {automatic_disclosure:true, cloud_provenance:true, absolute_source_seek:true} : {}) },
      duration: media.duration, seek_seconds: seek, absolute_seek: absoluteSeek, screenshot: screenshotPath, data_directory: dataRoot };
    fs.writeFileSync(path.join(project, `tmp/ingestion-evals/${cloudFixture ? "cloud-audio" : "audio"}-desktop.json`), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
    await backend.stop();
    app.exit(0);
  } catch (error) {
    console.error(error.message);
    await backend?.stop();
    app.exit(1);
  }
});
