import unittest,sqlite3
import feature_fee_income as f
class IncomeTests(unittest.TestCase):
 def setUp(self):self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;f.init(self.c)
 def test_unknown_usd_and_owner(self):
  raw={'operation':'create','kind':'earn_reward','asset':'Ethereum:native','quantity':'0.000000000000000001','date':'2026-01-01T00:00:00Z','source':'statement 1'}
  identity=f.action(self.c,1,raw)['id'];d=f.read(self.c,1,{})
  self.assertEqual(d['unknown_usd'],1);self.assertIsNone(d['net_usd']);self.assertEqual(d['records'][0]['quantity'],'1E-18');self.assertEqual(f.read(self.c,2,{})['records'],[])
  with self.assertRaises(ValueError):f.action(self.c,2,{'operation':'delete','id':identity,'confirm':True})
  f.action(self.c,1,{'operation':'delete','id':identity,'confirm':True});self.assertEqual(f.read(self.c,1,{})['records'],[])
 def test_known_totals(self):
  raw={'operation':'create','asset':'bitcoin','quantity':'1','date':'2026-01-01T00:00:00Z','source':'statement','usd':'10'}
  f.action(self.c,1,{**raw,'kind':'staking_reward'});f.action(self.c,1,{**raw,'kind':'funding_paid','usd':'3'})
  self.assertEqual(f.read(self.c,1,{})['net_usd'],'7')
if __name__=='__main__':unittest.main()
