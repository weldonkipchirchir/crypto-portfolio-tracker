import unittest
from unittest.mock import patch
import history_aptos as h
import providers

ADDRESS=providers.validate_address('Aptos','0x1')
def transaction(seq=0,**changes):
    row={'type':'user_transaction','sender':'0x1','sequence_number':str(seq),'hash':'0x'+format(seq,'064x'),'success':True,'timestamp':'1700000000123456','gas_used':'3','gas_unit_price':'100','payload':{'type':'entry_function_payload','function':'0x1::aptos_account::transfer','type_arguments':[],'arguments':['0x2','123456789']}}
    row.update(changes);return row

class AptosHistoryTests(unittest.TestCase):
    def test_latest_page_and_exact_units(self):
        with patch('providers.request_json',side_effect=[{'sequence_number':'26'},[transaction(25)]]) as request:
            result=h.fetch_history('0x1')
        item=result['items'][0]
        self.assertEqual(item['quantity'],'1.23456789');self.assertEqual(item['fee'],'0.000003')
        self.assertEqual(item['direction'],'out');self.assertEqual(item['asset_id'],'Aptos:native')
        self.assertEqual(result['cursors'],{'transactions':{'end':'1'}})
        self.assertIn('start=1',request.call_args_list[-1].args[0])
        self.assertIn('Incoming transfers',result['coverage'])
    def test_older_window(self):
        with patch('providers.request_json',return_value=[transaction(0)]) as request:
            result=h.fetch_history('0x1',{'transactions':{'end':'1'}})
        self.assertEqual(result['cursors'],{'transactions':None});self.assertEqual(request.call_count,1)
        self.assertIn('limit=1&start=0',request.call_args.args[0])
    def test_exhausted_and_zero_sequence(self):
        with patch('providers.request_json') as request:self.assertEqual(h.fetch_history('0x1',{'transactions':None})['items'],[]);request.assert_not_called()
        with patch('providers.request_json',return_value={'sequence_number':'0'}) as request:self.assertEqual(h.fetch_history('0x1')['items'],[]);self.assertEqual(request.call_count,1)
    def test_failed_transfer_no_net_quantity(self):
        with patch('providers.request_json',side_effect=[{'sequence_number':'1'},[transaction(success=False)] ]):item=h.fetch_history('0x1')['items'][0]
        self.assertEqual(item['status'],'failed');self.assertEqual(item['quantity'],'0');self.assertEqual(item['direction'],'self');self.assertEqual(item['fee'],'0.000003')
    def test_coin_type_must_be_verified(self):
        row=transaction();row['payload']['function']='0x1::coin::transfer';row['payload']['type_arguments']=['0x99::fake::APT']
        with patch('providers.request_json',side_effect=[{'sequence_number':'1'},[row]]):item=h.fetch_history('0x1')['items'][0]
        self.assertEqual(item['kind'],'contract_activity');self.assertEqual(item['quantity'],'0')
        row['payload']['type_arguments']=['0x1::aptos_coin::AptosCoin']
        with patch('providers.request_json',side_effect=[{'sequence_number':'1'},[row]]):self.assertEqual(h.fetch_history('0x1')['items'][0]['quantity'],'1.23456789')
    def test_self_transfer_and_unknown_events(self):
        row=transaction();row['payload']['arguments'][0]='0x1';row['events']=[{'type':'0x1::coin::DepositEvent','guid':{'account_address':'0x1'},'data':{'amount':'999'}}]
        with patch('providers.request_json',side_effect=[{'sequence_number':'1'},[row]]):items=h.fetch_history('0x1')['items']
        self.assertEqual(len(items),1);self.assertEqual(items[0]['direction'],'self')
    def test_invalid_cursor(self):
        for cursor in [[],{'transactions':False},{'transactions':{'end':True}},{'transactions':{'end':'-1'}},{'transactions':{'end':str(2**64)}},{'transactions':{'end':'1','url':'evil'}},{'evil':None}]:
            with self.subTest(cursor=cursor),patch('providers.request_json') as request:
                with self.assertRaises(ValueError):h.fetch_history('0x1',cursor)
                request.assert_not_called()
    def test_reject_other_wallet_duplicate_sequence_and_invalid_units(self):
        for rows in [[transaction(sender='0x2')],[transaction(),transaction()],[transaction(sequence_number='2')],[transaction(gas_used=True)],[transaction(success='true')]]:
            with self.subTest(rows=rows),patch('providers.request_json',side_effect=[{'sequence_number':'1'},rows]):
                with self.assertRaises(ValueError):h.fetch_history('0x1')
    def test_endpoint_configuration(self):
        for url in ['http://example.com/v1','https://user:password@example.com/v1','https://example.com/v1?url=bad']:
            with self.subTest(url=url),patch.dict('os.environ',{'APT_HISTORY_URL':url}),patch('providers.request_json') as request:
                with self.assertRaises(ValueError):h.fetch_history('0x1')
                request.assert_not_called()

if __name__=='__main__':unittest.main()
