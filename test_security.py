import json, unittest, urllib.request, urllib.error
from unittest.mock import patch
from test_integrations import APITests
import server

class SecurityTests(APITests):
 def setUp(self):
  server.AUTH_ATTEMPTS.clear()
  super().setUp()
 def request_status(self,body=b'{}',headers=None):
  req=urllib.request.Request('http://127.0.0.1:'+str(self.app.server_port)+'/api/login',data=body,headers=headers or {'Content-Type':'application/json'})
  try:
   with urllib.request.urlopen(req) as response:return response.status
  except urllib.error.HTTPError as error:return error.code
 def test_cross_site_and_host(self):
  self.assertEqual(self.request_status(headers={'Content-Type':'application/json','Origin':'https://evil.example'}),403)
  self.assertEqual(self.request_status(headers={'Content-Type':'application/json','Sec-Fetch-Site':'cross-site'}),403)
  self.assertEqual(self.request_status(headers={'Content-Type':'application/json','Host':'evil.example'}),403)
 def test_body_contract(self):
  self.assertEqual(self.request_status(headers={'Content-Type':'text/plain'}),415)
  for body in [b'[]',b'null',b'{',b'0']:
   self.assertEqual(self.request_status(body),400)
 def test_auth_throttle(self):
  with patch('server.password',return_value='invalid'):
   for i in range(28):self.request_status(json.dumps({'email':'missing@test.com','password':'test-password-123'}).encode())
   self.assertEqual(self.request_status(),429)
 def test_input_bounds(self):
  for value in ['1e9999999','1e-9999999','9'*81,True]:
   with self.assertRaises(ValueError):server.number(value)
  for value in ['<img>','ETH\nX','A'*31]:
   with self.assertRaises(ValueError):server.symbol_value(value)
 def test_security_headers(self):
  with urllib.request.urlopen('http://127.0.0.1:'+str(self.app.server_port)+'/') as response:
   self.assertEqual(response.headers['X-Frame-Options'],'DENY')
   self.assertEqual(response.headers['Referrer-Policy'],'no-referrer')
   self.assertIn("frame-ancestors 'none'",response.headers['Content-Security-Policy'])
 def test_logout_revokes(self):
  self.call(self.a,'logout',{})
  with self.assertRaises(urllib.error.HTTPError) as error:self.call(self.a,'state')
  self.assertEqual(error.exception.code,401)

if __name__=='__main__':unittest.main()
