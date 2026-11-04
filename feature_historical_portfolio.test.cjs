const assert=require('node:assert/strict');require('./feature_historical_portfolio.js');
const {geometry,select}=global.OrbitHistoricalPortfolio;
const points=[{timestamp:1767225600,date:'2026-01-01',value:'10'},{timestamp:1767312000,date:'2026-01-02',value:'20'},{timestamp:1767484800,date:'2026-01-04',value:'0'}];
let chart=geometry(points);assert.equal(chart.segments.length,2);assert.equal(chart.dots[2].y,210);assert.equal(chart.dots[1].y,30);assert.equal(chart.dots[0].x,50);assert.equal(chart.dots[2].x,930);assert.equal(select(points,'2').length,1);assert.equal(geometry([points[0]]).dots[0].y,120);assert.equal(geometry([]).dots.length,0);
const html=global.OrbitFeatureModules.historical_portfolio.render({series:{connected:[]},coverage:'<script>'});assert(html.includes('&lt;script&gt;'));assert(!html.includes('<script>'));
console.log('Historical chart checks passed');
