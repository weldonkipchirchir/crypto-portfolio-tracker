import unittest,urllib.request,urllib.error,json
from unittest.mock import patch
import server,test_integrations,coin_market
class MarketsAPITests(test_integrations.APITests):
 def test_authentication_and_routes(self):
  with self.assertRaises(urllib.error.HTTPError):self.call(self.client(),'market-listings',{})
  with patch('coin_market.listings',return_value={'coins':[{'id':'bitcoin'}],'fetched_at':1}):self.assertEqual(self.call(self.a,'market-listings',{})['coins'][0]['id'],'bitcoin')
  with patch('coin_market.detail',return_value={'coin':{'id':'bitcoin'}}):self.assertEqual(self.call(self.a,'market-detail',{'coin_id':'bitcoin'})['coin']['id'],'bitcoin')
  with patch('coin_market.chart',return_value={'candles':[]}) as chart:
   self.assertEqual(self.call(self.a,'market-chart',{'coin_id':'bitcoin','days':'max','kind':'candles'})['candles'],[]);chart.assert_called_once_with('bitcoin','max','candles')
  with patch('exchange_charts.chart',return_value={'source':'Binance','quote_currency':'USDT'}) as chart:
   self.assertEqual(self.call(self.a,'market-chart',{'coin_id':'bitcoin','days':'max','kind':'candles','source':'binance'})['quote_currency'],'USDT');chart.assert_called_once_with('bitcoin','max','candles','binance')
  with self.assertRaises(urllib.error.HTTPError):self.call(self.a,'market-chart',{'coin_id':'bitcoin','source':'bad'})
  with patch('market_news.news',return_value={'articles':[]}):self.assertEqual(self.call(self.a,'market-news',{'coin_id':'bitcoin'})['articles'],[])
  with patch('protocol_data.fundamentals',return_value={'coin_id':'bitcoin'}):self.assertEqual(self.call(self.a,'market-fundamentals',{'coin_id':'bitcoin'})['coin_id'],'bitcoin')
 def test_explicit_intervals_and_source_validation(self):
  with patch('exchange_charts.chart',return_value={'interval_code':'4h','candles':[]}) as chart:
   result=self.call(self.a,'market-chart',{'coin_id':'bitcoin','days':30,'kind':'candles','source':'binance','interval':'4h'})
   self.assertEqual(result['interval_code'],'4h');chart.assert_called_once_with('bitcoin',30,'candles','binance',interval='4h')
  with patch('coin_market.chart') as chart:
   with self.assertRaises(urllib.error.HTTPError) as e:self.call(self.a,'market-chart',{'coin_id':'bitcoin','interval':'1d'})
   self.assertEqual(e.exception.code,400);chart.assert_not_called()
 def test_shared_cache_and_source_files(self):
  server.market_cache_write(('list',),{'coins':[],'fetched_at':123});self.assertEqual(server.market_cache_read(('list',))['fetched_at'],123)
  for path in ['/market_dashboard.js','/market_dashboard.css']:
   with urllib.request.urlopen('http://127.0.0.1:'+str(self.app.server_port)+path) as r:self.assertEqual(r.status,200);self.assertIn("script-src 'self'",r.headers['Content-Security-Policy'])
  with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen('http://127.0.0.1:'+str(self.app.server_port)+'/coin_market.py')
if __name__=='__main__':unittest.main()
