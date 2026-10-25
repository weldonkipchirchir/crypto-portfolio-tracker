import json,unittest,urllib.error
from unittest.mock import patch
import history,server
from runtime_security import ProviderBudget
import test_integrations

class HistoryAPITests(unittest.TestCase):
 client=test_integrations.APITests.client
 call=test_integrations.APITests.call
 def setUp(self):
  server.AUTH_ATTEMPTS.clear();self.old_budget=server.PROVIDER_BUDGET;server.PROVIDER_BUDGET=ProviderBudget(limit=100)
  test_integrations.APITests.setUp(self)
  self.call(self.a,'wallet',{'chain':'Ethereum','address':'0x'+'1'*40,'label':'Private wallet'})
  self.wid=self.call(self.a,'state')['wallets'][0]['id']
  self.page={'items':[{'event_id':'event:1','hash':'0x'+'2'*64,'date':'2026-01-01T00:00:00Z','quantity':'1','asset':'ETH','kind':'native_transfer'}],'cursors':{'transactions':{'block_number':123},'token-transfers':None},'coverage':'Test coverage','updated_at':100}
 def tearDown(self):
  test_integrations.APITests.tearDown(self);server.PROVIDER_BUDGET=self.old_budget
 def sync(self):return self.call(self.a,'history',{'id':self.wid})
 def test_history_ownership_and_ledger_separation(self):
  with patch('history.fetch_history',return_value=self.page) as fetch:
   with self.assertRaises(urllib.error.HTTPError):self.call(self.b,'history',{'id':self.wid})
   fetch.assert_not_called();self.sync()
  own=self.call(self.a,'state');other=self.call(self.b,'state')
  self.assertEqual(len(own['history']),1);self.assertEqual(other['history'],[]);self.assertEqual(other['history_status'],[])
  self.assertEqual(own['trades'],[]);self.assertEqual(own['assets'],[])
 def test_repeat_and_failure_preserve_history(self):
  with patch('history.fetch_history',return_value=self.page):self.sync();self.sync()
  before=self.call(self.a,'state');self.assertEqual(len(before['history']),1)
  with patch('history.fetch_history',side_effect=ValueError('Provider unavailable')):self.assertFalse(self.sync()['ok'])
  after=self.call(self.a,'state');self.assertEqual(after['history'],before['history']);self.assertEqual(after['history_status'][0]['error'],'Provider unavailable')
  with patch('history.fetch_history',return_value=self.page):self.sync()
  self.assertIsNone(self.call(self.a,'state')['history_status'][0]['error'])
 def test_pagination_uses_saved_cursor(self):
  with patch('history.fetch_history',return_value=self.page):self.sync()
  with patch('history.fetch_history',return_value=self.page) as fetch:
   self.call(self.a,'history',{'id':self.wid,'more':True,'cursors':{'transactions':{'hash':'evil'}}})
   self.assertEqual(fetch.call_args.args[2],self.page['cursors'])
 def test_delete_removes_history(self):
  with patch('history.fetch_history',return_value=self.page):self.sync()
  self.call(self.a,'remove-wallet',{'id':self.wid})
  with server.connect() as c:
   self.assertEqual(c.execute('SELECT count(*) FROM chain_history').fetchone()[0],0)
   self.assertEqual(c.execute('SELECT count(*) FROM history_sync').fetchone()[0],0)

class CursorSecurityTests(unittest.TestCase):
 def test_malformed_cursor_cannot_change_outbound_url(self):
  for cursor in [{'hash':'x&redirect=https://evil.example'},{'hash':'../evil'},{'url':'https://evil.example'},{'hash':'%26'},{'hash':'a'*161}]:
   with patch('providers.request_json') as request:
    with self.assertRaises(ValueError):history.fetch_history('Ethereum','0x'+'1'*40,{'transactions':cursor})
    request.assert_not_called()

if __name__=='__main__':unittest.main()
