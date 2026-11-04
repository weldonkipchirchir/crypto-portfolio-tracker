const assert=require('node:assert/strict');require('./feature_named_watchlists.js');
const f=globalThis.OrbitFeatureModules.named_watchlists;
const html=f.render({coverage:'private',catalog:[{id:'bitcoin',name:'<img>'}],lists:[{id:'a',name:'<script>',columns:['current_price'],coins:[{id:'bitcoin',note:'</textarea><script>alert(1)</script>',market:null}]}]});
assert(!html.includes('<script>'));assert(!html.includes('<img>'));assert(html.includes('&lt;/textarea&gt;'));assert(html.includes('Unavailable'));assert.equal(f.category,'Research');
(async()=>{let request;await f.load(async(...args)=>{request=args;return {}},{});assert.deepEqual(request,['feature-read',{feature:'named_watchlists'}]);console.log('Named watchlists escaping and load passed');})();

const test=require('node:test');const {cell}=globalThis.OrbitWatchlistFormat;
test('watchlists format prices, ranks and signed return percentages',()=>{assert.match(cell(3.456,'price_change_percentage_24h'),/positive.*\+3.46%/);assert.match(cell(-2,'price_change_percentage_7d'),/negative.*-2%/);assert.match(cell(0,'price_change_percentage_30d'),/>0%/);assert.match(cell(1234.5,'current_price'),/\$1,234.50/);assert.match(cell(0.00001234,'current_price'),/0.00001234/);assert.match(cell(12,'market_cap_rank'),/>12</)});
test('unknown and invalid market values remain unavailable',()=>{for(const v of [null,undefined,NaN,Infinity,true,'12'])assert.equal(cell(v,'current_price'),'<td>Unavailable</td>')});
