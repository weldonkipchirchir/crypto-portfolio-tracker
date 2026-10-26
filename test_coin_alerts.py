import unittest,sqlite3,time
import coin_alerts as alerts
class CoinAlertsTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;alerts.init(self.c);self.now=1700000000
 def coin(self,price=110,stamp=None):return {'coin':{'id':'bitcoin','name':'Bitcoin','symbol':'BTC','current_price':price,'last_updated':self.now if stamp is None else stamp}}
 def save(self,uid=1,price='100',op='above'):
  return alerts.save(self.c,uid,{'coin_id':'bitcoin','target_usd':price,'operator':op},self.coin())
 def test_crossing_rearm_idempotency_and_first_observation(self):
  self.save();a=alerts.evaluate(self.c,1,self.coin(),self.now);self.assertEqual(a['triggered'],1);self.assertTrue(a['events'][0]['first_observation'])
  self.assertEqual(alerts.evaluate(self.c,1,self.coin(),self.now)['evaluated'],0)
  self.assertEqual(alerts.evaluate(self.c,1,self.coin(90,self.now+1),self.now+1)['triggered'],0)
  a=alerts.evaluate(self.c,1,self.coin(101,self.now+2),self.now+2);self.assertEqual(a['triggered'],1);self.assertFalse(a['events'][0]['first_observation'])
 def test_account_isolation(self):
  rule=self.save();self.assertEqual(alerts.state(self.c,2)['alerts'],[])
  with self.assertRaises(ValueError):alerts.remove(self.c,2,{'id':rule['id']})
  self.assertEqual(alerts.evaluate(self.c,2,self.coin(),self.now)['evaluated'],0)
 def test_stale_future_and_invalid_quotes(self):
  self.save()
  for price,stamp in [(110,self.now-901),(110,self.now+1),(True,self.now),('NaN',self.now),(-1,self.now),(110,True)]:
   with self.subTest(price=price,stamp=stamp),self.assertRaises(ValueError):alerts.evaluate(self.c,1,self.coin(price,stamp),self.now)
  bad=self.coin();bad['stale']=True
  with self.assertRaises(ValueError):alerts.evaluate(self.c,1,bad,self.now)
  self.assertEqual(alerts.state(self.c,1)['alerts'][0]['last_quote_at'],None)
 def test_validation_and_duplicate(self):
  self.save()
  for raw in [{'coin_id':'bitcoin','target_usd':'100','operator':'above'},{'coin_id':'bitcoin','target_usd':'NaN','operator':'below'},{'coin_id':'bitcoin','target_usd':True,'operator':'below'},{'coin_id':'bitcoin','target_usd':'0','operator':'below'},{'coin_id':'bitcoin','target_usd':'10','operator':'script'}]:
   with self.assertRaises(ValueError):alerts.save(self.c,1,raw,self.coin())
  with self.assertRaises(ValueError):alerts.save(self.c,1,{'coin_id':'ethereum','target_usd':10,'operator':'above'},self.coin())
 def test_limits_and_rolling_history(self):
  for i in range(50):self.save(price=str(i+1))
  with self.assertRaises(ValueError):self.save(price='99')
  for i in range(10):alerts.evaluate(self.c,1,self.coin(110 if i%2==0 else .1,self.now+i),self.now+i)
  self.assertEqual(len(alerts.state(self.c,1)['events']),200)
 def test_below_and_remove(self):
  rule=self.save(op='below');self.assertEqual(alerts.evaluate(self.c,1,self.coin(100),self.now)['triggered'],1)
  alerts.remove(self.c,1,{'id':rule['id']});self.assertEqual(alerts.state(self.c,1)['alerts'],[]);self.assertEqual(len(alerts.state(self.c,1)['events']),1)
if __name__=='__main__':unittest.main()
