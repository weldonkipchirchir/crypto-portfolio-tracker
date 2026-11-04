"""Bounded, read-only Binance USDT perpetual history; no synthetic observations."""
import copy
import math
import threading
import time
from urllib.parse import urlencode
import exchange_charts
import market_microstructure
import providers

ASSETS = {key: exchange_charts.ASSETS[key] for key in ('bitcoin', 'ethereum', 'solana')}
PERIODS = {'5m': 300000, '1h': 3600000, '4h': 14400000, '1d': 86400000}
DOCS = 'https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data'
_CACHE = {}
_LOCK = threading.Lock()


def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError, OverflowError):
        return None


def stamp(value, start, end):
    n = number(value)
    return int(n) if n is not None and n == int(n) and start <= n <= end else None


def observations(body, kind, symbol, start, end):
    if not isinstance(body, list) or len(body) > 500:
        raise ValueError('Invalid or oversized public history')
    points = {}
    for row in body:
        if kind == 'price':
            if not isinstance(row, list) or len(row) != 12:
                continue
            t = stamp(row[0], start, end)
            price, volume = number(row[1]), number(row[5])
            close_time = stamp(row[6], start, end)
            if price is None or price <= 0:
                continue
            point = {'price': price, 'volume': volume if volume is not None and volume >= 0 and close_time is not None else None}
        else:
            if not isinstance(row, dict) or row.get('symbol') != symbol:
                continue
            t = stamp(row.get('timestamp' if kind == 'oi' else 'fundingTime'), start, end)
            if kind == 'oi':
                quantity, value = number(row.get('sumOpenInterest')), number(row.get('sumOpenInterestValue'))
                if quantity is None or value is None or min(quantity, value) < 0:
                    continue
                point = {'oi_coin': quantity, 'oi_quote': value}
            else:
                rate = number(row.get('fundingRate'))
                if rate is None or abs(rate) > 1:
                    continue
                point = {'funding_rate': rate}
        if t is not None:
            points[t] = point
    return points


def align(feeds):
    """Outer join exact original timestamps; missing fields stay null."""
    fields = ('price', 'volume', 'oi_coin', 'oi_quote', 'funding_rate')
    return [dict(timestamp=t, **{field: next((feed[t][field] for feed in feeds.values() if t in feed and field in feed[t]), None) for field in fields})
            for t in sorted(set().union(*(set(feed) for feed in feeds.values())))]


def read(c, uid, raw):
    coin, period = raw.get('coin_id', 'bitcoin'), raw.get('period', '1h')
    if not isinstance(coin, str) or coin not in ASSETS:
        raise ValueError('Choose bitcoin, ethereum or solana by verified coin ID')
    if not isinstance(period, str) or period not in PERIODS:
        raise ValueError('Choose period 5m, 1h, 4h or 1d')
    identity, base = market_microstructure.identity(coin)
    now = int(time.time() * 1000)
    key = (identity, period)
    with _LOCK:
        cached = _CACHE.get(key)
        if cached and now - cached[0] < 300000:
            result = copy.deepcopy(cached[1]); result['cached'] = True
            return result
    # At most 288 intervals, and less than Binance's rolling month retention.
    start = now - min(29 * 86400000, 288 * PERIODS[period])
    symbol = base + 'USDT'
    common = {'symbol': symbol, 'startTime': start, 'endTime': now, 'limit': 500}
    paths = {'price': ('/fapi/v1/klines', {'interval': period}),
             'oi': ('/futures/data/openInterestHist', {'period': period}),
             'funding': ('/fapi/v1/fundingRate', {})}
    feeds, errors = {}, {}
    # Shared deadline bounds all three sequential calls, including partial failure.
    with providers.deadline(time.monotonic() + 15):
        for kind, (path, extra) in paths.items():
            try:
                body = providers.request_json('https://fapi.binance.com' + path + '?' + urlencode(dict(common, **extra)))
                feeds[kind] = observations(body, kind, symbol, start, now)
            except Exception:
                feeds[kind] = {}
                errors[kind] = 'Public history unavailable; retry later.'
    result = {'coin_id': identity, 'assets': ASSETS, 'base': base, 'symbol': symbol, 'venue': 'Binance USDⓈ-M perpetual',
              'quote': 'USDT', 'period': period, 'start': start, 'end': now, 'fetched_at': now,
              'rows': align(feeds), 'errors': errors, 'cached': False, 'source_url': DOCS,
              'counts': {name: len(feed) for name, feed in feeds.items()},
              'partial': bool(errors) or any(not feed for feed in feeds.values())}
    with _LOCK:
        _CACHE[key] = (now, copy.deepcopy(result))
        while len(_CACHE) > 12:
            _CACHE.pop(next(iter(_CACHE)))
    return result
