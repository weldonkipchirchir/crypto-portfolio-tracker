import unittest
from unittest.mock import patch
from backend.integrations import providers
class QuoteMappings(unittest.TestCase):
 def test_verified_inj_grass_quote_ids(self):
  def request(url,**kwargs):
   self.assertIn('grass',url);self.assertIn('injective-protocol',url)
   return {'grass':{'usd':1.2,'last_updated_at':1800000000},'injective-protocol':{'usd':3.4,'last_updated_at':1800000000}}
  with patch.object(providers,'request_json',side_effect=request):
   rows=providers.market_prices(['INJ','GRASS']);self.assertEqual(rows['GRASS']['price'],'1.2');self.assertEqual(rows['INJ']['price'],'3.4')
