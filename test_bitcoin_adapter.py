import unittest
from unittest.mock import patch
import bitcoin_adapter as b
A='1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa'
B='3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy'
class BitcoinTests(unittest.TestCase):
 def test_mainnet_checksums(self):
  for address in [A,B,'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4']:
   self.assertEqual(b.validate_address(address),address)
  for address in [A[:-1]+'b','mipcBbFg9gMiCh81Kj8tqqdgoZub1ZJRfn','bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kygt080','bC1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4']:
   with self.assertRaises(ValueError):b.validate_address(address)
 def test_balance(self):
  with patch('providers.request_json',return_value={'chain_stats':{'funded_txo_sum':123456789,'spent_txo_sum':1}}):
   self.assertEqual(b.balance(A)['quantity'],'1.23456788')
 def transaction(self):return {'txid':'a'*64,'status':{'confirmed':True,'block_time':1700000000},'vin':[{'prevout':{'scriptpubkey_address':A,'value':100000000}}],'vout':[{'scriptpubkey_address':A,'value':49999000},{'scriptpubkey_address':B,'value':50000000}],'fee':1000}
 def test_outgoing_excludes_fee(self):
  with patch('providers.request_json',return_value=[self.transaction()]):r=b.fetch_history(A)['items'][0]
  self.assertEqual(r['quantity'],'0.50000000');self.assertEqual(r['fee'],'0.00001000');self.assertTrue(r['review_eligible'])
 def test_mixed_owner_does_not_allocate_fee(self):
  tx=self.transaction();tx['vin'].append({'prevout':{'scriptpubkey_address':B,'value':1}})
  with patch('providers.request_json',return_value=[tx]):r=b.fetch_history(A)['items'][0]
  self.assertIsNone(r['fee']);self.assertFalse(r['review_eligible'])
 def test_pending_excluded(self):
  tx=self.transaction();tx['status']={'confirmed':False}
  with patch('providers.request_json',return_value=[tx]):r=b.fetch_history(A)['items'][0]
  self.assertEqual(r['status'],'pending');self.assertEqual(r['quantity'],'0');self.assertFalse(r['review_eligible'])
 def test_cursor_and_exhaustion(self):
  with patch('providers.request_json') as rpc:
   self.assertEqual(b.fetch_history(A,{'transactions':None})['items'],[])
   with self.assertRaises(ValueError):b.fetch_history(A,{'transactions':{'last_txid':'https://evil'}})
   rpc.assert_not_called()
if __name__=='__main__':unittest.main()

class WitnessTests(unittest.TestCase):
 def test_official_bip350_vectors(self):
  for address in ['bc1pw508d6qejxtdg4y5r3zarvary0c5xw7kw508d6qejxtdg4y5r3zarvary0c5xw7kt5nd6y','BC1SW50QGDZ25J','bc1zw508d6qejxtdg4y5r3zarvaryvaxxpcs']:
   self.assertEqual(b.validate_address(address),address.lower())
 def test_fee_inconsistency(self):
  tx=BitcoinTests().transaction();tx['fee']=2000
  with patch('providers.request_json',return_value=[tx]):
   with self.assertRaises(ValueError):b.fetch_history(A)
