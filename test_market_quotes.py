import unittest
from unittest.mock import patch
import coin_market as m
import market_quotes as q
NOW=1792886400
class QuoteTests(unittest.TestCase):
 def setUp(self):
  m.CACHE.clear();m.FAILURES.clear()
  for name,kwargs in [('coin_market.allowed',{'side_effect':lambda x:x}),('market_quotes.time.time',{'return_value':NOW})]:
   p=patch(name,**kwargs);p.start();self.addCleanup(p.stop)
 def meta(self,source='binance'):
  return {'source':source,'pair':'BTCUSDT' if source=='binance' else 'BTC-USD','base_currency':'BTC','quote_currency':'USDT' if source=='binance' else 'USD'}
 def test_binance_receipt_time_not_trade_time_and_cache(self):
  with patch('exchange_charts.metadata',return_value=self.meta()),patch('providers.request_json',return_value={'symbol':'BTCUSDT','price':'67000.25'}) as request:
   result=q.quote('bitcoin','binance');self.assertEqual(result,q.quote('bitcoin','binance'));request.assert_called_once()
  self.assertEqual(result['quote_currency'],'USDT');self.assertIsNone(result['observed_at']);self.assertEqual(result['received_at'],NOW);self.assertEqual(result['timestamp_kind'],'received')
 def test_coinbase_event_timestamp(self):
  with patch('exchange_charts.metadata',return_value=self.meta('coinbase')),patch('providers.request_json',return_value={'price':'66000','time':q.exchange.iso(NOW-20)}):r=q.quote('bitcoin','coinbase')
  self.assertEqual(r['observed_at'],NOW-20);self.assertEqual(r['quote_currency'],'USD');self.assertEqual(r['timestamp_kind'],'last_trade')
 def test_invalid_provider_identity_no_network(self):
  with patch('providers.request_json') as request:
   for coin,source in [('../btc','binance'),('unknown','coinbase'),('bitcoin','evil'),('bitcoin',{}),('bitcoin',None)]:
    with self.assertRaises(ValueError):q.quote(coin,source)
   request.assert_not_called()
 def test_invalid_price_values(self):
  for value in [None,True,0,-1,'NaN','Infinity','1e100',{},'bad']:
   m.CACHE.clear();m.FAILURES.clear()
   with patch('exchange_charts.metadata',return_value=self.meta()),patch('providers.request_json',return_value={'symbol':'BTCUSDT','price':value}):
    with self.assertRaises(ValueError):q.quote('bitcoin','binance')
 def test_wrong_symbol_or_shape(self):
  for payload in [[],{}, {'symbol':'ETHUSDT','price':'100'}]:
   m.CACHE.clear();m.FAILURES.clear()
   with patch('exchange_charts.metadata',return_value=self.meta()),patch('providers.request_json',return_value=payload):
    with self.assertRaises(ValueError):q.quote('bitcoin','binance')
 def test_metadata_units_and_stale_rejected(self):
  for changes in [{'quote_currency':'USD'},{'base_currency':'ETH'},{'pair':'ETHUSDT'},{'stale':True}]:
   m.CACHE.clear();m.FAILURES.clear()
   with patch('exchange_charts.metadata',return_value=dict(self.meta(),**changes)),patch('providers.request_json') as request:
    with self.assertRaises(ValueError):q.quote('bitcoin','binance')
    request.assert_not_called()
 def test_coinbase_old_future_missing_time(self):
  for stamp in [None,'bad',q.exchange.iso(NOW-901),q.exchange.iso(NOW+61)]:
   m.CACHE.clear();m.FAILURES.clear()
   with patch('exchange_charts.metadata',return_value=self.meta('coinbase')),patch('providers.request_json',return_value={'price':'100','time':stamp}):
    with self.assertRaises(ValueError):q.quote('bitcoin','coinbase')
 def test_aggregate_identity_and_update_age(self):
  for coin in [{'id':'ethereum','current_price':'3','last_updated':NOW},{'id':'bitcoin','current_price':'3','last_updated':NOW-901},{'id':'bitcoin','current_price':'3','last_updated':True}]:
   m.CACHE.clear();m.FAILURES.clear()
   with patch('coin_market.detail',return_value={'coin':coin}):
    with self.assertRaises(ValueError):q.quote('bitcoin')
 def test_aggregate_valid(self):
  with patch('coin_market.detail',return_value={'coin':{'id':'bitcoin','current_price':'3','last_updated':NOW-1}}):r=q.quote('bitcoin')
  self.assertEqual(r['price'],'3');self.assertEqual(r['quote_currency'],'USD');self.assertEqual(r['observed_at'],NOW-1)
 def test_outage_preserves_original_times(self):
  with patch('exchange_charts.metadata',return_value=self.meta()),patch('providers.request_json',return_value={'symbol':'BTCUSDT','price':'123'}):first=q.quote('bitcoin','binance')
  with patch('market_quotes.time.time',return_value=NOW+30),patch('exchange_charts.metadata',side_effect=ValueError('outage')):r=q.quote('bitcoin','binance')
  self.assertTrue(r['stale']);self.assertEqual(r['received_at'],first['received_at']);self.assertEqual(r['fetched_at'],first['fetched_at'])
if __name__=='__main__':unittest.main()

