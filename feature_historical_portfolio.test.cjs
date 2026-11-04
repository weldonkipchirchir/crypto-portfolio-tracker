const assert=require('node:assert/strict');require('./feature_historical_portfolio.js');
const {geometry,select}=global.OrbitHistoricalPortfolio;
const points=[{timestamp:1767225600,date:'2026-01-01',value:'10'},{timestamp:1767312000,date:'2026-01-02',value:'20'},{timestamp:1767484800,date:'2026-01-04',value:'0'}];
let chart=geometry(points);assert.equal(chart.segments.length,2);assert.equal(chart.dots[2].y,210);assert.equal(chart.dots[1].y,30);assert.equal(chart.dots[0].x,50);assert.equal(chart.dots[2].x,930);assert.equal(select(points,'2').length,1);assert.equal(geometry([points[0]]).dots[0].y,120);assert.equal(geometry([]).dots.length,0);
const html=global.OrbitFeatureModules.historical_portfolio.render({series:{connected:[]},coverage:'<script>'});assert(html.includes('&lt;script&gt;'));assert(!html.includes('<script>'));
console.log('Historical chart checks passed');

// Unknown observations never turn into zero-valued holdings, and unsorted input is chronological.
const unordered=[{timestamp:1767398400,value:30},{timestamp:1767225600,value:10},{timestamp:1767312000,value:null},{timestamp:1767312000,value:''},{timestamp:1767312000,value:false}];
assert.deepEqual(select(unordered,'all').map(p=>p.value),[10,30]);
assert.equal(geometry(unordered).segments.length,2);
// Calendar periods include the entire first UTC date, even when capture times differ.
const captures=[{timestamp:Date.parse('2026-01-01T01:00:00Z')/1000,value:10},{timestamp:Date.parse('2026-01-02T22:00:00Z')/1000,value:20}];
assert.equal(select(captures,'2').length,2);
assert.equal(geometry(captures).segments.length,1);
assert.equal(geometry([{timestamp:Infinity,value:10},{timestamp:1e30,value:10}]).dots.length,0);
