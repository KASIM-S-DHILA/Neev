// Actual Chromium video playback against a completed isolated evaluation database.
const { app, BrowserWindow, net, protocol } = require("electron");
const fs = require("node:fs");
const path = require("node:path");
const { startBackend } = require("../electron/backend.cjs");
const { registerStorage } = require("../electron/storage.cjs");
const project = path.resolve(__dirname, "..");
const dataRoot = path.resolve(process.argv[2] || "");
if (!dataRoot.startsWith(path.join(project, "tmp", "video-integration-"))) throw new Error("Use isolated video evaluation data.");
delete process.env.GROQ_API_KEY;
process.env.STUDYLENS_AUTO_VIDEO_FRAMES = "0"; // Completed 7A fixtures; independent frame gate is separate.
delete process.env.STUDYLENS_DEV_URL;
app.disableHardwareAcceleration();
app.setPath("userData", path.join(project, "tmp/video-ui-evaluation"));
let backend, window;
const mediaRequests = [];
const handle = protocol.handle.bind(protocol);
protocol.handle = (scheme, handler) => handle(scheme, async request => {
  const response = await handler(request);
  mediaRequests.push({method:request.method,origin:request.initiatorOrigin,status:response.status});
  console.log('Media request:', JSON.stringify(mediaRequests.at(-1)));
  return response;
});
async function evaluate(code) { return window.webContents.executeJavaScript(code, true); }
async function waitFor(expression) {
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    if (await evaluate(expression)) return;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error("Native UI condition timed out: " + expression + "\n" + await evaluate("document.querySelector('[data-testid=content-preview]')?.innerText"));
}
async function open(name) {
  await evaluate(`document.querySelectorAll('.material-card').forEach(card => {
    if (card.querySelector('h3')?.textContent === ${JSON.stringify(name)}) {
      card.querySelector('details').open = true;
      [...card.querySelectorAll('button')].find(b => b.textContent.includes('Review video')).click();
    }
  })`);
  await waitFor("document.querySelector('video')?.readyState >= 2 && !document.querySelector('video').seeking");
}
async function seekCheck() {
  const result = await evaluate(`(() => {
    const button = document.querySelector('.video-transcript .audio-segment button');
    const label = button.textContent.split(':').map(Number).reduce((a,b) => a*60+b, 0);
    button.click();
    return {label, actual:document.querySelector('video').currentTime};
  })()`);
  if (result.actual < result.label || result.actual >= result.label + 1.01) throw new Error("Video seek did not use the original timestamp");
  await waitFor("document.querySelector('video')?.readyState >= 2 && !document.querySelector('video').seeking");
  return result;
}
app.whenReady().then(async () => {
  try {
    backend = await startBackend({ dataRoot });
    const saved = await backend.request("/workspaces/semester-3/session");
    saved.session.tabs.find(tab => tab.id === saved.session.activeTabId).view = "materials";
    await backend.request("/workspaces/semester-3/session", {method:"PUT", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({base_revision:saved.revision,session:saved.session})});
    window = new BrowserWindow({width:1366,height:900,show:false,webPreferences:{
      preload:path.join(project,"electron/preload.cjs"), sandbox:true,contextIsolation:true,nodeIntegration:false,offscreen:true,
    }});
    registerStorage(() => window, async () => backend);
    window.webContents.on('console-message', details => console.log('Renderer:', details.message));
    await window.loadFile(path.join(project,"dist/index.html"));
    await waitFor("[...document.querySelectorAll('.material-card')].some(e => e.innerText.includes('delayed-audio.mp4'))");
    await open("delayed-audio.mp4");
    const media = await evaluate("({duration:document.querySelector('video').duration,width:document.querySelector('video').videoWidth,src:document.querySelector('video').src})");
    if (media.duration !== 20 || media.width !== 320 || !media.src.startsWith("studylens-media://original/")) throw new Error("Native original video metadata failed");
    const delayedSeek = await seekCheck();
    if (delayedSeek.actual < 3) throw new Error("Delayed speech seek lost the leading silence");
    const range = await net.fetch(media.src, {headers:{Range:"bytes=10-99"}});
    const bytes = Buffer.from(await range.arrayBuffer());
    if (range.status !== 206 || !bytes.equals(fs.readFileSync(path.join(project,"docs/evaluation/fixtures/phase-07/delayed-audio.mp4")).subarray(10,100))) throw new Error("Native media range streaming failed");
    const denied = await net.fetch(media.src.replace("semester-3", "other"));
    if (denied.status !== 404) throw new Error("Native media scope failed");
    await denied.arrayBuffer();
    const invalid = await net.fetch(media.src + "?token=forbidden");
    if (invalid.status !== 400) throw new Error("Media URL must reject query strings");
    await invalid.arrayBuffer();
    await evaluate("document.querySelector('[aria-label=\"Close extracted text\"]').click()");
    await open("intervals.mp4");
    await evaluate("document.querySelector('[aria-label=\"Next source unit\"]').click()");
    await waitFor("document.querySelector('.source-locator')?.innerText.includes('00:30–01:00') && document.querySelector('video')?.readyState >= 2 && !document.querySelector('video').seeking && !!document.querySelector('.audio-segment')");
    const intervalSeek = await seekCheck();
    if (intervalSeek.actual < 30) throw new Error("Second interval sought to clip time");
    if (!await evaluate("document.querySelector('.video-transcript').innerText.includes('Visual extraction is pending') && document.querySelector('.video-transcript').innerText.includes('Unverified')")) throw new Error("Video coverage or provenance missing");
    await evaluate("document.fonts.ready.then(() => true)");
    await evaluate("document.querySelector('[data-testid=content-preview]').scrollIntoView({block:'start'})");
    await evaluate("new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))");
    const screenshotPath = path.join(project,"docs/evaluation/screenshots/phase-07a-video-desktop.png");
    fs.writeFileSync(screenshotPath,(await window.webContents.capturePage(undefined,{stayHidden:true})).toPNG());
    await evaluate("document.querySelector('[aria-label=\"Close extracted text\"]').click()");
    await open("no-audio.mp4");
    if (!await evaluate("document.querySelector('.video-transcript').innerText.includes('no audio stream') && !document.querySelector('.video-transcript .audio-segment')")) throw new Error("No-audio UI failed");
    const report = {status:"passed",checks:{original_video_decoded:true,native_byte_range:true,scoped_playback:true,private_query_rejected:true,
      original_time_seek:true,coverage_and_provenance:true,no_audio_playback:true},media,delayed_seek:delayedSeek,interval_seek:intervalSeek,
      screenshot:screenshotPath,data_directory:dataRoot,media_requests:mediaRequests};
    fs.writeFileSync(path.join(project,"docs/evaluation/video-desktop.json"),JSON.stringify(report,null,2));
    console.log(JSON.stringify(report));
    window.destroy();
    await backend.stop();
    app.exit(0);
  } catch(error) {
    console.error(error.stack);
    window?.destroy();
    await backend?.stop();
    app.exit(1);
  }
});
