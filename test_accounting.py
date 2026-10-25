import unittest
from server import calculate,trade
class AccountingTests(unittest.TestCase):
 def test_partial_sale_with_fees(self):
  rows=[trade(dict(date='2026-01-01',symbol='ETH',side='buy',quantity=2,price=100,fee=10)),trade(dict(date='2026-01-02',symbol='ETH',side='sell',quantity=1,price=150,fee=5))]
  a=calculate(rows,{'ETH':'160'})[0]
  self.assertEqual(a['cost'],105); self.assertEqual(a['realized'],40); self.assertEqual(a['unrealized'],55)
 def test_weighted_average(self):
  rows=[trade(dict(date='2026-01-01',symbol='SOL',side='buy',quantity=q,price=p)) for q,p in [(1,10),(3,20)]]
  self.assertEqual(calculate(rows,{})[0]['average_buy'],17.5)
 def test_unknown_price(self):
  self.assertIsNone(calculate([trade(dict(date='2026-01-01',symbol='SOL',side='buy',quantity=1,price=10))],{})[0]['unrealized'])
 def test_oversell(self):
  with self.assertRaises(ValueError): calculate([trade(dict(date='2026-01-01',symbol='SOL',side='sell',quantity=1,price=10))],{})
 def test_invalid_numbers(self):
  for value in ['NaN','Infinity','-1']:
   with self.assertRaises(ValueError): trade(dict(date='2026-01-01',symbol='SOL',side='buy',quantity=value,price=10))
if __name__=='__main__': unittest.main()
