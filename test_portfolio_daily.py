import unittest,sqlite3
from datetime import datetime,timezone
import portfolio_daily
class DailyTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;portfolio_daily.init(self.c);self.addCleanup(self.c.close)
 def save(self,day,value=100,quantity='1',uid=1,unknown=False):
  stamp=int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp())
  balances=[{'asset':'BTC','quantity':quantity,'value_usd':str(value)}]
  if unknown:balances.append({'asset':'UNKNOWN','quantity':'1','value_usd':None})
  return portfolio_daily.record(self.c,uid,[],{},[{'id':'a','snapshot':{'balances':balances}}],stamp)
 def test_daily_changes_gaps_flows_and_isolation(self):
  self.save('2026-12-31',100);self.save('2027-01-01',110);self.save('2027-01-01T23:00:00',120)
  days=portfolio_daily.calendar(self.c,1)['days'];self.assertEqual(len(days),2);self.assertEqual(days[-1]['change'],'20');self.assertEqual(days[-1]['percentage'],'20.0')
  self.assertFalse(days[-1]['balances_changed']);self.assertEqual(portfolio_daily.calendar(self.c,2)['days'],[])
  self.save('2027-01-03',130);self.assertIsNone(portfolio_daily.calendar(self.c,1)['days'][-1]['change'])
  self.save('2027-01-04',260,quantity='2');last=portfolio_daily.calendar(self.c,1)['days'][-1];self.assertTrue(last['balances_changed']);self.assertEqual(last['change'],'130')
 def test_incomplete_coverage_and_first_day(self):
  self.save('2026-01-01',100);self.save('2026-01-02',120,unknown=True)
  days=portfolio_daily.calendar(self.c,1)['days'];self.assertIsNone(days[0]['change']);self.assertIsNone(days[1]['change'])
 def test_wallet_exchange_combination_and_account_dedup(self):
  wallets=[{'chain':'Ethereum','address':'0xabc','snapshot':{'quantity':'2'}}]
  exchange={'id':'a','snapshot':{'account_key':'same','balances':[{'asset':'BTC','quantity':'1','value_usd':'100'}]}}
  result=portfolio_daily.observation(wallets,{'ETH':{'price':'200'}},[exchange,{**exchange,'id':'b'}],1000)
  self.assertEqual(result['value'],'500');self.assertEqual(result['priced'],2)
  self.assertIsNone(portfolio_daily.observation([],{},[],1000))
import server,test_integrations,json
from unittest.mock import patch
class DailyAPITests(test_integrations.APITests):
 def test_refresh_records_connected_value_without_trades(self):
  with server.connect() as c:
   uid=c.execute('SELECT id FROM users WHERE email=?',('a@test.com',)).fetchone()[0]
   cursor=c.execute('INSERT INTO wallets(user_id,chain,address,label) VALUES (?,?,?,?)',(uid,'Ethereum','0x'+'1'*40,'Test wallet'))
   c.execute('INSERT INTO wallet_snapshots VALUES (?,?)',(cursor.lastrowid,json.dumps({'quantity':'2','symbol':'ETH'})));c.commit()
  with patch('providers.market_prices',return_value={'ETH':{'price':'200','source':'Test provider','updated_at':123}}):self.call(self.a,'refresh-prices',{})
  data=self.call(self.a,'state');self.assertEqual(data['trades'],[]);self.assertEqual(data['portfolio_calendar']['days'][0]['value'],'400');self.assertIsNone(data['portfolio_calendar']['days'][0]['change'])
  self.assertEqual(self.call(self.b,'state')['portfolio_calendar']['days'],[])
if __name__=='__main__':unittest.main()
