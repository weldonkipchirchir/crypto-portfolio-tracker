'use strict';
const assert=require('node:assert/strict');require('./pine_bridge.js');const nodes={};
global.document={createElement:()=>({className:'',innerHTML:'',querySelector:s=>nodes[s]||(nodes[s]={value:'',textContent:'',innerHTML:''}),addEventListener(){},showModal(){},close(){},remove(){}}),body:{append(){}}};require('./pine_editor.js');
const rows=Array.from({length:100},(_,i)=>({timestamp:1700000000000+i*86400000,open:i+1,high:i+3,low:i+.5,close:i+2}));
assert.equal(global.OrbitPine.compile(global.OrbitPineEditor.donchian,{rows}).ok,true);
let applied=[],drafts=[];global.OrbitPineEditor.open({rows,onDraft:r=>drafts.push(r),onApply:r=>applied.push(r)});
nodes['[data-pine-source]'].value=global.OrbitPine.templates.ema;nodes['[data-pine-apply]'].onclick();assert.equal(applied.length,1);assert.ok(applied[0].plots[0].values.some(Number.isFinite));assert.equal(applied[0].source,global.OrbitPine.templates.ema);
nodes['[data-pine-source]'].value='//@version=6\nstrategy("User prototype")';nodes['[data-pine-apply]'].onclick();assert.equal(applied.length,1);assert.ok(nodes['[data-pine-result]'].innerHTML.includes('Line 2'));assert.ok(nodes['[data-pine-result]'].innerHTML.includes('strategy'));
nodes['[data-pine-template]']={value:'strategyVisuals'};nodes['[data-pine-example]'].onclick();nodes['[data-pine-apply]'].onclick();assert.equal(applied.at(-1).plots.length,7);
nodes['[data-pine-clear]'].onclick();assert.deepEqual(applied.at(-1),{source:'',plots:[]});console.log('Pine editor applies real computed plots, rejects strategies without changing chart, and clears custom plots.');

nodes['[data-pine-source]'].value='indicator("Draft only", overlay=true)';nodes['[data-pine-source]'].oninput();assert.equal(drafts.at(-1),'indicator("Draft only", overlay=true)');nodes['[data-pine-companion]'].onclick();assert.match(nodes['[data-pine-result]'].textContent,/does not reproduce/);nodes['[data-pine-apply]'].onclick();assert.equal(applied.at(-1).plots.length,7);console.log('Unapplied Pine drafts are retained and strategy visual companion clearly states its scope.');
