import json,sqlite3,unittest
from unittest.mock import patch
import price_targets as p

class TargetTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;p.init(self.c);self.addCleanup(self.c.close)
  self.now=2000000000;self.clock=patch('price_targets.time.time',side_effect=lambda:self.now);self.clock.start();self.addCleanup(self.clock.stop)
  self.contract='0x'+'a'*40;self.identity='Ethereum:'+self.contract
  self.token={'asset_id':self.identity,'contract':self.contract,'symbol':'SAME','quantity':'2','price_usd':'10','price_fetched_at':self.now,'price_source':'DEX Screener'}
  self.wallets=[{'id':1,'chain':'Ethereum','address':'0x'+'b'*40,'snapshot':{'quantity':'1','updated_at':self.now},'token_snapshot':{'tokens':[self.token]}}]
  self.quotes={'ETH':{'price':'2000','updated_at':self.now,'source':'CoinGecko'}}
 def save(self,uid=1,identity=None,operator='above',target='10'):
  return p.save(self.c,uid,{'asset_id':identity or self.identity,'operator':operator,'target_usd':target},self.wallets,self.quotes)
 def tick(self,price):
  self.now+=1;self.token['price_usd']=price;self.token['price_fetched_at']=self.now
  return p.evaluate(self.c,1,self.wallets,self.quotes)
 def test_first_match_and_no_same_quote_duplicate(self):
  self.save();self.assertEqual(p.evaluate(self.c,1,self.wallets,self.quotes)['triggered'],1)
  self.assertEqual(p.evaluate(self.c,1,self.wallets,self.quotes)['evaluated'],0)
 def test_cross_rearm(self):
  self.save();p.evaluate(self.c,1,self.wallets,self.quotes)
  self.assertEqual(self.tick('11')['triggered'],0);self.assertEqual(self.tick('9')['triggered'],0);self.assertEqual(self.tick('10')['triggered'],1)
  self.assertEqual(len(p.state(self.c,1)['target_events']),2)
 def test_below_inclusive(self):
  self.save(operator='below');self.assertEqual(p.evaluate(self.c,1,self.wallets,self.quotes)['triggered'],1)
 def test_stale_failed_does_not_rearm(self):
  self.save();p.evaluate(self.c,1,self.wallets,self.quotes)
  self.now+=1000;self.token['price_usd']='1';self.assertEqual(p.evaluate(self.c,1,self.wallets,self.quotes)['evaluated'],0)
  self.token['price_fetched_at']=self.now;self.token['price_stale']=True;self.assertEqual(p.evaluate(self.c,1,self.wallets,self.quotes)['evaluated'],0)
  self.token.pop('price_stale');self.token['price_error']='Unavailable';self.assertEqual(p.evaluate(self.c,1,self.wallets,self.quotes)['evaluated'],0)
  self.token.pop('price_error');self.assertEqual(self.tick('11')['triggered'],0)
 def test_older_and_same_quote_ignored(self):
  self.save();p.evaluate(self.c,1,self.wallets,self.quotes);self.token['price_usd']='1';self.token['price_fetched_at']-=1
  self.assertEqual(p.evaluate(self.c,1,self.wallets,self.quotes)['evaluated'],0)
  self.assertEqual(self.tick('11')['triggered'],0)
 def test_future_and_fractional_stamp(self):
  self.save()
  for stamp in [self.now+61,str(self.now)+'.5','NaN']:
   self.token['price_fetched_at']=stamp;self.assertEqual(p.evaluate(self.c,1,self.wallets,self.quotes)['evaluated'],0)
 def test_identity_and_symbol_collision(self):
  self.save();self.token['asset_id']='Ethereum:0x'+'c'*40
  self.assertEqual(p.evaluate(self.c,1,self.wallets,self.quotes)['triggered'],0)
  for identity in ['SAME','Base:'+self.contract,'Ethereum:'+self.contract.upper()]:
   with self.assertRaises(ValueError):self.save(identity=identity)
 def test_owner_isolation_and_removed_history(self):
  target=self.save();p.evaluate(self.c,1,self.wallets,self.quotes)
  self.assertEqual(p.state(self.c,2),{'price_targets':[],'target_events':[]})
  with self.assertRaises(ValueError):p.remove(self.c,2,{'id':target['id']})
  self.wallets=[];p.remove(self.c,1,{'id':target['id']});self.assertEqual(len(p.state(self.c,1)['target_events']),1)
 def test_unknown_or_zero_holding(self):
  self.token['quantity']='0'
  with self.assertRaises(ValueError):self.save()
 def test_price_bounds_and_operator(self):
  for value in ['0','-1','NaN','Infinity','1e13','1e1000000',True,None]:
   with self.assertRaises(ValueError):self.save(target=value)
  with self.assertRaises(ValueError):self.save(operator='whatever')
 def test_duplicates_and_cap(self):
  self.save()
  with self.assertRaisesRegex(ValueError,'already'):self.save()
  for n in range(11,40):self.save(target=str(n))
  with self.assertRaisesRegex(ValueError,'30'):self.save(target='41')
 def test_event_cap_preserves_events(self):
  self.save()
  for i in range(200):self.c.execute('INSERT INTO price_target_events VALUES (?,?,?,?,?)',(str(i),1,'old',i,'{}'))
  result=p.evaluate(self.c,1,self.wallets,self.quotes)
  self.assertEqual(result['triggered'],0);self.assertTrue(result['event_limit_reached']);self.assertEqual(len(p.state(self.c,1)['target_events']),200);self.assertTrue(p.state(self.c,1)['price_targets'][0]['event_limit_reached'])
 def test_native_symbol_and_stale_holding_allowed(self):
  self.wallets[0]['chain']='Base';self.wallets[0]['snapshot']['updated_at']=1;self.wallets[0]['snapshot']['error']='Old holdings'
  self.save(identity='Base:native',target='1999')
  self.assertEqual(p.evaluate(self.c,1,self.wallets,self.quotes)['triggered'],1)
 def test_native_alias(self):
  self.wallets[0]['chain']='Base';self.quotes={'ETH_BASE':self.quotes['ETH']};self.save(identity='Base:native',target='1999')
  self.assertEqual(p.evaluate(self.c,1,self.wallets,self.quotes)['triggered'],1)
 def test_newest_quote_across_wallets(self):
  self.save();second=dict(self.token,price_usd='9',price_fetched_at=self.now+1)
  self.wallets.append(dict(self.wallets[0],id=2,token_snapshot={'tokens':[second]}))
  self.assertEqual(p.evaluate(self.c,1,self.wallets,self.quotes)['triggered'],0)
 def test_manual_prices_do_not_trigger(self):
  self.save();self.token['price_source']='Manual'
  self.assertEqual(p.evaluate(self.c,1,self.wallets,self.quotes)['triggered'],0)
  self.save(identity='Ethereum:native',target='1999');self.quotes['ETH']['source']='Manual'
  self.assertEqual(p.evaluate(self.c,1,self.wallets,self.quotes)['triggered'],0)
 def test_conflicting_same_time_rejected(self):
  self.save();second=dict(self.token,price_usd='9')
  self.wallets.append(dict(self.wallets[0],id=2,token_snapshot={'tokens':[second]}))
  self.assertEqual(p.evaluate(self.c,1,self.wallets,self.quotes)['evaluated'],0)
 def test_event_records_source(self):
  self.save();p.evaluate(self.c,1,self.wallets,self.quotes)
  self.assertEqual(p.state(self.c,1)['target_events'][0]['source'],'DEX Screener')
 def test_no_external_requests(self):
  self.save()
  with patch('providers.request_json',side_effect=AssertionError('Network forbidden')):p.evaluate(self.c,1,self.wallets,self.quotes)

if __name__=='__main__':unittest.main()
