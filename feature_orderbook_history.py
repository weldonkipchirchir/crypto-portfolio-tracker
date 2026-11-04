"""Account-scoped, explicitly captured quoted order-book samples."""
import json
import time
from decimal import Decimal
import exchange_charts
import market_microstructure as micro

LIMIT = 120
INTERVAL = 60000  # Existing verified depth feed caches for 60 seconds.

def init(c):
    c.execute('CREATE TABLE IF NOT EXISTS orderbook_history (user_id INTEGER NOT NULL, coin TEXT NOT NULL, venue TEXT NOT NULL, observed_at BIGINT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(user_id,coin,venue,observed_at))')

def validate(book, coin, venue, now):
    base = exchange_charts.ASSETS[coin]
    quote = 'USD' if venue == 'coinbase' else 'USDT'
    pair = base + ('-USD' if venue == 'coinbase' else 'USDT')
    if book.get('available') is not True or book.get('pair') != pair or book.get('base_currency') != base or book.get('quote_currency') != quote:
        raise ValueError('Verified depth for this exact instrument is unavailable')
    stamp = book.get('observed_at')
    if type(stamp) is not int or not now-120000 <= stamp <= now+1000:
        raise ValueError('Depth snapshot is stale')
    result = {'observed_at':stamp, 'bids':[], 'asks':[]}
    for side, reverse in [('bids',True),('asks',False)]:
        rows = book.get(side)
        if not isinstance(rows,list) or not 1 <= len(rows) <= 100:
            raise ValueError('Invalid depth levels')
        seen = set()
        for row in rows:
            price, qty = micro.positive(row.get('price')), micro.positive(row.get('quantity'))
            if price in seen: raise ValueError('Duplicate depth level')
            seen.add(price)
            result[side].append({'price':str(price),'quantity':str(qty),'notional':str(price*qty)})
        result[side].sort(key=lambda r:Decimal(r['price']), reverse=reverse)
    if Decimal(result['bids'][0]['price']) >= Decimal(result['asks'][0]['price']):
        raise ValueError('Crossed depth snapshot')
    return result

def read(c, uid, raw):
    coin, venue = raw.get('coin_id','bitcoin'), raw.get('venue','coinbase')
    if not isinstance(coin,str) or coin not in exchange_charts.ASSETS or venue not in ('coinbase','binance'):
        raise ValueError('Choose a verified asset and spot venue')
    operation = raw.get('operation','history')
    if operation not in ('history','capture'): raise ValueError('Unknown history operation')
    rows = c.execute('SELECT observed_at,payload FROM orderbook_history WHERE user_id=? AND coin=? AND venue=? ORDER BY observed_at',(uid,coin,venue)).fetchall()
    message = None
    if operation == 'capture':
        now = int(time.time()*1000)
        if rows and now-rows[-1]['observed_at'] < INTERVAL:
            message = 'Wait at least 60 seconds between samples; cached snapshots are not duplicated.'
        else:
            book = micro.microstructure(coin,venue)['orderbook']
            sample = validate(book,coin,venue,now)
            if rows and sample['observed_at']-rows[-1]['observed_at'] < INTERVAL:
                message = 'The public feed has not supplied a new sample yet.'
            else:
                c.execute('INSERT INTO orderbook_history(user_id,coin,venue,observed_at,payload) VALUES (?,?,?,?,?)',(uid,coin,venue,sample['observed_at'],json.dumps(sample)))
                stamps = [r['observed_at'] for r in rows] + [sample['observed_at']]
                if len(stamps)>LIMIT:
                    c.execute('DELETE FROM orderbook_history WHERE user_id=? AND coin=? AND venue=? AND observed_at<?',(uid,coin,venue,stamps[-LIMIT]))
                c.commit()
                rows = c.execute('SELECT observed_at,payload FROM orderbook_history WHERE user_id=? AND coin=? AND venue=? ORDER BY observed_at',(uid,coin,venue)).fetchall()
    samples = [json.loads(r['payload']) for r in rows]
    for i,s in enumerate(samples):
        s['gap_ms'] = s['observed_at']-samples[i-1]['observed_at'] if i else None
    base = exchange_charts.ASSETS[coin]
    return {'coin_id':coin,'venue':venue,'pair':base+('-USD' if venue=='coinbase' else 'USDT'),'quote':'USD' if venue=='coinbase' else 'USDT','base':base,'assets':exchange_charts.ASSETS,'samples':samples,'message':message,'limit':LIMIT,'interval_ms':INTERVAL}
