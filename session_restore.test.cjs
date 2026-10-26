const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const code=fs.readFileSync('app.js','utf8');
const start=code.indexOf('async function restoreSession('),end=code.indexOf('let sessionReady=',start);
const ctx={};vm.runInNewContext(code.slice(start,end),ctx);
(async()=>{
 let events=[],resolve;
 const view={loading:()=>events.push('loading'),ready:x=>events.push(['ready',x.email]),unauthorized:()=>events.push('login'),unavailable:()=>events.push('retry')};
 const pending=ctx.restoreSession(()=>new Promise(r=>resolve=r),view);
 assert.deepEqual(events,['loading']);resolve({email:'saved@example.test'});await pending;
 assert.deepEqual(events,['loading',['ready','saved@example.test']]);
 for(const error of [Error('offline'),Object.assign(Error('busy'),{status:503}),SyntaxError('Invalid JSON')]){
  events=[];await ctx.restoreSession(async()=>{throw error},view);assert.deepEqual(events,['loading','retry']);
 }
 events=[];await ctx.restoreSession(async()=>{throw Object.assign(Error('expired'),{status:401})},view);assert.deepEqual(events,['loading','login']);
 events=[];await ctx.restoreSession(async()=>({email:'saved@example.test'}),view);assert.deepEqual(events,['loading',['ready','saved@example.test']]);
 const html=fs.readFileSync('app.html','utf8');assert.match(html,/<section id="auth" class="hidden">/);assert.match(html,/id="sessionRetry"/);
 console.log('Session restoration: pending and valid sessions never show login; offline, 503 and malformed responses offer retry; only 401 shows login.');
})().catch(e=>{console.error(e);process.exitCode=1});
