import unittest,urllib.error,urllib.request
from unittest.mock import patch
from tests.backend import test_integrations; from backend import server
class ResearchAPITests(test_integrations.APITests):
 def test_research_routes_and_auth(self):
  with self.assertRaises(urllib.error.HTTPError):self.call(self.client(),'intelligence-overview',{})
  for path,method,args in [('intelligence-overview','backend.markets.market_intelligence.overview',{}),('intelligence-narrative','backend.markets.market_intelligence.narratives',{'slug':'ai'}),('intelligence-rsi','backend.markets.market_intelligence.rsi',{}),('intelligence-venues','backend.markets.market_intelligence.venues',{'coin_id':'bitcoin'}),('intelligence-flow','backend.markets.market_microstructure.microstructure',{'coin_id':'bitcoin'}),('intelligence-derivatives','backend.markets.market_microstructure.derivatives',{'coin_id':'bitcoin'}),('intelligence-exposures','backend.markets.market_microstructure.exposures',{'coin_id':'bitcoin'})]:
   with patch(method,return_value={'ok':True}):self.assertTrue(self.call(self.a,path,args)['ok'])
  for path in ['/market_intelligence.js','/market_intelligence.css']:
   with urllib.request.urlopen('http://127.0.0.1:'+str(self.app.server_port)+path) as r:self.assertEqual(r.status,200)
  with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen('http://127.0.0.1:'+str(self.app.server_port)+'/market_watch.py')
 def test_watchlist_accounts_and_remove_without_network(self):
  with patch('backend.markets.market_watch.resolve',return_value={'id':'bitcoin','name':'Bitcoin','symbol':'BTC'}):self.assertEqual(self.call(self.a,'market-watch-toggle',{'coin_id':'bitcoin'})['coins'][0]['id'],'bitcoin')
  self.assertEqual(self.call(self.b,'market-watchlist',{})['coins'],[])
  with patch('backend.markets.market_watch.resolve') as req:self.assertEqual(self.call(self.a,'market-watch-toggle',{'coin_id':'bitcoin'})['coins'],[]);req.assert_not_called()
if __name__=='__main__':unittest.main()
