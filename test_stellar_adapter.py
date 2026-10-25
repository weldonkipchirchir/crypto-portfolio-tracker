import base64,binascii,unittest
from unittest.mock import patch
import stellar_adapter as s

def address(seed):
    raw=bytes([48])+bytes([seed])*32
    return base64.b32encode(raw+binascii.crc_hqx(raw,0).to_bytes(2,'little')).decode()
A=address(1);B=address(2);ISSUER=address(3)
def payment(n=100,**changes):
    row={'type':'payment','paging_token':str(n),'transaction_hash':'a'*64,'created_at':'2026-01-01T00:00:00Z','transaction_successful':True,'from':A,'to':B,'asset_type':'native','amount':'1.2345678'};row.update(changes);return row

def page(rows):return {'_embedded':{'records':rows}}
class StellarTests(unittest.TestCase):
    def test_strkey(self):
        self.assertEqual(s.validate_address(A),A)
        self.assertEqual(s.validate_address('GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWHF'),'GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWHF')
        for bad in [A[:-1]+'A',A.lower(),'S'+A[1:],'M'+'A'*68,'G'+'A'*55,None]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):s.validate_address(bad)
    def test_native_balance(self):
        with patch('providers.request_json',return_value={'account_id':A,'balances':[{'asset_type':'native','balance':'123.0000001'},{'asset_type':'credit_alphanum4','balance':'1.0000000'}]}) as request:
            result=s.balance(A)
        self.assertEqual(result['quantity'],'123.0000001');self.assertEqual(result['symbol'],'XLM');self.assertTrue(request.call_args.args[0].startswith('https://horizon.stellar.org/accounts/'))
    def test_unfunded_not_network_failure(self):
        with patch('providers.request_json',side_effect=ValueError('Provider returned HTTP 404. Try again later or configure a provider endpoint.')):self.assertEqual(s.balance(A)['quantity'],'0.0000000')
        with patch('providers.request_json',side_effect=ValueError('Provider returned HTTP 429. Try again later.')):
            with self.assertRaises(ValueError):s.balance(A)
    def test_native_directions_fee_unknown(self):
        with patch('providers.request_json',return_value=page([payment(100),payment(99,**{'from':B,'to':A}),payment(98,to=A)])):result=s.fetch_history(A)
        self.assertEqual([x['direction'] for x in result['items']],['out','in','self']);self.assertEqual(result['items'][0]['quantity'],'1.2345678');self.assertIsNone(result['items'][0]['fee']);self.assertEqual(result['cursors'],{'payments':None})
    def test_funding_and_issuer_identity(self):
        funded=payment(100,type='create_account',funder=B,account=A,starting_balance='2.0000000')
        token=payment(99,asset_type='credit_alphanum4',asset_code='XLM',asset_issuer=ISSUER)
        with patch('providers.request_json',return_value=page([funded,token])):items=s.fetch_history(A)['items']
        self.assertEqual(items[0]['asset_id'],'Stellar:native');self.assertEqual(items[0]['direction'],'in')
        self.assertEqual(items[1]['asset_id'],'Stellar:XLM:'+ISSUER);self.assertFalse(items[1]['identity_verified'])
    def test_unsupported_and_failed_not_reviewable(self):
        with patch('providers.request_json',return_value=page([payment(100,type='path_payment_strict_receive'),payment(99,transaction_successful=False)])):items=s.fetch_history(A)['items']
        for item in items:self.assertEqual(item['quantity'],'0');self.assertFalse(item['review_eligible'])
    def test_pagination(self):
        with patch('providers.request_json',return_value=page([payment(n) for n in range(100,75,-1)])) as request:result=s.fetch_history(A,{'payments':'101'})
        self.assertEqual(result['cursors'],{'payments':'76'});self.assertIn('cursor=101',request.call_args.args[0])
        with patch('providers.request_json') as request:self.assertEqual(s.fetch_history(A,{'payments':None})['items'],[]);request.assert_not_called()
    def test_reject_cursor_and_provider_data(self):
        for cursor in [[],{'payments':True},{'payments':'https://evil'},{'payments':'-1'},{'bad':None}]:
            with self.subTest(cursor=cursor),patch('providers.request_json') as request:
                with self.assertRaises(ValueError):s.fetch_history(A,cursor)
                request.assert_not_called()
        for rows in [[payment(amount='0.00000001')],[payment(**{'from':B,'to':ISSUER})],[payment(100),payment(100)],[payment(asset_type='credit_alphanum4',asset_code='FAKECOIN',asset_issuer=ISSUER)]]:
            with self.subTest(rows=rows),patch('providers.request_json',return_value=page(rows)):
                with self.assertRaises(ValueError):s.fetch_history(A)
if __name__=='__main__':unittest.main()
