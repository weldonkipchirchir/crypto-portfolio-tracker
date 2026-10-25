import os,unittest
from unittest.mock import patch
import coin_market as m,protocol_data as p
class ProtocolTests(unittest.TestCase):
 def setUp(self):m.CACHE.clear();m.FAILURES.clear();self.env=patch.dict(os.environ,{'DEFILLAMA_API_KEY':''});self.env.start();self.addCleanup(self.env.stop);self.ids=patch('coin_market.allowed',side_effect=lambda x:x);self.ids.start();self.addCleanup(self.ids.stop)
 def test_exact_id_revenue_no_ticker_guess(self):
  with patch('providers.request_json',return_value={'gecko_id':'aave','name':'Aave','total24h':12,'total7d':0,'total30d':None}):d=p.fundamentals('aave')
  self.assertTrue(d['revenue']['available']);self.assertEqual(d['revenue']['week_usd'],'0');self.assertIsNone(d['revenue']['month_usd']);self.assertFalse(d['unlocks']['available'])
 def test_identity_mismatch_not_revenue(self):
  with patch('providers.request_json',return_value={'gecko_id':'wrong','name':'Aave','total24h':999}):d=p.fundamentals('aave')
  self.assertFalse(d['revenue']['available'])
 def test_invalid_numbers_and_provider_failure(self):
  with patch('providers.request_json',return_value={'gecko_id':'aave','total24h':'NaN','total7d':-1}):d=p.fundamentals('aave')
  self.assertFalse(d['revenue']['available']);m.CACHE.clear()
  with patch('providers.request_json',side_effect=ValueError('provider unavailable')):
   self.assertFalse(p.fundamentals('aave')['revenue']['available'])
 def test_optional_unlock_summary_and_key_not_returned(self):
  with patch.dict(os.environ,{'DEFILLAMA_API_KEY':'fake-test-key'}),patch('providers.request_json',side_effect=[{'gecko_id':'aave','total24h':10},[{'gecko_id':'aave','name':'Aave','totalLocked':12,'unlocksPerDay':1,'events':[{'timestamp':1700000000,'description':'Release'}]}]]) as req:d=p.fundamentals('aave')
  self.assertTrue(d['unlocks']['available']);self.assertEqual(d['unlocks']['locked_tokens'],'12');self.assertNotIn('fake-test-key',str(d));self.assertEqual(req.call_args.args[0],'https://pro-api.llama.fi/fake-test-key/api/emissions')
 def test_independent_failure_and_empty_unlock_coverage(self):
  with patch.dict(os.environ,{'DEFILLAMA_API_KEY':'fake'}),patch('providers.request_json',side_effect=[ValueError('offline'),[{'gecko_id':'aave','totalLocked':12}]]):
   d=p.fundamentals('aave');self.assertFalse(d['revenue']['available']);self.assertTrue(d['unlocks']['available'])
  m.CACHE.clear();m.FAILURES.clear()
  with patch.dict(os.environ,{'DEFILLAMA_API_KEY':'fake'}),patch('providers.request_json',side_effect=[{},[{'gecko_id':'aave'}]]):self.assertFalse(p.fundamentals('aave')['unlocks']['available'])
 def test_unlock_wrong_identity_and_duplicate_rejected(self):
  for rows in [[{'gecko_id':'other'}],[{'gecko_id':'aave'},{'gecko_id':'aave'}]]:
   m.CACHE.clear()
   with patch.dict(os.environ,{'DEFILLAMA_API_KEY':'fake'}),patch('providers.request_json',side_effect=[{},rows]):self.assertFalse(p.fundamentals('aave')['unlocks']['available'])
if __name__=='__main__':unittest.main()
