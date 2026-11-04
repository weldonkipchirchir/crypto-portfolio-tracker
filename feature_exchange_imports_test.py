import sqlite3,unittest
from unittest.mock import patch
import feature_exchange_imports as feature

class HistoryTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
  self.c.execute('CREATE TABLE exchange_connections(user_id INTEGER,id TEXT,label TEXT,credentials TEXT)')
  self.identity='a'*32;self.c.execute('INSERT INTO exchange_connections VALUES(1,?,?,?)',(self.identity,'Private','encrypted'))
  self.raw=dict(operation='preview',id=self.identity,pair='BTCUSDT',from_id='0',usdt_usd_rate='1')
 def rows(self):return [dict(symbol='BTCUSDT',id=9007199254740993,isBuyer=True,time=1700000000000,qty='1',price='100',commission='1',commissionAsset='USDT')]
 def test_owner_isolation(self):
  self.assertEqual(feature.read(self.c,2,{})['connections'],[])
  with patch.object(feature,'fetch') as fetch,self.assertRaisesRegex(ValueError,'not found'):feature.read(self.c,2,self.raw)
  fetch.assert_not_called()
 def test_page_preserves_large_ids_and_usd_fees(self):
  with patch.object(feature.ex,'crypt',return_value={}),patch.object(feature,'fetch',return_value=self.rows()):result=feature.read(self.c,1,self.raw)
  self.assertEqual(result['next_from_id'],'9007199254740994');self.assertIn('100,1,Binance API',result['csv'])
 def test_bad_cursor_rejected(self):
  for value in ['-1','1e3','01','9223372036854775807',True,1]:
   with self.subTest(value=value),self.assertRaises(ValueError):feature.cursor(value)
 def test_non_usdt_fees_fail_closed(self):
  rows=self.rows();rows[0]['commissionAsset']='BNB'
  with patch.object(feature.ex,'crypt',return_value={}),patch.object(feature,'fetch',return_value=rows),self.assertRaisesRegex(ValueError,'Historical fee valuation'):feature.read(self.c,1,self.raw)
 def test_out_of_range_and_repeated_ids_rejected(self):
  for rows in [self.rows()*2,[dict(self.rows()[0],id=-1)]]:
   with patch.object(feature.ex,'crypt',return_value={}),patch.object(feature,'fetch',return_value=rows),self.assertRaises(ValueError):feature.read(self.c,1,self.raw)
 def test_read_does_not_mutate_database(self):
  before=self.c.total_changes
  with patch.object(feature.ex,'crypt',return_value={}),patch.object(feature,'fetch',return_value=[]):result=feature.read(self.c,1,self.raw)
  self.assertEqual(result['count'],0);self.assertIsNone(result['next_from_id']);self.assertEqual(before,self.c.total_changes)

class ActivityTests(unittest.TestCase):
 setUp=HistoryTests.setUp
 def activity_raw(self,kind='deposits'):
  from datetime import datetime,timezone,timedelta
  now=datetime.now(timezone.utc).replace(second=0,microsecond=0)
  return dict(operation='activity',activity=kind,id=self.identity,start_utc=(now-timedelta(days=7)).strftime('%Y-%m-%dT%H:%M'),end_utc=now.strftime('%Y-%m-%dT%H:%M'),page='1')
 def row(self):
  return dict(id='deposit-1',coin='BTC',amount='0.00000001',status=1,insertTime=int(feature.time.time()*1000)-86400000,txId='tx-1',address='private-address',api_secret='never-expose')
 def test_activity_owner_filter_precedes_decryption_and_http(self):
  with patch.object(feature.ex,'crypt') as decrypt,patch.object(feature,'activity_fetch') as fetch,self.assertRaisesRegex(ValueError,'not found'):feature.read(self.c,2,self.activity_raw())
  decrypt.assert_not_called();fetch.assert_not_called()
 def test_deposit_native_value_unknown_fee_and_redaction(self):
  with patch.object(feature.ex,'crypt',return_value={}),patch.object(feature,'activity_fetch',return_value=([self.row()],None)) as fetch:result=feature.read(self.c,1,self.activity_raw())
  fetch.assert_called_once();event=result['events'][0]
  self.assertEqual(event['amount_native'],'0.00000001');self.assertEqual(event['fee_native'],'');self.assertEqual(event['status'],'Success')
  self.assertNotIn('never-expose',str(result));self.assertNotIn('private-address',str(result));self.assertNotIn('price',event)
  self.assertIn('not automatically income',result['coverage'])
 def test_withdrawal_native_fee_and_request_time(self):
  from datetime import datetime,timezone
  row=dict(self.row(),transactionFee='0.00000123',status=6,applyTime=datetime.fromtimestamp((self.row()['insertTime'])/1000,timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))
  with patch.object(feature.ex,'crypt',return_value={}),patch.object(feature,'activity_fetch',return_value=([row],None)):result=feature.read(self.c,1,self.activity_raw('withdrawals'))
  self.assertEqual(result['events'][0]['fee_native'],'0.00000123');self.assertEqual(result['events'][0]['fee_asset'],'BTC');self.assertEqual(result['events'][0]['status'],'Completed')
 def test_flexible_and_locked_reward_identity(self):
  for kind in ['flexible_rewards','locked_rewards']:
   row=dict(asset='BNB',rewards='0.00001234',amount='0.004',time=self.row()['insertTime'],type='BONUS' if kind=='flexible_rewards' else 'Locked Rewards',projectId='BNB001',positionId=9007199254740993)
   with patch.object(feature.ex,'crypt',return_value={}),patch.object(feature,'activity_fetch',return_value=([row],101)):result=feature.read(self.c,1,self.activity_raw(kind))
   event=result['events'][0];self.assertEqual(event['activity'],'reward');self.assertEqual(event['fee_native'],'');self.assertIn('Simple Earn',event['source']);self.assertEqual(result['next_page'],'2')
   self.assertEqual(event['amount_native'],'0.00001234' if kind=='flexible_rewards' else '0.004')
 def test_nonnumeric_and_unbounded_native_amount_rejected(self):
  for value in ['NaN','Infinity','1e10000000','-1','0.'+'1'*31,0.1,True]:
   with self.subTest(value=value),self.assertRaises(ValueError):feature.native_amount(value)
 def test_window_and_page_rejection_before_http(self):
  raw=self.activity_raw('flexible_rewards');raw['start_utc']='2000-01-01T00:00'
  with patch.object(feature,'activity_fetch') as fetch,self.assertRaises(ValueError):feature.read(self.c,1,raw)
  fetch.assert_not_called()
  raw=self.activity_raw();raw['page']='2'
  with self.assertRaises(ValueError):feature.read(self.c,1,raw)
  raw=self.activity_raw('flexible_rewards');raw['page']='11'
  with self.assertRaises(ValueError):feature.read(self.c,1,raw)
 def test_endpoint_allowlist_and_permission_errors_redacted(self):
  with patch.object(feature.urllib.request,'build_opener') as opener,self.assertRaises(ValueError):feature.activity_fetch({},'https://evil.test',1,2)
  opener.assert_not_called()
  with patch.object(feature.urllib.request,'build_opener',side_effect=Exception('403 KEY_SECRET_SENTINEL enableWithdrawals')):
   with self.assertRaises(ValueError) as caught:feature.activity_fetch(dict(api_key='KEY_SENTINEL',api_secret='SECRET_SENTINEL'),'deposits',1,2)
  self.assertNotIn('SENTINEL',str(caught.exception));self.assertIn('read permissions',str(caught.exception))
 def test_signed_get_fixed_path_bounded_one_request(self):
  import json
  class Response:
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self,size):self.size=size;return b'[]'
  response=Response()
  with patch.object(feature.urllib.request,'build_opener') as build:
   build.return_value.open.return_value=response
   result=feature.activity_fetch(dict(api_key='key',api_secret='secret'),'deposits',1,2)
  request=build.return_value.open.call_args.args[0]
  self.assertEqual(request.get_method(),'GET');self.assertTrue(request.full_url.startswith('https://api.binance.com/sapi/v1/capital/deposit/hisrec?'))
  self.assertIn('limit=1000',request.full_url);self.assertIn('signature=',request.full_url);self.assertNotIn('secret',request.full_url)
  self.assertEqual(response.size,2*1024*1024+1);build.return_value.open.assert_called_once();self.assertIs(build.call_args.args[0],feature.ex.NoRedirect)
 def test_unknown_status_retained_and_csv_formula_sanitized(self):
  row=self.row();row.update(status=999,txId='=BAD()')
  start,end=feature.activity_window(self.activity_raw(),'deposits');events=feature.normalize_activity([row],'deposits',start,end)
  self.assertEqual(events[0]['status'],'Unknown exchange status 999');self.assertIn("'=BAD()",feature.activity_csv(events))
 def test_outside_response_window_rejected(self):
  row=self.row();row['insertTime']=1
  with self.assertRaises(ValueError):feature.normalize_activity([row],'deposits',100,200)


 def test_reward_30_day_window(self):
  from datetime import datetime,timezone,timedelta
  raw=self.activity_raw('flexible_rewards')
  raw['start_utc']=(datetime.now(timezone.utc)-timedelta(days=31)).strftime('%Y-%m-%dT%H:%M')
  with self.assertRaisesRegex(ValueError,'30 days'):feature.activity_window(raw,'flexible_rewards')
 def test_oversized_or_malformed_reward_response(self):
  import json
  class Response:
   def __init__(self,body):self.body=body
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self,size):return self.body
  for body in [b'x'*(2*1024*1024+1),json.dumps(dict(rows=[{}]*101,total=101)).encode(),json.dumps(dict(rows=[],total='not numeric')).encode()]:
   with patch.object(feature.urllib.request,'build_opener') as build:
    build.return_value.open.return_value=Response(body)
    with self.assertRaises(ValueError):feature.activity_fetch(dict(api_key='key',api_secret='secret'),'flexible_rewards',1,2)
 def test_activity_read_does_not_mutate_database(self):
  before=self.c.total_changes
  with patch.object(feature.ex,'crypt',return_value={}),patch.object(feature,'activity_fetch',return_value=([self.row()],None)):feature.read(self.c,1,self.activity_raw())
  self.assertEqual(before,self.c.total_changes)

if __name__=='__main__':unittest.main()
