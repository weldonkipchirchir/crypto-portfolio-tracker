/* Wallet-only insights. API: OrbitInsights.render(state, {now: unixSeconds?}) -> HTML.
 * Parent supplies CSS for insights-* classes. No ledger holdings or inferred costs.
 * bind(container) is intentionally a no-op; native <progress> remains accessible.
 */
(function (global) {
  'use strict';
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const valid = value => {if(typeof value==='number')return Number.isFinite(value)&&value>=0;if(typeof value!=='string'||value.length>350||!/^\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$/.test(value))return false;const exp=Number(value.split(/[eE]/)[1]||0);return exp>=-255&&exp<=78&&Number.isFinite(Number(value))&&Number(value)>=0;};
  const expired = (stamp, now) => !valid(stamp) || Number(stamp) <= 0 || now - Number(stamp) > 900 || Number(stamp) - now > 300;
  const usd = value => new Intl.NumberFormat('en-US', {style:'currency',currency:'USD',maximumFractionDigits:2}).format(value);
  function render(input, helpers) {
    const state = input && typeof input === 'object' ? input : {};
    const wallets = Array.isArray(state.wallets) ? state.wallets : [];
    const now = valid(helpers?.now) ? Number(helpers.now) : Date.now() / 1000;
    const groups = new Map();
    let total = 0, priced = 0, unpriced = 0, unpricedTokens = 0, invalid = 0, stale = 0, unsynced = 0, undiscovered = 0;
    function add(chain, value, isStale, asset) {
      if (!valid(value) || !Number.isFinite(total + Number(value))) {invalid++;return;}
      const amount = Number(value);
      total += amount;priced++;if (isStale) stale++;
      const key=helpers?.allocation==='token'?asset:chain;
      const group = groups.get(key) || {value:0,count:0,stale:0};
      group.value += amount;group.count++;if (isStale) group.stale++;
      groups.set(key, group);
    }
    wallets.forEach(wallet => {
      if (!wallet || typeof wallet !== 'object') {invalid++;return;}
      const chain = typeof wallet.chain === 'string' && wallet.chain ? wallet.chain : 'Unknown chain';
      const native = wallet.snapshot;
      if (!native || !valid(native.quantity)) {unsynced++;if (native?.quantity != null) invalid++;}
      else if (Number(native.quantity) > 0) {
        const quote = state.price_metadata?.[native.symbol];
        if (!quote || !valid(quote.price)) unpriced++;
        else {
          const value = Number(native.quantity) * Number(quote.price);
          add(chain,value,Boolean(native.error || native.stale || quote.stale) || expired(native.updated_at,now) || expired(quote.updated_at,now),String(native.symbol||'Native')+' · '+chain);
        }
      }
      if (!wallet.token_snapshot) undiscovered++;
      const tokens = Array.isArray(wallet.token_snapshot?.tokens) ? wallet.token_snapshot.tokens : [];
      tokens.forEach(token => {
        if (!token || !valid(token.quantity)) {invalid++;return;}
        if (Number(token.quantity) === 0) return;
        if (!valid(token.value_usd) || !valid(token.price_usd)) {unpriced++;unpricedTokens++;return;}
        add(chain,token.value_usd,Boolean(token.stale || token.price_stale) || expired(token.price_fetched_at,now) || expired(wallet.token_snapshot.updated_at,now),String(token.symbol||'Unknown token')+' · '+chain+' · '+String(token.contract||token.mint||token.asset_id||'unknown'));
      });
    });
    const quality = '<ul class="insights-quality"><li>'+unsynced+' wallet native balances unavailable</li><li>'+undiscovered+' wallets without token discovery</li><li>'+unpriced+' nonzero holdings unpriced and excluded ('+unpricedTokens+' tokens)</li><li>'+invalid+' invalid amounts excluded</li><li>'+stale+' included holdings use stale balances or quotes</li><li>Purchase records are required for cost basis and P&amp;L; wallet balances alone do not establish purchase cost.</li></ul>';
    const coverage = '<p class="insights-caption">Wallet balances only · '+priced+' holdings valued · '+unpriced+' unpriced · '+stale+' stale. Token discovery may be incomplete. Recorded trade holdings are excluded from these totals.</p>';
    if (!wallets.length) return '<section class="insights-panel" aria-label="Wallet allocation and data quality"><h2>Wallet allocation</h2><p>Connect an address to see allocation from available wallet balances and quotes.</p>'+quality+'</section>';
    const rows = [...groups.entries()].sort((a,b) => b[1].value-a[1].value || a[0].localeCompare(b[0])).map(([chain,group]) => {
      const percent = total > 0 ? Math.min(100,group.value/total*100) : 0;
      const percentText = percent > 0 && percent < 0.1 ? '&lt;0.1%' : percent.toFixed(1)+'%';
      return '<li class="insights-allocation-row"><div class="insights-allocation-label"><strong>'+escape(chain)+'</strong><span class="insight-amount">'+usd(group.value)+' · '+percentText+'</span></div><progress class="insights-allocation-bar" max="100" value="'+percent.toFixed(6)+'" aria-label="'+escape(chain)+' share of known wallet value">'+percentText+'</progress><span class="insights-caption">'+group.count+' holdings valued'+(group.stale?' · '+group.stale+' stale':'')+'</span></li>';
    }).join('');
    return '<section class="insights-panel" aria-label="Wallet allocation and data quality"><div class="insights-heading"><h2>Wallet allocation by '+(helpers?.allocation==='token'?'token':'chain')+'</h2><strong class="insight-amount">'+(priced?usd(total):'Unpriced')+'</strong></div><p class="insights-caption">Approximate known USD value. Percentages apply only to valued holdings; unknown prices are never treated as zero.</p>'+coverage+(total>0?'<ul class="insights-allocation">'+rows+'</ul>':'<p>No positive priced wallet value is available yet. Sync balances and refresh quotes to populate allocation.</p>')+'</section><section class="insights-panel" aria-label="Wallet data health"><h2>Data health</h2>'+quality+'</section>';
  }
  global.OrbitInsights = Object.freeze({render,bind:function () {}});
})(window);
