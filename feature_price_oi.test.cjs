const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const box={window:{}};vm.runInNewContext(fs.readFileSync('feature_price_oi.js','utf8'),box);
const f=box.window.OrbitFeatureModules.price_oi;
const d={assets:{bitcoin:'<img src=x>'},coin_id:'bitcoin',base:'<script>',symbol:'<img>',venue:'Binance',period:'1h',fetched_at:1000,start:0,end:2000,errors:{oi:'<script>alert(1)</script>'},rows:[{timestamp:1000,price:10,oi_coin:null,oi_quote:null,volume:2,funding_rate:0.001}]};
const html=f.render(d);assert.ok(!html.includes('<script>'));assert.ok(!html.includes('<img'));assert.match(html,/Missing observation/);assert.match(html,/Exact timestamp matches only/);assert.match(html,/not contract count/);assert.match(html,/&lt;script&gt;/);
(async()=>{let call;await f.load(async(...a)=>{call=a},{});assert.equal(call[0],'feature-read');assert.equal(call[1].feature,'price_oi');assert.equal(call[1].period,'1h');console.log('Price/OI UI contract and escaping passed.');})().catch(e=>{console.error(e);process.exitCode=1});
