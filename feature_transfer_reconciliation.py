"""Evidence-only internal transfer review. Never modifies trades or balances."""
import hashlib
import json
from collections import defaultdict
from decimal import Decimal, InvalidOperation

PREFIX = 'transfer-reconciliation:'

def _address(value):
    # EVM hex addresses are case insensitive; other chain addresses are not.
    return value.lower() if isinstance(value, str) and value.startswith('0x') else value

def _amount(value):
    if not isinstance(value, (str, int)) or len(str(value)) > 350:
        return None
    try:
        number = Decimal(str(value))
        return number if number.is_finite() and number > 0 and -255 <= number.as_tuple().exponent <= 78 and number.adjusted() <= 78 else None
    except InvalidOperation:
        return None

def candidates(wallets, records):
    owned = {w['id']: w for w in wallets}
    groups = defaultdict(dict)
    for row in records:
        wallet = owned.get(row.get('wallet_id'))
        if not wallet or row.get('status') != 'confirmed' or row.get('review_eligible') is False:
            continue
        chain = wallet['chain']
        if row.get('kind') not in ('native_transfer', 'token_transfer') or row.get('direction') not in ('in', 'out'):
            continue
        asset = row.get('asset_id')
        if not isinstance(asset, str) or not asset.startswith(chain + ':') or not row.get('hash') or not row.get('event_id'):
            continue
        source, target = _address(row.get('from_address')), _address(row.get('to_address'))
        address = _address(wallet['address'])
        if not source or not target or source == target:
            continue
        if (row['direction'] == 'out' and source != address) or (row['direction'] == 'in' and target != address):
            continue
        quantity = _amount(row.get('quantity'))
        if quantity is None:
            continue
        key = (chain, row['hash'], row['event_id'], asset, source, target, quantity)
        groups[key][wallet['id']] = row
    result = []
    for key, entries in groups.items():
        outgoing = [r for r in entries.values() if r['direction'] == 'out']
        incoming = [r for r in entries.values() if r['direction'] == 'in']
        # Multiple wallet/event interpretations require manual investigation.
        if len(outgoing) != 1 or len(incoming) != 1:
            continue
        sent, received = outgoing[0], incoming[0]
        if sent['wallet_id'] == received['wallet_id']:
            continue
        chain, txhash, event, asset, source, target, quantity = key
        identity = json.dumps([chain, txhash, event, asset, source, target, str(quantity), sent['wallet_id'], received['wallet_id']], separators=(',', ':'))
        result.append({'id': PREFIX + hashlib.sha256(identity.encode()).hexdigest(), 'chain': chain, 'hash': txhash,
                       'event_id': event, 'asset_id': asset, 'asset': str(sent.get('asset') or asset),
                       'quantity': str(quantity), 'from_wallet': owned[sent['wallet_id']]['label'],
                       'to_wallet': owned[received['wallet_id']]['label'], 'from_address': source, 'to_address': target,
                       'date': sent.get('date'), 'fee': sent.get('fee'),
                       'evidence': 'Both owned wallets report the same confirmed event, chain, transaction hash, asset identity, quantity and matching endpoints.',
                       'status': 'pending'})
    return sorted(result, key=lambda r: (str(r.get('date') or ''), r['id']), reverse=True)

def read(c, uid, raw):
    wallets = [dict(r) for r in c.execute('SELECT id,chain,address,label FROM wallets WHERE user_id=?', (uid,))]
    records = []
    for row in c.execute('SELECT h.wallet_id,h.data FROM chain_history h JOIN wallets w ON w.id=h.wallet_id WHERE w.user_id=?', (uid,)):
        try:
            item = json.loads(row['data'])
            if isinstance(item, dict):
                records.append({**item, 'wallet_id': row['wallet_id']})
        except (ValueError, TypeError):
            continue
    items = candidates(wallets, records)
    decisions = {r['review_id']: r['status'] for r in c.execute('SELECT review_id,status FROM review_decisions WHERE user_id=?', (uid,))}
    for item in items:
        item['status'] = decisions.get(item['id'], 'pending')
    return {'items': items[:200], 'total': len(items), 'history_count': len(records),
            'coverage': 'Saved wallet history only. Sync both wallets in Wallets first. Requires two matching direct transfer events; balance changes, bridges, exchanges, unmatched legs and incomplete history are excluded. Token identity is chain-qualified, not a verified ticker. Fees remain separate metadata. Review decisions do not change balances, cost basis, tax treatment or P&L.'}

def action(c, uid, raw):
    identifier, status = raw.get('id'), raw.get('status')
    if status not in ('confirmed', 'dismissed', 'pending'):
        raise ValueError('Choose confirmed, dismissed or pending')
    item = next((item for item in read(c, uid, {})['items'] if item['id'] == identifier), None)
    if item is None:
        raise ValueError('Transfer evidence is unavailable for this account; refresh the review')
    c.execute('INSERT INTO review_decisions(user_id,review_id,status,data) VALUES (?,?,?,?) ON CONFLICT(user_id,review_id) DO UPDATE SET status=EXCLUDED.status,data=EXCLUDED.data',
              (uid, identifier, status, json.dumps({'feature': 'transfer_reconciliation', 'evidence': item})))
    return {'ok': True, 'status': status}
