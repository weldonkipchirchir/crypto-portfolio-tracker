import time,unittest
from unittest.mock import patch
from backend.markets import coin_market as m,market_intelligence as intel

def row(identity='tokenized-example',rank=None):
 return {'id':identity,'name':'Synthetic asset','symbol':'SYN','market_cap_rank':rank,'current_price':2,'market_cap':None,'total_volume':10,'price_change_percentage_24h':-2,'price_change_percentage_30d_in_currency':4,'image':'https://coin-images.coingecko.com/coins/images/1/large/synthetic.png'}
class MarketCategoryTests(unittest.TestCase):
 def setUp(self):m.CACHE.clear();m.FAILURES.clear()
 def test_category_keeps_unranked_assets_and_missing_cap(self):
  with patch.object(m,'request',return_value=[row()]) as request:
   d=m.market_listings('stocks');self.assertEqual(len(d['coins']),1)
   self.assertIn('category=tokenized-stock',request.call_args.args[0]);self.assertIn('30d',request.call_args.args[0])
   self.assertIsNone(d['coins'][0]['market_cap_rank']);self.assertIsNone(d['coins'][0]['market_cap']);self.assertEqual(d['coins'][0]['price_change_percentage_30d'],'4')
   m.market_listings('stocks');self.assertEqual(request.call_count,1)
  self.assertIsNone(m.coin_row(row()))
 def test_trending_is_provider_search_order_not_cap_rank(self):
  payload={'coins':[{'item':{'id':'coin-b'}},{'item':{'id':'coin-a'}},{'item':{'id':'../bad'}},{'item':{'id':'coin-b'}}]}
  with patch.object(m,'request',side_effect=[payload,[row('coin-a',1),row('coin-b',2)]]) as request:
   d=m.market_listings('trending');self.assertEqual([r['id'] for r in d['coins']],['coin-b','coin-a']);self.assertEqual(request.call_count,2)
  with patch.object(m,'listings',return_value={'coins':[]}):self.assertEqual(m.allowed('coin-b'),'coin-b')
 def test_invalid_sections_make_no_request(self):
  with patch.object(m,'request') as request:
   for section in ('../secret','https://evil.test','unknown',None,True,[]):
    with self.assertRaises(ValueError):m.market_listings(section)
   request.assert_not_called()
 def test_empty_category_is_explicit_and_not_global_fallback(self):
  with patch.object(m,'request',return_value=[]):self.assertEqual(m.market_listings('prediction')['coins'],[])
 def test_persisted_discovered_identity_can_open_on_another_worker(self):
  normalized=m.coin_row(row(),require_rank=False);saved={'coins':[normalized],'fetched_at':int(time.time())}
  key=('fundamentals','intelligence-narrative','stocks')
  with m.persistence(lambda k:saved if k==key else None,lambda *a:None),patch.object(m,'listings',return_value={'coins':[]}):
   self.assertEqual(m.allowed('tokenized-example'),'tokenized-example')
   with self.assertRaises(ValueError):m.allowed('not-discovered')
 def test_unranked_detail_retains_token_identity_and_logo(self):
  payload={**row(),'description':{'en':'Synthetic tokenized product'},'image':{'large':row()['image']},'market_data':{'current_price':{'usd':2},'market_cap':{'usd':None}},'links':{'homepage':[]}}
  with patch.object(m,'allowed',return_value='tokenized-example'),patch.object(m,'request',return_value=payload):
   d=m.detail('tokenized-example')['coin'];self.assertEqual(d['id'],'tokenized-example');self.assertIsNone(d['market_cap_rank']);self.assertEqual(d['image'],row()['image'])
