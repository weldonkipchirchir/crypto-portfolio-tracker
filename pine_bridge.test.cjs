'use strict';
const assert=require('node:assert/strict');require('./pine_bridge.js');const p=globalThis.OrbitPine;
const rows=Array.from({length:100},(_,i)=>({timestamp:1700000000000+i*86400000,open:i+1,high:i+3,low:i+.5,close:i+2,volume:100+i}));
const run=s=>p.compile(s,{rows});
for(const script of Object.values(p.templates)){const r=run(script);assert.equal(r.ok,true,JSON.stringify(r.diagnostics));assert.ok(r.plots.length>0);assert.equal(r.plots[0].values.length,100)}
let r=run('indicator("Math", overlay=true)\nx=ta.sma(close, 3)\nplot(x, "Mean", color.orange)');assert.equal(r.ok,true);assert.deepEqual(r.plots[0].values.slice(0,5),[null,null,3,4,5]);
r=run('indicator("EMA")\nplot(ta.ema(close, 3))');assert.equal(r.ok,true);assert.deepEqual(r.plots[0].values.slice(0,4),[2,2.5,3.25,4.125]);
r=run('indicator("Arithmetic")\nx=(close + high) / 2\nplot(x[1]-close[1])');assert.equal(r.ok,true);assert.deepEqual(r.plots[0].values.slice(0,3),[null,.5,.5]);
r=run('indicator("RSI", overlay=false)\nplot(ta.rsi(close,14))');assert.equal(r.ok,true);assert.equal(r.plots[0].pane,'oscillator');assert.equal(r.plots[0].values[13],null);assert.equal(r.plots[0].values[14],100);
r=run('indicator("BB")\n[mid,up,down]=ta.bb(close,3,2)\nplot(mid)\nplot(up)\nplot(down)');assert.equal(r.ok,true);assert.equal(r.plots[0].values[2],3);assert.ok(Math.abs(r.plots[1].values[2]-(3+2*Math.sqrt(2/3)))<1e-10);
r=run('indicator("Comment // quoted") // external comment\nplot(close, title="Price // not comment")');assert.equal(r.ok,true);assert.equal(r.title,'Comment // quoted');assert.equal(r.plots[0].label,'Price // not comment');
r=run('indicator("Volume")\nplot(volume)');assert.equal(r.ok,true);assert.equal(r.plots[0].values[0],100);
const rejects=['strategy("Example")','indicator("x")\nfetch("https://example.com")','indicator("x")\nx=window.location\nplot(x)','indicator("x")\nx=constructor.constructor("return process")()\nplot(x)','indicator("x")\nwhile true\nplot(close)','indicator("x")\nx=request.security("BTC","D",close)\nplot(x)','indicator("x")\nplot(ta.sma(close,1))','indicator("x")\nplot(close[-1])','indicator("x")\nplot(close[1.5])','indicator("x")\nplot(ta.ema(close,301))','indicator("x")\nplot(ta.macd(close,26,12,9))','indicator("x")\nplot(close,color="javascript:alert(1)")','indicator("x")\nx=close\nx=open\nplot(x)','indicator("x")\nplot(close);alert(1)'];
for(const s of rejects){r=run(s);assert.equal(r.ok,false,s);assert.equal(r.plots.length,0);assert.ok(r.diagnostics[0].line>=1);assert.ok(r.diagnostics[0].message)}
assert.equal(run('x'.repeat(20001)).ok,false);assert.equal(p.compile(p.sample,{rows:[]}).ok,false);
r=run('indicator("Bad line")\nx=ta.ema(close,20)\nplot(unknown)');assert.equal(r.diagnostics[0].line,3);
// Degenerate arithmetic never leaks Infinity/NaN into chart geometry.
r=run('indicator("Zeros")\nplot(close/0)\nplot(close)');assert.equal(r.ok,true);assert.ok(r.plots[0].values.every(x=>x===null));
console.log('Safe Pine subset: templates, arithmetic/history, indicator vectors, line diagnostics, injection rejection, bounds passed.');

r=run('indicator("ATR",overlay=false)\nplot(ta.atr(3))');assert.equal(r.ok,true);assert.equal(r.plots[0].values[2],2.5);
r=run('indicator("Math functions")\nplot(math.max(nz(close[1], 0), 1))');assert.equal(r.ok,true);assert.deepEqual(r.plots[0].values.slice(0,3),[1,2,3]);
