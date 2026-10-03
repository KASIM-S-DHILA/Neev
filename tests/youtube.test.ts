import { createRequire } from 'node:module';
import assert from 'node:assert/strict';
import test from 'node:test';
import { storageClient } from '../src/storage/client.ts';
const {youtubePlaybackUrl}=createRequire(import.meta.url)('../electron/youtube.cjs');
test('Only canonical YouTube playback links can leave the desktop app',()=>{
  assert.equal(youtubePlaybackUrl('https://www.youtube.com/watch?v=WUvTyaaNkzM&t=65'),'https://www.youtube.com/watch?v=WUvTyaaNkzM&t=65');
  for(const value of ['javascript:alert(1)','https://evil.test/','https://www.youtube.com.evil.test/watch?v=WUvTyaaNkzM',
    'https://www.youtube.com/watch?v=WUvTyaaNkzM&redirect=evil','https://www.youtube.com/watch?v=WUvTyaaNkzM&t=NaN',
    'https://www.youtube.com/watch?v=WUvTyaaNkzM&t=15000','https://user@www.youtube.com/watch?v=WUvTyaaNkzM']) assert.throws(()=>youtubePlaybackUrl(value));
});
test('YouTube import uses the correct browser API body and native IPC scope',async()=>{
  const globals=globalThis as unknown as {window:unknown;fetch:typeof fetch};
  const previousWindow=globals.window;const previousFetch=globals.fetch;
  const captured: {url:string;body:unknown}[]=[];
  try{
    globals.window={};
    globals.fetch=async(url,options)=>{
      captured.push({url:String(url),body:JSON.parse(String(options?.body))});
      return new Response(JSON.stringify({id:'queued-job'}),{status:202,headers:{'Content-Type':'application/json'}});
    };
    await storageClient.importYouTube('work-space','math','https://youtu.be/WUvTyaaNkzM','en','Calculus');
    assert.deepEqual(captured[0],{url:'/api/workspaces/work-space/subjects/math/youtube',body:{url:'https://youtu.be/WUvTyaaNkzM',language:'en',title:'Calculus'}});
    let ipc:unknown;
    globals.window={studyLens:{storage:{request:async(value:unknown)=>{ipc=value;return {ok:true,data:{id:'queued-job'}};}}}};
    await storageClient.importYouTube('work-space','math','https://youtu.be/WUvTyaaNkzM','hi');
    assert.deepEqual(ipc,{action:'importYouTube',workspaceId:'work-space',body:{subjectId:'math',url:'https://youtu.be/WUvTyaaNkzM',language:'hi',title:''}});
  }finally{globals.window=previousWindow;globals.fetch=previousFetch;}
});
