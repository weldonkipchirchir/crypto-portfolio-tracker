const assert=require('node:assert/strict');require('./feature_named_watchlists.js');
const f=globalThis.OrbitFeatureModules.named_watchlists;
const html=f.render({coverage:'private',catalog:[{id:'bitcoin',name:'<img>'}],lists:[{id:'a',name:'<script>',columns:['current_price'],coins:[{id:'bitcoin',note:'</textarea><script>alert(1)</script>',market:null}]}]});
assert(!html.includes('<script>'));assert(!html.includes('<img>'));assert(html.includes('&lt;/textarea&gt;'));assert(html.includes('Unavailable'));assert.equal(f.category,'Research');
(async()=>{let request;await f.load(async(...args)=>{request=args;return {}},{});assert.deepEqual(request,['feature-read',{feature:'named_watchlists'}]);console.log('Named watchlists escaping and load passed');})();
