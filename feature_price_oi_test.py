import unittest
from unittest.mock import patch
import feature_price_oi as f

class PriceOITest(unittest.TestCase):
    def setUp(self):
        f._CACHE.clear()

    def test_exact_outer_join_never_forward_fills(self):
        rows = f.align({'price': {100: {'price': 10}, 200: {'price': 12}}, 'oi': {101: {'oi_coin': 3}, 200: {'oi_coin': 4}}, 'funding': {}})
        self.assertEqual([r['timestamp'] for r in rows], [100, 101, 200])
        self.assertIsNone(rows[1]['price'])
        self.assertIsNone(rows[0]['oi_coin'])
        self.assertEqual(rows[2]['price'], 12)

    def test_units_identity_and_invalid_numbers(self):
        rows = [{'symbol':'BTCUSDT','timestamp':100,'sumOpenInterest':'2','sumOpenInterestValue':'120000'},
                {'symbol':'ETHUSDT','timestamp':101,'sumOpenInterest':'1','sumOpenInterestValue':'2'},
                {'symbol':'BTCUSDT','timestamp':102,'sumOpenInterest':'NaN','sumOpenInterestValue':'2'}]
        self.assertEqual(f.observations(rows,'oi','BTCUSDT',0,200), {100:{'oi_coin':2.0,'oi_quote':120000.0}})
        self.assertIsNone(f.number(True))

    @patch.object(f.market_microstructure, 'identity', return_value=('bitcoin','BTC'))
    @patch.object(f.time, 'time', return_value=2000000000)
    def test_partial_failure_and_bounded_cached_calls(self, clock, identity):
        candle = [1999996400000,'10','11','9','10','5',1999999999999,'50',1,'1','10','0']
        with patch.object(f.providers,'request_json',side_effect=[[candle],ValueError('down'),[]]) as request:
            data = f.read(None,1,{})
            self.assertTrue(data['partial'])
            self.assertEqual(data['rows'][0]['price'],10)
            self.assertIsNone(data['rows'][0]['oi_coin'])
            self.assertEqual(request.call_count,3)
            self.assertTrue(f.read(None,1,{})['cached'])
            self.assertEqual(request.call_count,3)

    def test_validation_precedes_network(self):
        with patch.object(f.providers,'request_json') as request:
            for raw in ({'coin_id':'BTC'}, {'coin_id':[]}, {'period':'2m'}):
                with self.assertRaises(ValueError): f.read(None,1,raw)
            request.assert_not_called()

if __name__ == '__main__': unittest.main()
