import json,tempfile,threading,unittest,urllib.request,urllib.error,http.cookiejar
from pathlib import Path
from unittest.mock import patch
import providers,server
class ProviderTests(unittest.TestCase):
 def test_addresses(self):
  self.assertEqual(providers.validate_address('Ethereum','0x'+'AB'*20),'0x'+'ab'*20)
  self.assertEqual(providers.validate_address('Sui','0x1'),'0x'+'0'*63+'1')
  for chain,address in [('Ethereum','invalid'),('Solana','0'*32),('Aptos','0xgg')]:
   with self.assertRaises(ValueError):providers.validate_address(chain,address)
 def test_native_units(self):
  for chain,result,expected in [('Ethereum',{'result':hex(10**18)},'1'),('Solana',{'result':{'value':10**9}},'1'),('Aptos',['100000000'],'1'),('Sui',{'data':{'address':{'balance':{'totalBalance':'1000000000'}}}},'1')]:
   address='1'*32 if chain=='Solana' else '0x'+'1'*40
   with patch('providers.request_json',return_value=result):self.assertEqual(providers.balance(chain,address)['quantity'],expected)
 def test_price_ids(self):
  with patch('providers.request_json',return_value={'ethereum':{'usd':2000,'last_updated_at':123}}):
   quotes=providers.market_prices(['ETH','FAKE']);self.assertEqual(quotes['ETH']['price'],'2000');self.assertNotIn('FAKE',quotes)
 def test_imported_coin_prices(self):
  ids={'NEAR':'near','UNI':'uniswap','AAVE':'aave','RENDER':'render-token','SUI':'sui','ENA':'ethena'}
  with patch('providers.request_json',return_value={coin:{'usd':2,'last_updated_at':123} for coin in ids.values()}):
   self.assertEqual(set(providers.market_prices(list(ids)+['UNKNOWN'])),set(ids))
class APITests(unittest.TestCase):
 def setUp(self):
  self.pricing_patch=patch('token_pricing.get_quote',return_value=None);self.pricing_patch.start();self.addCleanup(self.pricing_patch.stop)
  self.old_budget=server.PROVIDER_BUDGET;server.PROVIDER_BUDGET=server.ProviderBudget();server.AUTH_ATTEMPTS.clear()
  self.tmp=tempfile.TemporaryDirectory();self.old=server.DB;server.DB=Path(self.tmp.name)/'test.db';server.init()
  self.app=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);self.thread=threading.Thread(target=self.app.serve_forever,daemon=True);self.thread.start()
  self.a=self.client();self.b=self.client()
  for client,email in [(self.a,'a@test.com'),(self.b,'b@test.com')]:self.call(client,'register',{'email':email,'password':'test-password-123'})
 def tearDown(self):
  self.app.shutdown();self.app.server_close();self.thread.join();server.DB=self.old;server.PROVIDER_BUDGET=self.old_budget;self.tmp.cleanup()
 def client(self):return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def call(self,client,path,data=None):
  req=urllib.request.Request('http://127.0.0.1:'+str(self.app.server_port)+'/api/'+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
  with client.open(req) as r:return json.load(r)
 def test_import_dedup_and_isolation(self):
  data={'csv':'date,symbol,side,quantity,price\n2026-01-01,ETH,buy,2,100'}
  self.call(self.a,'import',data)
  with self.assertRaises(urllib.error.HTTPError) as error:self.call(self.a,'import',data)
  self.assertEqual(error.exception.code,400)
  self.assertEqual(len(self.call(self.a,'state')['trades']),1);self.assertEqual(self.call(self.b,'state')['trades'],[])
 def test_quotes_and_wallet_ownership(self):
  self.call(self.a,'wallet',{'chain':'Ethereum','address':'0x'+'1'*40,'label':'test'})
  with patch('providers.balance',return_value={'symbol':'ETH','quantity':'2','updated_at':100}):self.call(self.a,'sync',{})
  wid=self.call(self.a,'state')['wallets'][0]['id']
  with self.assertRaises(urllib.error.HTTPError):self.call(self.b,'remove-wallet',{'id':wid})
  with patch('providers.balance',side_effect=ValueError('Provider down')):self.call(self.a,'sync',{})
  snapshot=self.call(self.a,'state')['wallets'][0]['snapshot'];self.assertEqual(snapshot['quantity'],'2');self.assertEqual(snapshot['error'],'Provider down')
  with patch('providers.market_prices',return_value={'ETH':{'price':'2000','updated_at':123,'source':'CoinGecko'}}):self.call(self.a,'refresh-prices',{})
  self.assertEqual(self.call(self.a,'state')['price_metadata']['ETH']['price'],'2000')
  self.call(self.a,'remove-wallet',{'id':wid});self.assertEqual(self.call(self.a,'state')['wallets'],[])
if __name__=='__main__':unittest.main()
