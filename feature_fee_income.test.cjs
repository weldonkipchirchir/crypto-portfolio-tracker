const assert=require('node:assert/strict');
require('./feature_fee_income.js');
const m=globalThis.OrbitFeeIncome;
assert.equal(m.sum(['0.00000000000000000001','0.00000000000000000001']),'0.00000000000000000002');
assert.equal(m.sum(['9007199254740993','1']),'9007199254740994');
for(const v of [null,undefined,'',false,-1,NaN,Infinity])assert.equal(m.decimal(v),null);
const row={direction:'out',wallet_id:1,chain:'Ethereum',asset:'ETH',asset_id:'Ethereum:native',identity_verified:true,event_id:'tx:x',hash:'x',fee:'0.001',status:'failed',date:'2026-01-01'};
const state={wallets:[{id:1,chain:'Ethereum',label:'<script>'}],trades:[{fee:'0'},{fee:null}],history:[row,{...row,event_id:'duplicate'}, {...row,wallet_id:2,hash:'other'},{...row,hash:'unverified',identity_verified:false},{...row,hash:'token',asset_id:'Ethereum:token'},{...row,hash:'pending',status:'pending'}],exchanges:[{earn_balance:100}],history_status:[]};
const d=m.analyze(state);
assert.equal(d.gas.length,1);assert.equal(d.gasTotals[0].amount,'0.001');assert.equal(d.recordedTradeFeesUSD,null);assert.equal(d.knownTradeFeesUSD,'0');assert.equal(d.rewardIncomeUSD,null);assert.equal(d.fundingPaymentsUSD,null);
assert.equal(m.analyze({}).recordedTradeFeesUSD,null);assert.equal(m.analyze({trades:[]}).recordedTradeFeesUSD,'0');
assert(!m.render(d).includes('<script>'));assert(m.render(d).includes('&lt;script&gt;'));
(async()=>{let calls=0;const loaded=await globalThis.OrbitFeatureModules.fee_income.load(async route=>{assert(['state','feature-read'].includes(route));calls++;return route==='state'?{trades:[],history:[],wallets:[]}:{records:[],unknown_usd:0,received_usd_subtotal:'0',paid_usd_subtotal:'0',net_usd:null}},state);assert.equal(calls,2);assert.equal(loaded.gas.length,0);console.log('Fee/income precision, wallet scope, duplicates, missing data and fresh account checks passed.');})().catch(e=>{console.error(e);process.exitCode=1});

assert.equal(m.analyze({wallets:[{id:1,chain:'Ethereum'}],trades:[],history:[{...row,direction:'in'}]}).gas.length,0);console.log('Incoming transfers do not count sender gas as recipient portfolio fees.');

// Provider-verified payer identity survives gas-only, incoming and failed native activity.
for(const [chain,symbol,address] of [['Solana','SOL','payer'],['Sui','SUI','0x123']]){
 const wallet={id:1,chain,address};
 const native={...row,chain,asset:symbol,asset_id:chain+':native',from_address:null,fee_payer:address,fee:'0.000005'};
 for(const [direction,status] of [['self','confirmed'],['in','confirmed'],['self','failed']]){
  const event={...native,direction,status};
  const result=m.analyze({wallets:[wallet],trades:[],history:[event,{...event,event_id:'duplicate'}]});
  assert.equal(result.gas.length,1);assert.equal(result.gasTotals[0].amount,'0.000005');
 }
 assert.equal(m.analyze({wallets:[wallet],history:[{...native,direction:'out',fee_payer:'other'}]}).gas.length,0);
 assert.equal(m.analyze({wallets:[wallet],history:[{...native,direction:'in',fee_payer:null}]}).gas.length,0);
}
assert.equal(m.analyze({wallets:[{id:1,chain:'Ethereum',address:'0xrecipient'}],history:[{...row,direction:'in',from_address:'0xsender',fee_payer:'0xrecipient'}]}).gas.length,0);
