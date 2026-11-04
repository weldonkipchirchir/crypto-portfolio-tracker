const assert=require('node:assert/strict');
global.window={};
require('./feature_exchange_imports.js');
const feature=window.OrbitFeatureModules.exchange_imports;
const html=feature.render({connections:[{id:'a'.repeat(32),label:'<private account>'}]});
assert(html.includes('&lt;private account&gt;'));
for(const label of ['Deposits (not classified as income)','Withdrawals (not classified as sales)','Simple Earn Flexible rewards','Simple Earn Locked rewards','Start (UTC)','End (UTC)','100 per page','last 90 days']) assert(html.includes(label),label);
assert(!feature.render({connections:[]}).includes('data-activity-form'));
console.log('Exchange activity labels and account label escaping passed.');
