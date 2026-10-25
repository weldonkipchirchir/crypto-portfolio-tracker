"""Review confirmation API security and accounting regression tests."""
import json,unittest,urllib.error
import server,test_integrations

class ReviewAPITests(unittest.TestCase):
 client=test_integrations.APITests.client
 call=test_integrations.APITests.call
 def setUp(self):
  server.AUTH_ATTEMPTS.clear();test_integrations.APITests.setUp(self)
  self.call(self.a,'wallet',{'chain':'Ethereum','address':'0x'+'1'*40,'label':'Review wallet'})
  self.wid=self.call(self.a,'state')['wallets'][0]['id']
 def tearDown(self):test_integrations.APITests.tearDown(self)
 def event(self,event_id='in:1',direction='in',asset_id='Ethereum:0x'+'2'*40,asset='TOKEN',quantity='5',tx='3'):
  row={'event_id':event_id,'hash':'0x'+tx*64,'date':'2026-02-01T00:00:00','kind':'token_transfer','direction':direction,'asset_id':asset_id,'asset':asset,'quantity':quantity,'fee':None,'status':'confirmed'}
  with server.connect() as c:c.execute('INSERT INTO chain_history VALUES (?,?,?)',(self.wid,event_id,json.dumps(row)))
  return row
 def pending(self):return next(r for r in self.call(self.a,'state')['reviews'] if r['status']=='pending')
 def payload(self,review,**overrides):
  data={'id':review['id'],'action':'confirm','date':'2026-01-01T00:00:00','usd_value':'100','fee_usd':'0','received_symbol':'MYTOKEN','sent_symbol':'ETH','acknowledge':True};data.update(overrides);return data
 def rejected(self,client,payload):
  with self.assertRaises(urllib.error.HTTPError) as error:self.call(client,'review',payload)
  self.assertIn(error.exception.code,(400,403,404,409))
 def test_other_account_cannot_review(self):
  self.event();review=self.pending()
  self.rejected(self.b,self.payload(review));self.rejected(self.b,self.payload(review,action='dismiss'))
  self.assertEqual(self.call(self.a,'state')['trades'],[])
 def test_acknowledgement_required(self):
  self.event();review=self.pending()
  for ack in (False,'true',1,None):self.rejected(self.a,self.payload(review,acknowledge=ack))
  self.assertEqual(self.call(self.a,'state')['trades'],[])
 def test_acquisition_quantity_from_history_and_idempotency(self):
  self.event();review=self.pending()
  self.call(self.a,'review',self.payload(review,quantity='999',received=[{'quantity':'999'}]))
  state=self.call(self.a,'state');self.assertEqual(len(state['trades']),1);self.assertEqual(float(state['trades'][0]['quantity']),5)
  try:self.call(self.a,'review',self.payload(review))
  except urllib.error.HTTPError:pass
  self.assertEqual(len(self.call(self.a,'state')['trades']),1)
 def test_dismiss_does_not_create_trades(self):
  self.event();review=self.pending();self.call(self.a,'review',{'id':review['id'],'action':'dismiss'})
  self.assertEqual(self.call(self.a,'state')['trades'],[])
 def test_reserved_market_symbol_rejected(self):
  self.event();review=self.pending()
  self.rejected(self.a,self.payload(review,received_symbol='ETH'));self.assertEqual(self.call(self.a,'state')['trades'],[])
 def test_swap_oversell_atomic(self):
  self.event('out:1','out','Ethereum:native','ETH','2')
  self.event('in:1','in',quantity='5')
  review=self.pending();self.assertEqual(review['type'],'swap_candidate')
  self.rejected(self.a,self.payload(review))
  state=self.call(self.a,'state');self.assertEqual(state['trades'],[])
  self.assertEqual(next(r for r in state['reviews'] if r['id']==review['id'])['status'],'pending')

 def test_swap_confirmation_records_two_legs(self):
  self.call(self.a,'trade',{'date':'2026-01-01','symbol':'ETH','side':'buy','quantity':'2','price':'20'})
  self.event('out:1','out','Ethereum:native','ETH','1')
  self.event('in:1','in',quantity='5')
  review=self.pending()
  self.call(self.a,'review',self.payload(review,date='2026-02-01',fee_usd='3'))
  state=self.call(self.a,'state');self.assertEqual(len(state['trades']),3)
  eth=next(a for a in state['assets'] if a['symbol']=='ETH');token=next(a for a in state['assets'] if a['symbol']=='MYTOKEN')
  self.assertEqual(eth['realized'],77);self.assertEqual(token['cost'],100)
  self.assertEqual(next(r for r in state['reviews'] if r['id']==review['id'])['status'],'confirmed')
 def test_dismissed_cannot_be_confirmed(self):
  self.event();review=self.pending();self.call(self.a,'review',{'id':review['id'],'action':'dismiss'})
  self.rejected(self.a,self.payload(review));self.assertEqual(self.call(self.a,'state')['trades'],[])

if __name__=='__main__':unittest.main()
