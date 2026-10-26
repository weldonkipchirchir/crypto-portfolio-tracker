import base64,hashlib,json,os,sqlite3,unittest
from unittest.mock import patch
import account_features as a
import exchange_connections as e

class AccountFeaturesTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
  self.c.executescript('CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT,password TEXT); CREATE TABLE sessions(token TEXT,user_id INTEGER,expires REAL);')
  salt='ab'*16;digest=hashlib.scrypt(b'original-password',salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
  self.c.execute('INSERT INTO users VALUES (1,?,?)',('a@example.test',salt+':'+digest));self.c.execute('INSERT INTO users VALUES (2,?,?)',('b@example.test',salt+':'+digest))
  self.c.execute('INSERT INTO sessions VALUES (?,?,?)',('session',1,99999999));a.init(self.c);e.init(self.c)
 def tearDown(self):self.c.close()
 def test_profile_scope_and_limits(self):
  a.save_profile(self.c,1,{'name':'Alice'})
  self.assertEqual(a.state(self.c,1)['name'],'Alice');self.assertEqual(a.state(self.c,2)['name'],'')
  for value in ['x'*81,'bad\x00name',None]:
   with self.assertRaises(ValueError):a.save_profile(self.c,1,{'name':value})
 def test_password_reauth_and_session_revocation(self):
  with self.assertRaises(ValueError):a.change_password(self.c,1,{'current_password':'incorrect','new_password':'new-password-123'})
  self.assertEqual(self.c.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],1)
  result=a.change_password(self.c,1,{'current_password':'original-password','new_password':'new-password-123'})
  self.assertTrue(result['sign_in_required']);self.assertEqual(self.c.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],0)
  with self.assertRaises(ValueError):a.change_password(self.c,1,{'current_password':'original-password','new_password':'other-password-123'})
 def test_notes_scoped_and_limits(self):
  note=a.save_note(self.c,1,{'title':'Lesson','body':'<script>plain text</script>'})['notes'][0]
  self.assertEqual(a.notes(self.c,2)['notes'],[])
  a.delete_note(self.c,2,{'note_id':note['note_id']});self.assertEqual(len(a.notes(self.c,1)['notes']),1)
  a.save_note(self.c,1,{'note_id':note['note_id'],'title':'Updated','body':'Hello'})
  self.assertEqual(a.notes(self.c,1)['notes'][0]['title'],'Updated')
  with self.assertRaises(ValueError):a.save_note(self.c,1,{'title':'A','body':'x'*20001})
  a.delete_note(self.c,1,{'note_id':note['note_id']});self.assertEqual(a.notes(self.c,1)['notes'],[])
 def test_exchange_fail_closed_config(self):
  with patch.dict(os.environ,{'ORBIT_EXCHANGE_KEY':''}):
   self.assertFalse(e.state(self.c,1)['configured'])
   with self.assertRaises(ValueError):e.prepare({'api_key':'a'*64,'api_secret':'b'*64})
 def test_permissions_and_snapshot(self):
  permissions={x:False for x in e.PERMISSIONS};permissions.update(enableReading=True,ipRestrict=True)
  account={'balances':[{'asset':'BTC','free':'1.2','locked':'.1'},{'asset':'ETH','free':'0','locked':'0'}]}
  with patch.object(e,'signed',side_effect=[permissions,account]),patch.object(e.coin_market,'listings',return_value={'coins':[]}):
   result=e.snapshot('a','b');self.assertEqual(result['balances'][0]['quantity'],'1.3');self.assertEqual(len(result['balances']),1)
  for field in e.PERMISSIONS:
   unsafe={**permissions,field:True}
   with patch.object(e,'signed',return_value=unsafe),self.assertRaises(ValueError):e.snapshot('a','b')
  with patch.object(e,'signed',return_value={**permissions,'enableFutureTradingPermission':True}),self.assertRaises(ValueError):e.snapshot('a','b')
  for value in (None,0,'false'):
   with patch.object(e,'signed',return_value={**permissions,'enableWithdrawals':value}),self.assertRaisesRegex(ValueError,'all permission flags'):e.snapshot('a','b')
  del permissions['enableWithdrawals']
  with patch.object(e,'signed',return_value=permissions),self.assertRaises(ValueError):e.snapshot('a','b')
 def test_malformed_balances(self):
  permissions={x:False for x in e.PERMISSIONS};permissions['enableReading']=True
  for amount in ['NaN','Infinity','-1','1e99']:
   with patch.object(e,'signed',side_effect=[permissions,{'balances':[{'asset':'BTC','free':amount,'locked':'0'}]}]),self.assertRaises(ValueError):e.snapshot('a','b')
 def test_exchange_preserves_high_precision_balances_and_values(self):
  permissions={x:False for x in e.PERMISSIONS};permissions['enableReading']=True
  account={'balances':[{'asset':'BTC','free':'12345678901234567890.123456789012345678','locked':'0.000000000000000001'}]}
  quotes={'coins':[{'id':'bitcoin','current_price':'12345.123456789012345678'}]}
  with patch.object(e,'signed',side_effect=[permissions,account]),patch.object(e.coin_market,'listings',return_value=quotes):
   row=e.snapshot('a','b')['balances'][0]
  self.assertEqual(row['quantity'],'12345678901234567890.123456789012345679')
  from decimal import Decimal,localcontext
  with localcontext() as ctx:
   ctx.prec=160
   self.assertEqual(Decimal(row['value_usd']),Decimal(row['quantity'])*Decimal(quotes['coins'][0]['current_price']))
 def test_invalid_upstream_shapes_fail_cleanly(self):
  permissions={x:False for x in e.PERMISSIONS};permissions['enableReading']=True
  for invalid in (None,[],False,'bad'):
   with patch.object(e,'signed',return_value=invalid),self.assertRaisesRegex(ValueError,'permission response'):e.snapshot('a','b')
   with patch.object(e,'signed',side_effect=[permissions,invalid]),self.assertRaisesRegex(ValueError,'balance response'):e.snapshot('a','b')
  for invalid in ('true',1,None):
   with patch.object(e,'signed',return_value={**permissions,'enableNewTrading':invalid}),self.assertRaisesRegex(ValueError,'reading-only'):e.snapshot('a','b')
 def test_signed_transport_never_exposes_provider_error(self):
  class Response:
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self,n):return b'{"balances":[]}'
  with patch.object(e.urllib.request,'build_opener') as factory,patch.object(e.time,'time',return_value=123.456):
   factory.return_value.open.return_value=Response()
   result=e.signed('/api/v3/account','private-key','private-secret')
   req=factory.return_value.open.call_args.args[0]
   self.assertTrue(req.full_url.startswith('https://api.binance.com/api/v3/account?timestamp=123456&recvWindow=5000&signature='))
   self.assertNotIn('private-secret',req.full_url)
   self.assertEqual(result,{'balances':[]})
  with patch.object(e.urllib.request,'build_opener') as factory:
   factory.return_value.open.side_effect=RuntimeError('private-key private-secret')
   with self.assertRaises(ValueError) as caught:e.signed('/api/v3/account','private-key','private-secret')
   self.assertNotIn('private',str(caught.exception))
 def test_fixed_operations(self):
  with self.assertRaises(ValueError):e.signed('/api/v3/order','a','b')
 def test_exchange_version_rotation_and_legacy(self):
  from cryptography.hazmat.primitives.ciphers.aead import AESGCM
  import secrets
  first=base64.urlsafe_b64encode(bytes(range(32))).decode();second=base64.urlsafe_b64encode(bytes(range(32,64))).decode()
  payload={'api_key':'fake-test-key','api_secret':'fake-test-secret'}
  with patch.dict(os.environ,{'ORBIT_EXCHANGE_KEY':first,'ORBIT_EXCHANGE_KEY_ID':'old','ORBIT_EXCHANGE_PREVIOUS_KEYS':'{}'}):
   old=e.crypt(1,'connection',payload);self.assertTrue(old.startswith('v1:old:'))
   self.assertNotEqual(old,e.crypt(1,'connection',payload))
   nonce=secrets.token_bytes(12);legacy=base64.urlsafe_b64encode(nonce+AESGCM(bytes(range(32))).encrypt(nonce,json.dumps(payload).encode(),b'orbit:binance:1:connection')).decode()
   self.assertEqual(e.crypt(1,'connection',legacy,True),payload)
   self.c.execute('INSERT INTO exchange_connections VALUES (?,?,?,?,?)',(1,'connection','test',old,'{}'))
   with self.assertRaises(ValueError):e.crypt(1,'connection',old.replace('v1:old:','v2:old:'),True)
  with patch.dict(os.environ,{'ORBIT_EXCHANGE_KEY':second,'ORBIT_EXCHANGE_KEY_ID':'new','ORBIT_EXCHANGE_PREVIOUS_KEYS':json.dumps({'old':first})}):
   self.assertEqual(e.crypt(1,'connection',old,True),payload)
   self.assertEqual(e.rewrap_credentials(self.c,1),1)
   new=self.c.execute('SELECT credentials FROM exchange_connections').fetchone()[0]
   self.assertTrue(new.startswith('v1:new:'));self.assertEqual(e.crypt(1,'connection',new,True),payload)
   with self.assertRaises(ValueError):e.crypt(1,'connection',old.replace('v1:old:','v1:new:'),True)
  with patch.dict(os.environ,{'ORBIT_EXCHANGE_KEY':second,'ORBIT_EXCHANGE_KEY_ID':'new','ORBIT_EXCHANGE_PREVIOUS_KEYS':'{}'}):
   self.assertEqual(e.crypt(1,'connection',new,True),payload)
   with self.assertRaises(ValueError):e.crypt(1,'connection',old,True)
 def test_encrypted_credentials_account_binding(self):
  try:import cryptography
  except ImportError:self.skipTest('cryptography not installed')
  with patch.dict(os.environ,{'ORBIT_EXCHANGE_KEY':base64.urlsafe_b64encode(bytes(range(32))).decode()}):
   encrypted=e.crypt(1,'id',{'api_key':'secret'})
   self.assertNotIn('secret',encrypted);self.assertEqual(e.crypt(1,'id',encrypted,True)['api_key'],'secret')
   with self.assertRaises(ValueError):e.crypt(2,'id',encrypted,True)
   with self.assertRaises(ValueError):e.crypt(1,'other',encrypted,True)
   with self.assertRaises(ValueError):e.crypt(1,'id',encrypted[:-6]+'abcdef',True)
   prepared={'label':'Spot','credentials':{'api_key':'secret'},'snapshot':{'balances':[]}}
   result=e.add(self.c,1,prepared);self.assertEqual(len(result['connections']),1);self.assertNotIn('credentials',json.dumps(result))
   self.assertEqual(e.state(self.c,2)['connections'],[])
   e.delete(self.c,2,{'id':result['connections'][0]['id']});self.assertEqual(len(e.state(self.c,1)['connections']),1)

if __name__=='__main__':unittest.main()
