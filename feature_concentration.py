"""Bounded, read-only provider taxonomy samples for concentration."""
import copy
import threading
import time
from urllib.parse import urlencode
import coin_market as market
import market_intelligence as intelligence
import providers

# Official taxonomy: https://www.coingecko.com/en/categories/stablecoins
CATEGORIES = {'stablecoin': ('Stablecoins', 'stablecoins'), **intelligence.NARRATIVES}
CACHE = {}
LOCK = threading.RLock()
TTL = 900
FAILURE_TTL = 60

def read(c, uid, raw):
    category = raw.get('category', 'stablecoin')
    if not isinstance(category, str) or category not in CATEGORIES:
        raise ValueError('Unsupported concentration category')
    name, category_id = CATEGORIES[category]
    with LOCK:
        cached = CACHE.get(category)
        if cached and time.monotonic() < cached[0]:
            return copy.deepcopy(cached[1])
        result = {'category': category, 'category_id': category_id, 'name': name,
                  'source': 'CoinGecko', 'source_url': 'https://www.coingecko.com/en/categories/' + category_id,
                  'available': False, 'coin_ids': [], 'stale': False, 'fetched_at': None,
                  'coverage': 'Up to 250 ranked assets from one category page. Positive exact CoinGecko ID membership only; absent assets are unclassified, never confirmed nonmembers.'}
        try:
            cutoff = min(getattr(providers._REQUEST_CONTEXT, 'cutoff', None) or float('inf'), time.monotonic() + 8)
            with providers.deadline(cutoff):
                if category == 'stablecoin':
                    coins = market.request('/coins/markets?' + urlencode({'vs_currency': 'usd', 'category': category_id, 'order': 'market_cap_desc', 'per_page': 250, 'page': 1, 'sparkline': 'false'}))
                else:
                    payload = intelligence.narratives(category)
                    coins = payload.get('coins')
                    result['stale'] = bool(payload.get('stale'))
                    result['fetched_at'] = payload.get('fetched_at')
            if not isinstance(coins, list) or not 1 <= len(coins) <= 250:
                raise ValueError('Invalid category sample')
            ids = set()
            for row in coins:
                if not isinstance(row, dict): continue
                try: ids.add(market.identifier(row.get('id')))
                except ValueError: continue
            if not ids: raise ValueError('No valid category identities')
            result.update(available=True, coin_ids=sorted(ids), fetched_at=result['fetched_at'] or int(time.time()))
        except (ValueError, OSError, TimeoutError):
            result['error'] = 'Provider taxonomy unavailable. No classification is inferred; retry later.'
        CACHE[category] = (time.monotonic() + (TTL if result['available'] else FAILURE_TTL), result)
        return copy.deepcopy(result)
