import os,unittest
from unittest.mock import patch
import providers,history,history_bnb,token_integrations,server,test_integrations
class ExtraChainTests(unittest.TestCase):
 def test_address_balance_identity_and_rpc(self):
  for chain,symbol in [('Base','ETH'),('Arbitrum','ETH'),('Polygon','POL'),('Avalanche','AVAX'),('Sonic','S'),('Gnosis','XDAI'),('Celo','CELO')]:
   self.assertEqual(providers.validate_address(chain,'0x'+'AB'*20),'0x'+'ab'*20)
   with patch('providers.request_json',return_value={'result':hex(10**18)}) as request:
    result=providers.balance(chain,'0x'+'1'*40);self.assertEqual(result['quantity'],'1');self.assertEqual(result['symbol'],symbol);self.assertEqual(request.call_args.args[1]['method'],'eth_getBalance')
 def test_token_read_only_support(self):
  for chain in ('Base','Arbitrum','Polygon','Avalanche','Sonic','Gnosis','Celo'):
   with patch('providers.request_json',side_effect=[{'result':'0x'+format(123,'064x')},{'result':'0x'+format(2,'064x')}]) as request:
    result=token_integrations.token_balances(chain,'0x'+'1'*40,['0x'+'2'*40]);self.assertEqual(result['tokens'][0]['quantity'],'1.23');self.assertTrue(result['tokens'][0]['asset_id'].startswith(chain+':'));self.assertTrue(all(c.args[1]['method']=='eth_call' for c in request.call_args_list))
 def test_history_keys_and_public_avalanche(self):
  for chain in ('Base','Arbitrum','Polygon','Sonic'):
   with patch.dict(os.environ,{},clear=True),patch('providers.request_json') as request:
    with self.assertRaisesRegex(ValueError,'ETHERSCAN_API_KEY'):history.fetch_history(chain,'0x'+'1'*40)
    request.assert_not_called()
  with patch.dict(os.environ,{},clear=True),patch('providers.request_json',return_value={'status':'0','message':'No transactions found','result':[]}) as request:
   result=history.fetch_history('Avalanche','0x'+'1'*40);self.assertEqual(result['items'],[]);self.assertTrue(request.call_args.args[0].startswith('https://api.routescan.io/'));self.assertNotIn('apikey',request.call_args.args[0])
 def test_configured_history_chain_id(self):
  from urllib.parse import urlsplit,parse_qs
  for chain,chain_id in [('Base','8453'),('Arbitrum','42161'),('Polygon','137'),('Sonic','146')]:
   with patch.dict(os.environ,{'ETHERSCAN_API_KEY':'fake-key'}),patch('providers.request_json',return_value={'status':'1','result':[]}) as request:
    history.fetch_history(chain,'0x'+'1'*40);query=parse_qs(urlsplit(request.call_args.args[0]).query);self.assertEqual(query['chainid'],[chain_id]);self.assertEqual(query['action'],['txlist'])
 def test_gnosis_celo_history_and_celo_fee_policy(self):
  owner='0x'+'1'*40;other='0x'+'2'*40
  row={'hash':'0x'+'3'*64,'timestamp':'2026-01-01T00:00:00Z','from':{'hash':owner},'to':{'hash':other},'value':'1000000000000000000','status':'ok','fee':{'value':'1000','type':'actual'}}
  for chain,symbol,host in [('Gnosis','XDAI','gnosis.blockscout.com'),('Celo','CELO','celo.blockscout.com')]:
   with patch('providers.request_json',side_effect=[{'items':[row],'next_page_params':None},{'items':[],'next_page_params':None}]) as request:
    result=history.fetch_history(chain,owner);self.assertEqual(result['items'][0]['asset'],symbol);self.assertEqual(result['items'][0]['asset_id'],chain+':native');self.assertIn(host,request.call_args_list[0].args[0])
    if chain=='Celo':self.assertIsNone(result['items'][0]['fee'])
class WalletExtraChains(test_integrations.APITests):
 def test_wallet_registration_all_new_chains(self):
  for chain in ('Base','Arbitrum','Polygon','Avalanche','Sonic','Gnosis','Celo'):self.call(self.a,'wallet',{'chain':chain,'address':'0x'+'1'*40,'label':chain})
  state=self.call(self.a,'state');self.assertEqual(len(state['wallets']),7)
  support={n['chain']:n for n in state['network_support']};self.assertEqual(len(support),20)
  self.assertTrue(support['Avalanche']['history_configured'])
if __name__=='__main__':unittest.main()
