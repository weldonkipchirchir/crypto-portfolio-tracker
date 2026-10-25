import os,unittest
from unittest.mock import patch
import token_discovery as d
A='0x'+'1'*40;C='0x'+'2'*40
class DiscoveryTests(unittest.TestCase):
 def test_known_rh_and_empty_other(self):
  with patch.dict(os.environ,{},clear=True),patch('providers.request_json') as req:
   r=d.discover('Robinhood Chain',A);self.assertEqual(r['contracts'],d.CATALOG['Robinhood Chain']);self.assertTrue(r['has_more'])
   self.assertEqual(d.discover('Ethereum',A)['contracts'],[]);req.assert_not_called()
 def test_alchemy_nonzero_dedup_and_pagination(self):
  response={'result':{'address':A,'pageKey':'more','tokenBalances':[{'contractAddress':C,'tokenBalance':'0x1'},{'contractAddress':C,'tokenBalance':'0x2'},{'contractAddress':A,'tokenBalance':'0x0'}]}}
  with patch.dict(os.environ,{'ALCHEMY_ETH_RPC_URL':'https://eth-mainnet.g.alchemy.com/v2/secret'},clear=True),patch('providers.request_json',return_value=response) as req:
   r=d.discover('Ethereum',A);self.assertEqual(r['contracts'],[C]);self.assertTrue(r['has_more']);self.assertNotIn('secret',str(r))
   self.assertEqual(req.call_args.args[1]['method'],'alchemy_getTokenBalances')
 def test_errors_sanitized_catalog_survives(self):
  with patch.dict(os.environ,{'ALCHEMY_RH_RPC_URL':'https://example.com/secret'},clear=True),patch('providers.request_json',side_effect=ValueError('secret')):
   r=d.discover('Robinhood Chain',A);self.assertTrue(r['contracts']);self.assertNotIn('secret',str(r));self.assertTrue(r['errors'])
 def test_wrong_owner_rejected(self):
  with patch.dict(os.environ,{'ALCHEMY_ETH_RPC_URL':'https://example.com'},clear=True),patch('providers.request_json',return_value={'result':{'address':C,'tokenBalances':[]}}):
   r=d.discover('Ethereum',A);self.assertEqual(r['contracts'],[]);self.assertTrue(r['errors'])
 def test_transfer_fallback_is_partial(self):
  response={'status':'1','result':[{'from':A,'to':C,'contractAddress':C}]}
  with patch.dict(os.environ,{'ETHERSCAN_API_KEY':'secret'},clear=True),patch('providers.request_json',return_value=response):
   r=d.discover('Ethereum',A);self.assertEqual(r['contracts'],[C]);self.assertTrue(r['has_more']);self.assertIn('partial',r['coverage'])
 def test_cap_twenty(self):
  rows=[{'contractAddress':'0x'+format(i,'040x'),'tokenBalance':'0x1'} for i in range(25)]
  with patch.dict(os.environ,{'ALCHEMY_ETH_RPC_URL':'https://example.com'},clear=True),patch('providers.request_json',return_value={'result':{'address':A,'tokenBalances':rows}}):
   r=d.discover('Ethereum',A);self.assertEqual(len(r['contracts']),20);self.assertTrue(r['has_more'])
if __name__=='__main__':unittest.main()
