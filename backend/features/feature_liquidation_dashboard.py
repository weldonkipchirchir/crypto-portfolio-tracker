"""Public OKX observation configuration; no retired REST endpoint or paid key."""
def read(c, uid, raw):
    pair = raw.get('pair', 'BTC-USDT-SWAP')
    if pair not in ('BTC-USDT-SWAP', 'ETH-USDT-SWAP'):
        raise ValueError('Choose BTC or ETH USDT perpetual')
    return {'pair': pair, 'venue': 'OKX', 'quote': 'USDT', 'events': [],
            'status': 'idle', 'source': 'wss://ws.okx.com:8443/ws/v5/public',
            'docs': 'https://www.okx.com/docs-v5/en/#public-data-websocket-liquidation-orders-channel',
            'limit': 100, 'observation_ms': 8000}
