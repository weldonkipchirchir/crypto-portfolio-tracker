import unittest,time
from unittest.mock import patch
from decimal import Decimal
import coin_market as market
import market_footprint as f
NOW=1793534700
BASE=1793534400000
class FootprintTests(unittest.TestCase):
 def setUp(self):
  market.CACHE.clear();market.FAILURES.clear()
  for target,kwargs in [('market_footprint.time.time',{'return_value':NOW}),('coin_market.allowed',{'side_effect':lambda x:x}),('market_footprint.product',{'return_value':{'pair':'BTCUSDT','source':'Binance USDT Perpetual'}})]:
   p=patch(target,**kwargs);p.start();self.addCleanup(p.stop)
 def trade(self,i,t,p,q,side):return {'id':i,'timestamp':t,'price':str(p),'quantity':str(q),'side':side}
 def sample(self):
  rows=[self.trade(1,BASE-1000,99,1,'sell'),self.trade(2,BASE+100,100,2,'buy'),self.trade(3,BASE+200,101,3,'sell'),self.trade(4,BASE+300,102,4,'buy'),self.trade(5,BASE+60100,103,1,'buy')]
  return {'trades':rows,'observed_from':rows[0]['timestamp'],'observed_to':rows[-1]['timestamp'],'id_gaps':0}

 def test_historical_candles_are_verified_and_venue_specific(self):
  row=[BASE,'100','103','99','102','2',BASE+59999,'204',3,'1','102','0']
  with patch.object(f.providers,'request_json',return_value=[row]) as request:
   result=f.candle_history('bitcoin','perp','1')
   self.assertEqual(result['interval'],'1m');self.assertEqual(result['candles'][0]['close'],'102')
   self.assertIn('fapi.binance.com/fapi/v1/klines',request.call_args[0][0])
   self.assertIn('historical bid/ask footprints are not available',result['coverage'])
  with patch.object(f.providers,'request_json',return_value=[row]) as request:
   result=f.candle_history('bitcoin','spot','max')
   self.assertEqual(result['interval'],'1w');self.assertIn('startTime=0',request.call_args[0][0])
   self.assertIn('data-api.binance.vision',request.call_args[0][0])
 def test_historical_candles_reject_invalid_ohlc_and_options(self):
  for venue,days in [('bad','1'),('perp','all'),([], '1')]:
   with self.assertRaises(ValueError):f.candle_history('bitcoin',venue,days)
  with patch.object(f.providers,'request_json',return_value=[[BASE,'100','90','99','102','2',0,0,0,0,0,0]]):
   with self.assertRaises(ValueError):f.candle_history('bitcoin','perp','1')
 def test_volume_delta_vwap_and_coverage(self):
  result=f.aggregate(self.sample(),'1m','1',BASE+300000);bar=result['bars'][1]
  self.assertEqual(bar['volume'],'9');self.assertEqual(bar['delta'],'3');self.assertEqual(bar['buy'],'6');self.assertEqual(bar['sell'],'3');self.assertEqual(bar['notional'],'911');self.assertEqual(bar['prints'],3);self.assertEqual(bar['min_delta'],'-1');self.assertEqual(bar['max_delta'],'3');self.assertEqual(bar['poc'],'102');self.assertTrue(bar['complete']);self.assertFalse(result['bars'][0]['complete']);self.assertFalse(result['bars'][-1]['complete']);self.assertAlmostEqual(float(bar['vwap']),911/9)
  self.assertEqual(sum(Decimal(r['buy'])+Decimal(r['sell']) for r in bar['rows']),Decimal(bar['volume']))
 def test_gaps_and_forming_bars_never_claim_complete(self):
  sample=self.sample();sample['id_gaps']=1;self.assertFalse(any(b['complete'] for b in f.aggregate(sample,'1m','1',BASE+300000)['bars']))
  sample['trades']=sample['trades'][:4];sample['observed_to']=BASE+300
  bars=f.aggregate(sample,'1m','1',BASE+30000)['bars'];self.assertTrue(bars[-1]['forming']);self.assertFalse(bars[-1]['complete'])
 def test_bounded_backwards_pagination(self):
  def response(url,**kw):
   start=0 if 'fromId=0' in url else 1000
   return [{'a':i,'T':NOW*1000-10000+i,'p':'100','q':'1','m':i%2==0} for i in range(start,start+1000)]
  with patch('providers.request_json',side_effect=response) as request:sample=f.raw_trades('bitcoin','BTC','perp')
  self.assertEqual(len(sample['trades']),2000);self.assertEqual(sample['pages'],2);self.assertEqual(sample['id_gaps'],0);self.assertEqual(request.call_count,2)
 def test_bad_direction_or_conflicting_records_fail(self):
  for rows in [[{'a':1,'T':NOW*1000,'p':'1','q':'1','m':'false'}],[{'a':1,'T':NOW*1000,'p':'1','q':'1','m':True},{'a':1,'T':NOW*1000,'p':'2','q':'1','m':True}]]:
   market.CACHE.clear();market.FAILURES.clear()
   with patch('providers.request_json',return_value=rows):self.assertFalse(f.footprint('bitcoin')['available'])
 def test_invalid_options(self):
  for kwargs in [{'venue':[]},{'interval':[]},{'interval':'1s'},{'row_size':'0.00000000001'}]:
   with self.assertRaises(ValueError):f.footprint('bitcoin',**kwargs)
 def test_top_trader_accounts_and_positions_are_separate(self):
  def response(url,**kwargs):
   long='.6' if 'AccountRatio' in url else '.8';short='.4' if long=='.6' else '.2';ratio='1.5' if long=='.6' else '4'
   return [{'symbol':'BTCUSDT','longAccount':long,'shortAccount':short,'longShortRatio':ratio,'timestamp':NOW*1000}]
  with patch('providers.request_json',side_effect=response):result=f.top_traders('bitcoin')
  self.assertEqual(result['accounts']['latest']['long_fraction'],'0.6');self.assertEqual(result['positions']['latest']['long_fraction'],'0.8');self.assertEqual(result['positions']['latest']['ratio'],'4')
 def test_invalid_positions_do_not_hide_valid_account_feed(self):
  def response(url,**kwargs):return [{'symbol':'WRONG' if 'PositionRatio' in url else 'BTCUSDT','longAccount':'.5','shortAccount':'.5','longShortRatio':'1','timestamp':NOW*1000}]
  with patch('providers.request_json',side_effect=response):result=f.top_traders('bitcoin')
  self.assertTrue(result['accounts']['available']);self.assertFalse(result['positions']['available'])
 def test_top_history_supports_30_day_observations(self):
  rows=[{'symbol':'BTCUSDT','longAccount':'.5','shortAccount':'.5','longShortRatio':'1','timestamp':(NOW-i*86400)*1000} for i in range(30)]
  with patch('providers.request_json',return_value=rows):result=f.top_traders('bitcoin','1d')
  self.assertEqual(len(result['accounts']['history']),30)
if __name__=='__main__':unittest.main()
