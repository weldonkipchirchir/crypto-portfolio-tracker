import unittest
import feature_liquidation_dashboard as feature
class Tests(unittest.TestCase):
    def test_public_configuration(self):
        d = feature.read(None, 1, {})
        self.assertEqual(d['events'], [])
        self.assertEqual(d['status'], 'idle')
        self.assertEqual(d['limit'], 100)
        self.assertEqual(d['source'], 'wss://ws.okx.com:8443/ws/v5/public')
    def test_instrument_validation(self):
        with self.assertRaises(ValueError): feature.read(None, 1, {'pair':'FAKE'})
if __name__ == '__main__': unittest.main()
