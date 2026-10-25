import unittest
from unittest.mock import patch
import token_integrations as tokens

class TokenTests(unittest.TestCase):
 def test_precise_balance_and_read_only_rpc(self):
  address='0x'+'1'*40; contract='0x'+'2'*40
  with patch('providers.request_json',side_effect=[{'result':'0x'+format(123456789012345678901234567890,'064x')},{'result':'0x'+format(18,'064x')}]) as rpc:
   result=tokens.token_balances('Ethereum',address,[contract,contract])
   self.assertEqual(result['tokens'][0]['quantity'],'123456789012.34567890123456789')
   self.assertFalse(result['tokens'][0]['identity_verified'])
   self.assertEqual(rpc.call_count,2)
   for call in rpc.call_args_list:self.assertEqual(call.args[1]['method'],'eth_call')
 def test_partial_errors(self):
  with patch('providers.request_json',side_effect=[{'result':'0x'}, {'result':'0x'+format(1,'064x')},{'result':'0x'+format(256,'064x')}]):
   result=tokens.token_balances('Optimism','0x'+'1'*40,['0x'+'2'*40,'0x'+'3'*40])
   self.assertEqual(len(result['errors']),2)
   self.assertEqual(result['tokens'],[])
 def test_validation_before_network(self):
  with patch('providers.request_json') as rpc:
   for contracts in ['bad',['bad'],['0x'+'1'*40]*21]:
    with self.assertRaises(ValueError):tokens.token_balances('Ethereum','0x'+'1'*40,contracts)
   rpc.assert_not_called()
 def test_unsupported_is_explicit(self):
  result=tokens.token_balances('Sui','0x1')
  self.assertEqual(result['tokens'],[])
  self.assertIn('not yet supported',result['coverage'])

if __name__=='__main__':unittest.main()

class SolanaTests(unittest.TestCase):
 def test_aggregate_and_partial_program_error(self):
  owner='1'*32; mint='So11111111111111111111111111111111111111112'
  row={'account':{'data':{'parsed':{'info':{'owner':owner,'mint':mint,'tokenAmount':{'amount':'123','decimals':2}}}}}}
  with patch('providers.request_json',side_effect=[{'result':{'value':[row,row]}},ValueError('Rate limited')]) as rpc:
   result=tokens.token_balances('Solana',owner)
   self.assertEqual(result['tokens'][0]['quantity'],'2.46')
   self.assertEqual(len(result['errors']),1)
   self.assertEqual(rpc.call_args_list[0].args[1]['method'],'getTokenAccountsByOwner')
 def test_bad_owner_is_not_a_holding(self):
  row={'account':{'data':{'parsed':{'info':{'owner':'wrong'}}}}}
  with patch('providers.request_json',return_value={'result':{'value':[row]}}):
   result=tokens.solana_tokens('1'*32)
   self.assertEqual(result['tokens'],[]);self.assertEqual(len(result['errors']),2)
 def test_activity_cursor_and_failure(self):
  signature='2'*88
  with patch('providers.request_json',return_value={'result':[{'signature':signature,'slot':123,'blockTime':None,'err':{'error':'failed'}}]}):
   result=tokens.recent_activity('Solana','1'*32,1)
   self.assertEqual(result['next_cursor'],signature)
   self.assertTrue(result['activities'][0]['failed'])
 def test_activity_bounds(self):
  with patch('providers.request_json') as rpc:
   for limit in [0,101,True]:
    with self.assertRaises(ValueError):tokens.recent_activity('Solana','1'*32,limit)
   with self.assertRaises(ValueError):tokens.recent_activity('Solana','1'*32,before='bad')
   rpc.assert_not_called()
