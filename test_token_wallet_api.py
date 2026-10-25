"""Account isolation and persisted token inventory API regressions."""
import copy,json,unittest,urllib.error
from unittest.mock import patch
import server,test_integrations
from runtime_security import ProviderBudget

CONTRACT='0x'+'2'*40
SECOND='0x'+'3'*40

class TokenWalletAPITests(unittest.TestCase):
 client=test_integrations.APITests.client
 call=test_integrations.APITests.call
 def setUp(self):
  server.AUTH_ATTEMPTS.clear();self.old_budget=server.PROVIDER_BUDGET;server.PROVIDER_BUDGET=ProviderBudget(limit=100)
  test_integrations.APITests.setUp(self)
  self.call(self.a,'wallet',{'chain':'Ethereum','address':'0x'+'1'*40,'label':'Token owner'})
  self.wid=self.call(self.a,'state')['wallets'][0]['id']
  self.discovery={'contracts':[CONTRACT],'coverage':'Partial index inventory','errors':[],'has_more':False}
  self.snapshot={'tokens':[{'asset_id':'Ethereum:'+CONTRACT,'contract':CONTRACT,'quantity':'5','decimals':18,'symbol':'<img src=x onerror=alert(1)>','name':'<script>bad()</script>','identity_verified':False}],'errors':[],'coverage':'Unverified ERC20','updated_at':123}
 def tearDown(self):test_integrations.APITests.tearDown(self);server.PROVIDER_BUDGET=self.old_budget
 def invoke(self,client=None,path='discover-tokens',data=None,result=None,discovery=None):
  with patch('token_discovery.discover',return_value=copy.deepcopy(discovery or self.discovery)),patch('token_integrations.token_balances',return_value=copy.deepcopy(result or self.snapshot)):
   return self.call(client or self.a,path,data or {'id':self.wid})
 def state(self):return self.call(self.a,'state')
 def test_ownership_before_any_provider_request(self):
  for path in ['discover-tokens','wallet-details']:
   with patch('token_discovery.discover') as discover,patch('token_integrations.token_balances') as balances:
    with self.assertRaises(urllib.error.HTTPError):self.call(self.b,path,{'id':self.wid})
    discover.assert_not_called();balances.assert_not_called()
 def test_contract_limit_and_type_before_provider(self):
  for path in ['discover-tokens','wallet-details']:
   for contracts in [[CONTRACT]*21,CONTRACT,{},[None],['https://evil.example']]:
    with patch('token_discovery.discover') as discover,patch('token_integrations.token_balances') as balances:
     with self.assertRaises(urllib.error.HTTPError) as error:self.call(self.a,path,{'id':self.wid,'contracts':contracts})
     self.assertEqual(error.exception.code,400);discover.assert_not_called();balances.assert_not_called()
 def test_snapshot_owner_only_and_no_ledger_creation(self):
  self.invoke();state=self.state()
  self.assertEqual(len(state['wallets'][0]['token_snapshot']['tokens']),1)
  self.assertEqual(self.call(self.b,'state')['wallets'],[]);self.assertEqual(state['trades'],[]);self.assertEqual(state['assets'],[])
 def test_repeat_replaces_snapshot_without_duplicates(self):
  self.invoke();self.invoke()
  self.assertEqual(len(self.state()['wallets'][0]['token_snapshot']['tokens']),1)
  with server.connect() as c:self.assertEqual(c.execute('SELECT count(*) FROM wallet_tokens').fetchone()[0],1)
 def test_zero_does_not_retain_previous_positive_quantity(self):
  self.invoke();zero=copy.deepcopy(self.snapshot);zero['tokens'][0]['quantity']='0'
  self.invoke(result=zero);token=self.state()['wallets'][0]['token_snapshot']['tokens'][0]
  self.assertEqual(token['quantity'],'0');self.assertFalse(token.get('stale',False))
 def test_partial_error_preserves_previous_as_stale(self):
  self.invoke();partial={'tokens':[],'errors':['Temporary provider failure'],'coverage':'Partial','updated_at':456}
  self.invoke(result=partial);token=self.state()['wallets'][0]['token_snapshot']['tokens'][0]
  self.assertEqual(token['quantity'],'5');self.assertTrue(token['stale'])
 def test_watchlist_saved_and_reused(self):
  self.invoke(path='wallet-details',data={'id':self.wid,'contracts':[CONTRACT,CONTRACT,SECOND]})
  with server.connect() as c:
   watched=json.loads(c.execute('SELECT contracts FROM token_watchlist WHERE wallet_id=?',(self.wid,)).fetchone()[0])
   self.assertEqual(watched,[CONTRACT,SECOND])
  with patch('token_discovery.discover',return_value=copy.deepcopy(self.discovery)),patch('token_integrations.token_balances',return_value=copy.deepcopy(self.snapshot)) as balances:
   self.call(self.a,'discover-tokens',{'id':self.wid})
   self.assertEqual(balances.call_args.args[2],[CONTRACT,SECOND]);self.assertTrue(balances.call_args.kwargs['include_metadata'])
 def test_wallet_delete_removes_private_token_data(self):
  self.invoke();self.call(self.a,'remove-wallet',{'id':self.wid})
  with server.connect() as c:
   self.assertEqual(c.execute('SELECT count(*) FROM wallet_tokens').fetchone()[0],0)
   self.assertEqual(c.execute('SELECT count(*) FROM token_watchlist').fetchone()[0],0)
 def test_metadata_is_untrusted_data(self):
  self.invoke();token=self.state()['wallets'][0]['token_snapshot']['tokens'][0]
  self.assertFalse(token['identity_verified']);self.assertEqual(token['symbol'],self.snapshot['tokens'][0]['symbol'])

if __name__=='__main__':unittest.main()
