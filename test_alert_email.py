import json,os,sqlite3,unittest
from unittest.mock import patch
import alert_email as mail

class EmailTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
  self.c.execute('CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT)')
  self.c.executemany('INSERT INTO users VALUES (?,?)',[(1,'owner@example.com'),(2,'other@example.com')]);mail.init(self.c)
  self.env=patch.dict(os.environ,{'RESEND_API_KEY':'test-only','ALERT_EMAIL_FROM':'Orbit <alerts@example.com>'},clear=True);self.env.start()
  self.event={'id':'event-1','symbol':'BTC','operator':'above','target_usd':'100','price_usd':'101','source':'test','wallet':'private','secret':'never'}
 def tearDown(self):self.env.stop();self.c.close()
 def enable(self):mail.preference(self.c,1,{'enabled':True,'recipient':'attacker@example.com'})
 def test_opt_in_and_recipient_ownership(self):
  self.assertFalse(mail.enqueue(self.c,1,self.event));self.enable()
  self.assertEqual(mail.state(self.c,1)['recipient'],'owner@example.com');self.assertFalse(mail.state(self.c,2)['enabled'])
 def test_deduplication_and_private_payload(self):
  self.enable();mail.enqueue(self.c,1,self.event);mail.enqueue(self.c,1,self.event)
  rows=list(self.c.execute('SELECT * FROM alert_email_outbox'));self.assertEqual(len(rows),1)
  self.assertNotIn('secret',rows[0]['data']);self.assertNotIn('wallet',rows[0]['data'])
 def test_delivery_once_and_account_isolation(self):
  self.enable();mail.enqueue(self.c,1,self.event)
  with patch.object(mail,'send') as send:
   mail.deliver(self.c,2);send.assert_not_called()
   result=mail.deliver(self.c,1);mail.deliver(self.c,1)
   self.assertEqual(send.call_count,1);self.assertEqual(send.call_args.args[0],'owner@example.com')
   self.assertEqual(result['events'][0]['status'],'accepted')
 def test_failure_backoff_and_expiry(self):
  self.enable();mail.enqueue(self.c,1,self.event)
  with patch.object(mail,'send',side_effect=ValueError('provider unavailable')) as send:
   mail.deliver(self.c,1);mail.deliver(self.c,1);self.assertEqual(send.call_count,1)
   self.c.execute('UPDATE alert_email_outbox SET created_at=0,last_attempt=0')
   self.assertEqual(mail.deliver(self.c,1)['events'][0]['status'],'expired')
 def test_disabled_delivery_and_limit(self):
  self.enable()
  for i in range(25):mail.enqueue(self.c,1,{**self.event,'id':str(i)})
  self.assertEqual(self.c.execute('SELECT COUNT(*) FROM alert_email_outbox').fetchone()[0],20)
  mail.preference(self.c,1,{'enabled':False})
  with patch.object(mail,'send') as send:mail.deliver(self.c,1);send.assert_not_called()
 def test_resend_request_is_idempotent(self):
  class Response:
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self,*args):return b'{"id":"mail-1"}'
  with patch.object(mail.urllib.request,'urlopen',return_value=Response()) as request:
   mail.send('owner@example.com',self.event,'event-1');r=request.call_args.args[0]
   self.assertEqual(json.loads(r.data)['to'],['owner@example.com']);self.assertEqual(r.get_header('Idempotency-key'),'orbit-alert-event-1')
 def test_smtp_rejects_plaintext_port(self):
  with patch.dict(os.environ,{'SMTP_PORT':'25'},clear=False):
   del os.environ['RESEND_API_KEY']
   with self.assertRaises(ValueError):mail.send('owner@example.com',self.event,'event-1')

if __name__=='__main__':unittest.main()
