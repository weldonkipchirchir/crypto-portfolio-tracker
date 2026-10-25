import unittest
from unittest.mock import patch
import history_solana as h
A='11111111111111111111111111111111'
M='So11111111111111111111111111111111111111112'
S='1'*64

def tx():return {'blockTime':1700000000,'transaction':{'message':{'accountKeys':[{'pubkey':A},{'pubkey':M}]}},'meta':{'err':None,'fee':5000,'preBalances':[2000000000,1],'postBalances':[999995000,1],'preTokenBalances':[{'owner':A,'mint':M,'accountIndex':1,'uiTokenAmount':{'amount':'0','decimals':6}}],'postTokenBalances':[{'owner':A,'mint':M,'accountIndex':1,'uiTokenAmount':{'amount':'123456789','decimals':6}}]}}
class SolanaHistoryTests(unittest.TestCase):
 def test_native_fee_removed_and_token_exact(self):
  with patch('history_solana._rpc',side_effect=[[{'signature':S}],tx()]):r=h.fetch_history(A)
  native,token=r['items'];self.assertEqual(native['quantity'],'1');self.assertEqual(native['fee'],'0.000005')
  self.assertEqual(native['direction'],'out');self.assertEqual(token['quantity'],'123.456789')
  self.assertEqual(token['direction'],'in');self.assertIsNone(token['from_address'])
 def test_failed_metadata_no_trade(self):
  transaction=tx();transaction['meta']['err']={'error':'failed'}
  with patch('history_solana._rpc',side_effect=[[{'signature':S}],transaction]):r=h.fetch_history(A)
  self.assertEqual(len(r['items']),1);self.assertEqual(r['items'][0]['status'],'failed');self.assertEqual(r['items'][0]['quantity'],'0')
 def test_null_transaction_aborts_no_cursor(self):
  with patch('history_solana._rpc',side_effect=[[{'signature':S}],None]):
   with self.assertRaises(ValueError):h.fetch_history(A)
 def test_cursor_validation_and_exhaustion(self):
  with patch('history_solana._rpc') as rpc:
   self.assertEqual(h.fetch_history(A,{'signatures':None})['items'],[])
   for cursor in [{'bad':{}},{'signatures':{'before':'bad'}},{'signatures':{'before':S,'url':'evil'}}]:
    with self.assertRaises(ValueError):h.fetch_history(A,cursor)
   rpc.assert_not_called()
 def test_decimals_conflict_and_quantity_bounds(self):
  transaction=tx();transaction['meta']['postTokenBalances'][0]['uiTokenAmount']['decimals']=9
  with self.assertRaises(ValueError):h._parse(A,S,transaction)
  for value in ['1e100000',-1,True,2**64]:
   with self.assertRaises(ValueError):h._uint(value)
 def test_other_owner_not_counted(self):
  transaction=tx();transaction['meta']['preTokenBalances'][0]['owner']=M;transaction['meta']['postTokenBalances'][0]['owner']=M
  self.assertEqual(len(h._parse(A,S,transaction)),1)
if __name__=='__main__':unittest.main()
