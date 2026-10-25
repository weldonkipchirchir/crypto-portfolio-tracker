"""Contract-specific market identity, precision, cache and unknown-value regressions."""
import copy,unittest
from decimal import Decimal
from unittest.mock import patch
import token_pricing as pricing

CONTRACT='0x'+'2'*40
OTHER='0x'+'3'*40
PAIR='0x'+'4'*40
OWNER='0x'+'1'*40

def pair(price='2.5',liquidity='10000',chain='ethereum',contract=CONTRACT,pair_address=PAIR):
 return {'chainId':chain,'baseToken':{'address':contract,'symbol':'FAKE_TICKER'},'quoteToken':{'address':OTHER,'symbol':'ETH'},'pairAddress':pair_address,'priceUsd':price,'liquidity':{'usd':liquidity}}
def snapshot(quantity='3'):
 return {'tokens':[{'contract':CONTRACT,'asset_id':'Ethereum:'+CONTRACT,'quantity':quantity,'symbol':'ETH','identity_verified':False}],'updated_at':100,'errors':[]}

class TokenPricingTests(unittest.TestCase):
 def setUp(self):pricing.CACHE.clear()
 def test_selected_pool_metrics_and_optional_bounds(self):
  row=pair();row.update(volume={'h24':'123.456'},priceChange={'h24':'-12.5'},dexId='uniswap')
  with patch('providers.request_json',return_value=[row]):quote=pricing.get_quote('Ethereum',CONTRACT)
  self.assertEqual(quote['market_change_24h_pct'],'-12.5');self.assertEqual(quote['market_volume_24h_usd'],'123.456');self.assertEqual(quote['market_dex'],'uniswap')
  for invalid in ['NaN','Infinity','-101','1e9999']:
   pricing.CACHE.clear();row['priceChange']={'h24':invalid};row['volume']={'h24':'-1'}
   with patch('providers.request_json',return_value=[row]):quote=pricing.get_quote('Ethereum',CONTRACT)
   self.assertIsNone(quote['market_change_24h_pct']);self.assertIsNone(quote['market_volume_24h_usd'])
 def test_chain_and_base_contract_identity(self):
  for rows in [[pair(chain='bsc')],[pair(contract=OTHER)], [{'chainId':'ethereum','baseToken':{'address':OTHER},'quoteToken':{'address':CONTRACT},'pairAddress':PAIR,'priceUsd':'5','liquidity':{'usd':'1000000'}}]]:
   pricing.CACHE.clear()
   with patch('providers.request_json',return_value=rows):self.assertIsNone(pricing.get_quote('Ethereum',CONTRACT))
 def test_ticker_is_not_identity(self):
  with patch('providers.request_json',return_value=[pair()]) as request:
   quote=pricing.get_quote('Ethereum',CONTRACT)
   self.assertEqual(quote['price_usd'],'2.5')
   self.assertEqual(request.call_args.args[0],'https://api.dexscreener.com/token-pairs/v1/ethereum/'+CONTRACT)
   self.assertNotIn(OWNER,request.call_args.args[0]);self.assertNotIn('ETH',request.call_args.args[0])
 def test_liquidity_floor_and_highest_pool(self):
  with patch('providers.request_json',return_value=[pair('999','9999'),pair('2','10000'),pair('3','100000',pair_address=OTHER)]):
   quote=pricing.get_quote('Ethereum',CONTRACT);self.assertEqual(quote['price_usd'],'3');self.assertEqual(quote['price_liquidity_usd'],'100000')
 def test_invalid_prices_and_liquidity_never_valid_quote(self):
  for field in ['priceUsd','liquidity']:
   for value in ['NaN','Infinity','-1','0','1e99999999','1e-99999999',True]:
    pricing.CACHE.clear();row=pair()
    if field=='liquidity':row[field]={'usd':value}
    else:row[field]=value
    with patch('providers.request_json',return_value=[row]):self.assertIsNone(pricing.get_quote('Ethereum',CONTRACT))
 def test_price_upper_bound(self):
  with patch('providers.request_json',return_value=[pair('1e13')]):self.assertIsNone(pricing.get_quote('Ethereum',CONTRACT))
 def test_exact_decimal_value_and_original_not_mutated(self):
  original=snapshot('12345678901234567890.123456789');saved=copy.deepcopy(original)
  with patch('providers.request_json',return_value=[pair('0.000000123456789')]):result=pricing.enrich('Ethereum',original)
  self.assertEqual(result['tokens'][0]['value_usd'],'1524157875171.467887517146788750190521')
  self.assertEqual(original,saved);self.assertFalse(result['tokens'][0]['identity_verified'])
 def test_missing_quote_unknown_not_zero(self):
  with patch('providers.request_json',return_value=[]):result=pricing.enrich('Ethereum',snapshot())
  token=result['tokens'][0];self.assertIsNone(token['price_usd']);self.assertIsNone(token['value_usd']);self.assertIn('price_error',token)
 def test_previous_quote_retained_explicitly_stale(self):
  original=snapshot('4');original['tokens'][0].update(price_usd='2',price_fetched_at=123,price_source='DEX Screener',value_usd='6')
  with patch('providers.request_json',side_effect=ValueError('Provider unavailable')):result=pricing.enrich('Ethereum',original)
  token=result['tokens'][0];self.assertTrue(token['price_stale']);self.assertEqual(token['price_fetched_at'],123);self.assertEqual(token['value_usd'],'8');self.assertIn('price_error',token)
 def test_asset_identity_mismatch_never_freshly_priced(self):
  original=snapshot();original['tokens'][0]['asset_id']='BNB Chain:'+CONTRACT
  with patch('providers.request_json') as request:
   token=pricing.enrich('Ethereum',original)['tokens'][0];request.assert_not_called();self.assertIsNone(token['value_usd'])
 def test_identity_mismatch_discards_prior_price(self):
  original=snapshot();original['tokens'][0].update(asset_id='BNB Chain:'+CONTRACT,price_usd='100',value_usd='300',price_fetched_at=123,price_source='DEX Screener')
  with patch('providers.request_json') as request:
   token=pricing.enrich('Ethereum',original)['tokens'][0];request.assert_not_called()
  self.assertIsNone(token['price_usd']);self.assertIsNone(token['value_usd']);self.assertIsNone(token['price_source']);self.assertIsNone(token['price_fetched_at'])
  self.assertIn('price_error',token)
 def test_strict_price_ceiling(self):
  with patch('providers.request_json',return_value=[pair('1000000000000.1')]):self.assertIsNone(pricing.get_quote('Ethereum',CONTRACT))
 def test_cache_expires_after_sixty_seconds(self):
  with patch('providers.request_json',return_value=[pair()]) as request,patch('token_pricing.time.time',return_value=100):pricing.get_quote('Ethereum',CONTRACT)
  with patch('providers.request_json') as request,patch('token_pricing.time.time',return_value=159):
   self.assertEqual(pricing.get_quote('Ethereum',CONTRACT)['price_fetched_at'],100);request.assert_not_called()
  with patch('providers.request_json',return_value=[pair('3')]) as request,patch('token_pricing.time.time',return_value=160):
   self.assertEqual(pricing.get_quote('Ethereum',CONTRACT)['price_usd'],'3');request.assert_called_once()
 def test_unsupported_chain_and_unknown_quantity(self):
  with patch('providers.request_json') as request:self.assertIsNone(pricing.get_quote('Sui','0x1'));request.assert_not_called()
  with patch('providers.request_json',return_value=[pair()]):
   token=pricing.enrich('Ethereum',snapshot(None))['tokens'][0];self.assertIsNone(token['value_usd'])
 def test_known_zero_balance_has_zero_value(self):
  with patch('providers.request_json',return_value=[pair()]):token=pricing.enrich('Ethereum',snapshot('0'))['tokens'][0]
  self.assertEqual(Decimal(token['value_usd']),Decimal(0));self.assertIsNotNone(token['price_usd'])
 def test_invalid_quantity_does_not_become_good_zero(self):
  for quantity in ['-1','NaN','1e99999999','1e-99999999']:
   with patch('providers.request_json',return_value=[pair()]):token=pricing.enrich('Ethereum',snapshot(quantity))['tokens'][0]
   self.assertIsNone(token['value_usd'])
 def test_quote_success_recovers_previous_error(self):
  original=snapshot();original['tokens'][0]['price_error']='old failure'
  with patch('providers.request_json',return_value=[pair()]):token=pricing.enrich('Ethereum',original)['tokens'][0]
  self.assertNotIn('price_error',token);self.assertFalse(token['price_stale'])

if __name__=='__main__':unittest.main()
