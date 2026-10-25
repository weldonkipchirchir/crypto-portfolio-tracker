"""Optional real PostgreSQL tests. Set ORBIT_TEST_DATABASE_URL to a disposable database."""
import os,uuid,unittest
from unittest.mock import patch
import test_integrations as base
import cloud_storage
@unittest.skipUnless(os.environ.get('ORBIT_TEST_DATABASE_URL'),'Disposable PostgreSQL not configured')
class CloudTests(base.APITests):
 def test_concurrent_sales_cannot_oversell(self):
  import test_features
  test_features.FeatureAPITests.test_concurrent_sales_cannot_oversell(self)

 def setUp(self):
  import psycopg
  from psycopg import sql
  from psycopg.conninfo import make_conninfo
  self.url=os.environ['ORBIT_TEST_DATABASE_URL'];self.schema='orbit_test_'+uuid.uuid4().hex
  with psycopg.connect(self.url,autocommit=True) as c:c.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(self.schema)))
  def cleanup():
   with psycopg.connect(self.url,autocommit=True) as c:c.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(self.schema)))
  self.addCleanup(cleanup)
  self.env=patch.dict(os.environ,{'DATABASE_URL':make_conninfo(self.url,options='-csearch_path='+self.schema),'ORBIT_REGISTRATION_EMAIL':''});self.env.start();self.addCleanup(self.env.stop)
  cloud_storage.initialize_limits();super().setUp()
 def test_upsert_id_rows_and_quota(self):
  with cloud_storage.connect() as c:
   uid=c.execute('SELECT id FROM users WHERE email=?',('a@test.com',)).fetchone()[0]
   c.execute('INSERT OR REPLACE INTO prices VALUES (?,?,?)',(uid,'ETH','1'))
   c.execute('INSERT OR REPLACE INTO prices VALUES (?,?,?)',(uid,'ETH','2'))
   self.assertEqual(c.execute('SELECT price FROM prices WHERE user_id=?',(uid,)).fetchone()['price'],'2')
   trade=c.execute('INSERT INTO trades(user_id,date,symbol,side,quantity,price,fee,account) VALUES (?,?,?,?,?,?,?,?)',(uid,'2026-01-01','ETH','buy','1','2','0','Test'))
   self.assertIsInstance(trade.lastrowid,int)
  self.assertTrue(cloud_storage.allowance('test',1,60));self.assertFalse(cloud_storage.allowance('test',1,60))
 def test_lease_exclusion(self):
  from runtime_security import BudgetExceeded
  with cloud_storage.provider_action(123):
   with self.assertRaises(BudgetExceeded):
    with cloud_storage.provider_action(123):pass
  with cloud_storage.provider_action(123):pass
 def test_rollback(self):
  with self.assertRaises(ValueError):
   with cloud_storage.connect() as c:
    c.execute('INSERT INTO users(email,password) VALUES (?,?)',('rollback@test.com','dummy'));raise ValueError()
  with cloud_storage.connect() as c:self.assertIsNone(c.execute('SELECT id FROM users WHERE email=?',('rollback@test.com',)).fetchone())
if __name__=='__main__':unittest.main()
