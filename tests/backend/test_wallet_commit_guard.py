import json,threading,unittest,urllib.error
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from backend import server; from tests.backend import test_integrations as base

class WalletCommitTests(unittest.TestCase):
 setUp=base.APITests.setUp
 tearDown=base.APITests.tearDown
 client=base.APITests.client
 call=base.APITests.call
 def wallet(self):
  self.call(self.a,'wallet',{'chain':'Ethereum','address':'0x'+'1'*40,'label':'Synthetic A'})
  with server.connect() as c:return c.execute('SELECT id FROM wallets').fetchone()['id']
 def status(self,path,data):
  try:self.call(self.a,path,data);return 200
  except urllib.error.HTTPError as error:return error.code
 def race(self,path,data,patcher,change,table):
  entered,release=threading.Event(),threading.Event()
  def pause(*args,**kwargs):
   entered.set()
   if not release.wait(6):raise ValueError('Synthetic fixture release timed out')
   return patcher[1](*args,**kwargs)
  with patch(patcher[0],side_effect=pause),ThreadPoolExecutor(max_workers=1) as pool:
   future=pool.submit(self.status,path,data)
   try:
    self.assertTrue(entered.wait(4),'Synthetic provider was not reached')
    change()
   finally:release.set()
   status=future.result(timeout=8)
  with server.connect() as c:count=c.execute('SELECT COUNT(*) AS n FROM '+table).fetchone()['n']
  return status,count
 def revoke(self):self.call(self.a,'logout',{})
 def test_sync_rejects_revoked_session_after_provider_returns(self):
  wid=self.wallet()
  result=self.race('sync',{},('backend.server.sync_wallet',lambda w:(w['id'],{'symbol':'ETH','quantity':'42','updated_at':1})),self.revoke,'wallet_snapshots')
  self.assertEqual(result,(401,0),'Revoked request must not persist its synthetic snapshot')
 def test_sync_does_not_write_to_reused_wallet_id(self):
  wid=self.wallet()
  def replace():
   self.call(self.a,'remove-wallet',{'id':wid})
   self.call(self.b,'wallet',{'chain':'Ethereum','address':'0x'+'2'*40,'label':'Synthetic B'})
   with server.connect() as c:self.assertEqual(c.execute('SELECT id FROM wallets').fetchone()['id'],wid,'Fixture must reproduce SQLite ID reuse')
  result=self.race('sync',{},('backend.server.sync_wallet',lambda w:(w['id'],{'symbol':'ETH','quantity':'42','updated_at':1})),replace,'wallet_snapshots')
  self.assertEqual(result,(409,0),'Stale A result must not create a snapshot for B')
 def test_history_success_rejects_revoked_session(self):
  wid=self.wallet()
  result=self.race('history',{'id':wid},('backend.chains.history.fetch_history',lambda *a:{'items':[{'event_id':'synthetic-transfer','date':'2026-01-01','quantity':'1'}],'cursors':{},'coverage':'Synthetic'}),self.revoke,'history_sync')
  self.assertEqual(result,(401,0))
  with server.connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) AS n FROM chain_history').fetchone()['n'],0)
 def test_history_error_rejects_revoked_session(self):
  wid=self.wallet()
  def fail(*args):raise ValueError('Synthetic provider unavailable')
  result=self.race('history',{'id':wid},('backend.chains.history.fetch_history',fail),self.revoke,'history_sync')
  self.assertEqual(result,(401,0))
 def token_revoke(self,path):
  wid=self.wallet()
  with patch('backend.integrations.token_integrations.token_balances',return_value={'tokens':[],'coverage':'Synthetic'}),patch('backend.integrations.token_discovery.discover',return_value={'contracts':[],'coverage':'Synthetic','errors':[]}):
   result=self.race(path,{'id':wid},('backend.integrations.token_pricing.enrich',lambda chain,result:result),self.revoke,'wallet_tokens')
  self.assertEqual(result,(401,0),'Session must be rechecked after final token enrichment')
 def test_wallet_details_guard_follows_last_enrichment(self):self.token_revoke('wallet-details')
 def test_discovery_guard_follows_last_enrichment(self):self.token_revoke('discover-tokens')

 def replace_wallet(self,wid):
  self.call(self.a,'remove-wallet',{'id':wid})
  self.call(self.b,'wallet',{'chain':'Ethereum','address':'0x'+'2'*40,'label':'Synthetic B'})
  with server.connect() as c:self.assertEqual(c.execute('SELECT id FROM wallets').fetchone()['id'],wid)
 def test_details_rejects_replaced_wallet_after_enrichment(self):
  wid=self.wallet()
  with patch('backend.integrations.token_integrations.token_balances',return_value={'tokens':[],'coverage':'Synthetic'}):
   result=self.race('wallet-details',{'id':wid},('backend.integrations.token_pricing.enrich',lambda chain,result:result),lambda:self.replace_wallet(wid),'wallet_tokens')
  self.assertEqual(result,(409,0))
 def refresh_race(self,replace=False):
  wid=self.wallet()
  with server.connect() as c:c.execute('INSERT INTO wallet_tokens VALUES (?,?)',(wid,json.dumps({'tokens':[],'coverage':'Original synthetic'})))
  with patch('backend.integrations.providers.market_prices',return_value={'ETH':{'price':'100','updated_at':1,'source':'Synthetic'}}),patch('backend.integrations.exchange_connections.reprice_snapshots',return_value=[]):
   result=self.race('refresh-prices',{},('backend.integrations.token_pricing.enrich',lambda chain,result:{**result,'coverage':'Repriced synthetic'}),lambda:self.replace_wallet(wid) if replace else self.revoke(),'wallet_tokens')
  self.assertEqual(result,(409,0) if replace else (401,1))
  if not replace:
   with server.connect() as c:self.assertEqual(json.loads(c.execute('SELECT data FROM wallet_tokens').fetchone()['data'])['coverage'],'Original synthetic')
 def test_refresh_rejects_revoked_session_after_enrichment(self):self.refresh_race()
 def test_refresh_rejects_replaced_wallet_after_enrichment(self):self.refresh_race(True)
 def test_live_unchanged_wallet_requests_still_commit(self):
  wid=self.wallet()
  with patch('backend.server.sync_wallet',side_effect=lambda w:(w['id'],{'symbol':'ETH','quantity':'2','updated_at':1})):
   self.assertTrue(self.call(self.a,'sync',{})['ok'])
  with patch('backend.chains.history.fetch_history',return_value={'items':[{'event_id':'synthetic-live','date':'2026-01-01','quantity':'1'}],'cursors':{},'coverage':'Synthetic'}):
   self.assertEqual(self.call(self.a,'history',{'id':wid})['fetched'],1)
  with patch('backend.integrations.token_integrations.token_balances',return_value={'tokens':[],'coverage':'Synthetic'}),patch('backend.integrations.token_pricing.enrich',side_effect=lambda chain,result:result):
   self.call(self.a,'wallet-details',{'id':wid})
  with server.connect() as c:
   for table in ['wallet_snapshots','wallet_tokens','history_sync','chain_history']:self.assertEqual(c.execute('SELECT COUNT(*) AS n FROM '+table).fetchone()['n'],1)
