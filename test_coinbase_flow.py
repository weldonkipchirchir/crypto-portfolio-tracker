import unittest,datetime
from unittest.mock import patch
import market_microstructure as x
import coin_market as m
NOW=1793563200
class CoinbaseTests(unittest.TestCase):
 def setUp(self):
  m.CACHE.clear();m.FAILURES.clear()
  for target,kwargs in [('coin_market.allowed',{'side_effect':lambda x:x}),('market_microstructure.time.time',{'return_value':NOW}),('exchange_charts.metadata',{'return_value':{'source':'coinbase','pair':'BTC-USD'}})]:
   p=patch(target,**kwargs);p.start();self.addCleanup(p.stop)
 def responses(self,url):
  if '/book?' in url:return {'bids':[['99','2',7],['98','3',2]],'asks':[['101','4',9],['102','5',3]]}
  return [{'trade_id':1,'time':datetime.datetime.fromtimestamp(NOW,datetime.timezone.utc).isoformat(),'price':'100000','size':'2','side':'sell'},{'trade_id':2,'time':datetime.datetime.fromtimestamp(NOW,datetime.timezone.utc).isoformat(),'price':'100000','size':'1','side':'buy'}]
 def test_units_aggregation_and_maker_reversal(self):
  with patch('providers.request_json',side_effect=self.responses):data=x.microstructure('bitcoin','coinbase')
  book=data['orderbook'];trades=data['large_trades'];self.assertTrue(book['available']);self.assertEqual(book['quote_currency'],'USD');self.assertEqual(book['bids'][0]['quantity'],'2');self.assertEqual(book['bids'][0]['notional'],'198');self.assertEqual(book['asks'][1]['cumulative_quantity'],'9');self.assertEqual([r['direction'] for r in trades['sample_trades']],['buy','sell'])
 def test_auction_rejected_independently(self):
  def response(url):
   raw=self.responses(url)
   if isinstance(raw,dict):raw['auction_mode']=True
   return raw
  with patch('providers.request_json',side_effect=response):data=x.microstructure('bitcoin','coinbase')
  self.assertFalse(data['orderbook']['available']);self.assertTrue(data['large_trades']['available'])
 def test_invalid_trade_side_is_not_guessed(self):
  def response(url):
   raw=self.responses(url)
   if isinstance(raw,list):raw[0]['side']='invalid'
   return raw
  with patch('providers.request_json',side_effect=response):data=x.microstructure('bitcoin','coinbase')
  self.assertTrue(data['orderbook']['available']);self.assertFalse(data['large_trades']['available'])
 def test_duplicate_and_crossed_book_rejected(self):
  for bids in [[['101','1',1]],[['99','1',1],['99','1',2]]]:
   m.CACHE.clear();m.FAILURES.clear()
   with patch('providers.request_json',side_effect=lambda url:{'bids':bids,'asks':[['100','1',1]]} if '/book?' in url else []):self.assertFalse(x.microstructure('bitcoin','coinbase')['orderbook']['available'])
if __name__=='__main__':unittest.main()
