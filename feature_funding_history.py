"""Bounded public perpetual funding observations; no account credentials."""
import copy
import math
import time
import threading
from urllib.parse import urlencode
import exchange_charts
import providers

_CACHE = {}
_LOCK = threading.Lock()
TTL = 300
DOCS = {'Binance':'https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History','Bybit':'https://bybit-exchange.github.io/docs/v5/market/history-fund-rate'}


def number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError, OverflowError):
        return None


def venue(name, symbol, start, end):
    limit = 1000 if name == 'Binance' else 200
    query = {'symbol':symbol, 'startTime':start, 'endTime':end, 'limit':limit}
    if name == 'Binance':
        url = 'https://fapi.binance.com/fapi/v1/fundingRate?'
    else:
        query['category'] = 'linear'
        url = 'https://api.bybit.com/v5/market/funding/history?'
    body = providers.request_json(url + urlencode(query))
    if name == 'Bybit':
        if not isinstance(body, dict) or body.get('retCode') != 0:
            raise ValueError('Bybit rejected funding history')
        body = (body.get('result') or {}).get('list')
    if not isinstance(body, list) or len(body) > limit:
        raise ValueError('Invalid or oversized funding response')
    points = {}
    for row in body:
        if not isinstance(row, dict) or row.get('symbol') != symbol:
            continue
        stamp = number(row.get('fundingTime' if name == 'Binance' else 'fundingRateTimestamp'))
        rate = number(row.get('fundingRate'))
        if stamp is None or stamp != int(stamp) or not start <= stamp <= end or rate is None or abs(rate) > 1:
            continue
        points[int(stamp)] = {'timestamp':int(stamp), 'rate':rate}
    ordered = [points[t] for t in sorted(points)]
    for i, row in enumerate(ordered):
        row['observed_spacing_hours'] = (row['timestamp'] - ordered[i-1]['timestamp']) / 3600000 if i else None
    return {'name':name, 'symbol':symbol, 'quote':'USDT', 'points':ordered, 'truncated':len(body)==limit,
            'source_url':DOCS[name], 'error':None}


def read(c, uid, raw):
    coin = raw.get('coin_id', 'bitcoin')
    if not isinstance(coin, str) or coin not in exchange_charts.ASSETS:
        raise ValueError('Choose a verified asset identity')
    now = int(time.time() * 1000)
    with _LOCK:
        cached = _CACHE.get(coin)
        if cached and now - cached[0] < TTL * 1000:
            result = copy.deepcopy(cached[1]); result['cached'] = True
            return result
    start = now - 30 * 86400000
    symbol = exchange_charts.ASSETS[coin] + 'USDT'
    venues = []
    for name in DOCS:
        try:
            venues.append(venue(name, symbol, start, now))
        except Exception:
            venues.append({'name':name, 'symbol':symbol, 'quote':'USDT', 'points':[], 'truncated':False,
                           'source_url':DOCS[name], 'error':'Public funding history unavailable; retry later.'})
    result = {'coin_id':coin, 'assets':exchange_charts.ASSETS, 'start':start, 'end':now, 'fetched_at':now,
              'venues':venues, 'cached':False, 'partial':any(v['error'] or v['truncated'] or not v['points'] for v in venues)}
    with _LOCK:
        _CACHE[coin] = (now, copy.deepcopy(result))
        while len(_CACHE) > len(exchange_charts.ASSETS):
            _CACHE.pop(next(iter(_CACHE)))
    return result
