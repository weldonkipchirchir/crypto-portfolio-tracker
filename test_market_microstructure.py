import time,unittest
from unittest.mock import patch
import coin_market as m
import market_microstructure as x
NOW=1792954800
class MicrostructureTests(unittest.TestCase):
 def setUp(self):
  m.CACHE.clear();m.FAILURES.clear()
  for target,kwargs in [('coin_market.allowed',{'side_effect':lambda v:v}),('market_microstructure.time.time',{'return_value':NOW}),('market_microstructure.spot_metadata',{'return_value':None})]:
   p=patch(target,**kwargs);p.start();self.addCleanup(p.stop)
 def trade(self,**values):return dict(id=1,price='10000',qty='10',time=NOW*1000,isBuyerMaker=True,**values)
 def test_book_sorted_cumulative_and_aggressor(self):
  book={'bids':[['9','2'],['10','3']],'asks':[['12','4'],['11','1']]}
  with patch('providers.request_json',side_effect=[book,[self.trade(),dict(self.trade(),id=2,isBuyerMaker=False),dict(self.trade(),id=3,qty='1')]]):d=x.microstructure('bitcoin')
  b=d['orderbook'];t=d['large_trades'];self.assertTrue(b['available']);self.assertEqual(b['bids'][1]['cumulative_quantity'],'5');self.assertEqual(b['asks'][0]['price'],'11');self.assertEqual([r['direction'] for r in t['trades']],['sell','buy']);self.assertEqual(t['sample_size'],3);self.assertIn('USDT is not USD',b['coverage'])
 def test_feed_failure_independent(self):
  with patch('providers.request_json',side_effect=[ValueError('region'),[self.trade()]]):d=x.microstructure('bitcoin')
  self.assertFalse(d['orderbook']['available']);self.assertTrue(d['large_trades']['available'])
 def test_bad_book_and_trade_rejected(self):
  for book in [{'bids':[['12','1']],'asks':[['11','1']]},{'bids':[['9','1'],['9','2']],'asks':[['11','1']]},{'bids':[['NaN','1']],'asks':[['11','1']]}]:
   m.CACHE.clear();m.FAILURES.clear()
   with patch('providers.request_json',side_effect=[book,[dict(self.trade(),isBuyerMaker='false')]]):d=x.microstructure('bitcoin')
   self.assertFalse(d['orderbook']['available']);self.assertFalse(d['large_trades']['available'])
 def test_cache_stale_timestamp(self):
  book={'bids':[['9','1']],'asks':[['11','1']]}
  with patch('providers.request_json',side_effect=[book,[self.trade()]]):first=x.microstructure('bitcoin')
  with patch('market_microstructure.time.time',return_value=NOW+61),patch('providers.request_json',side_effect=ValueError('outage')):last=x.microstructure('bitcoin')
  self.assertTrue(last['orderbook']['stale']);self.assertEqual(first['orderbook']['fetched_at'],last['orderbook']['fetched_at'])
 def test_invalid_identity_or_venue_no_requests(self):
  with patch('providers.request_json') as r:
   for value in ['../../../etc','unverified-symbol']:
    with self.assertRaises(ValueError):x.microstructure(value)
   with self.assertRaises(ValueError):x.microstructure('bitcoin','evil')
   r.assert_not_called()
 def responses(self,url):
  if 'fapi.' in url:return [{'symbol':'BTCUSDT','longAccount':'.6','shortAccount':'.4','longShortRatio':'1.5','timestamp':NOW*1000}]
  if 'instruments-info' in url:return {'retCode':0,'result':{'list':[{'symbol':'BTCUSDT','baseCoin':'BTC','quoteCoin':'USDT'}]}}
  if 'account-ratio' in url and 'bybit' in url:return {'retCode':0,'result':{'list':[{'symbol':'BTCUSDT','buyRatio':'.75','sellRatio':'.25','timestamp':str(NOW*1000)}]}}
  if '/public/instruments' in url:return {'code':'0','data':[{'instId':'BTC-USDT-SWAP','ctValCcy':'BTC','settleCcy':'USDT'}]}
  return {'code':'0','data':[[str(NOW*1000),'2']]}
 def test_three_venues_definitions_and_units(self):
  with patch('providers.request_json',side_effect=self.responses):d=x.derivatives('bitcoin')
  self.assertTrue(all(r['available'] for r in d['venues']));self.assertEqual(d['venues'][0]['ratio'],'1.5');self.assertEqual(d['venues'][1]['ratio'],'3');self.assertAlmostEqual(float(d['venues'][2]['long_fraction']),2/3);self.assertIn('not solely',d['venues'][2]['coverage'])
 def test_ratio_failure_does_not_abort_other_venues(self):
  def req(url):
   if 'fapi.' in url:raise ValueError('restricted')
   return self.responses(url)
  with patch('providers.request_json',side_effect=req):d=x.derivatives('bitcoin')
  self.assertFalse(d['venues'][0]['available']);self.assertTrue(d['venues'][1]['available']);self.assertTrue(d['venues'][2]['available'])
 def test_identity_mismatch_not_disguised(self):
  def req(url):
   raw=self.responses(url)
   if 'instruments-info' in url:raw['result']['list'][0]['baseCoin']='EVIL'
   if '/public/instruments' in url:raw['data'][0]['ctValCcy']='EVIL'
   return raw
  with patch('providers.request_json',side_effect=req):d=x.derivatives('bitcoin')
  self.assertTrue(d['venues'][0]['available']);self.assertFalse(d['venues'][1]['available']);self.assertFalse(d['venues'][2]['available'])
 def test_zero_long_fraction_is_reported_as_zero(self):
  self.assertEqual(x.ratio('0','1',NOW*1000)['ratio'],'0')
 def test_invalid_fractions_and_timestamp(self):
  for args in [('.7','.5',NOW*1000),('NaN','.5',NOW*1000),('.6','.4',(NOW+1000)*1000),('.6','.4',(NOW-200000)*1000)]:
   with self.assertRaises(ValueError):x.ratio(*args)
if __name__=='__main__':unittest.main()
class ExposureTests(MicrostructureTests):
 def exposures_response(self,url):
  if 'premiumIndex' in url:return {'symbol':'BTCUSDT','lastFundingRate':'0','nextFundingTime':(NOW+3600)*1000,'markPrice':'100','time':NOW*1000}
  if '/fapi/v1/openInterest' in url:return {'symbol':'BTCUSDT','openInterest':'0','time':NOW*1000}
  if 'instruments-info' in url:return {'retCode':0,'result':{'list':[{'symbol':'BTCUSDT','baseCoin':'BTC','quoteCoin':'USDT','contractType':'LinearPerpetual'}]}}
  if '/tickers' in url:return {'retCode':0,'time':NOW*1000,'result':{'list':[{'symbol':'BTCUSDT','fundingRate':'-.0001','nextFundingTime':(NOW+3600)*1000,'openInterest':'10','openInterestValue':'1000','markPrice':'100'}]}}
  if '/public/instruments' in url:return {'code':'0','data':[{'instId':'BTC-USDT-SWAP','ctValCcy':'BTC','settleCcy':'USDT'}]}
  if '/funding-rate' in url:return {'code':'0','data':[{'instId':'BTC-USDT-SWAP','fundingRate':'.0002','fundingTime':(NOW+3600)*1000,'nextFundingTime':(NOW+7200)*1000,'ts':NOW*1000}]}
  return {'code':'0','data':[{'instId':'BTC-USDT-SWAP','oi':'42','oiUsd':'1234','ts':NOW*1000}]}
 def test_exposure_units_zero_negative_and_funding_schedule(self):
  with patch('providers.request_json',side_effect=self.exposures_response):d=x.exposures('bitcoin')
  b,y,o=d['venues'];self.assertTrue(all(r['available'] for r in d['venues']));self.assertEqual(b['funding_rate'],'0');self.assertEqual(b['open_interest'],'0');self.assertEqual(y['funding_rate'],'-0.0001');self.assertEqual(y['open_interest_quote'],'1000');self.assertNotIn('open_interest_usd',y);self.assertEqual(o['open_interest_unit'],'contracts');self.assertEqual(o['open_interest_usd'],'1234');self.assertEqual(o['next_funding_at'],(NOW+3600)*1000);self.assertNotIn('mark_price',o)
 def test_exposure_feed_failures_are_independent(self):
  def req(url):
   if 'fapi.binance' in url:raise ValueError('region')
   return self.exposures_response(url)
  with patch('providers.request_json',side_effect=req):d=x.exposures('bitcoin')
  self.assertFalse(d['venues'][0]['available']);self.assertTrue(d['venues'][1]['available']);self.assertTrue(d['venues'][2]['available'])
 def test_exposure_identity_mismatch(self):
  def req(url):
   raw=self.exposures_response(url)
   if 'premiumIndex' in url:raw['symbol']='ETHUSDT'
   if 'instruments-info' in url:raw['result']['list'][0]['contractType']='LinearFutures'
   if '/funding-rate' in url:raw['data'][0]['instId']='ETH-USDT-SWAP'
   return raw
  with patch('providers.request_json',side_effect=req):d=x.exposures('bitcoin')
  self.assertFalse(any(r['available'] for r in d['venues']))
 def test_exposure_bounds_and_stale_observation(self):
  def req(url):
   raw=self.exposures_response(url)
   if 'premiumIndex' in url:raw['lastFundingRate']='NaN'
   if '/tickers' in url:raw['time']=(NOW-700)*1000
   if '/funding-rate' in url:raw['data'][0]['fundingTime']=(NOW+300000)*1000
   return raw
  with patch('providers.request_json',side_effect=req):d=x.exposures('bitcoin')
  self.assertFalse(any(r['available'] for r in d['venues']))
 def test_exposure_stale_cache_keeps_source_times(self):
  with patch('providers.request_json',side_effect=self.exposures_response):first=x.exposures('bitcoin')
  with patch('market_microstructure.time.time',return_value=NOW+61),patch('providers.request_json',side_effect=ValueError('outage')):last=x.exposures('bitcoin')
  for a,b in zip(first['venues'],last['venues']):self.assertTrue(b['stale']);self.assertEqual(a['fetched_at'],b['fetched_at']);self.assertEqual(a['observed_at'],b['observed_at'])
