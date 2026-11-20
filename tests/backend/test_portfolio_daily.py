import unittest,sqlite3
from datetime import datetime,timezone
from backend.portfolio import portfolio_daily
class DailyTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;portfolio_daily.init(self.c);self.addCleanup(self.c.close)
 def save(self,day,value=100,quantity='1',uid=1,unknown=False):
  stamp=int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp())
  balances=[{'asset':'BTC','quantity':quantity,'value_usd':str(value)}]
  if unknown:balances.append({'asset':'UNKNOWN','quantity':'1','value_usd':None})
  return portfolio_daily.record(self.c,uid,[],{},[{'id':'a','snapshot':{'balances':balances}}],stamp)
 def test_freshness_metadata_is_explicit(self):
  row={'asset':'BTC','quantity':'1','value_usd':'100','price_updated_at':1000}
  result=portfolio_daily.observation([],{},[{'id':'a','snapshot':{'updated_at':1000,'balances':[row]}}],1001)
  self.assertTrue(result['freshness_verified']);self.assertEqual(result['stale_count'],0)
  old=portfolio_daily.observation([],{},[{'id':'a','snapshot':{'updated_at':1000,'balances':[row]}}],2001)
  self.assertTrue(old['freshness_verified']);self.assertEqual(old['stale_count'],1)
  row.pop('price_updated_at');unknown=portfolio_daily.observation([],{},[{'id':'a','snapshot':{'updated_at':1000,'balances':[row]}}],1001)
  self.assertFalse(unknown['freshness_verified'])
 def test_daily_changes_gaps_flows_and_isolation(self):
  self.save('2026-12-31',100);self.save('2027-01-01',110);self.save('2027-01-01T23:00:00',120)
  days=portfolio_daily.calendar(self.c,1)['days'];self.assertEqual(len(days),2);self.assertEqual(days[-1]['change'],'20');self.assertEqual(days[-1]['percentage'],'20.0')
  self.assertFalse(days[-1]['balances_changed']);self.assertEqual(portfolio_daily.calendar(self.c,2)['days'],[])
  self.save('2027-01-03',130);self.assertIsNone(portfolio_daily.calendar(self.c,1)['days'][-1]['change'])
  self.save('2027-01-04',260,quantity='2');last=portfolio_daily.calendar(self.c,1)['days'][-1];self.assertTrue(last['balances_changed']);self.assertEqual(last['change'],'130')
 def test_incomplete_coverage_and_first_day(self):
  self.save('2026-01-01',100);self.save('2026-01-02',120,unknown=True)
  days=portfolio_daily.calendar(self.c,1)['days'];self.assertIsNone(days[0]['change']);self.assertIsNone(days[1]['change'])
 def test_stable_partial_coverage_compares_known_value(self):
  self.save('2026-01-01',100,unknown=True);self.save('2026-01-02',110,unknown=True)
  row=portfolio_daily.calendar(self.c,1)['days'][-1];self.assertEqual(row['change'],'10');self.assertTrue(row['partial'])
 def test_wallet_exchange_combination_and_account_dedup(self):
  wallets=[{'chain':'Ethereum','address':'0xabc','snapshot':{'quantity':'2'}}]
  exchange={'id':'a','snapshot':{'account_key':'same','balances':[{'asset':'BTC','quantity':'1','value_usd':'100'}]}}
  result=portfolio_daily.observation(wallets,{'ETH':{'price':'200'}},[exchange,{**exchange,'id':'b'}],1000)
  self.assertEqual(result['value'],'500');self.assertEqual(result['priced'],2)
  self.assertIsNone(portfolio_daily.observation([],{},[],1000))
 def test_timestamp_normalization_and_invalid_duplicates(self):
  now=1800000000
  stamp=datetime.fromtimestamp(now,timezone.utc).isoformat()
  def connection(value,updated):return {'id':'same','snapshot':{'account_key':'same-account','updated_at':updated,'balances':[{'asset':'BTC','quantity':'1','value_usd':str(value),'price_updated_at':stamp}]}}
  for bad in ('not-a-time',True,now+3600,1e100):
   result=portfolio_daily.observation([],{},[connection(999,bad),connection(100,stamp)],now)
   self.assertEqual(result['value'],'100');self.assertEqual(result['priced'],1)
  result=portfolio_daily.observation([],{},[connection(90,now-100),connection(100,now*1000)],now)
  self.assertEqual(result['value'],'100');self.assertTrue(result['freshness_verified']);self.assertEqual(result['stale_count'],0)
  for invalid in (None,True,[],{},' ',1e100):self.assertIsNone(portfolio_daily.observed_time(invalid))
 def test_latest_wallet_observation_and_real_token_quote_timestamp(self):
  now=1800000000
  def wallet(quantity,updated):return {'chain':'Ethereum','address':'0xabc','snapshot':{'quantity':quantity,'updated_at':updated}}
  result=portfolio_daily.observation([wallet('9',now+3600),wallet('2',now)],{'ETH':{'price':'10','updated_at':now}},[],now)
  self.assertEqual(result['value'],'20')
  contract='0x'+'1'*40
  w=wallet('0',now);w['token_snapshot']={'updated_at':now,'tokens':[{'asset_id':'Ethereum:'+contract,'contract':contract,'quantity':'2','price_usd':'5','price_fetched_at':now}]}
  result=portfolio_daily.observation([w],{},[],now)
  self.assertEqual(result['value'],'10');self.assertTrue(result['freshness_verified']);self.assertEqual(result['stale_count'],0)
 def test_missing_earn_sections_are_partial_and_not_interchangeable(self):
  def save(day,status,value):
   now=int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp())
   snapshot={'updated_at':now,'balances':[{'asset':'BTC','quantity':'1','value_usd':str(value),'price_updated_at':now}],**status}
   return portfolio_daily.record(self.c,1,[],{},[{'id':'a','snapshot':snapshot}],now)
  first=save('2026-01-01',{'earn_status':'unavailable'},100)
  second=save('2026-01-02',{'locked_earn_status':'unavailable'},110)
  self.assertEqual(first['unpriced'],1);self.assertEqual(second['unpriced'],1)
  self.assertNotEqual(first['coverage_fingerprint'],second['coverage_fingerprint'])
  self.assertIsNone(portfolio_daily.calendar(self.c,1)['days'][-1]['change'])
  save('2026-01-03',{'locked_earn_status':'unavailable'},120)
  last=portfolio_daily.calendar(self.c,1)['days'][-1]
  self.assertTrue(last['partial']);self.assertEqual(last['change'],'10')
 def test_workspace_capture_deduplicates_and_preserves_explicit_observations(self):
  exchange={'id':'a','snapshot':{'updated_at':1000,'balances':[{'asset':'BTC','quantity':'1','value_usd':'100','price_updated_at':1000}]}}
  first=portfolio_daily.record(self.c,1,[],{},[exchange],1001,reason='price_refresh')
  changes=self.c.total_changes
  repeated=portfolio_daily.record(self.c,1,[],{},[exchange],3000,deduplicate=True,reason='workspace_view')
  self.assertEqual(self.c.total_changes,changes);self.assertEqual(repeated,first);self.assertEqual(repeated['capture_reason'],'price_refresh')
  exchange['snapshot']['balances'][0]['value_usd']='110'
  updated=portfolio_daily.record(self.c,1,[],{},[exchange],3001,deduplicate=True,reason='workspace_view')
  self.assertEqual(updated['value'],'110');self.assertEqual(updated['capture_reason'],'workspace_view')
 def test_stale_workspace_days_are_observations_not_invented_daily_returns(self):
  exchange={'id':'a','snapshot':{'updated_at':1000,'balances':[{'asset':'BTC','quantity':'1','value_usd':'100','price_updated_at':1000}]}}
  portfolio_daily.record(self.c,1,[],{},[exchange],86400,reason='workspace_view')
  portfolio_daily.record(self.c,1,[],{},[exchange],172800,reason='workspace_view')
  days=portfolio_daily.calendar(self.c,1,172800)['days']
  self.assertEqual(len(days),2);self.assertIsNone(days[-1]['change']);self.assertIn('stale or unverified',days[-1]['comparison_reason'])
 def test_fresh_workspace_days_compare_actual_saved_values(self):
  def capture(stamp,value):
   exchange={'id':'a','snapshot':{'updated_at':stamp,'balances':[{'asset':'BTC','quantity':'1','value_usd':str(value),'price_updated_at':stamp}]}}
   return portfolio_daily.record(self.c,1,[],{},[exchange],stamp,reason='workspace_view')
  capture(86400,100);capture(172800,110)
  day=portfolio_daily.calendar(self.c,1,172800)['days'][-1]
  self.assertEqual(day['change'],'10');self.assertIsNone(day['comparison_reason'])
from backend import server; from tests.backend import test_integrations; import json
from unittest.mock import patch
class DailyAPITests(test_integrations.APITests):
 def test_refresh_records_connected_value_without_trades(self):
  with server.connect() as c:
   uid=c.execute('SELECT id FROM users WHERE email=?',('a@test.com',)).fetchone()[0]
   cursor=c.execute('INSERT INTO wallets(user_id,chain,address,label) VALUES (?,?,?,?)',(uid,'Ethereum','0x'+'1'*40,'Test wallet'))
   c.execute('INSERT INTO wallet_snapshots VALUES (?,?)',(cursor.lastrowid,json.dumps({'quantity':'2','symbol':'ETH'})));c.commit()
  with patch('backend.integrations.providers.market_prices',return_value={'ETH':{'price':'200','source':'Test provider','updated_at':123}}):self.call(self.a,'refresh-prices',{})
  data=self.call(self.a,'state');self.assertEqual(data['trades'],[]);self.assertEqual(data['portfolio_calendar']['days'][0]['value'],'400');self.assertIsNone(data['portfolio_calendar']['days'][0]['change'])
  self.assertEqual(self.call(self.b,'state')['portfolio_calendar']['days'],[])
 def seed_wallet_prices(self):
  with server.connect() as c:
   uid=c.execute('SELECT id FROM users WHERE email=?',('a@test.com',)).fetchone()[0]
   cursor=c.execute('INSERT INTO wallets(user_id,chain,address,label) VALUES (?,?,?,?)',(uid,'Ethereum','0x'+'1'*40,'Test wallet'))
   c.execute('INSERT INTO wallet_snapshots VALUES (?,?)',(cursor.lastrowid,json.dumps({'quantity':'1','symbol':'ETH','updated_at':int(__import__('time').time())})))
   c.execute('INSERT INTO prices VALUES (?,?,?)',(uid,'ETH','200'))
   c.execute('INSERT INTO price_metadata VALUES (?,?,?,?)',(uid,'ETH','Fixture',int(__import__('time').time())))
   c.commit();return uid
 def test_workspace_read_saves_today_without_fetching_providers(self):
  self.seed_wallet_prices()
  with patch('backend.integrations.providers.request_json',side_effect=AssertionError('state must not fetch providers')):
   state=self.call(self.a,'state')
  day=state['portfolio_calendar']['days'][0]
  self.assertEqual(day['value'],'200');self.assertEqual(day['capture_reason'],'workspace_view');self.assertIsNone(day['change'])
  self.assertEqual(self.call(self.b,'state')['portfolio_calendar']['days'],[])
 def test_wallet_sync_saves_without_needing_price_refresh_or_state_read(self):
  uid=self.seed_wallet_prices()
  with patch('backend.integrations.providers.balance',return_value={'symbol':'ETH','quantity':'2','updated_at':int(__import__('time').time())}):self.call(self.a,'sync',{})
  with server.connect() as c:
   day=json.loads(c.execute('SELECT data FROM portfolio_daily_values WHERE user_id=?',(uid,)).fetchone()['data'])
  self.assertEqual(day['value'],'400');self.assertEqual(day['capture_reason'],'balance_sync')
if __name__=='__main__':unittest.main()
