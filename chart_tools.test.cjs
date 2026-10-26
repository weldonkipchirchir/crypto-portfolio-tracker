'use strict';
const assert=require('node:assert/strict');require('./chart_panels.js');require('./chart_tools.js');const t=globalThis.OrbitChartTools;
assert.deepEqual(t.ema([1,2,3,4,5],3),[1,1.5,2.25,3.125,4.0625]);
assert.deepEqual(t.sma([1,2,3,4,5],3),[null,null,2,3,4]);
assert.deepEqual(t.ema([1,2,null,3,4,5],3),[1,1.5,null,2.25,3.125,4.0625]);
assert.equal(t.rsi(Array.from({length:20},(_,i)=>i+1),14).at(-1),100);
assert.equal(t.rsi(Array.from({length:20},(_,i)=>20-i),14).at(-1),0);
assert.equal(t.rsi(Array(20).fill(3),14).at(-1),50);
// Wilder's published example rounded intermediate values produce approximately 70.464.
const prices=[44.34,44.09,44.15,43.61,44.33,44.83,45.10,45.42,45.84,46.08,45.89,46.03,45.61,46.28,46.28];
assert.ok(Math.abs(t.rsi(prices,14)[14]-70.464135)<.00001);
const m=t.macd(Array.from({length:70},(_,i)=>i+1));const linearEma=(p,i)=>i+1-(p-1)/2*(1-((p-1)/(p+1))**i);assert.equal(m.line[0],0);assert.equal(m.signal[0],0);assert.ok(Math.abs(m.line[25]-(linearEma(12,25)-linearEma(26,25)))<1e-10);assert.ok(m.histogram.every(Number.isFinite));
assert.equal(t.parse('EMA(20)\nRSI(14); MACD(12, 26, 9)').length,3);
for(const bad of ['alert(1)','EMA(1)','EMA(301)','MACD(26,12,9)','EMA(20);while(true){}','EMA(2)\n'.repeat(9),'EMA(2.5)'])assert.throws(()=>t.parse(bad));
assert.deepEqual(t.fib(100,200).map(x=>Number(x.value.toFixed(8))),[200,176.4,161.8,150,138.2,121.4,100]);
assert.equal(t.normalize([{timestamp:3,close:4},{timestamp:1,price:2},{timestamp:3,close:6},{timestamp:4,close:0}]).length,2);
assert.throws(()=>t.macd([1,2],30,20));
console.log('Chart tools math, warm-up, parser and normalization checks passed.');

// Exercise dialog rendering and user actions without a network or provider dependency.
let dialog;const fields={};global.document={querySelector:()=>null,createElement:()=>dialog={innerHTML:'',className:'',classList:{toggle(){}},querySelector:s=>fields[s]||(fields[s]={value:'EMA(10)',textContent:'',setAttribute(){},getBoundingClientRect:()=>({left:0,top:0,width:1000,height:352}),viewBox:{baseVal:{width:1000,height:352}}}),addEventListener(){},showModal(){this.shown=true},close(){this.closed=true},remove(){}},body:{append(){}}};
const rows=Array.from({length:100},(_,i)=>({timestamp:1700000000000+i*86400000,open:100+i,high:102+i,low:99+i,close:101+i}));
let saved=null;const action=async name=>dialog.onclick({target:{closest:()=>({dataset:{ot:name}})}});
t.open({autoRestore:false,rows,coinId:'bitcoin',name:'<unsafe>',candles:true,intervalCode:'1d',intervals:[{value:'4h',label:'4H'}],loadInterval:async()=>({rows:rows.slice(0,80),intervalCode:'4h',intervalLabel:'4H',candles:true,source:'binance',quote:'USDT'}),saveSetup:async(k,v)=>{saved=v},loadSetup:async()=>saved});
assert.ok(dialog.shown);assert.ok(dialog.innerHTML.includes('data-ot-panel="rsi"'));assert.ok(dialog.innerHTML.includes('data-ot-panel="macd"'));assert.ok(dialog.innerHTML.includes('ot-current-line'));assert.ok(dialog.innerHTML.includes('Latest close'));assert.ok(dialog.innerHTML.includes('&lt;unsafe&gt;'));assert.ok(dialog.innerHTML.includes('MACD(12,26,9)'));
(async()=>{fields['[data-ot-editor]'].value='EMA(11)';await action('in');assert.ok(dialog.innerHTML.includes('EMA(11)</textarea>'));fields['[data-ot-editor]'].value='EMA(10)';assert.ok(dialog.innerHTML.includes('visible 50'));await action('apply');assert.ok(dialog.innerHTML.includes('EMA(10)'));await action('save');assert.ok(saved);await action('reset');await action('load');assert.ok(dialog.innerHTML.includes('visible 50'));await action('fib');dialog.querySelector('[data-ot-time]').value='2023-11-14T22:13:20';dialog.querySelector('[data-ot-price-input]').value='100';await action('anchor');assert.ok(dialog.innerHTML.includes('data-ot-pending'));dialog.querySelector('[data-ot-time]').value='2023-12-14T22:13:20';dialog.querySelector('[data-ot-price-input]').value='200';await action('anchor');assert.ok(dialog.innerHTML.includes('61.8% 138.2'));await action('extensions');assert.equal(Number(t.fib(100,200,true).at(-1).value.toFixed(8)),38.2);assert.ok(!dialog.innerHTML.includes('161.8% 38.2'));await action('save');assert.equal(saved.drawings.length,1);assert.equal(saved.extensions,true);await action('reverse');await action('save');assert.equal(saved.drawings[0].a.price,200);await action('clear');await action('load');assert.ok(dialog.innerHTML.includes('Drawings (1)'));await dialog.onclick({target:{closest:()=>({dataset:{ot:'interval',interval:'4h'}})}});assert.ok(dialog.innerHTML.includes('visible 80'));assert.ok(dialog.innerHTML.includes('USDT'));assert.ok(dialog.innerHTML.includes('quote currency changed'));await action('save');assert.equal(saved.drawings.length,0);assert.ok(dialog.innerHTML.includes('Drawings (0)'));globalThis.OrbitPineEditor={open:({onApply})=>onApply({source:'indicator("Test")',plots:[{label:'MACD',values:rows.slice(0,80).map((_,i)=>i-40),color:'#57b7ff',pane:'oscillator'},{label:'Signal',values:rows.slice(0,80).map((_,i)=>(i-40)*.5),color:'#f5c565',pane:'oscillator'}]})};await action('pine');assert.equal((dialog.innerHTML.match(/ot-custom-pane/g)||[]).length,1);assert.ok(dialog.innerHTML.includes('shared scale'));assert.ok(dialog.innerHTML.includes('Signal'));await action('fib');const svg=dialog.querySelector('[data-ot-price]'),evt=(x,y,target={closest:()=>null})=>({currentTarget:svg,target,clientX:x,clientY:y,button:0,pointerId:1,preventDefault(){}});svg.onpointerdown(evt(200,100));svg.onpointermove(evt(650,230));svg.onpointerup(evt(650,230));await action('save');assert.equal(saved.drawings.length,1);const before=saved.drawings[0].b.price;const handle={closest:()=>({getAttribute:()=> '0:b'})};svg.onpointerdown(evt(650,230,handle));svg.onpointermove(evt(600,180,handle));svg.onpointerup(evt(600,180,handle));await action('save');assert.notEqual(saved.drawings[0].b.price,before);assert.equal(saved.drawings.length,1);const adjusted=saved.drawings[0].b.price;const match=/data-ot-handle="0:b"[^>]*cx="([^"]+)" cy="([^"]+)"/.exec(dialog.innerHTML);assert.ok(match);svg.onpointerdown(evt(Number(match[1]),Number(match[2])));svg.onpointermove(evt(550,140));svg.onpointerup(evt(550,140));await action('save');assert.equal(saved.drawings.length,1);assert.notEqual(saved.drawings[0].b.price,adjusted);await action('extend-right');await action('save');assert.equal(saved.extendRight,false);await action('focus');await action('close');assert.ok(dialog.closed);console.log('Chart studio rendering, zoom, safe editor and account setup callbacks passed.');})().catch(e=>{console.error(e);process.exitCode=1});

assert.deepEqual(t.normalize([null,{timestamp:null,close:4},{timestamp:'',close:4},{timestamp:Infinity,close:3}]),[]);
const malformed=t.normalize([{timestamp:1,close:4,open:3,low:5,high:2}])[0];assert.equal(malformed.high,undefined);assert.equal(malformed.low,undefined);assert.equal(malformed.close,4);
assert.deepEqual(t.normalize({not:'an array'}),[]);

// Pointer conversion must account for SVG letterboxing on tall/fullscreen charts.
const point=t.svgPoint({getBoundingClientRect:()=>({left:10,top:20,width:1000,height:700})},80,245);assert.deepEqual(point,{x:70,y:50});
const snapped=t.drawingPoint(70,50,rows,90,210,true);assert.equal(snapped.time,rows[0].timestamp);assert.equal(snapped.price,rows[0].high);
assert.equal(t.drawingPoint(10,50,rows,90,210),null);
assert.equal(t.fib(100,200,true).at(-1).ratio,1.618);assert.equal(Number(t.fib(100,200,true).at(-1).value.toFixed(8)),38.2);

// Fibonacci geometry stays inside the price pane, even with reversed time anchors.
const fg={left:16,right:312,top:24,bottom:300},fx=n=>16+n*29.6,fy=n=>300-n*2.76,ff=n=>n.toFixed(2);
const renderFib=(a,b,extra={})=>t.fibDrawing({type:'fib',a,b},{x:fx,y:fy,G:fg,fmt:ff,...extra});
const a={time:1,price:10},b={time:7,price:90};
const normal=renderFib(a,b),backwards=renderFib(b,a);
assert.ok(normal.includes('61.8% 40.56'));assert.ok(backwards.includes('61.8% 59.44'));
assert.ok(normal.includes('x2="312"'));assert.ok(backwards.includes('x2="312"'));
assert.ok(normal.includes('data-ot-handle="0:a"'));assert.ok(normal.includes('data-ot-handle="0:b"'));
assert.ok(!renderFib(a,b,{preview:true}).includes('data-ot-handle'));
assert.ok(renderFib(a,b,{extendRight:false}).includes('x2="223.20000000000002"'));
assert.ok(!renderFib({time:20,price:10},{time:30,price:90}));
assert.ok(!renderFib(a,b,{extensions:true}).includes('161.8%'));
assert.ok(normal.includes('text-anchor="end"'));assert.ok(normal.includes('fill-opacity=".045"'));
console.log('Fibonacci reversed anchors, clipping, preview, handles and extension geometry passed.');

const tight=renderFib({time:1,price:40},{time:7,price:42});const labelYs=[...tight.matchAll(/class="ot-fib-label" x="[^"]+" y="([^"]+)"/g)].map(m=>Number(m[1])).sort((a,b)=>a-b);assert.equal(labelYs.length,7);for(let i=1;i<labelYs.length;i++)assert.ok(labelYs[i]-labelYs[i-1]>=14.99);assert.ok(labelYs[0]>=fg.top+12);assert.ok(labelYs.at(-1)<=fg.bottom-4);console.log('Tightly spaced Fibonacci labels remain separated inside the plot.');
