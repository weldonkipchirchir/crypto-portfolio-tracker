import copy,time,unittest
from unittest.mock import patch
import coin_market as m
import market_intelligence as mi

class IntelligenceTests(unittest.TestCase):
 def setUp(self):m.CACHE.clear();m.FAILURES.clear()
 def tearDown(self):m.CACHE.clear();m.FAILURES.clear()
 def row(self,identity='bitcoin',rank=1,change=10):
  return {'id':identity,'market_cap_rank':rank,'name':identity,'symbol':identity[:4],'current_price':10,'price_change_percentage_30d_in_currency':change}
 def test_sentiment_real_observations_and_attribution(self):
  now=int(time.time());data={'data':[{'value':'25','value_classification':'Fear','timestamp':str(now)},{'value':'999','timestamp':str(now-86400)},{'value':'NaN','timestamp':'1'}]}
  with patch.object(mi.providers,'request_json',return_value=data):r=mi.fear_greed()
  self.assertEqual(r['value'],25);self.assertEqual(len(r['history']),1);self.assertEqual(r['source'],'Alternative.me');self.assertIn('Bitcoin',r['coverage']);self.assertTrue(r['source_url'].startswith('https:'))
 def test_sentiment_rejects_invalid_payload(self):
  for bad in ({'data':[]},{'data':[{'value':True,'timestamp':str(int(time.time()))}]},{'data':[{'value':'12.5','timestamp':str(int(time.time()))}]}):
   m.FAILURES.clear()
   with patch.object(mi.providers,'request_json',return_value=bad):
    with self.assertRaises(ValueError):mi.fear_greed()
 def test_real_cmc_alt_season_not_breadth(self):
  data={'data':{'altcoin_index':51,'snapshot_time':mi.exchange_charts.iso(int(time.time()))},'status':{'error_code':0}}
  with patch.object(mi.providers,'request_json',return_value=data) as request:r=mi.alt_season()
  self.assertEqual(r['value'],51);self.assertEqual(r['window_days'],90);self.assertEqual(r['source'],'CoinMarketCap');self.assertIn('/public-api/',request.call_args.args[0])
 def test_cmc_errors_and_out_of_range(self):
  for data in ({'status':{'error_code':1},'data':{}},{'status':{'error_code':0},'data':{'altcoin_index':101,'snapshot_time':mi.exchange_charts.iso(int(time.time()))}}):
   m.FAILURES.clear()
   with patch.object(mi.providers,'request_json',return_value=data):
    with self.assertRaises(ValueError):mi.alt_season()
 def test_breadth_signed_values_missing_and_exclusions(self):
  rows=[self.row(),self.row('tether',2,100),self.row('wrapped-bitcoin',3,100)]+[self.row('coin-'+str(i),i+4,11 if i<6 else -10) for i in range(12)]+[self.row('missing',17,None)]
  with patch.object(m,'request',return_value=rows) as req:r=mi.breadth()
  self.assertEqual(r['value'],50);self.assertEqual(r['eligible'],12);self.assertEqual(r['missing'],1);self.assertEqual(r['excluded'],2);self.assertIn('price_change_percentage=30d',req.call_args.args[0]);self.assertEqual(req.call_count,1)
 def test_breadth_no_bitcoin_no_fake_value(self):
  with patch.object(m,'request',return_value=[self.row('other')]):
   with self.assertRaises(ValueError):mi.breadth()
 def test_overview_failure_independent_sources(self):
  with patch.object(mi,'fear_greed',side_effect=ValueError()),patch.object(mi,'breadth',return_value={'available':True}),patch.object(mi,'alt_season',return_value={'value':51}):r=mi.overview()
  self.assertFalse(r['fear_greed']['available']);self.assertEqual(r['alt_season']['value'],51)
 def test_overview_parallel_with_deadline_and_persistence(self):
  import threading
  gate=threading.Barrier(3);cutoff=time.monotonic()+20;callbacks=(lambda k:None,lambda *a:None)
  def load():
   self.assertEqual(mi.providers._REQUEST_CONTEXT.cutoff,cutoff)
   self.assertEqual(m.STORE.callbacks,callbacks)
   gate.wait(timeout=2)
   return {'available':True}
  with mi.providers.deadline(cutoff),m.persistence(*callbacks),patch.object(mi,'fear_greed',side_effect=load),patch.object(mi,'breadth',side_effect=load),patch.object(mi,'alt_season',side_effect=load):r=mi.overview()
  self.assertTrue(all(r[k]['available'] for k in ('fear_greed','altcoin_breadth','alt_season')))
 def test_sentiment_outdated_observation_not_current(self):
  data={'data':[{'value':'25','timestamp':str(int(time.time())-3*86400)}]}
  with patch.object(mi.providers,'request_json',return_value=data):
   with self.assertRaises(ValueError):mi.fear_greed()
 def test_rsi_missing_latest_completed_day_not_current(self):
  payload,now=self.candles();payload['candles']=payload['candles'][:-2]
  with self.assertRaises(ValueError):mi.daily_rsi(payload,now)
 def test_narrative_fixed_allowlist_and_dedup(self):
  with self.assertRaises(ValueError):mi.narratives('../x')
  with patch.object(m,'request',return_value=[self.row('ondo-finance'),self.row('ondo-finance'),{'id':'bad'}]) as req:r=mi.narratives('rwa')
  self.assertEqual(len(r['coins']),1);self.assertIn('category=real-world-assets-rwa',req.call_args.args[0]);self.assertEqual(r['narrative']['id'],'rwa')
 def test_catalog_validates_and_never_fetches(self):
  key=('fundamentals','intelligence-narrative','rwa');data={'coins':[self.row('newcoin')],'fetched_at':int(time.time())}
  with m.persistence(lambda k:data if k==key else None,lambda *a:None),patch.object(m,'request',side_effect=AssertionError('upstream')):r=mi.catalog_coin('newcoin')
  self.assertEqual(r['id'],'newcoin')
  data['fetched_at']-=86401
  with m.persistence(lambda k:data,lambda *a:None):self.assertIsNone(mi.catalog_coin('newcoin'))
 def test_venues_filters_identity_stale_unsafe_urls(self):
  row={'coin_id':'bitcoin','market':{'name':'Example','identifier':'example'},'base':'BTC','target':'USD','converted_last':{'usd':0},'converted_volume':{'usd':100},'last_traded_at':mi.exchange_charts.iso(int(time.time())),'trade_url':'javascript:alert(1)'}
  invalid=copy.deepcopy(row);invalid['coin_id']='other'
  stale=copy.deepcopy(row);stale['is_stale']=True
  with patch.object(m,'allowed',return_value='bitcoin'),patch.object(m,'request',return_value={'tickers':[row,invalid,stale,row]}):r=mi.venues('bitcoin')
  self.assertEqual(len(r['venues']),1);self.assertEqual(r['venues'][0]['price_usd'],'0');self.assertIsNone(r['venues'][0]['trade_url'])
 def test_wilder_known_values_edges_and_smoothing(self):
  self.assertEqual(mi.wilder([1]*16),50);self.assertEqual(mi.wilder(range(1,17)),100);self.assertEqual(mi.wilder(range(17,1,-1)),0)
  classic=[44.34,44.09,44.15,43.61,44.33,44.83,45.10,45.42,45.84,46.08,45.89,46.03,45.61,46.28,46.28,46.00,46.03]
  self.assertAlmostEqual(mi.wilder(classic),66.48094,places=4)
  with self.assertRaises(ValueError):mi.wilder([1]*14)
  with self.assertRaises(ValueError):mi.wilder([1]*14+['NaN'])
 def candles(self):
  day=int(time.time())//86400*86400
  return {'interval':'daily','stale':False,'source':'Binance','pair':'BTCUSDT','candles':[{'timestamp':(day-(20-i)*86400)*1000,'close':str(10+i)} for i in range(21)]},day+100
 def test_rsi_closed_candles_and_utc_timestamp(self):
  payload,now=self.candles();value,stamp=mi.daily_rsi(payload,now)
  self.assertEqual(value,100);self.assertEqual(stamp,now//86400*86400-86400)
 def test_rsi_gaps_stale_and_incomplete_not_filled(self):
  payload,now=self.candles();del payload['candles'][-5]
  with self.assertRaises(ValueError):mi.daily_rsi(payload,now)
  payload,now=self.candles();payload['stale']=True
  with self.assertRaises(ValueError):mi.daily_rsi(payload,now)
 def test_rsi_fallback_and_explicit_coverage(self):
  payload,_=self.candles();payload.update(source='Coinbase Exchange',pair='BTC-USD')
  def chart(identity,days,kind,source):
   if source=='binance':raise ValueError('regional restriction')
   return payload
  with patch.object(mi.exchange_charts,'chart',side_effect=chart):r=mi.rsi()
  self.assertEqual(len(r['rows']),8);self.assertTrue(all(x['available'] for x in r['rows']));self.assertEqual(r['rows'][0]['source'],'Coinbase Exchange');self.assertEqual(r['period'],14)
 def test_cached_narrative_identity_survives_rankings_outage(self):
  now=int(time.time());key=('fundamentals','intelligence-narrative','rwa');m.CACHE[key]=(now,{'fetched_at':now,'coins':[m.coin_row(self.row('outside-catalog',500))]})
  with patch.object(m,'listings',side_effect=ValueError('outage')):
   self.assertEqual(m.allowed('outside-catalog'),'outside-catalog')
   with self.assertRaises(ValueError):m.allowed('unknown-coin')
 def test_rsi_all_fail_no_fake_neutral(self):
  with patch.object(mi.exchange_charts,'chart',side_effect=ValueError()):
   with self.assertRaises(ValueError):mi.rsi()

if __name__=='__main__':unittest.main()
