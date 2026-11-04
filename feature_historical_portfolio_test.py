import json, sqlite3, unittest
import feature_historical_portfolio as history

class HistoryTest(unittest.TestCase):
 def test_account_scope_and_observed_values(self):
  c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
  c.execute('CREATE TABLE portfolio_daily_values(user_id,day,data)')
  c.execute('CREATE TABLE portfolio_checkpoints(user_id,created_at,id,data)')
  for uid,day,stamp,value in [(1,'2026-01-01',1767225600,'10'),(1,'2026-01-03',1767398400,'20'),(2,'2026-01-02',1767312000,'999')]:
   c.execute('INSERT INTO portfolio_daily_values VALUES (?,?,?)',(uid,day,json.dumps(dict(observed_at=stamp,value=value,balance_fingerprint=day))))
  d=history.read(c,1,{})
  self.assertEqual([p['value'] for p in d['series']['connected']],['10','20'])
  self.assertEqual([p['date'] for p in d['series']['connected']],['2026-01-01','2026-01-03'])
  self.assertTrue(d['series']['connected'][1]['balances_changed'])
  self.assertEqual(d['series']['wallets'],[])
  self.assertFalse(d['series']['connected'][0]['freshness_verified'])
  point=history._points([{'data':json.dumps({'created_at':1767225600,'value_usd':'10','partial':True,'stale_count':0})}],'wallets')[0]
  self.assertTrue(point['partial']);self.assertTrue(point['freshness_verified'])
if __name__=='__main__':unittest.main()
