(function () {
  'use strict';
  const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  window.OrbitFeatureModules ||= {};
  window.OrbitFeatureModules.transfer_reconciliation = {
    title: 'Transfer review', category: 'Portfolio',
    description: 'Review matching transfers between your connected wallets using saved chain evidence.',
    load: async api => api('feature-read', {feature: 'transfer_reconciliation'}),
    render(data) {
      const items = Array.isArray(data.items) ? data.items : [];
      return `<section><h2>Transfers between your wallets</h2><p>${esc(data.coverage)}</p><p>${esc(data.total || 0)} matching candidates · ${esc(data.history_count || 0)} saved history events</p>
        ${items.length ? items.map(item => `<article style="padding:16px 0;border-bottom:1px solid var(--border,#344054)"><h3>${esc(item.quantity)} ${esc(item.asset)} · ${esc(item.status)}</h3><p>${esc(item.from_wallet)} → ${esc(item.to_wallet)} · ${esc(item.chain)} · ${esc(item.date || 'Date unavailable')}</p><p>${esc(item.evidence)}</p><details><summary>Inspect evidence</summary><dl><dt>Transaction hash</dt><dd style="overflow-wrap:anywhere">${esc(item.hash)}</dd><dt>Event</dt><dd style="overflow-wrap:anywhere">${esc(item.event_id)}</dd><dt>Asset identity</dt><dd style="overflow-wrap:anywhere">${esc(item.asset_id)}</dd><dt>From</dt><dd style="overflow-wrap:anywhere">${esc(item.from_address)}</dd><dt>To</dt><dd style="overflow-wrap:anywhere">${esc(item.to_address)}</dd><dt>Sender fee (separate)</dt><dd>${esc(item.fee == null ? 'Unavailable' : item.fee)}</dd></dl></details><p>Confirm only after inspecting the evidence. This records your review only.</p><div><button data-transfer-id="${esc(item.id)}" data-transfer-status="confirmed">Confirm internal transfer</button> <button data-transfer-id="${esc(item.id)}" data-transfer-status="dismissed">Dismiss candidate</button> <button data-transfer-id="${esc(item.id)}" data-transfer-status="pending">Reset review</button></div></article>`).join('') : '<p>No matching direct transfer evidence is available. Sync history for both connected wallets. An empty review does not prove there were no transfers.</p>'}
        ${data.total > items.length ? '<p>Showing the newest 200 candidates.</p>' : ''}</section>`;
    },
    bind(host, ctx) {
      host.querySelectorAll('[data-transfer-id]').forEach(button => button.addEventListener('click', async () => {
        const buttons = host.querySelectorAll('[data-transfer-id]');
        buttons.forEach(b => { b.disabled = true; });
        try {
          await ctx.api('feature-action', {feature: 'transfer_reconciliation', id: button.dataset.transferId, status: button.dataset.transferStatus});
          await ctx.reload();
        } catch (error) {
          ctx.error(error);
        } finally {
          buttons.forEach(b => { b.disabled = false; });
        }
      }));
    }
  };
})();
