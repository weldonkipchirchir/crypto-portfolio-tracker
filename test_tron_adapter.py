import copy,os,unittest
from unittest.mock import patch
import tron_adapter as tron

OWNER='T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb'
OWNER_HEX='41'+'00'*20
OTHER_HEX='41'+'11'*20
OTHER=tron.validate_address(OTHER_HEX)

def row(kind='TransferContract',owner=OWNER_HEX,target=OTHER_HEX,amount=1234567,outcome='SUCCESS'):
 return {'txID':'ab'*32,'block_timestamp':1700000000123,'ret':[{'contractRet':outcome}],'raw_data':{'contract':[{'type':kind,'parameter':{'value':{'owner_address':owner,'to_address':target,'amount':amount}}}]}}
def page(rows,fingerprint=None):return {'success':True,'data':rows,'meta':{'fingerprint':fingerprint,'links':{'next':'https://evil.example/leak'}}}

class TronTests(unittest.TestCase):
 def fetch(self,rows):
  with patch('providers.request_json',return_value=page(rows)):return tron.fetch_history(OWNER)
 def test_known_base58check_and_hex(self):
  self.assertEqual(tron.validate_address(OWNER_HEX),OWNER);self.assertEqual(tron.validate_address(OWNER),OWNER)
  for address in [OWNER[:-1]+'a','41'+'00'*19,'0x'+OWNER_HEX,'T'+'1'*33,'S'+OWNER[1:],None,'a'*10000]:
   with self.assertRaises(ValueError):tron.validate_address(address)
 def test_exact_native_balance_and_request(self):
  with patch('providers.request_json',return_value={'address':OWNER,'balance':123456789012345678901234567}) as request:
   self.assertEqual(tron.balance(OWNER)['quantity'],'123456789012345678901.234567')
   self.assertEqual(request.call_args.args,('https://api.trongrid.io/wallet/getaccount',{'address':OWNER,'visible':True}))
 def test_unactivated_account_zero(self):
  with patch('providers.request_json',return_value={}):self.assertEqual(tron.balance(OWNER)['quantity'],'0')
 def test_account_mismatch_and_error_not_misread_zero(self):
  for result in [{'address':OTHER,'balance':5},{'Error':'secret from server'},{'success':False},{'foo':'bad'}]:
   with patch('providers.request_json',return_value=result):
    with self.assertRaises(ValueError):tron.balance(OWNER)
 def test_api_key_header_only(self):
  with patch.dict(os.environ,{'TRON_PRO_API_KEY':'private-key'}),patch('providers.request_json',return_value={}) as request:
   tron.balance(OWNER);self.assertEqual(request.call_args.kwargs['headers']['TRON-PRO-API-KEY'],'private-key')
   self.assertNotIn('private-key',repr(request.call_args.args))
 def test_native_transfer_timestamp_and_unknown_fee(self):
  e=self.fetch([row()])['items'][0];self.assertEqual(e['quantity'],'1.234567');self.assertIsNone(e['fee']);self.assertTrue(e['review_eligible']);self.assertEqual(e['direction'],'out');self.assertEqual(e['date'],'2023-11-14T22:13:20.123000+00:00')
 def test_receipt_fee_owner_only(self):
  tx=row();tx['receipt']={'energy_fee':1000,'net_fee':2000};self.assertEqual(self.fetch([tx])['items'][0]['fee'],'0.003')
  tx=row(owner=OTHER_HEX,target=OWNER_HEX);tx['receipt']={'energy_fee':1000,'net_fee':2000};self.assertIsNone(self.fetch([tx])['items'][0]['fee'])
 def test_failed_and_unknown_status_not_reviewable(self):
  e=self.fetch([row(outcome='REVERT')])['items'][0];self.assertEqual(e['status'],'failed');self.assertFalse(e['review_eligible'])
  tx=row();tx['ret']=[];self.assertFalse(self.fetch([tx])['items'][0]['review_eligible'])
 def test_smart_contracts_are_metadata(self):
  e=self.fetch([row(kind='TriggerSmartContract')])['items'][0];self.assertIsNone(e['quantity']);self.assertFalse(e['review_eligible']);self.assertEqual(e['kind'],'contract_activity')
 def test_foreign_transfer_rejected(self):
  with self.assertRaises(ValueError):self.fetch([row(owner=OTHER_HEX,target=OTHER_HEX)])
 def test_cursor_is_encoded_and_response_links_ignored(self):
  with patch('providers.request_json',return_value=page([],fingerprint='abc==')) as request:
   r=tron.fetch_history(OWNER,{'transactions':'before+/'})
   url=request.call_args.args[0];self.assertTrue(url.startswith('https://api.trongrid.io/v1/accounts/'+OWNER+'/transactions?'));self.assertIn('fingerprint=before%2B%2F',url);self.assertNotIn('evil.example',url);self.assertEqual(r['cursors'],{'transactions':'abc=='})
 def test_invalid_cursors_rejected_without_network(self):
  for cursor in [{'transactions':'x&evil=yes'},{'transactions':'https://evil.example'},{'url':'evil'},{'transactions':'a'*2049},{'transactions':False}]:
   with patch('providers.request_json') as request:
    with self.assertRaises(ValueError):tron.fetch_history(OWNER,cursor)
    request.assert_not_called()
 def test_exhausted_cursor_no_request(self):
  with patch('providers.request_json') as request:
   self.assertEqual(tron.fetch_history(OWNER,{'transactions':None})['items'],[]);request.assert_not_called()
 def test_bad_numbers_and_oversized_pages(self):
  for amount in [True,-1,'1e99','9'*79]:
   with self.assertRaises(ValueError):self.fetch([row(amount=amount)])
  with self.assertRaises(ValueError):self.fetch([row()]*21)

if __name__=='__main__':unittest.main()
