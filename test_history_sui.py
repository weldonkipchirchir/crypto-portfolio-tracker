import copy,unittest
from unittest.mock import patch
import history_sui as sui

OWNER='0x'+'0'*63+'1'
OTHER='0x'+'0'*63+'2'
DIGEST='1'*43

def change(amount,coin='0x2::sui::SUI',owner=OWNER):return {'amount':str(amount),'coinType':{'repr':coin},'owner':{'address':owner}}
def transaction(changes,gas=1000,payer=OWNER,status='SUCCESS'):
 return {'digest':DIGEST,'gasInput':{'gasSponsor':{'address':payer} if payer else None},'effects':{'timestamp':'2026-01-01T00:00:00Z','status':status,'gasEffects':{'gasSummary':{'computationCost':gas,'storageCost':0,'storageRebate':0}},'balanceChanges':{'nodes':changes,'pageInfo':{'hasNextPage':False}}}}
def page(txs,more=False,cursor=None):return {'data':{'transactions':{'nodes':txs,'pageInfo':{'hasPreviousPage':more,'startCursor':cursor}}}}

class SuiHistoryTests(unittest.TestCase):
 def fetch(self,txs):
  with patch('providers.request_json',return_value=page(txs)):return sui.fetch_history(OWNER)
 def test_native_gas_adjusted_and_other_owner_filtered(self):
  r=self.fetch([transaction([change(-1000001000),change(5000000000,owner=OTHER)])])
  self.assertEqual(len(r['items']),1);e=r['items'][0]
  self.assertEqual(e['quantity'],'1');self.assertEqual(e['fee'],'0.000001');self.assertTrue(e['review_eligible']);self.assertFalse(e['gas_inclusive'])
 def test_gas_only_does_not_become_sale(self):
  e=self.fetch([transaction([change(-1000)])])['items'][0]
  self.assertEqual(e['quantity'],'0');self.assertEqual(e['direction'],'self');self.assertEqual(e['kind'],'contract_activity')
 def test_sponsored_gas_not_added_to_owner(self):
  e=self.fetch([transaction([change(-1000000000)],payer=OTHER)])['items'][0]
  self.assertEqual(e['quantity'],'1');self.assertIsNone(e['fee'])
 def test_unknown_gas_is_not_reviewable(self):
  tx=transaction([change(-1000)],payer=None)
  e=self.fetch([tx])['items'][0];self.assertTrue(e['gas_inclusive']);self.assertFalse(e['review_eligible'])
 def test_unknown_token_decimals_are_raw_only(self):
  e=self.fetch([transaction([change(123456,'0x3::coin::TOKEN')])])['items'][0]
  self.assertIsNone(e['quantity']);self.assertIsNone(e['decimals']);self.assertEqual(e['raw_quantity'],'123456');self.assertFalse(e['review_eligible'])
 def test_failed_transaction_not_reviewable(self):
  self.assertFalse(self.fetch([transaction([change(-1000001000)],status='FAILURE')])['items'][0]['review_eligible'])
 def test_rebate_restored_as_signed_gas(self):
  tx=transaction([change(1000001000)],gas=0);tx['effects']['gasEffects']['gasSummary']['storageRebate']=1000
  e=self.fetch([tx])['items'][0];self.assertEqual(e['quantity'],'1');self.assertEqual(e['gas_net_cost'],'-0.000001');self.assertIsNone(e['fee'])
 def test_pagination_is_bound_variable_and_uses_startcursor(self):
  with patch('providers.request_json',return_value=page([],True,'abc==')) as request:
   r=sui.fetch_history(OWNER,{'transactions':'before=='})
   self.assertEqual(r['cursors'],{'transactions':'abc=='})
   self.assertEqual(request.call_args.args[1]['variables']['before'],'before==')
   self.assertNotIn('before==',request.call_args.args[1]['query'])
 def test_bad_cursor_rejected_before_request(self):
  for cursor in [{'transactions':'x&evil=yes'},{'url':'https://evil.example'},{'transactions':[]},{'transactions':'a'*2049}]:
   with patch('providers.request_json') as request:
    with self.assertRaises(ValueError):sui.fetch_history(OWNER,cursor)
    request.assert_not_called()
 def test_exhausted_cursor_no_network(self):
  with patch('providers.request_json') as request:
   self.assertEqual(sui.fetch_history(OWNER,{'transactions':None})['items'],[]);request.assert_not_called()
 def test_incomplete_changes_fail_instead_of_false_swap(self):
  tx=transaction([change(1000)]);tx['effects']['balanceChanges']['pageInfo']['hasNextPage']=True
  with self.assertRaises(ValueError):self.fetch([tx])
 def test_bounded_pages_and_malformed_amounts(self):
  with self.assertRaises(ValueError):self.fetch([transaction([])]*11)
  for amount in ['1e1000','9'*79,True,'NaN']:
   with self.assertRaises(ValueError):self.fetch([transaction([change(amount)])])
 def test_units_not_rounded_by_decimal_context(self):
  amount=123456789012345678901234567890123456789
  e=self.fetch([transaction([change(amount)],payer=OTHER)])['items'][0]
  self.assertEqual(e['quantity'],'123456789012345678901234567890.123456789')

if __name__=='__main__':unittest.main()
