// Production Electron form/review test. External launches are captured locally.
const {app,BrowserWindow,shell}=require('electron');
const fs=require('node:fs');
const path=require('node:path');
const {startBackend}=require('../electron/backend.cjs');
const {registerStorage}=require('../electron/storage.cjs');
const project=path.resolve(__dirname,'..');
const dataRoot=path.resolve(process.argv[2]||'');
if(!dataRoot.startsWith(path.join(project,'tmp','youtube-integration-')))throw new Error('Use isolated YouTube evaluation data');
delete process.env.GROQ_API_KEY;
delete process.env.STUDYLENS_DEV_URL;
app.disableHardwareAcceleration();
app.setPath('userData',path.join(project,'tmp/youtube-ui-evaluation'));
const opened=[];
shell.openExternal=async url=>{opened.push(url);};
let backend,window;
const evaluate=code=>window.webContents.executeJavaScript(code,true);
async function waitFor(expression){
  const end=Date.now()+15000;
  while(Date.now()<end){if(await evaluate('Boolean('+expression+')'))return;await new Promise(resolve=>setTimeout(resolve,100));}
  throw new Error('YouTube UI condition timed out: '+expression);
}
async function open(name){
  await evaluate(`document.querySelectorAll('.material-card').forEach(card=>{
    if(card.querySelector('h3')?.textContent===${JSON.stringify(name)}){
      card.querySelector('details').open=true;
      [...card.querySelectorAll('button')].find(button=>button.textContent.includes('Review YouTube source')).click();
    }
  })`);
  await waitFor("document.querySelector('.youtube-cue')");
}
app.whenReady().then(async()=>{
  try{
    backend=await startBackend({dataRoot});
    window=new BrowserWindow({width:1366,height:1000,show:false,webPreferences:{preload:path.join(project,'electron/preload.cjs'),sandbox:true,contextIsolation:true,nodeIntegration:false,offscreen:true}});
    registerStorage(()=>window,async()=>backend);
    await window.loadFile(path.join(project,'dist/index.html'));
    await waitFor("document.querySelectorAll('.material-card').length>=2 && document.querySelector('.save-state.saved')");
    await evaluate("[...document.querySelectorAll('button')].find(button=>button.textContent==='Add YouTube link').click()");
    await waitFor("document.querySelector('.youtube-import-form')");
    await evaluate(`const form=document.querySelector('.youtube-import-form');
      const input=form.querySelector('input[type=url]');
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,'https://example.com/not-youtube');
      input.dispatchEvent(new Event('input',{bubbles:true}));`);
    await evaluate("document.querySelector('.youtube-import-form').requestSubmit()");
    await waitFor("[...document.querySelectorAll('[role=alert]')].some(alert=>alert.innerText.includes('YouTube video HTTPS link'))");
    await evaluate("[...document.querySelectorAll('.youtube-import-form button')].find(button=>button.textContent==='Cancel').click()");
    await open('The essence of calculus (live import)');
    if(!await evaluate("document.querySelector('.youtube-review').innerText.includes('Transcript only · Visuals not processed') && document.querySelector('.youtube-review').innerText.includes('Manual captions')"))throw new Error('Live coverage/provenance labels missing');
    const liveCues=await evaluate("document.querySelectorAll('.youtube-cue').length");
    if(liveCues<1)throw new Error('Live saved captions missing');
    await evaluate("document.querySelector('[aria-label=\"Close YouTube review\"]').click()");
    await open('Authored caption fixture · UI test');
    await evaluate("[...document.querySelectorAll('.youtube-review button')].find(button=>button.textContent==='Next interval').click()");
    await waitFor("document.querySelector('.youtube-cue p')?.textContent==='अगला विषय'");
    await evaluate("document.querySelector('.youtube-cue button').click()");
    await waitFor("document.querySelector('.youtube-cue button')?.textContent==='01:05'");
    if(opened[0]!=='https://www.youtube.com/watch?v=WUvTyaaNkzM&t=65')throw new Error('Native source timestamp link failed');
    const denied=await evaluate("window.studyLens.storage.request({action:'openYouTube',body:{url:'https://example.com/'}})");
    if(denied.ok || opened.length!==1)throw new Error('Arbitrary external link was not rejected');
    await evaluate("document.querySelector('.youtube-review').scrollIntoView({block:'start'});document.fonts.ready.then(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))");
    const screenshot=path.join(project,'docs/evaluation/screenshots/youtube-desktop.png');
    fs.writeFileSync(screenshot,(await window.webContents.capturePage(undefined,{stayHidden:true})).toPNG());
    const checks={native_import_form:true,invalid_url_rejected:true,live_captions_review:true,coverage_labels:true,hindi_caption_page:true,native_timestamp_link:true,external_url_boundary:true};
    const report={status:'passed',checks,live_first_interval_cues:liveCues,external_launches:'Captured; no browser opened',timestamp_link:opened[0],screenshot,data_directory:dataRoot};
    fs.writeFileSync(path.join(project,'docs/evaluation/youtube-desktop.json'),JSON.stringify(report,null,2));
    console.log(JSON.stringify(report));window.destroy();await backend.stop();app.exit(0);
  }catch(error){console.error(error.stack);window?.destroy();await backend?.stop();app.exit(1);}
});
