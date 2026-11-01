const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const c={window:{},URL,Intl,Date,Number,Map,Set,WeakMap};vm.createContext(c);vm.runInContext(fs.readFileSync('market_intelligence.js','utf8'),c);const ui=c.window.OrbitIntelligence;
const book=ui.bookAnalytics({bids:[{price:99,quantity:2}],asks:[{price:101,quantity:3}],quote_currency:'USDT'});
assert(book.includes('USDT'));assert(!book.includes('NaN'));assert(!book.includes('$'));
const trades=ui.tradeCharts({sample_trades:[{timestamp:1700000000000,notional:'100',direction:'buy'},{timestamp:1700000060000,notional:'40',direction:'sell'}],quote_currency:'USDT'});
assert(trades.includes('<svg'));assert(trades.includes('USDT'));assert(!trades.includes('NaN'));assert(!trades.includes('$'));assert(!ui.tradeCharts({sample_trades:[]}).includes('<polyline'));
console.log('Order-flow charts preserve quote units and valid graph geometry.');
