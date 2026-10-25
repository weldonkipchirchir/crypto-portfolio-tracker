import unittest,urllib.error
from unittest.mock import patch
import server,imports,test_integrations
class PreviewTests(unittest.TestCase):
 def test_overlap_normalizes_quantities_and_dates(self):
  old=server.trade(dict(date='2026-01-01',symbol='ETH',side='buy',quantity='1.0',price='100.00'))
  result=imports.preview('date,symbol,side,quantity,price\n2026-01-01T00:00:00,eth,buy,1,100\n2026-01-02,ETH,buy,2,150',[old],server.trade,server.calculate)
  self.assertEqual(result['duplicates'],1);self.assertEqual(result['count'],1);self.assertEqual(result['errors'],[])
 def test_row_errors_and_missing_cost(self):
  result=imports.preview('date,symbol,side,quantity,price\n2026-01-01,ETH,sell,1,100',[],server.trade,server.calculate)
  self.assertTrue(result['errors']);self.assertEqual(result['errors'][0]['row'],0)
  result=imports.preview('date,symbol,side,quantity,price\nbad,ETH,buy,1,100',[],server.trade,server.calculate)
  self.assertEqual(result['errors'][0]['row'],2)
class FeatureAPITests(test_integrations.APITests):
 def test_preview_is_read_only_and_import_skips_overlap(self):
  csv='date,symbol,side,quantity,price\n2026-01-01,ETH,buy,1,100'
  result=self.call(self.a,'import-preview',{'csv':csv});self.assertEqual(result['count'],1);self.assertEqual(self.call(self.a,'state')['trades'],[])
  self.call(self.a,'import',{'csv':csv})
  result=self.call(self.a,'import',{'csv':csv+'\n2026-01-02,ETH,buy,2,200'})
  self.assertEqual(result['imported'],1);self.assertEqual(result['duplicates'],1);self.assertEqual(len(self.call(self.a,'state')['trades']),2)
 def test_token_inspection_requires_ownership(self):
  self.call(self.a,'wallet',{'chain':'Ethereum','address':'0x'+'1'*40})
  wid=self.call(self.a,'state')['wallets'][0]['id']
  with patch('token_integrations.token_balances',return_value={'tokens':[],'coverage':'explicit contracts','errors':[]}):
   result=self.call(self.a,'wallet-details',{'id':wid});self.assertEqual(result['tokens']['tokens'],[]);self.assertEqual(result['activity']['items'],[])
   with self.assertRaises(urllib.error.HTTPError) as error:self.call(self.b,'wallet-details',{'id':wid})
   self.assertEqual(error.exception.code,400)
 def test_solana_activity_is_not_trades(self):
  self.call(self.a,'wallet',{'chain':'Solana','address':'1'*32})
  wid=self.call(self.a,'state')['wallets'][0]['id']
  with patch('token_integrations.token_balances',return_value={'tokens':[],'errors':[]}),patch('token_integrations.recent_activity',return_value={'activities':[{'signature':'sig','slot':1,'timestamp':0,'failed':False}],'coverage':'metadata','next_cursor':None}):
   result=self.call(self.a,'wallet-details',{'id':wid});self.assertEqual(result['activity']['items'][0]['status'],'Confirmed');self.assertIn('1970-01-01',result['activity']['items'][0]['timestamp'])
  self.assertEqual(self.call(self.a,'state')['trades'],[])
 def test_concurrent_sales_cannot_oversell(self):
  from concurrent.futures import ThreadPoolExecutor
  self.call(self.a,'trade',{'date':'2026-01-01','symbol':'ETH','side':'buy','quantity':1,'price':100})
  def sell(_):
   try:self.call(self.a,'trade',{'date':'2026-01-02','symbol':'ETH','side':'sell','quantity':1,'price':150});return 200
   except urllib.error.HTTPError as error:return error.code
  with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(sell,range(2)))
  self.assertEqual(sorted(statuses),[200,400]);state=self.call(self.a,'state');self.assertEqual(state['assets'][0]['quantity'],0);self.assertEqual(len(state['trades']),2)
 def test_provider_limit_returns_429(self):
  with patch.object(server,'PROVIDER_BUDGET',server.ProviderBudget(limit=1)),patch('providers.market_prices',return_value={'ETH':{'price':'100','source':'CoinGecko','updated_at':123}}):
   self.call(self.a,'refresh-prices',{})
   with self.assertRaises(urllib.error.HTTPError) as error:self.call(self.a,'refresh-prices',{})
   self.assertEqual(error.exception.code,429)
 def test_static_routes_have_strict_script_policy(self):
  import urllib.request
  for path in ['/app.js','/styles.css','/']:
   with urllib.request.urlopen('http://127.0.0.1:'+str(self.app.server_port)+path) as r:
    self.assertEqual(r.status,200);self.assertIn("script-src 'self';",r.headers['Content-Security-Policy'])
if __name__=='__main__':unittest.main()
