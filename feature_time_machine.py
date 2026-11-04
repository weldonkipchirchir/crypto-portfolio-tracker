"""Browse actual saved observations; never backcast current balances."""
import json
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import advanced_portfolio as ap

COVERAGE = ('Actual saved observations only. Select a UTC date to see the latest saved observation on or before that day. '
            'Connected daily totals, wallet checkpoints and detailed wallet captures have different coverage and remain separate. '
            'Captures copy already saved wallet balances and quotes without refreshing providers. Capture time is not balance observation time. '
            'Unknown historical costs remain unknown; values exclude unpriced holdings and are not returns.')


def init(c):
    c.execute('CREATE TABLE IF NOT EXISTS time_machine_snapshots(user_id INTEGER NOT NULL,id TEXT NOT NULL,captured_at INTEGER NOT NULL,data TEXT NOT NULL,PRIMARY KEY(user_id,id))')
    c.execute('CREATE INDEX IF NOT EXISTS time_machine_owner_date ON time_machine_snapshots(user_id,captured_at)')


def action(c, uid, raw):
    if raw.get('operation') != 'capture':
        raise ValueError('Unknown time machine operation')
    now = int(time.time())
    previous = c.execute('SELECT captured_at FROM time_machine_snapshots WHERE user_id=? ORDER BY captured_at DESC LIMIT 1', (uid,)).fetchone()
    if previous and now - previous['captured_at'] < 60:
        raise ValueError('Wait one minute between captures')
    if c.execute('SELECT COUNT(*) AS n FROM time_machine_snapshots WHERE user_id=?', (uid,)).fetchone()['n'] >= 365:
        raise ValueError('Detailed capture limit reached (365)')
    wallets = []
    for r in c.execute('SELECT w.id,w.chain,w.address,w.label,s.data,t.data AS token_data FROM wallets w LEFT JOIN wallet_snapshots s ON s.wallet_id=w.id LEFT JOIN wallet_tokens t ON t.wallet_id=w.id WHERE w.user_id=?', (uid,)):
        w = dict(r)
        w['snapshot'] = json.loads(w.pop('data') or 'null')
        w['token_snapshot'] = json.loads(w.pop('token_data') or 'null')
        wallets.append(w)
    quotes = {r['symbol']: dict(r) for r in c.execute('SELECT p.symbol,p.price,m.updated_at FROM prices p LEFT JOIN price_metadata m ON m.user_id=p.user_id AND m.symbol=p.symbol WHERE p.user_id=?', (uid,))}
    holdings = []
    seen = set()
    total = Decimal(0)
    with localcontext() as context:
        context.prec = 700
        for a in ap.assets(wallets):
            w = a['wallet']
            key = (w['id'], a['asset_id'])
            if key in seen:
                continue
            seen.add(key)
            if len(holdings) >= 2000:
                raise ValueError('Capture exceeds 2000 wallet holdings')
            quantity = ap.number(a['quantity'])
            if quantity == 0:
                continue
            row = a['row']
            quote = quotes.get(ap.providers.CHAINS[a['chain']][0], {}) if a['native'] else row
            price = ap.number(quote.get('price') if a['native'] else quote.get('price_usd'))
            value = quantity * price if quantity is not None and price is not None else None
            if value is not None:
                total += value
            balance_stamp = row.get('updated_at') if a['native'] else (w.get('token_snapshot') or {}).get('updated_at')
            quote_stamp = quote.get('updated_at') if a['native'] else row.get('price_fetched_at')
            holdings.append({'asset_id':a['asset_id'], 'symbol':a['symbol'], 'wallet':w['label'] or str(w['id']), 'chain':a['chain'],
                             'quantity':str(quantity) if quantity is not None else None, 'price_usd':str(price) if price is not None else None,
                             'value_usd':str(value) if value is not None else None, 'cost_usd':None,
                             'balance_observed_at':balance_stamp, 'price_observed_at':quote_stamp,
                             'stale':bool(row.get('error') or row.get('stale') or row.get('price_stale') or ap.stale(balance_stamp,now) or ap.stale(quote_stamp,now))})
    if not holdings:
        raise ValueError('No saved nonzero wallet holdings are available to capture')
    data = {'timestamp':now, 'value':str(total) if any(h['value_usd'] is not None for h in holdings) else None,
            'holdings':holdings, 'partial':any(h['value_usd'] is None for h in holdings), 'stale':any(h['stale'] for h in holdings)}
    identity = uuid.uuid4().hex
    c.execute('INSERT INTO time_machine_snapshots VALUES (?,?,?,?)', (uid,identity,now,json.dumps(data)))
    return {'ok':True, 'captured_at':now}


def read(c, uid, raw):
    source = raw.get('source','connected')
    if source not in ('connected','wallets','detailed'):
        raise ValueError('Choose a saved observation source')
    requested = raw.get('date') or datetime.now(timezone.utc).date().isoformat()
    try:
        day = datetime.strptime(requested,'%Y-%m-%d').date()
        if day.isoformat() != requested:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('Choose a valid UTC date') from None
    cutoff = int(datetime(day.year,day.month,day.day,tzinfo=timezone.utc).timestamp()) + 86399
    if source == 'connected':
        rows = c.execute('SELECT data FROM portfolio_daily_values WHERE user_id=? AND day<=? ORDER BY day DESC LIMIT 2001',(uid,requested))
    elif source == 'wallets':
        rows = c.execute('SELECT data FROM portfolio_checkpoints WHERE user_id=? AND created_at<=? ORDER BY created_at DESC,id DESC LIMIT 2001',(uid,cutoff))
    else:
        rows = c.execute('SELECT data FROM time_machine_snapshots WHERE user_id=? AND captured_at<=? ORDER BY captured_at DESC,id DESC LIMIT 2001',(uid,cutoff))
    selected = None
    for r in rows:
        try:
            d = json.loads(r['data'])
            stamp = int(d['observed_at'] if source=='connected' else d['created_at'] if source=='wallets' else d['timestamp'])
            if stamp < 0 or stamp > cutoff:
                continue
            actual = datetime.fromtimestamp(stamp,timezone.utc).date()
            value = d.get('value_usd') if source=='wallets' else d.get('value')
            if value is not None and ap.number(value) is None:
                continue
            candidate = {'timestamp':stamp,'date':actual.isoformat(),'offset_days':(day-actual).days,'value':value,
                         'holdings':d.get('holdings') if source=='detailed' else None,
                         'partial':bool(d.get('partial') or d.get('unpriced') or d.get('unpriced_count') or d.get('truncated')),
                         'stale':bool(d.get('stale') or d.get('stale_count'))}
            if selected is None or stamp > selected['timestamp']:
                selected = candidate
        except (ValueError,TypeError,KeyError,OverflowError,OSError):
            continue
    return {'source':source,'date':requested,'observation':selected,'coverage':COVERAGE}
