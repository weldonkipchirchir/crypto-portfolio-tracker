(function(g){
'use strict';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cache=new Map();
function normalize(packet,pair,now=Date.now()){
 const out=[];
 if(!Array.isArray(packet?.data))return out;
 for(const group of packet.data.slice(0,100)){
  if(group?.instType!=='SWAP'||group.instId!==pair||!Array.isArray(group.details))continue;
  for(const r of group.details.slice(0,100)){
   if(!r||typeof r!=='object')continue;
   const ts=Number(r.ts),sz=Number(r.sz),px=Number(r.bkPx);
   if(!Number.isSafeInteger(ts)||ts<=0||ts>now+60000||typeof r.sz!=='string'||!Number.isFinite(sz)||sz<=0||!['buy','sell'].includes(r.side))continue;
   const positionSide=['long','short'].includes(r.posSide)?r.posSide:r.posSide==='net'?(r.side==='sell'?'long':'short'):'unknown';
   out.push({venue:'OKX',pair,timestamp:ts,position_side:positionSide,order_side:r.side,contracts:r.sz,unit:'contracts',liquidation_mark_price:Number.isFinite(px)&&px>0?String(r.bkPx):null,quote:'USDT',usd_notional:null});
   if(out.length>=100)return out;
  }
 }
 return out;
}
function observe(d,WebSocketClass=g.WebSocket,signal=null){
 return new Promise(resolve=>{
  const started=Date.now(),events=[],seen=new Set();let socket,done=false,timer;
  const finish=(status,message)=>{if(done)return;done=true;clearTimeout(timer);signal?.removeEventListener('abort',cancel);if(socket){socket.onopen=null;socket.onmessage=null;socket.onerror=null;socket.onclose=null;try{socket.close()}catch{}}resolve({...d,events,status,message,started_at:started,ended_at:Date.now()})};
  const cancel=()=>finish('cancelled','Observation stopped because this tool was closed.');if(signal?.aborted){cancel();return}signal?.addEventListener('abort',cancel,{once:true});
  timer=setTimeout(()=>finish('observed','Observation ended. No returned events does not establish that no liquidations occurred.'),Math.min(8000,Math.max(1,Number(d.observation_ms)||8000)));
  try{
   socket=new WebSocketClass('wss://ws.okx.com:8443/ws/v5/public');
   socket.onopen=()=>socket.send(JSON.stringify({op:'subscribe',args:[{channel:'liquidation-orders',instType:'SWAP'}]}));
   socket.onmessage=e=>{if(typeof e.data!=='string'||e.data.length>100000)return;let p;try{p=JSON.parse(e.data)}catch{return}if(p.event==='error'){finish('unavailable','Public feed rejected the subscription. Try again later.');return}for(const r of normalize(p,d.pair)){const key=JSON.stringify(r);if(!seen.has(key)){seen.add(key);events.push(r)}if(events.length>=100){finish('capped','Stopped at 100 reported records; coverage is partial.');break}}};
   socket.onerror=()=>finish('unavailable','Public WebSocket unavailable in this network or region. No synthetic events are substituted.');
   socket.onclose=()=>finish('interrupted','Connection ended; only records received during this observation are shown.');
  }catch{finish('unavailable','Public WebSocket is unavailable in this browser.')}
 });
}
async function load(api,state,params={},context={}){
 const d=await api('feature-read',{feature:'liquidation_dashboard',pair:params.pair||'BTC-USDT-SWAP'});
 const old=cache.get(d.pair);if(old&&Date.now()-old.ended_at<60000)return {...old,cached:true};
 if(!params.observe)return d;
 const result=await observe(d,g.WebSocket,context.signal);if(result.status!=='cancelled')cache.set(d.pair,result);while(cache.size>2)cache.delete(cache.keys().next().value);return result;
}
function render(d){
 const events=d.events||[],counts={long:0,short:0,unknown:0};events.forEach(r=>counts[r.position_side]++);
 return '<section><h2>Liquidation dashboard</h2><label>Perpetual <select data-liq-pair>'+['BTC-USDT-SWAP','ETH-USDT-SWAP'].map(p=>'<option '+(p===d.pair?'selected':'')+'>'+p+'</option>').join('')+'</select></label> <button data-liq-observe>Observe public feed for 8 seconds</button><p>OKX public sampled liquidation records only. No API key required. Up to 100 records per observation; 60-second cache per instrument. No historical coverage, continuous collection, global totals, or guaranteed complete venue coverage.</p><p>Size is contracts, not coins. Liquidation mark price is USDT, not an execution price. Contract values and USD conversion are unverified; USD notional is unknown. Side means the liquidated position; net-mode sell closes long and buy closes short.</p><p role="status">'+esc(d.message||'Start an observation to receive public events.')+(d.cached?' Cached observation.':'')+'</p>'+(d.started_at?'<p>UTC observation: '+esc(new Date(d.started_at).toISOString())+' to '+esc(new Date(d.ended_at).toISOString())+'</p>':'')+'<p>Covered records: '+events.length+' · Long '+counts.long+' · Short '+counts.short+' · Unknown '+counts.unknown+'. USD total: unknown.</p><div style="overflow:auto"><table><thead><tr><th>Record</th><th>Venue</th><th>Pair</th><th>Position side</th><th>UTC event time</th><th>Reported size</th><th>Liquidation mark (USDT)</th><th>USD notional</th></tr></thead><tbody>'+events.map((r,i)=>'<tr><td>'+esc(i+1)+'</td><td>OKX</td><td>'+esc(r.pair)+'</td><td>'+esc(r.position_side)+'</td><td>'+esc(new Date(r.timestamp).toISOString())+'</td><td>'+esc(r.contracts)+' contracts</td><td>'+esc(r.liquidation_mark_price??'Unknown')+'</td><td>Unknown</td></tr>').join('')+'</tbody></table></div><p>Record numbers are local display indices; identical reported records are deduplicated because the feed has no unique event ID. <a href="https://www.okx.com/docs-v5/en/#public-data-websocket-liquidation-orders-channel" target="_blank" rel="noopener noreferrer">Official OKX source and coverage documentation</a></p></section>';
}
function bind(host,ctx){const select=host.querySelector('[data-liq-pair]'),button=host.querySelector('[data-liq-observe]');let busy=false;const go=async observe=>{if(busy)return;busy=true;button.disabled=true;button.textContent=observe?'Observing for up to 8 seconds…':'Loading…';try{await ctx.reload({pair:select.value,observe})}catch(e){ctx.error?.(e)}finally{busy=false;button.disabled=false;button.textContent='Observe public feed for 8 seconds'}};const change=()=>go(false),click=()=>go(true);select.addEventListener('change',change);button.addEventListener('click',click);return()=>{select.removeEventListener('change',change);button.removeEventListener('click',click)}}
 g.OrbitFeatureModules||={};g.OrbitFeatureModules.liquidation_dashboard={title:'Liquidation dashboard',category:'Derivatives',description:'Bounded observations of public OKX liquidation records with explicit partial coverage.',load,render,bind};g.OrbitLiquidations={normalize,observe,render,load};
})(typeof window!=='undefined'?window:globalThis);
