// Hidden native review of saved Phase 7C results from the isolated real OCR pilot.
const {app, BrowserWindow} = require('electron');
const fs = require('node:fs');
const path = require('node:path');
const {startBackend} = require('../electron/backend.cjs');
const {registerStorage} = require('../electron/storage.cjs');
const project = path.resolve(__dirname, '..');
const dataRoot = path.resolve(process.argv[2] || '');
if (!dataRoot.startsWith(path.join(project, 'tmp', 'video-visuals-integration-'))) throw new Error('Use isolated visual evaluation data');
delete process.env.GROQ_API_KEY;
delete process.env.STUDYLENS_DEV_URL;
app.disableHardwareAcceleration();
app.setPath('userData', path.join(project, 'tmp', 'frame-visual-ui-evaluation'));
let backend, window;
const evaluate = code => window.webContents.executeJavaScript(code, true);
async function waitFor(expression) {
  const end = Date.now() + 15000;
  while (Date.now() < end) {
    if (await evaluate(expression)) return;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error('Frame visual UI condition timed out: ' + expression);
}
app.whenReady().then(async () => {
  try {
    backend = await startBackend({dataRoot});
    const saved = await backend.request('/workspaces/semester-3/session');
    saved.session.tabs.find(tab => tab.id === saved.session.activeTabId).view = 'materials';
    await backend.request('/workspaces/semester-3/session', {method:'PUT',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({base_revision:saved.revision,session:saved.session})});
    window = new BrowserWindow({width:1366,height:1000,show:false,
      webPreferences:{preload:path.join(project,'electron/preload.cjs'),sandbox:true,
        contextIsolation:true,nodeIntegration:false,offscreen:true}});
    registerStorage(() => window, async () => backend);
    await window.loadFile(path.join(project, 'dist/index.html'));
    await waitFor("[...document.querySelectorAll('.material-card')].some(card=>card.innerText.includes('slides.mp4'))");
    await evaluate("document.querySelectorAll('.material-card').forEach(card=>{if(card.querySelector('h3')?.textContent==='slides.mp4'){card.querySelector('details').open=true;[...card.querySelectorAll('button')].find(button=>button.textContent.includes('Review video')).click()}})");
    await waitFor("document.querySelector('video')?.readyState>=2");
    await evaluate("document.querySelector('.video-frames').open=true");
    await waitFor("document.querySelectorAll('.video-frame-grid img').length===3");
    await evaluate("document.querySelector('.video-frame-grid figure details').open=true");
    const cloudSaved = await evaluate("!!document.querySelector('.video-frame-grid figure details details')");
    if (cloudSaved) await evaluate("document.querySelector('.video-frame-grid figure details details').open=true");
    const checks = await evaluate("({threeFrames:document.querySelectorAll('.video-frame-grid img').length===3,textVisible:!!document.querySelector('.frame-extracted-text')?.innerText.trim(),unverified:document.querySelector('.video-frame-grid figure details summary')?.textContent.includes('unverified'),timestamp:document.querySelector('[aria-label=\"Seek frame at 00:04\"]')!==null,noAudioClaim:document.querySelector('.video-transcript')?.innerText.includes('Transcript unavailable')})");
    checks.savedCloudRendered = !cloudSaved || await evaluate("!!document.querySelector('.video-frame-grid figure details details .extracted-text')?.innerText.trim()");
    if (!Object.values(checks).every(Boolean)) throw new Error('Native frame visual checks failed: ' + JSON.stringify(checks));
    await new Promise(resolve => setTimeout(resolve, 900));
    await evaluate("document.querySelector('.video-frame-grid figure').scrollIntoView({block:'center',behavior:'instant'})");
    await evaluate("document.fonts.ready.then(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))");
    const screenshot = path.join(project, 'docs/evaluation/screenshots/' +
      (cloudSaved ? 'phase-07c-cloud-frame-desktop.png' : 'phase-07c-frame-text-desktop.png'));
    fs.writeFileSync(screenshot, (await window.webContents.capturePage(undefined,{stayHidden:true})).toPNG());
    const report = {status:'passed', checks, screenshot, data_directory:dataRoot, saved_cloud:cloudSaved};
    fs.writeFileSync(path.join(project, 'docs/evaluation/' +
      (cloudSaved ? 'video-visuals-cloud-desktop.json' : 'video-visuals-desktop.json')), JSON.stringify(report,null,2));
    console.log(JSON.stringify(report));
    window.destroy();
    await backend.stop();
    app.exit(0);
  } catch (error) {
    console.error(error.stack);
    window?.destroy();
    await backend?.stop();
    app.exit(1);
  }
});
