import os,unittest
from unittest.mock import patch
import history,history_bnb,review,server,test_review_api
class NetworkTests(unittest.TestCase):
 def test_optimism_identity_and_fixed_host(self):
  owner='0x'+'1'*40;other='0x'+'2'*40;tx='0x'+'3'*64
  page={'items':[{'hash':tx,'timestamp':'2026-01-01T00:00:00Z','from':{'hash':other},'to':{'hash':owner},'value':'1000000000000000000','status':'ok'}],'next_page_params':None}
  with patch('providers.request_json',side_effect=[page,{'items':[],'next_page_params':None}]) as request:
   r=history.fetch_history('Optimism',owner)
   self.assertTrue(request.call_args_list[0].args[0].startswith('https://optimism.blockscout.com/'))
   self.assertEqual(r['items'][0]['asset_id'],'Optimism:native');self.assertTrue(r['items'][0]['event_id'].startswith('Optimism:'))
 def test_dispatch_all_networks(self):
  modules={'Solana':'history_solana','Aptos':'history_aptos','Sui':'history_sui','BNB Chain':'history_bnb'}
  for chain,module in modules.items():
   address='1'*32 if chain=='Solana' else '0x'+'1'*40
   with patch(module+'.fetch_history',return_value={'items':[]}) as fetch:
    self.assertEqual(history.fetch_history(chain,address),{'items':[]});fetch.assert_called_once()
 def test_bnb_requires_key_without_network(self):
  with patch.dict(os.environ,{},clear=True),patch('providers.request_json') as fetch:
   with self.assertRaisesRegex(ValueError,'ETHERSCAN_API_KEY'):history_bnb.fetch_history('0x'+'1'*40)
   fetch.assert_not_called()
 def test_bnb_transactions_and_pagination_validation(self):
  address='0x'+'1'*40;other='0x'+'2'*40
  row={'from':other,'to':address,'hash':'0x'+'3'*64,'blockNumber':'100','timeStamp':'1767225600','value':'1000000000000000000','gasUsed':'21000','gasPrice':'1000000000','isError':'0'}
  with patch.dict(os.environ,{'ETHERSCAN_API_KEY':'not-a-real-key'}),patch('providers.request_json',return_value={'status':'1','result':[row]}) as fetch:
   result=history_bnb.fetch_history(address);self.assertEqual(result['items'][0]['asset_id'],'BNB Chain:native');self.assertEqual(result['items'][0]['quantity'],'1')
   with self.assertRaises(ValueError):history_bnb.fetch_history(address,{'transactions':{'url':'https://attacker.invalid'}})
 def test_unsafe_unknown_token_blocks_entire_review_group(self):
  record={'wallet_id':1,'chain':'Sui','hash':'abc','date':'2026-01-01','status':'confirmed','event_id':'a','direction':'in','quantity':'1','asset_id':'Sui:native','asset':'SUI'}
  unknown={**record,'event_id':'b','direction':'out','quantity':None,'raw_quantity':'12345','asset_id':'Sui:coin','review_eligible':False}
  self.assertEqual(review.build_reviews([record,unknown]),[])
 def test_network_capabilities_no_secrets(self):
  with patch.dict(os.environ,{},clear=True):
   networks=server.network_support();self.assertEqual(len(networks),20);self.assertFalse(next(n for n in networks if n['chain']=='BNB Chain')['history_configured'])
class NetworkReviewTests(test_review_api.ReviewAPITests):
 def test_native_optimism_uses_separate_ledger_alias(self):
  self.call(self.a,'wallet',{'chain':'Optimism','address':'0x'+'4'*40,'label':'Optimism'})
  wid=next(w['id'] for w in self.call(self.a,'state')['wallets'] if w['chain']=='Optimism')
  import json
  row={'event_id':'op','hash':'0x'+'5'*64,'date':'2026-02-01','kind':'native_transfer','direction':'in','asset_id':'Optimism:native','asset':'ETH','quantity':'1','status':'confirmed'}
  with server.connect() as c:c.execute('INSERT INTO chain_history VALUES (?,?,?)',(wid,'op',json.dumps(row)))
  r=next(r for r in self.call(self.a,'state')['reviews'] if r['chain']=='Optimism')
  self.call(self.a,'review',self.payload(r,received_symbol='ETH_OP'))
  self.assertEqual(self.call(self.a,'state')['trades'][0]['symbol'],'ETH_OP')
if __name__=='__main__':unittest.main()
