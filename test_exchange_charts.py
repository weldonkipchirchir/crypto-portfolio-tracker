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
  self.assertEqual(len(d['candles']),2);self.assertEqual(d['quote_currency'],'USDT');self.assertEqual(d['pair'],'BTCUSDT');self.assertEqual(d['candles'][0]['volume'],'1');self.assertIn('USDT is not USD',d['coverage']);self.assertIn('startTime=',req.call_args.args[0]);self.assertIn('30m',req.call_args.args[0])
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
class ExplicitIntervalTests(ExchangeTests):
 def test_explicit_binance_four_hour_and_cache_identity(self):
  start=NOW//14400*14400-28800
  with patch('providers.request_json',side_effect=[self.meta(),[bn(start*1000),bn((start+14400)*1000)]]) as req:
   data=e.chart('bitcoin',7,'candles','binance','4h')
  self.assertEqual(data['interval_code'],'4h');self.assertEqual(data['interval_seconds'],14400)
  self.assertIn('interval=4h',req.call_args.args[0]);self.assertEqual(len(data['candles']),2)
  self.assertIn(('chart','exchange','binance','bitcoin',7,'candles','4h'),m.CACHE)
  self.assertNotIn(('chart','exchange','binance','bitcoin',7,'candles'),m.CACHE)
 def test_explicit_invalid_or_too_large_interval(self):
  for interval in ('2h',True,{},''):
   with self.assertRaises(ValueError):e.chart('bitcoin',7,'candles','binance',interval)
  for source in ('coinbase','binance'):
   m.CACHE.clear();m.FAILURES.clear()
   with patch('providers.request_json',return_value=self.meta(source)) as req:
    with self.assertRaisesRegex(ValueError,'shorter range'):e.chart('bitcoin','max','candles',source,'1h')
   self.assertEqual(req.call_count,0)
 def test_aggregate_four_hour_exact_ohlc_missing_and_forming(self):
  start=NOW//14400*14400-43200
  points=[]
  for i in range(12):
   if i==6:continue
   points.append({'timestamp':(start+i*3600)*1000,'open':str(i+10),'high':str(i+12),'low':str(i+9),'close':str(i+11)})
  result,omitted=e.aggregate(points,14400,3600,start+11*3600)
  self.assertEqual(len(result),1);self.assertEqual(omitted,2)
  self.assertEqual(result[0],{'timestamp':start*1000,'open':'10','high':'15','low':'9','close':'14'})
 def test_weekly_monday_alignment(self):
  monday=1792368000 # 2026-10-19 UTC Monday
  self.assertEqual(e.datetime.datetime.fromtimestamp(monday,e.datetime.timezone.utc).weekday(),0)
  points=[{'timestamp':(monday+i*86400)*1000,'open':'10','high':'12','low':'9','close':'11'} for i in range(14)]
  result,omitted=e.aggregate(points,604800,86400,monday+14*86400)
  self.assertEqual([p['timestamp'] for p in result],[monday*1000,(monday+604800)*1000]);self.assertEqual(omitted,0)
 def test_coinbase_four_hour_actual_base_interval(self):
  start=NOW//14400*14400-86400
  def request(url):
   if '/candles?' not in url:return self.meta('coinbase')
   self.assertIn('granularity=3600',url)
   return [cb(start+i*3600,o=str(i+10),h=str(i+12),l=str(i+9),c=str(i+11)) for i in range(24)]
  with patch('providers.request_json',side_effect=request):data=e.chart('bitcoin',1,'candles','coinbase','4h')
  self.assertEqual(data['interval_seconds'],14400);self.assertEqual(len(data['candles']),6)
  self.assertEqual(data['candles'][0]['close'],'14');self.assertIn('incomplete and still-forming',data['coverage'])
 def test_explicit_binance_pagination_progress_guard(self):
  start=NOW//3600*3600-3600
  with patch('providers.request_json',side_effect=[self.meta(),[bn(start*1000)]*1000,[bn(start*1000)]*1000]):
   with self.assertRaises(ValueError):e.chart('bitcoin',7,'candles','binance','1h')

class NewIntervalTests(unittest.TestCase):
 setUp=ExchangeTests.setUp
 meta=ExchangeTests.meta
 def test_new_native_binance_intervals(self):
  for code,seconds in [('1m',60),('5m',300),('30m',1800),('6h',21600)]:
   m.CACHE.clear();start=(NOW//seconds-2)*seconds
   with patch('providers.request_json',side_effect=[self.meta(),[bn(start*1000),bn((start+seconds)*1000)]]) as req:
    result=e.chart('bitcoin',1,'candles','binance',code)
   self.assertEqual(result['interval_seconds'],seconds);self.assertIn('interval='+code,req.call_args.args[0]);self.assertEqual(len(result['candles']),2)
 def test_new_native_coinbase_interval(self):
  start=NOW//21600*21600-43200
  with patch('providers.request_json',side_effect=[self.meta('coinbase'),[cb(start),cb(start+21600)]]) as req:result=e.chart('bitcoin',1,'candles','coinbase','6h')
  self.assertEqual(result['interval_seconds'],21600);self.assertIn('granularity=21600',req.call_args.args[0])

 def test_weekly_all_has_enough_real_bars_for_ema200(self):
  last=e.bucket_start(NOW,604800);rows=[bn((last-(400-i)*604800)*1000) for i in range(401)]
  with patch('providers.request_json',side_effect=[self.meta(),rows]) as request:result=e.chart('bitcoin','max','candles','binance','1w')
  self.assertEqual(len(result['candles']),401);self.assertEqual(result['interval_seconds'],604800);self.assertIn('startTime=0',request.call_args.args[0]);self.assertIn('interval=1w',request.call_args.args[0])

if __name__=='__main__':unittest.main()
