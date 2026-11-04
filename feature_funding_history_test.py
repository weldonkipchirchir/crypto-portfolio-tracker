import unittest
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs
import feature_funding_history as f

class FundingHistoryTests(unittest.TestCase):
    def setUp(self): f._CACHE.clear()
    def test_requests_validation_intervals_cache(self):
        calls=[]
        end=1800000000000
        def request(url):
            calls.append(url)
            if 'binance' in url:
                return [{'symbol':'BTCUSDT','fundingTime':end-7200000,'fundingRate':'0.0001'},
                        {'symbol':'BTCUSDT','fundingTime':end,'fundingRate':'-0.0002'},
                        {'symbol':'BTCUSDT','fundingTime':end+1,'fundingRate':'0.1'},
                        {'symbol':'ETHUSDT','fundingTime':end,'fundingRate':'0.1'},
                        {'symbol':'BTCUSDT','fundingTime':end,'fundingRate':'NaN'}]
            return {'retCode':0,'result':{'list':[{'symbol':'BTCUSDT','fundingRateTimestamp':str(end),'fundingRate':'0.0003'}]}}
        with patch.object(f.time,'time',return_value=end/1000), patch.object(f.providers,'request_json',side_effect=request):
            d=f.read(None,1,{})
            again=f.read(None,2,{})
        self.assertEqual(len(calls),2)
        self.assertTrue(again['cached'])
        self.assertEqual(d['venues'][0]['points'][1]['observed_spacing_hours'],2)
        self.assertIsNone(d['venues'][1]['points'][0]['observed_spacing_hours'])
        self.assertEqual(d['venues'][0]['points'][1]['rate'],-0.0002)
        for url in calls:
            q=parse_qs(urlparse(url).query)
            self.assertEqual(q['symbol'],['BTCUSDT'])
            self.assertEqual(int(q['endTime'][0])-int(q['startTime'][0]),30*86400000)
        self.assertEqual(parse_qs(urlparse(calls[1]).query)['category'],['linear'])
    def test_partial_failure_and_unknown_identity(self):
        def request(url):
            if 'binance' in url: raise ValueError('blocked')
            return {'retCode':0,'result':{'list':[]}}
        with patch.object(f.providers,'request_json',side_effect=request):
            d=f.read(None,1,{})
        self.assertTrue(d['partial'])
        self.assertTrue(d['venues'][0]['error'])
        self.assertIsNone(d['venues'][1]['error'])
        with self.assertRaises(ValueError): f.read(None,1,{'coin_id':'BTC'})
    def test_bounds(self):
        with patch.object(f.providers,'request_json',return_value={'retCode':0,'result':{'list':[{}]*201}}):
            with self.assertRaises(ValueError):f.venue('Bybit','BTCUSDT',0,100)

if __name__=='__main__':unittest.main()
