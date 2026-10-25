import json,unittest,urllib.error
from unittest.mock import patch
import server,test_integrations
class AdvancedAPITests(test_integrations.APITests):
 def owned_wallet(self):
  self.call(self.a,'wallet',{'chain':'Base','address':'0x'+'1'*40,'label':'Owned'})
  with server.connect() as c:
   wallet=c.execute('SELECT id,user_id FROM wallets').fetchone()
   c.execute('INSERT INTO wallet_snapshots VALUES (?,?)',(wallet['id'],json.dumps({'quantity':'2','symbol':'ETH','updated_at':1000})))
   c.execute('INSERT INTO prices VALUES (?,?,?)',(wallet['user_id'],'ETH','10'))
   c.execute('INSERT INTO price_metadata VALUES (?,?,?,?)',(wallet['user_id'],'ETH','Test',1000))
  return wallet['user_id']
 def test_checkpoint_uses_server_data_and_isolation(self):
  self.owned_wallet()
  with patch('advanced_portfolio.time.time',return_value=1001):
   result=self.call(self.a,'checkpoint',{'user_id':999,'value_usd':'9999999','created_at':1})['checkpoint']
   self.assertEqual(result['value_usd'],'20');self.assertEqual(result['created_at'],1001)
   with self.assertRaises(urllib.error.HTTPError):self.call(self.a,'checkpoint',{})
  self.assertEqual(len(self.call(self.a,'state')['checkpoints']),1);self.assertEqual(self.call(self.b,'state')['checkpoints'],[])
 def test_watchlist_only_owns_identity_and_reversible(self):
  self.owned_wallet();identity='Base:native'
  with self.assertRaises(urllib.error.HTTPError):self.call(self.b,'watch-toggle',{'asset_id':identity,'user_id':1})
  result=self.call(self.a,'watch-toggle',{'asset_id':identity});self.assertTrue(result['watching'])
  self.assertEqual(self.call(self.b,'state')['watchlist'],[])
  self.assertEqual(self.call(self.a,'state')['watchlist'][0]['asset_id'],identity)
  self.assertFalse(self.call(self.a,'watch-toggle',{'asset_id':identity})['watching'])
 def test_advanced_static_routes_no_source_exposure(self):
  import urllib.request
  for path in ['/advanced_dashboard.js','/advanced_dashboard.css']:
   with urllib.request.urlopen('http://127.0.0.1:'+str(self.app.server_port)+path) as response:
    self.assertEqual(response.status,200);self.assertIn("script-src 'self'",response.headers['Content-Security-Policy'])
  with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen('http://127.0.0.1:'+str(self.app.server_port)+'/advanced_portfolio.py')
if __name__=='__main__':unittest.main()
