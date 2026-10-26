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
