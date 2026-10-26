import os,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
import test_integrations as base
class PublicRegistrationTests(base.APITests):
 def test_public_signup_respects_explicit_flag(self):
  with patch.dict(os.environ,{'ORBIT_REGISTRATION_EMAIL':'owner@example.test','ORBIT_PUBLIC_REGISTRATION':'0'}):
   import urllib.error
   with self.assertRaises(urllib.error.HTTPError) as error:self.call(self.client(),'register',{'email':'new-person@example.test','password':'Long-Test-Password-2026!'})
   self.assertEqual(error.exception.code,400)
  with patch.dict(os.environ,{'ORBIT_REGISTRATION_EMAIL':'owner@example.test','ORBIT_PUBLIC_REGISTRATION':'1'}):
   client=self.client();self.call(client,'register',{'email':'new-person@example.test','password':'Long-Test-Password-2026!'})
   self.assertEqual(self.call(client,'state')['email'],'new-person@example.test')
 def test_public_build_updates_copy(self):
  from build_static import build
  with patch.dict(os.environ,{'ORBIT_PUBLIC_REGISTRATION':'1'}),tempfile.TemporaryDirectory() as directory:
   build(directory)
   self.assertIn('content="public"',Path(directory,'app.html').read_text(encoding='utf-8'))
   self.assertNotIn('restricted to the deployment owner',Path(directory,'index.html').read_text(encoding='utf-8'))
if __name__=='__main__':unittest.main()
