// Native frame review with real saved previews and unavailable/cancelled ASR.
const {app,BrowserWindow} = require('electron');
const fs = require('node:fs');
const path = require('node:path');
const {startBackend} = require('../electron/backend.cjs');
const {registerStorage} = require('../electron/storage.cjs');
const project = path.resolve(__dirname,'../..');
const dataRoot = path.resolve(process.argv[2] || '');
if (!dataRoot.startsWith(path.join(project,'tmp','video-frames-integration-'))) throw new Error('Use isolated frame evaluation data');
delete process.env.GROQ_API_KEY;
delete process.env.STUDYLENS_DEV_URL;
app.disableHardwareAcceleration();
app.setPath('userData',path.join(project,'tmp/frame-ui-evaluation'));
let backend,window;
const evaluate = code => window.webContents.executeJavaScript(code,true);
async function waitFor(expression) {
  const end = Date.now()+15000;
  while(Date.now()<end) {
    if(await evaluate(expression)) return;
    await new Promise(resolve=>setTimeout(resolve,100));
  }
  throw new Error('Frame UI condition timed out: '+expression+'\n'+await evaluate("document.querySelector('[data-testid=content-preview]')?.innerText"));
}
async function open(name) {
  await evaluate(`document.querySelectorAll('.material-card').forEach(card=>{
    if(card.querySelector('h3')?.textContent === ${JSON.stringify(name)}){
      card.querySelector('details').open=true;
      [...card.querySelectorAll('button')].find(button=>button.textContent.includes('Review video')).click();
    }
  })`);
  await waitFor("document.querySelector('video')?.readyState>=2 && !document.querySelector('video').seeking");
  await evaluate("document.querySelector('.video-frames').open=true");
  await waitFor("document.querySelectorAll('.video-frame-grid img').length>0 && [...document.querySelectorAll('.video-frame-grid img')].every(image=>image.complete && image.naturalWidth>0)");
}
app.whenReady().then(async()=>{
  try {
    backend=await startBackend({dataRoot});
    const saved=await backend.request('/workspaces/semester-3/session');
    saved.session.tabs.find(tab=>tab.id===saved.session.activeTabId).view='materials';
    await backend.request('/workspaces/semester-3/session',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({base_revision:saved.revision,session:saved.session})});
    window=new BrowserWindow({width:1366,height:1000,show:false,webPreferences:{preload:path.join(project,'electron/preload.cjs'),sandbox:true,contextIsolation:true,nodeIntegration:false,offscreen:true}});
    registerStorage(()=>window,async()=>backend);
    await window.loadFile(path.join(project,'dist/index.html'));
    await waitFor("[...document.querySelectorAll('.material-card')].some(card=>card.innerText.includes('slides.mp4'))");
    await open('slides.mp4');
    const source=await evaluate("({width:document.querySelector('video').videoWidth,duration:document.querySelector('video').duration})");
    if(source.duration!==12 || source.width!==640) throw new Error('Authored source metadata failed');
    if(await evaluate("document.querySelectorAll('.video-frame-grid img').length")!==3) throw new Error('Saved slide frames missing');
    if(!await evaluate("document.querySelector('.video-frames').innerText.includes('OCR pending') && document.querySelector('.video-transcript').innerText.includes('Transcript unavailable')")) throw new Error('Independent frame coverage labels missing');
    await evaluate("document.querySelector('[aria-label=\"Seek frame at 00:08\"]').click()");
    await waitFor("document.querySelector('video').currentTime===8 && !document.querySelector('video').seeking && document.querySelector('video').readyState>=2");
    const seek=await evaluate("document.querySelector('video').currentTime");
    await evaluate("document.querySelector('.video-frames').scrollIntoView({block:'center'})");
    await evaluate("document.fonts.ready.then(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))");
    const screenshot=path.join(project,'tmp/ingestion-evals/screenshots/phase-07b-frames-desktop.png');
    fs.writeFileSync(screenshot,(await window.webContents.capturePage(undefined,{stayHidden:true})).toPNG());
    await evaluate("document.querySelector('[aria-label=\"Close extracted text\"]').click()");
    await open('whiteboard.mp4');
    await evaluate("[...document.querySelectorAll('.video-frame-actions button')].find(button=>button.textContent==='Next frames').click()");
    await waitFor("document.querySelector('.video-frame-actions')?.innerText.includes('5–5 of 5') && document.querySelector('.video-frame-grid img')?.alt.includes('00:12') && document.querySelector('.video-frame-grid img').complete");
    await evaluate("document.querySelector('[aria-label=\"Seek frame at 00:12\"]').click()");
    await waitFor("document.querySelector('video').currentTime===12 && !document.querySelector('video').seeking");
    const report={status:'passed',checks:{frame_review_without_asr:true,real_previews_decoded:true,source_timestamp_seek:true,whiteboard_page_two:true,coverage_labels:true},
      slide_source:source,seek_seconds:seek,screenshot,data_directory:dataRoot};
    fs.writeFileSync(path.join(project,'tmp/ingestion-evals/video-frames-desktop.json'),JSON.stringify(report,null,2));
    console.log(JSON.stringify(report));
    window.destroy();
    await backend.stop();
    app.exit(0);
  }catch(error){
    console.error(error.stack);
    window?.destroy();
    await backend?.stop();
    app.exit(1);
  }
});
