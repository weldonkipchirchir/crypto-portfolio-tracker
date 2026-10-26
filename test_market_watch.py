import json,sqlite3,unittest
from unittest.mock import patch
import market_watch as w
class WatchTests(unittest.TestCase):
 def setUp(self):self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;w.init(self.c);self.addCleanup(self.c.close)
 def test_account_scope_toggle_and_no_prices(self):
  saved={'id':'bitcoin','name':'Bitcoin','symbol':'BTC'}
  self.assertEqual(w.toggle(self.c,1,{'coin_id':'bitcoin'},saved)['coins'][0]['id'],'bitcoin');self.assertEqual(w.state(self.c,2)['coins'],[]);self.assertNotIn('current_price',w.state(self.c,1)['coins'][0]);self.assertEqual(w.toggle(self.c,1,{'coin_id':'bitcoin'})['coins'],[])
 def test_rejects_unverified_and_caps(self):
  with self.assertRaises(ValueError):w.toggle(self.c,1,{'coin_id':'bitcoin'})
  for i in range(100):w.toggle(self.c,1,{'coin_id':'coin-'+str(i)},{'id':'coin-'+str(i),'name':'Coin','symbol':'C'})
  with self.assertRaises(ValueError):w.toggle(self.c,1,{'coin_id':'extra'},{'id':'extra'})
  self.assertEqual(len(w.state(self.c,1)['coins']),100)
 def test_resolve_uses_verified_provider_identity(self):
  with patch('coin_market.allowed',return_value='bitcoin'),patch('coin_market.listings',return_value={'coins':[{'id':'bitcoin','name':'<b>Bitcoin</b>','symbol':'BTC'}]}):self.assertEqual(w.resolve('bitcoin')['name'],'Bitcoin')
if __name__=='__main__':unittest.main()
