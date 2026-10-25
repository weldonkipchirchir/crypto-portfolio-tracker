import time,unittest
from unittest.mock import patch
from urllib.parse import urlsplit,parse_qs
import exchange_charts as e,coin_market as m
NOW=1792886400

def bn(ts,o='10',h='12',l='9',c='11'):return [ts,o,h,l,c,'1',ts+1000,'1',1,'1','1','0']
def cb(ts,o='10',h='12',l='9',c='11'):return [ts,l,h,o,c,1]
class ExchangeTests(unittest.TestCase):
 def setUp(self):
  m.CACHE.clear();m.FAILURES.clear()
  for target,kwargs in [('coin_market.allowed',{'side_effect':lambda x:x}),('exchange_charts.time.time',{'return_value':NOW})]:
   p=patch(target,**kwargs);p.start();self.addCleanup(p.stop)
 def meta(self,source='binance'):
  return {'symbols':[{'symbol':'BTCUSDT','baseAsset':'BTC','quoteAsset':'USDT'}]} if source=='binance' else {'id':'BTC-USD','base_currency':'BTC','quote_currency':'USD'}
 def test_binance_real_ohlc_and_quote(self):
  rows=[bn((NOW-3600)*1000),bn((NOW-1800)*1000,c='10'),bn((NOW-1800)*1000,c='99'),bn((NOW-1000)*1000,h='5'),bn((NOW+1000)*1000)]
  with patch('providers.request_json',side_effect=[self.meta(),rows]) as req:d=e.chart('bitcoin',1,'candles')
  self.assertEqual(len(d['candles']),2);self.assertEqual(d['quote_currency'],'USDT');self.assertEqual(d['pair'],'BTCUSDT');self.assertIn('USDT is not USD',d['coverage']);self.assertIn('startTime=',req.call_args.args[0]);self.assertIn('30m',req.call_args.args[0])
 def test_binance_all_since_earliest_weekly(self):
  with patch('providers.request_json',side_effect=[self.meta(),[bn(1502928000000),bn((NOW-86400)*1000)]]) as req:d=e.chart('bitcoin','max')
  q=parse_qs(urlsplit(req.call_args.args[0]).query);self.assertEqual(q['startTime'],['0']);self.assertEqual(q['interval'],['1w']);self.assertEqual(d['points'][0]['price'],'11');self.assertTrue(d['complete_request'])
 def test_full_response_cannot_claim_complete_all(self):
  with patch('providers.request_json',side_effect=[self.meta(),[bn((NOW-86400)*1000)]*1000]):
   with self.assertRaises(ValueError):e.chart('bitcoin','max')
 def test_exact_identity_validation(self):
  for metadata in [{'symbols':[{'symbol':'BTCUSDT','baseAsset':'ETH','quoteAsset':'USDT'}]},{'symbols':[]},{'symbols':[{'symbol':'BTCUSDT','baseAsset':'BTC','quoteAsset':'USD'}]}]:
   m.CACHE.clear();m.FAILURES.clear()
   with patch('providers.request_json',return_value=metadata):
    with self.assertRaises(ValueError):e.chart('bitcoin',1)
 def test_unsupported_ids_sources_ranges(self):
  with patch('providers.request_json') as req:
   for args in [('unverified-token',1),('bitcoin',True),('bitcoin',366),('bitcoin',1,'ohlc'),('bitcoin',1,'line','evil'),('bitcoin',1,'line',{})]:
    with self.assertRaises(ValueError):e.chart(*args)
   req.assert_not_called()
 def test_coinbase_ohlc_field_order_and_units(self):
  with patch('providers.request_json',side_effect=[self.meta('coinbase'),[cb(NOW-7200),cb(NOW-3600,c='10')]]) as req:d=e.chart('bitcoin',1,'candles','coinbase')
  self.assertEqual(d['source'],'Coinbase Exchange');self.assertEqual(d['quote_currency'],'USD');self.assertEqual(d['candles'][0]['high'],'12');self.assertEqual(d['candles'][0]['low'],'9');self.assertEqual(d['candles'][0]['timestamp'],(NOW-7200)*1000);self.assertIn('granularity=3600',req.call_args.args[0])
 def test_coinbase_all_paginates_from_2015_and_does_not_fill_gaps(self):
  calls=[]
  def request(url):
   calls.append(url)
   if '/candles?' not in url:return self.meta('coinbase')
   q=parse_qs(urlsplit(url).query)
   start=int(e.datetime.datetime.fromisoformat(q['start'][0].replace('Z','+00:00')).timestamp())
   return [cb(start),cb(start+86400)]
  with patch('providers.request_json',side_effect=request):d=e.chart('bitcoin','max','line','coinbase')
  self.assertEqual(d['history_start_requested'],e.COINBASE_START*1000);self.assertLessEqual(d['request_chunks'],16);self.assertGreater(d['request_chunks'],10);self.assertEqual(len(d['points']),d['request_chunks']*2);self.assertIn('2015-01-01',d['coverage']);self.assertIn('not the full history',d['coverage'])
 def test_coinbase_page_failure_never_caches_partial_all(self):
  with patch('providers.request_json',side_effect=[self.meta('coinbase'),[cb(e.COINBASE_START),cb(e.COINBASE_START+86400)],ValueError('outage')]):
   with self.assertRaises(ValueError):e.chart('bitcoin','max','line','coinbase')
  self.assertNotIn(('chart','exchange','coinbase','bitcoin','max','line'),m.CACHE)
 def test_coinbase_bound_and_invalid_rows(self):
  for rows in [[cb(NOW-3600)]*301,[cb(NOW-3600,h='NaN'),cb(NOW-7200,l='20')]]:
   m.CACHE.clear();m.FAILURES.clear()
   with patch('providers.request_json',side_effect=[self.meta('coinbase'),rows]):
    with self.assertRaises(ValueError):e.chart('bitcoin',1,'line','coinbase')
 def test_cache_preserves_old_timestamp_during_outage(self):
  rows=[bn((NOW-7200)*1000),bn((NOW-3600)*1000)]
  with patch('providers.request_json',side_effect=[self.meta(),rows]):first=e.chart('bitcoin',1)
  with patch('exchange_charts.time.time',return_value=NOW+400),patch('providers.request_json',side_effect=ValueError('bad')):last=e.chart('bitcoin',1)
  self.assertTrue(last['stale']);self.assertEqual(first['fetched_at'],last['fetched_at'])
if __name__=='__main__':unittest.main()
