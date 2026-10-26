import unittest
from portfolio_performance import realized_calendar
class PerformanceTests(unittest.TestCase):
 def test_weighted_average_fees_and_years(self):
  rows=[dict(id=1,date='2023-01-01T00:00:00',symbol='BTC',side='buy',quantity='2',price='100',fee='2'),dict(id=2,date='2024-02-29T12:00:00',symbol='BTC',side='sell',quantity='1',price='150',fee='1'),dict(id=3,date='2025-01-01T00:00:00',symbol='BTC',side='buy',quantity='1',price='200',fee='0'),dict(id=4,date='2026-01-01T00:00:00',symbol='BTC',side='sell',quantity='2',price='100',fee='1')]
  result=realized_calendar(list(reversed(rows)));self.assertEqual(result['start_date'],'2023-01-01');self.assertEqual(result['days'],[{'date':'2024-02-29','realized':48.0,'sales':1},{'date':'2026-01-01','realized':-102.0,'sales':1}]);self.assertEqual(sum(d['realized'] for d in result['days']),-54)
 def test_empty_and_buy_only_do_not_invent_daily_returns(self):
  self.assertEqual(realized_calendar([])['days'],[])
  self.assertEqual(realized_calendar([dict(date='2024-01-01',symbol='ETH',side='buy',quantity='1',price='100',fee='0')])['days'],[])
 def test_sale_exceeds_holdings(self):
  with self.assertRaises(ValueError):realized_calendar([dict(date='2024-01-01',symbol='BTC',side='sell',quantity='1',price='100',fee='0')])
