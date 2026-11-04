import unittest
from unittest.mock import patch
import feature_concentration as f

class TaxonomyTests(unittest.TestCase):
    def setUp(self): f.CACHE.clear()
    def test_bounded_stablecoin_and_cache(self):
        with patch.object(f.market,'request',return_value=[{'id':'usd-coin','symbol':'USDC'},{'id':'invalid ID'}]) as request:
            result=f.read(None,1,{'category':'stablecoin'})
            self.assertEqual(result['coin_ids'],['usd-coin'])
            self.assertIn('per_page=250',request.call_args.args[0])
            self.assertIn('category=stablecoins',request.call_args.args[0])
            self.assertEqual(f.read(None,2,{'category':'stablecoin'}),result)
            self.assertEqual(request.call_count,1)
    def test_narrative_one_existing_loader(self):
        with patch.object(f.intelligence,'narratives',return_value={'coins':[{'id':'chainlink'}],'stale':True}) as request:
            result=f.read(None,1,{'category':'rwa'})
            request.assert_called_once_with('rwa')
            self.assertEqual(result['coin_ids'],['chainlink'])
            self.assertTrue(result['stale'])
    def test_failure_caches_no_inferred_memberships(self):
        with patch.object(f.market,'request',side_effect=ValueError('offline')) as request:
            result=f.read(None,1,{'category':'stablecoin'})
            self.assertFalse(result['available'])
            self.assertEqual(result['coin_ids'],[])
            self.assertIn('unclassified',result['coverage'])
            f.read(None,1,{'category':'stablecoin'})
            self.assertEqual(request.call_count,1)
    def test_fixed_allowlist(self):
        with patch.object(f.market,'request') as request:
            with self.assertRaises(ValueError): f.read(None,1,{'category':'untrusted'})
            request.assert_not_called()

if __name__=='__main__': unittest.main()
