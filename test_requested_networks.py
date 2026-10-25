import unittest,os
from unittest.mock import patch
import providers,history,token_integrations,server,test_integrations
class RequestedNetworks(unittest.TestCase):
 def test_evm_balances_and_namespaces(self):
  expected={'Arc':'USDC','Monad':'MON','Robinhood Chain':'ETH','Linea':'ETH'}
  for chain,symbol in expected.items():
   with patch('providers.request_json',return_value={'result':hex(10**18)}):
    r=providers.balance(chain,'0x'+'1'*40);self.assertEqual(r['symbol'],symbol);self.assertEqual(r['quantity'],'1')
   self.assertIn(chain,providers.EVM_CHAINS)
  self.assertEqual(providers.LEDGER_ALIASES['Arc'],'USDC_ARC');self.assertEqual(providers.LEDGER_ALIASES['Robinhood Chain'],'ETH_RH')
 def test_non_evm_dispatch_and_validation(self):
  cases=[('Bitcoin','bitcoin_adapter','1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa'),('Stellar','stellar_adapter','GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWHF'),('Tron','tron_adapter','T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb')]
  for chain,module,address in cases:
   self.assertEqual(providers.validate_address(chain,address),address)
   with patch(module+'.balance',return_value={'quantity':'1'}) as adapter:self.assertEqual(providers.balance(chain,address),{'quantity':'1'});adapter.assert_called_once()
   with patch(module+'.fetch_history',return_value={'items':[]}) as adapter:self.assertEqual(history.fetch_history(chain,address),{'items':[]});adapter.assert_called_once()
 def test_arc_native_interface_not_double_counted(self):
  with patch('providers.request_json') as request:
   r=token_integrations.token_balances('Arc','0x'+'1'*40,['0x3600000000000000000000000000000000000000'])
   self.assertEqual(r['tokens'],[]);self.assertIn('same',r['coverage'].replace('shares','same'));request.assert_not_called()
 def test_new_evm_history_needs_provider_key(self):
  for chain in ('Arc','Monad','Robinhood Chain','Linea'):
   with patch.dict(os.environ,{},clear=True),patch('providers.request_json') as request:
    with self.assertRaisesRegex(ValueError,'ETHERSCAN_API_KEY'):history.fetch_history(chain,'0x'+'1'*40)
    request.assert_not_called()
class RequestedNetworkWallets(test_integrations.APITests):
 def test_register_requested_wallet_types(self):
  addresses={'Bitcoin':'1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa','Stellar':'GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWHF','Tron':'T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb'}
  for chain in ('Arc','Monad','Robinhood Chain','Linea'):addresses[chain]='0x'+'1'*40
  for chain,address in addresses.items():self.call(self.a,'wallet',{'chain':chain,'address':address,'label':chain})
  state=self.call(self.a,'state');self.assertEqual(len(state['wallets']),7);self.assertEqual(len(state['network_support']),20)
  self.assertEqual(self.call(self.b,'state')['wallets'],[])
if __name__=='__main__':unittest.main()
