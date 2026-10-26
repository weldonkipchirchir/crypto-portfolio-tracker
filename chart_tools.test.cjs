'use strict';
const assert=require('node:assert/strict');require('./chart_tools.js');const t=globalThis.OrbitChartTools;
assert.deepEqual(t.ema([1,2,3,4,5],3),[null,null,2,3,4]);
assert.deepEqual(t.sma([1,2,3,4,5],3),[null,null,2,3,4]);
assert.deepEqual(t.ema([1,2,null,3,4,5],3),[null,null,null,null,null,4]);
assert.equal(t.rsi(Array.from({length:20},(_,i)=>i+1),14).at(-1),100);
assert.equal(t.rsi(Array.from({length:20},(_,i)=>20-i),14).at(-1),0);
assert.equal(t.rsi(Array(20).fill(3),14).at(-1),50);
// Wilder's published example rounded intermediate values produce approximately 70.464.
const prices=[44.34,44.09,44.15,43.61,44.33,44.83,45.10,45.42,45.84,46.08,45.89,46.03,45.61,46.28,46.28];
assert.ok(Math.abs(t.rsi(prices,14)[14]-70.464135)<.00001);
const m=t.macd(Array.from({length:70},(_,i)=>i+1));assert.equal(m.line[24],null);assert.equal(m.signal[32],null);assert.equal(m.line[25],7);assert.equal(m.signal[33],7);assert.equal(m.histogram[33],0);
assert.equal(t.parse('EMA(20)\nRSI(14); MACD(12, 26, 9)').length,3);
for(const bad of ['alert(1)','EMA(1)','EMA(301)','MACD(26,12,9)','EMA(20);while(true){}','EMA(2)\n'.repeat(9),'EMA(2.5)'])assert.throws(()=>t.parse(bad));
assert.deepEqual(t.fib(100,200).map(x=>Number(x.value.toFixed(8))),[200,176.4,161.8,150,138.2,121.4,100]);
assert.equal(t.normalize([{timestamp:3,close:4},{timestamp:1,price:2},{timestamp:3,close:6},{timestamp:4,close:0}]).length,2);
assert.throws(()=>t.macd([1,2],30,20));
console.log('Chart tools math, warm-up, parser and normalization checks passed.');

// Exercise dialog rendering and user actions without a network or provider dependency.
let dialog;const fields={};global.document={querySelector:()=>null,createElement:()=>dialog={innerHTML:'',className:'',querySelector:s=>fields[s]||(fields[s]={value:'EMA(10)',textContent:''}),addEventListener(){},showModal(){this.shown=true},close(){this.closed=true},remove(){}},body:{append(){}}};
const rows=Array.from({length:100},(_,i)=>({timestamp:1700000000000+i*86400000,open:100+i,high:102+i,low:99+i,close:101+i}));
let saved=null;const action=async name=>dialog.onclick({target:{closest:()=>({dataset:{ot:name}})}});
t.open({rows,coinId:'bitcoin',name:'<unsafe>',candles:true,saveSetup:async(k,v)=>{saved=v},loadSetup:async()=>saved});
assert.ok(dialog.shown);assert.ok(dialog.innerHTML.includes('&lt;unsafe&gt;'));assert.ok(dialog.innerHTML.includes('MACD(12,26,9)'));
(async()=>{fields['[data-ot-editor]'].value='EMA(11)';await action('in');assert.ok(dialog.innerHTML.includes('EMA(11)</textarea>'));fields['[data-ot-editor]'].value='EMA(10)';assert.ok(dialog.innerHTML.includes('visible 50'));await action('apply');assert.ok(dialog.innerHTML.includes('EMA(10)'));await action('save');assert.ok(saved);await action('reset');await action('load');assert.ok(dialog.innerHTML.includes('visible 50'));await action('close');assert.ok(dialog.closed);console.log('Chart studio rendering, zoom, safe editor and account setup callbacks passed.');})().catch(e=>{console.error(e);process.exitCode=1});

assert.deepEqual(t.normalize([null,{timestamp:null,close:4},{timestamp:'',close:4},{timestamp:Infinity,close:3}]),[]);
const malformed=t.normalize([{timestamp:1,close:4,open:3,low:5,high:2}])[0];assert.equal(malformed.high,undefined);assert.equal(malformed.low,undefined);assert.equal(malformed.close,4);
assert.deepEqual(t.normalize({not:'an array'}),[]);
