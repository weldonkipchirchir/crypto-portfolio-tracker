import json,unittest,urllib.error
from unittest.mock import patch
import server,test_integrations,test_advanced_api
class TargetsAPITests(test_integrations.APITests):
 def owned_wallet(self):
  uid=test_advanced_api.AdvancedAPITests.owned_wallet(self)
  with server.connect() as c:c.execute("UPDATE price_metadata SET source=? WHERE user_id=?",('CoinGecko',uid))
  return uid
 def test_targets_authority_and_account_isolation(self):
  self.owned_wallet()
  with patch('price_targets.time.time',return_value=1001):
   result=self.call(self.a,'target-save',{'asset_id':'Base:native','operator':'above','target_usd':'5','user_id':999,'price_usd':'99999'})
  self.assertEqual(result['evaluation']['triggered'],1);target=result['target']
  own=self.call(self.a,'state');other=self.call(self.b,'state')
  self.assertEqual(own['target_events'][0]['price_usd'],'10');self.assertEqual(other['price_targets'],[]);self.assertEqual(other['target_events'],[])
  with self.assertRaises(urllib.error.HTTPError):self.call(self.b,'target-remove',{'id':target['id']})
  with self.assertRaises(urllib.error.HTTPError):self.call(self.b,'target-save',{'asset_id':'Base:native','operator':'above','target_usd':'5'})
  self.call(self.a,'target-remove',{'id':target['id']});self.assertEqual(self.call(self.a,'state')['price_targets'],[]);self.assertEqual(len(self.call(self.a,'state')['target_events']),1)
 def test_price_refresh_evaluates_without_duplicates(self):
  self.owned_wallet()
  with patch('price_targets.time.time',return_value=1001):self.call(self.a,'target-save',{'asset_id':'Base:native','operator':'above','target_usd':'15'})
  def refresh(price,stamp):
   with patch('price_targets.time.time',return_value=stamp),patch('providers.market_prices',return_value={'ETH':{'price':str(price),'source':'CoinGecko','updated_at':stamp}}):return self.call(self.a,'refresh-prices',{})
  self.assertEqual(refresh(20,1002)['target_evaluation']['triggered'],1)
  self.assertEqual(refresh(20,1002)['target_evaluation']['triggered'],0)
  self.assertEqual(refresh(10,1003)['target_evaluation']['triggered'],0)
  self.assertEqual(refresh(20,1004)['target_evaluation']['triggered'],1)
  self.assertEqual(len(self.call(self.a,'state')['target_events']),2)
if __name__=='__main__':unittest.main()
