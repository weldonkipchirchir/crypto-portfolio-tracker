import time,unittest
from unittest.mock import patch
import coin_market as m

def row(identity='bitcoin',rank=1):return {'id':identity,'name':'Bitcoin','symbol':'btc','market_cap_rank':rank,'current_price':12.5,'market_cap':100,'total_volume':10,'circulating_supply':20,'max_supply':21,'last_updated':'2026-01-01T00:00:00Z'}
class MarketTests(unittest.TestCase):
 def setUp(self):m.CACHE.clear();m.FAILURES.clear()
 def test_ranked_deduplicated_and_unknown_values(self):
  bad=row('bad',2);bad['market_cap']=float('nan');bad['current_price']=None
  with patch('providers.request_json',return_value=[row('second',2),row(),row(),bad]):data=m.listings()
  self.assertEqual([c['id'] for c in data['coins']],['bitcoin','bad','second']);self.assertIsNone(data['coins'][1]['market_cap']);self.assertIsNone(data['coins'][1]['current_price'])
 def test_ids_reject_traversal_and_unknown(self):
  for value in ['../secret','https://evil','Bitcoin',True,'x'*101]:
   with self.assertRaises(ValueError):m.identifier(value)
  with patch('providers.request_json',return_value=[row()]):
   with self.assertRaises(ValueError):m.detail('not-listed')
 def test_numeric_validation(self):
  for value in [True,'NaN','Infinity','-1','1e999','1e-999'] :self.assertIsNone(m.numeric(value))
  self.assertEqual(m.numeric(0),'0');self.assertEqual(m.numeric('-2',True),'-2')
 def test_cache_ttl_and_fallback(self):
  with patch('coin_market.time.time',return_value=1700000000),patch('providers.request_json',return_value=[row()]):first=m.listings()
  with patch('coin_market.time.time',return_value=1700000100),patch('providers.request_json') as req:self.assertEqual(m.listings()['fetched_at'],first['fetched_at']);req.assert_not_called()
  with patch('coin_market.time.time',return_value=1700000400),patch('providers.request_json',side_effect=ValueError('down')):fallback=m.listings()
  self.assertTrue(fallback['stale']);self.assertEqual(fallback['fetched_at'],first['fetched_at'])
 def test_persistent_cache_avoids_network(self):
  data={'coins':[row()],'source':'CoinGecko','fetched_at':1700000000,'stale':False}
  with patch('coin_market.time.time',return_value=1700000010),patch('providers.request_json') as req,m.persistence(lambda key:data,lambda *args:None):self.assertEqual(len(m.listings()['coins']),1);req.assert_not_called()
 def test_provider_payload_bounds(self):
  with patch('providers.request_json',return_value=[row()]*251):
   with self.assertRaises(ValueError):m.listings()
 def test_description_and_https_links(self):
  self.assertEqual(m.text('<p>Hello</p><script>bad()</script><b>world</b>',100),'Hello world')
  self.assertIsNone(m.url('javascript:alert(1)'));self.assertIsNone(m.url('https://user:password@example.com'));self.assertEqual(m.url('https://example.com'),'https://example.com')
 def test_detail_identity_and_supply_unknown(self):
  payload={'id':'bitcoin','name':'Bitcoin','symbol':'btc','market_cap_rank':1,'market_data':{'current_price':{'usd':12},'max_supply':None,'circulating_supply':20},'description':{'en':'<b>Hello</b>'},'links':{'homepage':['javascript:evil','https://bitcoin.org']}}
  with patch('providers.request_json',side_effect=[[row()],payload]):d=m.detail('bitcoin')
  self.assertEqual(d['coin']['description'],'Hello');self.assertIsNone(d['coin']['max_supply']);self.assertEqual(d['coin']['website'],'https://bitcoin.org')
 def test_chart_uses_only_real_valid_points(self):
  now=int(time.time()*1000);points=[[now-3000,10],[now-2000,11],[now-2000,99],[now-1000,float('nan')],[now+1000000,1],[1,1]]
  with patch('providers.request_json',side_effect=[[row()],{'prices':points}]):data=m.chart('bitcoin',1)
  self.assertEqual([p['price'] for p in data['points']],['10','11']);self.assertEqual(len(data['points']),2)
 def test_chart_range_validation(self):
  with patch('providers.request_json',return_value=[row()]):
   for days in [True,365,'../']:
    with self.assertRaises(ValueError):m.chart('bitcoin',days)
if __name__=='__main__':unittest.main()
