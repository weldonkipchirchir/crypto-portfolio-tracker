(function(global){
'use strict';
function markers(trades,alias,start,end){return (trades||[]).filter(t=>t.symbol===alias&&(t.side==='buy'||t.side==='sell')).map(t=>{let raw=String(t.date||'');if(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?$/.test(raw))raw+='Z';return {timestamp:Date.parse(raw),price:Number(t.price),quantity:Number(t.quantity),side:t.side,id:t.id}}).filter(t=>Number.isFinite(t.timestamp)&&t.timestamp>=start&&t.timestamp<=end&&Number.isFinite(t.price)&&t.price>0&&t.price<=1e40&&Number.isFinite(t.quantity)&&t.quantity>0).sort((a,b)=>a.timestamp-b.timestamp).slice(-100)}
global.OrbitTradeMarkers={markers};
})(window);
