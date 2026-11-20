import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from backend import server; from backend.portfolio import portfolio_background as bg; from backend.portfolio import portfolio_daily

class BackgroundTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.old=server.DB;server.DB=Path(self.tmp.name)/'test.db';self.addCleanup(setattr,server,'DB',self.old)
  self.env=patch.dict(os.environ,{},clear=True);self.env.start();self.addCleanup(self.env.stop)
  server.init();self.now=1800000000
  with server.connect() as c:
   for uid in (1,2):
    c.execute('INSERT INTO users VALUES (?,?,?)',(uid,str(uid)+'@example.test','unused'))
    c.execute('INSERT INTO wallets VALUES (?,?,?,?,?)',(uid,uid,'Ethereum','0x'+str(uid)*40,'Synthetic'))
    c.execute('INSERT INTO wallet_snapshots VALUES (?,?)',(uid,json.dumps({'quantity':str(uid),'updated_at':self.now-86400})))
 def run_job(self,price='100',now=None,**kwargs):
  now=self.now if now is None else now
  with patch('backend.integrations.providers.market_prices',return_value={'ETH':{'price':price,'updated_at':now,'source':'CoinGecko'}}),patch('backend.integrations.token_pricing.get_quote',side_effect=AssertionError('No token quote expected')):
   return bg.run(server.connect,server.snapshots,now=now,**kwargs)
 def test_no_login_two_days_and_idempotence(self):
  self.assertEqual(self.run_job()['saved'],2)
  self.assertEqual(self.run_job()['status'],'already_completed_or_running')
  self.assertEqual(self.run_job(price='120',now=self.now+86400)['saved'],2)
  with server.connect() as c:
   one=portfolio_daily.calendar(c,1,now=self.now+86400)['days'];two=portfolio_daily.calendar(c,2,now=self.now+86400)['days']
   self.assertEqual(one[-1]['change'],'20');self.assertEqual(two[-1]['change'],'40')
   self.assertEqual(one[-1]['valuation_basis'],'saved_balances_refreshed_prices')
   self.assertEqual(c.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],0)
   bg.preference(c,1,{'enabled':False})
  self.assertEqual(self.run_job(now=self.now+2*86400)['saved'],1)
 def test_refresh_does_not_change_saved_balances_or_credentials(self):
  with server.connect() as c:
   c.execute('INSERT INTO exchange_connections VALUES (?,?,?,?,?)',(1,'x','test','never-decrypt-this',json.dumps({'updated_at':self.now-86400,'balances':[{'asset':'BTC','coin_id':'bitcoin','quantity':'2','value_usd':'1'}]})))
  with patch('backend.integrations.providers.market_prices',return_value={'BTC':{'price':'10','updated_at':self.now},'ETH':{'price':'100','updated_at':self.now}}),patch('backend.integrations.exchange_connections.crypt',side_effect=AssertionError('Do not decrypt')):
   self.assertTrue(bg.run(server.connect,server.snapshots,now=self.now)['ok'])
  with server.connect() as c:
   row=json.loads(c.execute('SELECT data FROM portfolio_daily_values WHERE user_id=1').fetchone()[0]);self.assertEqual(row['value'],'120')
   self.assertEqual(json.loads(c.execute('SELECT snapshot FROM exchange_connections').fetchone()[0])['balances'][0]['value_usd'],'1')
 def test_stale_workspace_cannot_replace_automatic_observation(self):
  self.run_job()
  with server.connect() as c:
   portfolio_daily.record(c,1,server.snapshots(c,1),{'ETH':{'price':'50','updated_at':self.now-86400}},[],self.now+10,deduplicate=True,reason='workspace_view')
   row=json.loads(c.execute('SELECT data FROM portfolio_daily_values WHERE user_id=1').fetchone()[0]);self.assertEqual(row['value'],'100');self.assertEqual(row['capture_reason'],'scheduled_prices')
 def test_account_failure_does_not_block_other_owners(self):
  def read(c,uid):
   if uid==1:raise ValueError('do not expose provider details')
   return server.snapshots(c,uid)
  with patch('backend.integrations.providers.market_prices',return_value={'ETH':{'price':'100','updated_at':self.now}}):
   result=bg.run(server.connect,read,now=self.now)
  self.assertFalse(result['ok']);self.assertEqual(result['failed'],1);self.assertEqual(result['saved'],1)
  with server.connect() as c:
   self.assertEqual(c.execute('SELECT COUNT(*) FROM portfolio_daily_values WHERE user_id=1').fetchone()[0],0)
   self.assertEqual(c.execute('SELECT COUNT(*) FROM portfolio_daily_values WHERE user_id=2').fetchone()[0],1)
   self.assertEqual(bg.status(c,1)['error'],'Daily snapshot failed; retry needed')
  self.assertEqual(self.run_job()['saved'],1)
 def test_invalid_optional_snapshot_does_not_stop_other_accounts(self):
  with server.connect() as c:c.execute('INSERT INTO wallet_tokens VALUES (?,?)',(1,'not-json'))
  result=self.run_job()
  self.assertEqual(result['failed'],1)
  self.assertEqual(result['saved'],1)
  self.assertFalse(result['ok'])
 def test_provider_failure_retry_and_backlog(self):
  with patch('backend.integrations.providers.market_prices',side_effect=ValueError('provider secret must not leak')):
   r=bg.run(server.connect,server.snapshots,now=self.now);self.assertFalse(r['ok']);self.assertNotIn('secret',json.dumps(r))
  r=self.run_job(max_accounts=1);self.assertTrue(r['pending']);self.assertFalse(r['ok'])
  r=self.run_job();self.assertEqual(r['saved'],1);self.assertTrue(r['ok'])
 def test_contract_pricing_and_missing_values_are_explicit(self):
  address='0x'+'a'*40
  wallet={'chain':'Ethereum','address':'0x'+'1'*40,'snapshot':{'quantity':'1','updated_at':self.now},'token_snapshot':{'updated_at':self.now,'tokens':[{'contract':address,'asset_id':'Ethereum:'+address,'quantity':'2','price_usd':'999','value_usd':'1998'}]}}
  prices={'ETH':{'price':'100','updated_at':self.now}}
  q={('Ethereum',address):{'price_usd':'3','price_fetched_at':self.now,'price_stale':False}}
  row=bg.valuation([wallet],[],prices,q,self.now);self.assertEqual(row['value'],'106');self.assertEqual(row['priced'],2)
  row=bg.valuation([wallet],[],prices,{},self.now);self.assertEqual(row['value'],'100');self.assertEqual(row['unpriced'],1)
  self.assertEqual(wallet['token_snapshot']['tokens'][0]['value_usd'],'1998')
 def test_authorization_fails_closed_and_preferences_isolate(self):
  self.assertFalse(bg.authorized({'Authorization':'Bearer '}))
  with patch.dict(os.environ,{'CRON_SECRET':'s'*48}):
   self.assertTrue(bg.authorized({'Authorization':'Bearer '+'s'*48}));self.assertFalse(bg.authorized({'Authorization':'Bearer wrong'}))
  with server.connect() as c:
   bg.preference(c,1,{'enabled':False});self.assertFalse(bg.status(c,1)['enabled']);self.assertTrue(bg.status(c,2)['enabled'])
   with self.assertRaises(ValueError):bg.preference(c,1,{'enabled':'true'})
 def test_unpriced_account_can_retry_same_day(self):
  def unavailable(c,uid):return [] if uid==1 else server.snapshots(c,uid)
  with patch('backend.integrations.providers.market_prices',return_value={'ETH':{'price':'100','updated_at':self.now}}):
   first=bg.run(server.connect,unavailable,now=self.now)
  self.assertFalse(first['ok']);self.assertEqual(first['unpriced'],1)
  with server.connect() as c:
   status=c.execute('SELECT last_day,last_success,error FROM portfolio_tracking WHERE user_id=1').fetchone()
   self.assertIsNone(status['last_day']);self.assertIsNone(status['last_success']);self.assertIn('retry',status['error'])
  second=self.run_job();self.assertTrue(second['ok']);self.assertEqual(second['saved'],1)
  with server.connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM portfolio_daily_values').fetchone()[0],2)
 def test_primary_and_recovery_schedule_are_registered(self):
  config=json.loads(Path('vercel.json').read_text(encoding='utf-8'))
  jobs=[r['schedule'] for r in config['crons'] if r['path']==bg.PATH]
  self.assertEqual(jobs,[bg.SCHEDULE,bg.RECOVERY_SCHEDULE])
 def test_invalid_quotes_not_zero(self):
  for p in (None,True,'NaN','-1'):
   self.assertIsNone(bg.fresh_quote({'price':p,'updated_at':self.now},self.now))
  self.assertIsNone(bg.fresh_quote({'price':'2','updated_at':self.now-901},self.now))
  self.assertIsNone(bg.valuation([],[],{}, {},self.now))
class CronEndpointTests(unittest.TestCase):
 def test_bearer_without_session_and_missing_secret(self):
  import http.client,threading
  with patch.dict(os.environ,{'CRON_SECRET':'s'*48}),patch('backend.portfolio.portfolio_background.run',return_value={'ok':True,'saved':1}) as run:
   app=server.BoundedHTTPServer(('127.0.0.1',0),server.Handler,max_workers=2);t=threading.Thread(target=app.serve_forever,daemon=True);t.start()
   try:
    for auth,expected in [(None,401),('Bearer wrong',401),('Bearer '+'s'*48,200)]:
     client=http.client.HTTPConnection('127.0.0.1',app.server_port,timeout=2)
     client.request('GET',bg.PATH,headers={'Authorization':auth} if auth else {});response=client.getresponse();self.assertEqual(response.status,expected);response.read();client.close()
    self.assertEqual(run.call_count,1)
   finally:app.shutdown();app.server_close();t.join()
 def test_hosted_rejects_cron_before_database_initialization(self):
  import importlib.util,http.client,threading
  spec=importlib.util.spec_from_file_location('cron_hosted_fixture','api/index.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  with patch.object(mod,'initialize',side_effect=AssertionError('Do not initialize')) as init:
   app=server.BoundedHTTPServer(('127.0.0.1',0),mod.handler,max_workers=2);t=threading.Thread(target=app.serve_forever,daemon=True);t.start()
   try:
    client=http.client.HTTPConnection('127.0.0.1',app.server_port,timeout=2);client.request('GET',bg.PATH);r=client.getresponse();self.assertEqual(r.status,401);r.read();client.close();init.assert_not_called()
   finally:app.shutdown();app.server_close();t.join()
if __name__=='__main__':unittest.main()
