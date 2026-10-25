import unittest
from unittest.mock import patch
import history
A='0x'+'1'*40
B='0x'+'2'*40
H='0x'+'a'*64

def transaction():return {'hash':H,'timestamp':'2026-01-01T00:00:00Z','from':{'hash':A},'to':{'hash':B},'value':'1000000000000000001','fee':{'value':'21000'},'status':'ok'}
def transfer():return {'transaction_hash':H,'timestamp':'2026-01-01T00:00:00Z','from':{'hash':B},'to':{'hash':A},'log_index':5,'token':{'type':'ERC-20','address_hash':B,'symbol':'USD'},'total':{'value':'1234567','decimals':'6'}}
class HistoryTests(unittest.TestCase):
 def test_native_token_units_and_ids(self):
  with patch('providers.request_json',side_effect=[{'items':[transaction()],'next_page_params':{'block_number':12,'index':1,'items_count':50}},{'items':[transfer()],'next_page_params':None}]) as req:
   r=history.fetch_history('Ethereum',A)
   self.assertEqual(r['items'][0]['quantity'],'1.000000000000000001')
   self.assertEqual(r['items'][0]['direction'],'out')
   self.assertEqual(r['items'][1]['quantity'],'1.234567')
   self.assertFalse(r['items'][1]['identity_verified'])
   self.assertIn(':5',r['items'][1]['event_id'])
   self.assertEqual(req.call_count,2)
 def test_skip_exhausted_and_fixed_host(self):
  with patch('providers.request_json',return_value={'items':[],'next_page_params':None}) as req:
   r=history.fetch_history('Ethereum',A,{'transactions':None,'token-transfers':{'block_number':1}})
   self.assertEqual(req.call_count,1)
   self.assertEqual(req.call_args.args[0],'https://eth.blockscout.com/api/v2/addresses/'+A+'/token-transfers?block_number=1')
 def test_bad_cursor_before_network(self):
  with patch('providers.request_json') as req:
   for value in [{'transactions':{'url':'https://evil.test'}},{'bad':{}},{'transactions':{'block_number':{}}}]:
    with self.assertRaises(ValueError):history.fetch_history('Ethereum',A,value)
   req.assert_not_called()
 def test_wrong_owner_and_failed(self):
  row=transaction();row['status']='error'
  with patch('providers.request_json',side_effect=[{'items':[row]},{'items':[]}]):
   self.assertEqual(history.fetch_history('Ethereum',A)['items'][0]['status'],'failed')
  row['from']['hash']=B
  with patch('providers.request_json',return_value={'items':[row]}):
   with self.assertRaises(ValueError):history.fetch_history('Ethereum',A)
 def test_oversized_page(self):
  with patch('providers.request_json',return_value={'items':[transaction()]*51}):
   with self.assertRaises(ValueError):history.fetch_history('Ethereum',A)
if __name__=='__main__':unittest.main()
