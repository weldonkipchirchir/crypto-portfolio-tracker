import unittest,urllib.error
import test_integrations
class TradeEditTests(test_integrations.APITests):
 def test_edit_recalculates_and_rejects_invalid_history(self):
  self.call(self.a,'trade',dict(date='2026-01-01',symbol='BTC',side='buy',quantity=2,price=100,fee=2))
  self.call(self.a,'trade',dict(date='2026-01-02',symbol='BTC',side='sell',quantity=1,price=150,fee=1))
  buy=self.call(self.a,'state')['trades'][0]
  self.call(self.a,'trade-update',{**buy,'price':120})
  state=self.call(self.a,'state');self.assertEqual(len(state['trades']),2)
  self.assertEqual(state['assets'][0]['realized'],28)
  self.assertEqual(state['trades'][1]['realized_pnl'],28)
  self.assertEqual(state['trades'][0]['net_cash_flow'],-242)
  self.assertEqual(state['assets'][0]['cost'],121)
  with self.assertRaises(urllib.error.HTTPError):self.call(self.a,'trade-update',{**buy,'quantity':0.5})
  self.assertEqual(self.call(self.a,'state')['assets'][0]['cost'],121)
  with self.assertRaises(urllib.error.HTTPError):self.call(self.b,'trade-update',{**buy,'price':1})
  self.assertEqual(self.call(self.a,'state')['assets'][0]['cost'],121)
if __name__=='__main__':unittest.main()
