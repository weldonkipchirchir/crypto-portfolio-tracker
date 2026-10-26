"""Optional real PostgreSQL tests. Set ORBIT_TEST_DATABASE_URL to a disposable database."""
import os,uuid,unittest
from unittest.mock import patch
import test_integrations as base
import cloud_storage
@unittest.skipUnless(os.environ.get('ORBIT_TEST_DATABASE_URL'),'Disposable PostgreSQL not configured')
class CloudTests(base.APITests):
 def owned_wallet(self):
  import test_advanced_api
  return test_advanced_api.AdvancedAPITests.owned_wallet(self)
 def test_advanced_api_checkpoint(self):
  import test_advanced_api
  test_advanced_api.AdvancedAPITests.test_checkpoint_uses_server_data_and_isolation(self)
 def test_advanced_api_watchlist(self):
  import test_advanced_api
  test_advanced_api.AdvancedAPITests.test_watchlist_only_owns_identity_and_reversible(self)
 def test_targets_authority_and_account_isolation(self):
  import test_targets_api
  # Use the target fixture to mark a genuine eligible provider quote.
  original=self.owned_wallet
  self.owned_wallet=lambda:test_targets_api.TargetsAPITests.owned_wallet(self)
  try:test_targets_api.TargetsAPITests.test_targets_authority_and_account_isolation(self)
  finally:self.owned_wallet=original
 def test_targets_refresh(self):
  import test_targets_api
  original=self.owned_wallet
  self.owned_wallet=lambda:test_targets_api.TargetsAPITests.owned_wallet(self)
  try:test_targets_api.TargetsAPITests.test_price_refresh_evaluates_without_duplicates(self)
  finally:self.owned_wallet=original
 def test_research_auth_routes(self):
  import test_research_api
  test_research_api.ResearchAPITests.test_research_routes_and_auth(self)
 def test_market_watch_account_scope(self):
  import test_research_api
  test_research_api.ResearchAPITests.test_watchlist_accounts_and_remove_without_network(self)
 def test_markets_auth_routes(self):
  import test_markets_api
  test_markets_api.MarketsAPITests.test_authentication_and_routes(self)
 def test_markets_shared_cache(self):
  import test_markets_api
  test_markets_api.MarketsAPITests.test_shared_cache_and_source_files(self)
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
