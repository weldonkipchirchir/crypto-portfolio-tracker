'use strict';
const assert=require('node:assert/strict');require('./chart_panels.js');const p=globalThis.OrbitChartPanels;
assert.deepEqual(p.range([[99999,null,1,2],[NaN,Infinity,-3,1]],2,2),{min:-3.42,max:3.42});
assert.deepEqual(p.range([[null,NaN,Infinity]],0,3),{min:-1,max:1});
const rows=Array.from({length:6},(_,i)=>({timestamp:Date.UTC(2026,0,i+1)}));
const r=p.rsi({values:[null,10,20,45,60,80],rows,start:2,count:3,width:700,label:'<script>bad</script>',zone:'UTC'});
assert.ok(r.includes('viewBox="0 0 700 180"'));assert.ok(r.includes('x2="612"'));assert.ok(r.includes('RSI 60'));assert.ok(!r.includes('<script>'));assert.ok(r.includes('&lt;script&gt;'));assert.ok(r.includes('Jan 3'));assert.ok(r.includes('Jan 5'));assert.ok(!r.includes('NaN'));
const warm=p.rsi({values:[null,null],rows,start:0,count:2});assert.ok(warm.includes('Warming up'));assert.ok(!warm.includes('<path'));
const m=p.macd({line:[999999,1,2],signal:[999999,.8,1.5],histogram:[999999,.2,.5],rows,start:1,count:2,width:700});assert.ok(m.includes('viewBox="0 0 700 200"'));assert.ok(m.includes('MACD 2'));assert.ok(m.includes('Signal 1.5'));assert.ok(!m.includes('999'));assert.ok(m.includes('fill="#22c8a0"'));assert.ok(!m.includes('NaN'));
const gaps=p.macd({line:[1,null,2],signal:[null,null,null],histogram:[null,null,null],rows,start:0,count:3});assert.ok(gaps.includes('M16.00'));assert.ok(!gaps.includes(' L'));assert.ok(gaps.includes('Warming up'));
console.log('Professional indicator pane bounds, warm-up, gaps, dimensions, dates and escaping passed.');
// Nonuniform provider timestamps must share the exact price-chart x coordinates.
const uneven=[{timestamp:0},{timestamp:1000},{timestamp:10000}];
const aligned=p.rsi({values:[20,40,60],rows:uneven,start:0,count:3,width:700});
assert.ok(aligned.includes('L75.60,98.00'), 'Middle observation uses time fraction, not its array index');
const four=p.macd({line:[1,1,1,1],signal:[0,0,0,0],histogram:[1,2,-2,-1],rows,start:0,count:4,width:700});
for(const c of ['#91dacc','#22c8a0','#f05d79','#e89aa6'])assert.ok(four.includes('fill="'+c+'"'));
const small=p.macd({line:[1e-10,2e-10],signal:[1e-10,1e-10],histogram:[0,1e-10],rows,start:0,count:2});assert.ok(small.includes('2.00e-10'));
const originalTZ=process.env.TZ;process.env.TZ='America/Los_Angeles';
try {const utc=p.rsi({values:[50,51],rows:[{timestamp:Date.UTC(2026,0,1,1)},{timestamp:Date.UTC(2026,0,2,1)}],start:0,count:2,zone:'utc'});assert.ok(utc.includes('Jan 1'));assert.ok(!utc.includes('Dec 31'));} finally {if(originalTZ===undefined)delete process.env.TZ;else process.env.TZ=originalTZ;}
