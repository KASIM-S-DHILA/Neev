// Isolated production Electron check. The remote player is deliberately not asserted as playable.
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
process.env.STUDYLENS_AUTO_VIDEO_FRAMES='0';
app.disableHardwareAcceleration();
app.setPath('userData',path.join(project,'tmp/youtube-media-ui-evaluation'));
const opened=[];
shell.openExternal=async url=>{opened.push(url);};
let backend,window;
const evaluate=code=>window.webContents.executeJavaScript(code,true);
async function waitFor(expression){
  const end=Date.now()+20000;
  while(Date.now()<end){if(await evaluate('Boolean('+expression+')'))return;await new Promise(resolve=>setTimeout(resolve,100));}
  throw new Error('YouTube media UI condition timed out: '+expression);
}
app.whenReady().then(async()=>{
  try{
    backend=await startBackend({dataRoot});
    const uploaded=await backend.request('/workspaces/semester-3/subjects/probability/sources?filename=youtube-local-slides.mp4',{
      method:'POST',headers:{'Content-Type':'application/octet-stream'},
      body:fs.readFileSync(path.join(project,'docs/evaluation/fixtures/phase-07b/slides.mp4'))});
    window=new BrowserWindow({width:1366,height:1000,show:false,webPreferences:{
      preload:path.join(project,'electron/preload.cjs'),sandbox:true,contextIsolation:true,nodeIntegration:false,offscreen:true}});
    registerStorage(()=>window,async()=>backend);
    await window.loadFile(path.join(project,'dist/index.html'));
    await waitFor("document.querySelectorAll('.material-card').length>=3 && document.querySelector('.save-state.saved')");
    await evaluate(`document.querySelectorAll('.material-card').forEach(card=>{
      if(card.querySelector('h3')?.textContent==='Authored caption fixture · UI test'){
        card.querySelector('details').open=true;
        [...card.querySelectorAll('button')].find(button=>button.textContent.includes('Review YouTube source')).click();
      }
    })`);
    await waitFor("document.querySelector('.youtube-cue')");
    await evaluate("[...document.querySelectorAll('.youtube-review button')].find(button=>button.textContent==='Watch here').click()");
    await waitFor("document.querySelector('.youtube-player iframe')");
    if(!await evaluate("document.querySelector('.youtube-player iframe').src==='https://www.youtube-nocookie.com/embed/WUvTyaaNkzM?start=0'"))
      throw new Error('On-demand embed URL is incorrect');
    await evaluate("[...document.querySelectorAll('.youtube-review button')].find(button=>button.textContent==='Close player').click()");
    if(await evaluate("Boolean(document.querySelector('.youtube-player iframe'))"))throw new Error('Player stayed mounted after close');
    await evaluate("[...document.querySelectorAll('.youtube-review button')].find(button=>button.textContent==='Open on YouTube').click()");
    if(opened[0]!=='https://www.youtube.com/watch?v=WUvTyaaNkzM&t=0')throw new Error('Browser fallback did not open');
    await evaluate(`const details=[...document.querySelectorAll('.youtube-review details')].find(value=>value.querySelector('summary')?.textContent.startsWith('Local video copy'));
      details.open=true;
      const select=details.querySelector('select');select.value=${JSON.stringify(uploaded.version_id)};select.dispatchEvent(new Event('change',{bubbles:true}));
      const input=details.querySelector('input[type=number]');
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,'60');input.dispatchEvent(new Event('input',{bubbles:true}));`);
    await evaluate("[...document.querySelectorAll('.youtube-review button')].find(button=>['Attach local copy','Change local copy'].includes(button.textContent)).click()");
    await waitFor("document.querySelector('.youtube-review summary')?.textContent.includes('youtube-local-slides.mp4')");
    await evaluate("document.querySelector('.youtube-review summary').scrollIntoView({block:'center'});document.fonts.ready.then(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))");
    const screenshot=path.join(project,'docs/evaluation/screenshots/youtube-media-desktop.png');
    fs.writeFileSync(screenshot,(await window.webContents.capturePage(undefined,{stayHidden:true})).toPNG());
    await evaluate("[...document.querySelectorAll('.youtube-review button')].find(button=>button.textContent==='Next interval').click()");
    await waitFor("document.querySelector('.youtube-cue p')?.textContent==='अगला विषय'");
    await evaluate("[...document.querySelectorAll('.youtube-cue button')].find(button=>button.textContent==='Review copy').click()");
    await waitFor("document.querySelector('video[aria-label=\"Original source video\"]')?.readyState>=1");
    const position=await evaluate("document.querySelector('video[aria-label=\"Original source video\"]').currentTime");
    if(Math.abs(position-5.5)>.4)throw new Error('Mapped local seek was '+position+', expected 5.5 seconds');
    const report={status:'passed',fixture:'authored captions and authored local slides.mp4',
      checks:{on_demand_embed_url:true,player_unmount:true,browser_fallback:true,local_attachment_ui:true,mapped_seek:true},
      local_seek_seconds:position,remote_playback:'student manual check pending',screenshot};
    fs.writeFileSync(path.join(project,'docs/evaluation/youtube-media-desktop.json'),JSON.stringify(report,null,2));
    console.log(JSON.stringify(report));window.destroy();await backend.stop();app.exit(0);
  }catch(error){console.error(error.stack);window?.destroy();await backend?.stop();app.exit(1);}
});
