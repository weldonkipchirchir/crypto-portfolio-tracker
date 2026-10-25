import json,sqlite3,unittest
from unittest.mock import patch
import advanced_portfolio as a

class AdvancedTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;a.init(self.c)
  self.clock=patch('advanced_portfolio.time.time',return_value=2000000000);self.clock.start();self.addCleanup(self.clock.stop);self.addCleanup(self.c.close)
  self.contract='0x'+'a'*40
  self.w=[{'id':1,'chain':'Ethereum','address':'0x'+'b'*40,'snapshot':{'quantity':'1.000000000000000001','updated_at':2000000000},'token_snapshot':{'updated_at':2000000000,'tokens':[{'asset_id':'Ethereum:'+self.contract,'contract':self.contract,'quantity':'36.971015322469809651','price_usd':'0.2264','price_fetched_at':2000000000,'symbol':'PONS'}]}}]
  self.q={'ETH':{'price':'2000','updated_at':2000000000}}
 def test_exact(self):
  v=a.checkpoint(self.c,1,self.w,self.q)
  self.assertEqual(v['value_usd'],'2008.3702378690071669049864');self.assertEqual(v['priced_count'],2);self.assertEqual(v['stale_count'],0);self.assertTrue(v['partial']);self.assertNotIn('return',v)
 def test_base_native_uses_eth_quote(self):
  self.w[0]['chain']='Base';self.w[0]['token_snapshot']=None
  v=a.checkpoint(self.c,1,self.w,self.q)
  self.assertEqual(v['value_usd'],'2000.000000000000002000');self.assertEqual(v['priced_count'],1)
 def test_native_alias_fallback(self):
  self.w[0]['chain']='Base';self.w[0]['token_snapshot']=None
  self.assertEqual(a.checkpoint(self.c,1,self.w,{'ETH_BASE':self.q['ETH']})['priced_count'],1)
 def test_zero_price_unpriced(self):
  self.q['ETH']['price']='0'
  v=a.checkpoint(self.c,1,self.w,self.q);self.assertEqual(v['unpriced_count'],1);self.assertEqual(v['priced_count'],1)
 def test_recent_native_error_stale(self):
  self.w[0]['snapshot']['error']='Provider unavailable'
  self.assertEqual(a.checkpoint(self.c,1,self.w,self.q)['stale_count'],1)
 def test_ownership(self):
  a.checkpoint(self.c,1,self.w,self.q);a.toggle_watch(self.c,1,{'asset_id':'Ethereum:'+self.contract},self.w)
  self.assertEqual(a.state(self.c,2),{'checkpoints':[],'watchlist':[]})
  with self.assertRaises(ValueError):a.toggle_watch(self.c,2,{'asset_id':'Ethereum:'+self.contract},[])
 def test_cooldown(self):
  a.checkpoint(self.c,1,self.w,self.q)
  with self.assertRaisesRegex(ValueError,'minute'):a.checkpoint(self.c,1,self.w,self.q)
 def test_stale_and_invalid(self):
  self.w[0]['token_snapshot']['tokens'][0]['price_usd']='NaN';self.q['ETH']['updated_at']=1
  v=a.checkpoint(self.c,1,self.w,self.q);self.assertEqual(v['unpriced_count'],1);self.assertEqual(v['stale_count'],1);self.assertEqual(v['priced_count'],1)
 def test_timestamp_and_membership(self):
  self.w[0]['created_at']=123
  v=a.checkpoint(self.c,1,self.w,self.q);self.assertEqual(v['created_at'],2000000000)
  with patch('advanced_portfolio.time.time',return_value=2000000061):
   self.w[0]['address']='0x'+'c'*40
   v=a.checkpoint(self.c,1,self.w,self.q);self.assertTrue(v['membership_changed'])
 def test_balances_change(self):
  a.checkpoint(self.c,1,self.w,self.q)
  with patch('advanced_portfolio.time.time',return_value=2000000061):
   self.w[0]['snapshot']['quantity']='2';v=a.checkpoint(self.c,1,self.w,self.q);self.assertTrue(v['balances_changed']);self.assertFalse(v['membership_changed'])
 def test_cap_no_delete(self):
  for i in range(365):self.c.execute('INSERT INTO portfolio_checkpoints VALUES (?,?,?,?)',(str(i),1,i,'{}'))
  with self.assertRaisesRegex(ValueError,'365'):a.checkpoint(self.c,1,self.w,self.q)
  self.assertEqual(len(a.state(self.c,1)['checkpoints']),365)
 def test_watch_toggle_and_remove_absent(self):
  identity='Ethereum:'+self.contract
  self.assertTrue(a.toggle_watch(self.c,1,{'asset_id':identity},self.w)['watching'])
  self.assertFalse(a.toggle_watch(self.c,1,{'asset_id':identity},[])['watching'])
 def test_native_watch(self):
  v=a.toggle_watch(self.c,1,{'asset_id':'Ethereum:native'},self.w);self.assertIsNone(v['watchlist'][0]['contract'])
 def test_identity_no_symbol_or_wrong_case(self):
  for identity in ['PONS','Ethereum:'+self.contract.upper(),'Base:'+self.contract]:
   with self.assertRaises(ValueError):a.toggle_watch(self.c,1,{'asset_id':identity},self.w)
 def test_zero_unpriced_not_fabricated(self):
  self.w[0]['snapshot']['quantity']='0';self.w[0]['token_snapshot']['tokens'][0]['price_usd']=None
  with self.assertRaisesRegex(ValueError,'No priced'):a.checkpoint(self.c,1,self.w,self.q)
 def test_decimal_guards(self):
  for v in ['-1','Infinity','NaN','1e1000000','1e-1000000',True,None]:self.assertIsNone(a.number(v))
 def test_deduplicate_wallet_and_token(self):
  original=a.checkpoint(self.c,1,self.w,self.q)['value_usd']
  self.w.append(dict(self.w[0],id=2))
  self.assertEqual(a.checkpoint(self.c,2,self.w,self.q)['value_usd'],original)
 def test_tokens_limit(self):
  t=self.w[0]['token_snapshot']['tokens'][0];self.w[0]['token_snapshot']['tokens']=[dict(t,contract='0x'+format(i,'040x'),asset_id='Ethereum:0x'+format(i,'040x')) for i in range(201)]
  self.assertTrue(a.checkpoint(self.c,1,self.w,self.q)['truncated'])
 def test_watch_cap(self):
  for i in range(50):self.c.execute('INSERT INTO portfolio_favorites VALUES (?,?,?,?)',(str(i),1,str(i),'{}'))
  with self.assertRaisesRegex(ValueError,'50'):a.toggle_watch(self.c,1,{'asset_id':'Ethereum:native'},self.w)

if __name__=='__main__':unittest.main()
