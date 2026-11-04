import sqlite3, unittest
import feature_token_unlocks as f
class UnlockTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;f.init(self.c)
  self.event=dict(operation='create',coin_id='arbitrum',unlock_date='2028-02-29',amount='100',recipient='Team',source_url='https://example.org/vesting')
 def create(self,**kw):return f.action(self.c,1,{**self.event,**kw})
 def test_owner_provenance_and_supply(self):
  identity=self.create(circulating='1000',snapshot_asof='2026-11-04')['id']
  item=f.read(self.c,1,{})['events'][0]
  self.assertEqual(item['percent_circulating'],'10.000000');self.assertIn('not independently verified',item['provenance'])
  self.assertEqual(f.read(self.c,2,{})['events'],[])
  with self.assertRaises(ValueError):f.action(self.c,2,dict(operation='delete',id=identity,confirm=True))
  self.assertEqual(len(f.read(self.c,1,{'max_supply':100000,'circulating_supply':100})['events']),1)
  with self.assertRaises(ValueError):f.action(self.c,1,dict(operation='delete',id=identity))
  f.action(self.c,1,dict(operation='delete',id=identity,confirm=True));self.assertEqual(f.read(self.c,1,{})['events'],[])
 def test_dates_numbers_and_sources(self):
  for value in ['2027-02-29','2028-2-29','2028-02-29T00:00Z','bad']:
   with self.assertRaises(ValueError):self.create(unlock_date=value)
  for value in ['NaN','Infinity','0','-1','1e31','0.0000000000000000001']:
   with self.assertRaises(ValueError):self.create(amount=value)
  for value in ['http://example.com','javascript:alert(1)','https://localhost/x','https://127.0.0.1/x','https://user:pass@example.org','https://example.org:8080','https://example.org/\nfoo']:
   with self.assertRaises(ValueError):self.create(source_url=value)
  with self.assertRaises(ValueError):self.create(circulating='100')
  with self.assertRaises(ValueError):self.create(coin_id='ARB')
  self.create();self.assertIsNone(f.read(self.c,1,{})['events'][0]['percent_circulating'])
 def test_supply_cannot_create_schedule(self):
  d=f.read(self.c,1,{'coin_id':'arbitrum','max_supply':1000,'circulating_supply':10})
  self.assertEqual(d['events'],[]);self.assertFalse(d['provider']['configured'])
  with self.assertRaises(ValueError):self.create(operation='infer',max_supply=1000)
if __name__=='__main__':unittest.main()
