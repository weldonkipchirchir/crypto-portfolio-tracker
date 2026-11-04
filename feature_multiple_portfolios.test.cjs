const test=require('node:test');const assert=require('node:assert/strict');
require('./feature_multiple_portfolios.js');
const mod=globalThis.OrbitFeatureModules.multiple_portfolios;
test('renders separate source totals and escapes account-controlled labels',()=>{
 const valuation={value:'20',unpriced:0,source:'Saved quote'};
 const html=mod.render({coverage:'saved',combined:{connected:valuation,ledger:valuation},groups:[{id:'x',name:'<script>alert(1)</script>',kind:'ledger',members:{accounts:['a']},valuation}],sources:{wallets:[],exchanges:[],accounts:[{id:'a',label:'<img src=x onerror=alert(1)>'}]}});
 assert.match(html,/Connected:/);assert.match(html,/Ledger:/);assert.doesNotMatch(html,/<script>|<img/);assert.match(html,/&lt;script&gt;/);
});
test('loads only the account-scoped multiple portfolios endpoint',async()=>{
 let call;const result=await mod.load(async(...args)=>{call=args;return {groups:[]}},{});
 assert.deepEqual(call,['feature-read',{feature:'multiple_portfolios'}]);assert.deepEqual(result,{groups:[]});
});
