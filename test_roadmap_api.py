import unittest,urllib.error
from unittest.mock import patch
import test_integrations as base
class FeatureAPITests(unittest.TestCase):
 setUp=base.APITests.setUp
 tearDown=base.APITests.tearDown
 client=base.APITests.client
 call=base.APITests.call
 def test_authenticated_dispatch_owner(self):
  with patch('roadmap_features.read',side_effect=lambda c,uid,raw:{'owner':uid}),patch('roadmap_features.action',side_effect=lambda c,uid,raw:{'owner':uid,'ok':True}):
   a=self.call(self.a,'feature-read',{'feature':'missing_cost'})['owner'];b=self.call(self.b,'feature-read',{'feature':'missing_cost'})['owner']
   self.assertNotEqual(a,b);self.assertEqual(self.call(self.a,'feature-action',{'feature':'missing_cost'})['owner'],a)
   for route in ('feature-read','feature-action'):
    with self.assertRaises(urllib.error.HTTPError) as caught:self.call(self.client(),route,{'feature':'missing_cost'})
    self.assertEqual(caught.exception.code,401)
 def test_unknown_feature_rejected(self):
  for route in ('feature-read','feature-action'):
   with self.assertRaises(urllib.error.HTTPError) as caught:self.call(self.a,route,{'feature':'../server'})
   self.assertEqual(caught.exception.code,400)
if __name__=='__main__':unittest.main()
