import unittest
import roadmap_features as r
class DispatcherTests(unittest.TestCase):
 def test_allowlist(self):
  self.assertEqual(len(r.IDS),25);self.assertEqual(len(set(r.IDS)),25)
  for key in ['../server','server',None,{},[]]:
   with self.assertRaises(ValueError):r.module(key)
 def test_unknown_dispatch_rejected(self):
  for fn in (r.read,r.action):
   with self.assertRaises(ValueError):fn(None,1,{'feature':'no-such-feature'})
if __name__=='__main__':unittest.main()
