import unittest,urllib.error
from unittest.mock import patch
import test_integrations as base
class UpgradeTests(base.APITests):
 def test_multichain_atomic_idempotent(self):
  data={'chains':['Ethereum','Base','Arbitrum'],'address':'0x'+'a'*40,'label':'Multi'}
  self.assertEqual(len(self.call(self.a,'wallet-batch',data)['added']),3)
  self.assertEqual(len(self.call(self.a,'wallet-batch',data)['skipped']),3)
  with self.assertRaises(urllib.error.HTTPError):self.call(self.a,'wallet-batch',{**data,'chains':['Optimism','Solana']})
  self.assertEqual(len(self.call(self.a,'state')['wallets']),3);self.assertEqual(self.call(self.b,'state')['wallets'],[])
 def test_profile_notes_setups_scope(self):
  self.call(self.a,'profile-save',{'name':'Weldon'})
  self.assertEqual(self.call(self.a,'profile',{})['name'],'Weldon');self.assertEqual(self.call(self.b,'profile',{})['name'],'')
  notes=self.call(self.a,'learning-note-save',{'title':'Plan','body':'Private'})['notes'];self.assertEqual(self.call(self.b,'learning-notes',{})['notes'],[])
  self.call(self.b,'learning-note-delete',{'note_id':notes[0]['note_id']});self.assertEqual(len(self.call(self.a,'learning-notes',{})['notes']),1)
  self.call(self.a,'chart-setup-save',{'key':'bitcoin:binance:USDT','value':{'script':'EMA(20)'}})
  self.assertIsNone(self.call(self.b,'chart-setup-load',{'key':'bitcoin:binance:USDT'})['value'])
  self.assertEqual(self.call(self.a,'chart-setup-load',{'key':'bitcoin:binance:USDT'})['value']['script'],'EMA(20)')
 def test_password_revokes_sessions(self):
  self.call(self.a,'password-change',{'current_password':'test-password-123','new_password':'updated-password-456'})
  with self.assertRaises(urllib.error.HTTPError) as e:self.call(self.a,'state')
  self.assertEqual(e.exception.code,401)
  self.call(self.a,'login',{'email':'a@test.com','password':'updated-password-456'})
 def test_exchange_connect_sync_disconnect_and_credential_isolation(self):
  import os,base64,json,server
  key='a'*64;secret='b'*64
  snapshot={'balances':[{'asset':'BTC','quantity':'0.25','value_usd':'20000','price_usd':80000}],'updated_at':123,'permissions_verified':True}
  with patch.dict(os.environ,{'ORBIT_EXCHANGE_KEY':base64.urlsafe_b64encode(bytes(range(32))).decode(),'ORBIT_EXCHANGE_KEY_ID':'test','ORBIT_EXCHANGE_PREVIOUS_KEYS':'{}'}),patch('exchange_connections.snapshot',return_value=snapshot):
   result=self.call(self.a,'exchange-connect',{'label':'Binance fixture','api_key':key,'api_secret':secret})
   connection=result['connections'][0];identity=connection['id']
   self.assertNotIn(key,json.dumps(result));self.assertNotIn(secret,json.dumps(result))
   state=self.call(self.a,'state');self.assertEqual(state['exchanges'][0]['snapshot']['balances'][0]['quantity'],'0.25')
   self.assertEqual(self.call(self.b,'state')['exchanges'],[])
   with server.connect() as c:
    stored=c.execute('SELECT credentials FROM exchange_connections WHERE id=?',(identity,)).fetchone()[0]
    self.assertTrue(stored.startswith('v1:test:'));self.assertNotIn(key,stored);self.assertNotIn(secret,stored)
   with self.assertRaises(urllib.error.HTTPError):self.call(self.b,'exchange-sync',{'id':identity})
   refreshed=self.call(self.a,'exchange-sync',{'id':identity});self.assertEqual(len(refreshed['connections']),1)
   self.call(self.a,'exchange-delete',{'id':identity});self.assertEqual(self.call(self.a,'state')['exchanges'],[])
 def test_price_refresh_revalues_exchange_without_resync(self):
  import server,json
  snapshot={'balances':[{'asset':'LDBNB','display_quantity':'1.25','quantity':'1','coin_id':'binancecoin','valuation_basis':'verified_earn_underlying','value_usd':'100'}],'updated_at':123}
  with server.connect() as c:
   uid=c.execute('SELECT id FROM users WHERE email=?',('a@test.com',)).fetchone()['id']
   c.execute('INSERT INTO exchange_connections VALUES (?,?,?,?,?)',(uid,'reprice-fixture','Binance','encrypted-placeholder',json.dumps(snapshot)));c.commit()
  with patch('providers.market_prices',return_value={'BTC':{'price':'50000','source':'fixture','updated_at':456}}),patch('coin_market.listings',return_value={'coins':[{'id':'binancecoin','current_price':600,'last_updated':456}]}),patch('exchange_connections.crypt',side_effect=AssertionError('must not decrypt')),patch('exchange_connections.signed',side_effect=AssertionError('must not resync')):
   self.call(self.a,'refresh-prices',{})
  saved=self.call(self.a,'state')['exchanges'][0]['snapshot'];self.assertEqual(saved['balances'][0]['value_usd'],'750.00');self.assertEqual(saved['balances'][0]['quantity'],'1');self.assertEqual(saved['updated_at'],123);self.assertEqual(self.call(self.b,'state')['exchanges'],[])
 def test_exchange_state_no_secret(self):
  result=self.call(self.a,'exchange-state',{});self.assertEqual(result['connections'],[]);self.assertNotIn('credentials',str(result))

 def test_coin_alert_routes_are_account_scoped(self):
  import time
  quote={'coin':{'id':'bitcoin','name':'Bitcoin','symbol':'BTC','current_price':100,'last_updated':int(time.time())}}
  with patch('coin_market.detail',return_value=quote):
   rules=self.call(self.a,'coin-alert-save',{'coin_id':'bitcoin','operator':'above','target_usd':'90'})['alerts']
   self.assertEqual(self.call(self.b,'coin-alert-list',{'coin_id':'bitcoin'})['alerts'],[])
   event=self.call(self.a,'coin-alert-check',{'coin_id':'bitcoin'});self.assertEqual(event['triggered'],1)
   self.assertEqual(self.call(self.a,'coin-alert-check',{'coin_id':'bitcoin'})['triggered'],0)
  with self.assertRaises(urllib.error.HTTPError):self.call(self.b,'coin-alert-delete',{'id':rules[0]['id']})
  self.assertEqual(len(self.call(self.a,'coin-alert-list',{'coin_id':'bitcoin'})['alerts']),1)
 def test_invalid_multichain_types_are_bad_request(self):
  for chains in [[{}],[['Ethereum']]]:
   with self.assertRaises(urllib.error.HTTPError) as e:self.call(self.a,'wallet-batch',{'chains':chains,'address':'0x'+'a'*40,'label':'Invalid'})
   self.assertEqual(e.exception.code,400)

 def test_revoked_inflight_trade_cannot_commit(self):
  import threading,server
  from concurrent.futures import ThreadPoolExecutor
  entered=threading.Event();original=server.Handler.user
  def observed(handler,c):
   uid=original(handler,c)
   if handler.path=='/api/trade':entered.set()
   return uid
  def submit():
   try:self.call(self.a,'trade',{'date':'2026-01-01','symbol':'BTC','side':'buy','quantity':1,'price':100});return 200
   except urllib.error.HTTPError as e:return e.code
  with server.connect() as c,patch.object(server.Handler,'user',observed):
   uid=c.execute('SELECT id FROM users WHERE email=?',('a@test.com',)).fetchone()['id']
   if getattr(c,'dialect',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(?)',(uid,))
   else:c.execute('BEGIN IMMEDIATE')
   with ThreadPoolExecutor(max_workers=1) as pool:
    pending=pool.submit(submit)
    try:self.assertTrue(entered.wait(3));c.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
    finally:c.commit()
    self.assertEqual(pending.result(timeout=5),401)
   self.assertEqual(c.execute('SELECT COUNT(*) AS n FROM trades WHERE user_id=?',(uid,)).fetchone()['n'],0)
