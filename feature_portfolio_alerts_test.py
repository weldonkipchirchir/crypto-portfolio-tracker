import sqlite3,unittest,json
from unittest.mock import patch
import feature_portfolio_alerts as f
class Alerts(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
  self.c.execute('CREATE TABLE trades(user_id INTEGER,symbol TEXT)');self.c.executemany('INSERT INTO trades VALUES (?,?)',[(1,'BTC'),(1,'WBTC'),(2,'ETH')]);f.init(self.c)
 def create(self,uid=1,**kw):
  return f.action(self.c,uid,dict(operation='create',metric='value',operator='above',threshold='100',**kw))
 def check(self,value,reason=None):
  with patch.object(f,'snapshot',return_value=(None if value is None else {'value':f.number(value),'allocation':{'BTC':f.number(30)},'unrealized_return':None},reason)):
   return f.action(self.c,1,{'operation':'evaluate'})
 def test_crossing_and_stale_preserves_state(self):
  self.create();self.assertEqual(len(self.check(100)['events']),1);self.assertEqual(len(self.check(101)['events']),1)
  self.check(None,'Stale');self.assertEqual(len(self.check(102)['events']),1)
  self.check(90);self.assertEqual(len(self.check(110)['events']),2)
 def test_owner_and_exact_symbol(self):
  r=self.create()['rules'][0]
  self.assertEqual(f.read(self.c,2)['rules'],[])
  with self.assertRaises(ValueError):f.action(self.c,2,{'operation':'delete','id':r['id']})
  with self.assertRaises(ValueError):f.action(self.c,1,{'operation':'create','metric':'allocation','operator':'above','threshold':20,'asset':'ETH'})
  f.action(self.c,1,{'operation':'create','metric':'allocation','operator':'above','threshold':20,'asset':'WBTC'})
  self.assertEqual(len(self.check(100)['events']),1)
 def test_invalid_threshold(self):
  for v in ['NaN','Infinity',True,None]:
   with self.assertRaises(ValueError):f.action(self.c,1,{'operation':'create','metric':'value','operator':'above','threshold':v})
if __name__=='__main__':unittest.main()

class Snapshot(unittest.TestCase):
 def test_quote_freshness_and_cost(self):
  import types,sys
  c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
  c.execute('CREATE TABLE trades(user_id INTEGER,symbol TEXT)');c.execute("INSERT INTO trades VALUES(1,'BTC')")
  c.execute('CREATE TABLE prices(user_id INTEGER,symbol TEXT,price TEXT)');c.execute("INSERT INTO prices VALUES(1,'BTC','150')")
  c.execute('CREATE TABLE price_metadata(user_id INTEGER,symbol TEXT,updated_at INTEGER)');c.execute("INSERT INTO price_metadata VALUES(1,'BTC',1000)")
  calculate=lambda rows,prices:[dict(symbol='BTC',quantity=1,value=150,cost=100)] if rows else []
  with patch.dict(sys.modules,{'server':types.SimpleNamespace(calculate=calculate)}):
   values,reason=f.snapshot(c,1,1001);self.assertIsNone(reason);self.assertEqual(values['unrealized_return'],50)
   self.assertIsNone(f.snapshot(c,1,2000)[0]);self.assertIsNone(f.snapshot(c,2,1001)[0])
