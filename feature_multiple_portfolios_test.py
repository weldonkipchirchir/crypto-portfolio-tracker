import json,sqlite3,unittest
import feature_multiple_portfolios as f
class Groups(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
  self.c.executescript('CREATE TABLE wallets(id INTEGER,user_id INTEGER,chain TEXT,address TEXT,label TEXT);CREATE TABLE wallet_snapshots(wallet_id INTEGER,data TEXT);CREATE TABLE wallet_tokens(wallet_id INTEGER,data TEXT);CREATE TABLE exchange_connections(user_id INTEGER,id TEXT,label TEXT,snapshot TEXT);CREATE TABLE trades(user_id INTEGER,account TEXT,symbol TEXT,quantity TEXT,side TEXT);CREATE TABLE prices(user_id INTEGER,symbol TEXT,price TEXT);')
  f.init(self.c)
  self.c.execute('INSERT INTO trades VALUES(1,?,?,?,?)',('main','BTC','2','buy'))
  self.c.execute('INSERT INTO prices VALUES(1,?,?)',('BTC','10'))
  for identity in ('one','two'):
   self.c.execute('INSERT INTO exchange_connections VALUES(1,?,?,?)',(identity,identity,json.dumps({'account_key':'same','updated_at':1,'balances':[{'asset':'BTC','quantity':'2','value_usd':'20'}]})))
 def save(self,**kw):
  raw=dict(name='Group',kind='ledger',members={'accounts':['main']});raw.update(kw);return f.action(self.c,1,raw)
 def test_owner_isolation(self):
  group=self.save()
  self.assertEqual(f.read(self.c,2,{})['groups'],[])
  with self.assertRaises(ValueError):f.action(self.c,2,dict(operation='delete',id=group['id']))
  with self.assertRaises(ValueError):f.action(self.c,2,dict(name='X',kind='ledger',members={'accounts':['main']}))
 def test_union_and_separate_views(self):
  self.save();self.save(name='Other')
  self.save(kind='connected',members={'exchanges':['one','two']})
  d=f.read(self.c,1,{})
  self.assertEqual(d['combined']['ledger']['value'],'20')
  self.assertEqual(d['combined']['connected']['value'],'20')
  self.assertNotIn('total',d['combined'])
 def test_invalid_mixed_and_foreign_members(self):
  for members in ({'wallets':[99]},{'accounts':['foreign']},{'wallets':[True]},{'exchanges':['one'],'accounts':['main']}):
   with self.subTest(members=members),self.assertRaises(ValueError):self.save(members=members)
 def test_edit_delete_only_group(self):
  identity=self.save()['id'];self.save(id=identity,name='Renamed')
  self.assertEqual(len(f.read(self.c,1,{})['groups']),1)
  f.action(self.c,1,dict(id=identity,operation='delete'))
  self.assertEqual(self.c.execute('SELECT COUNT(*) FROM trades').fetchone()[0],1)
 def test_bounds(self):
  with self.assertRaises(ValueError):self.save(name='x'*81)
  for i in range(20):self.save(name=str(i))
  with self.assertRaises(ValueError):self.save()
if __name__=='__main__':unittest.main()
