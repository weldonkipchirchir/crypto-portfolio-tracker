import unittest
import review

def row(event,asset='ETH',quantity='1',direction='out',**changes):
 result={'event_id':event,'wallet_id':1,'chain':'Ethereum','hash':'0xabc','date':'2026-01-01T00:00:00Z','wallet_label':'Wallet','status':'confirmed','direction':direction,'asset_id':'Ethereum:'+asset,'asset':asset,'quantity':quantity,'fee':None,'kind':'token_transfer'}
 result.update(changes);return result

class ReviewTests(unittest.TestCase):
 def test_swap_exact_net_duplicate_and_fee(self):
  events=[row('a',quantity='1.000000000000000001',kind='native_transfer',fee='0.002'),row('b','USDC','2000','in'),row('c','ETH','0.000000000000000001','in')]
  events.append(events[0])
  r=review.build_reviews(events)[0]
  self.assertEqual(r['kind'],'swap_candidate');self.assertEqual(r['sent'][0]['quantity'],'1.000000000000000000')
  self.assertEqual(r['received'][0]['quantity'],'2000');self.assertEqual(r['native_fee'],'0.002')
  self.assertEqual(len(review.build_reviews(events)),1)
 def test_ignore_failed_pending_self_and_zero(self):
  events=[row('a',status='failed'),row('b',status='pending'),row('c',direction='self'),row('d',quantity='0')]
  self.assertEqual(review.build_reviews(events),[])
 def test_acquisition_disposal_complex(self):
  self.assertEqual(review.build_reviews([row('a',direction='in')])[0]['kind'],'acquisition_review')
  self.assertEqual(review.build_reviews([row('a')])[0]['kind'],'disposal_review')
  events=[row('a'),row('b','USDC','2','in'),row('c','WETH','3','in')]
  self.assertEqual(review.build_reviews(events)[0]['kind'],'complex_activity')
 def test_deterministic_status_and_isolation(self):
  events=[row('a'),row('b','USDC','2','in'),row('a',wallet_id=2)]
  first=review.build_reviews(events);second=review.build_reviews(list(reversed(events)))
  self.assertEqual(first,second);self.assertEqual(len(first),2)
  updated=review.build_reviews(events,{first[0]['id']:'dismissed'})
  self.assertEqual(updated[0]['status'],'dismissed')
 def test_net_same_asset_is_not_swap(self):
  events=[row('a','ETH','2','out'),row('b','ETH','1','in')]
  result=review.build_reviews(events)[0]
  self.assertEqual(result['kind'],'disposal_review');self.assertEqual(result['sent'][0]['quantity'],'1')
 def test_gas_on_zero_contract_call_and_no_token_gas(self):
  events=[row('a','ETH','0',kind='contract_activity',fee='0.003'),row('b','AAA','1','out',fee='10'),row('c','BBB','2','in')]
  self.assertEqual(review.build_reviews(events)[0]['native_fee'],'0.003')
 def test_invalid_and_extreme_quantities(self):
  for quantity in ['NaN','Infinity','-1','1e1000000','1e-1000000']:
   self.assertEqual(review.build_reviews([row('a',quantity=quantity)]),[])

if __name__=='__main__':unittest.main()

class ReviewIdentityTests(unittest.TestCase):
 def test_identity_stays_same_after_more_history(self):
  first=review.build_reviews([row('b','USDC','2000','in')])[0]
  second=review.build_reviews([row('a'),row('b','USDC','2000','in')],{first['id']:'imported'})[0]
  self.assertEqual(first['id'],second['id']);self.assertEqual(second['status'],'imported')
  self.assertEqual(second['kind'],'swap_candidate')
 def test_missing_date_is_skipped(self):
  self.assertEqual(review.build_reviews([row('a',date=None)]),[])
