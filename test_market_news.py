import os,time,datetime,unittest
from unittest.mock import patch
import coin_market as m,market_news as n
class NewsTests(unittest.TestCase):
 def setUp(self):
  m.CACHE.clear();m.FAILURES.clear()
  self.env=patch.dict(os.environ,{'NEWS_API_KEY':'fixture-secret','VERCEL':'','NEWS_API_PRODUCTION_LICENSED':''});self.env.start();self.addCleanup(self.env.stop)
  self.ids=patch('coin_market.allowed',return_value='bitcoin');self.ids.start();self.addCleanup(self.ids.stop)
  self.rows=patch('coin_market.listings',return_value={'coins':[{'id':'bitcoin','name':'Bitcoin','symbol':'BTC'}]});self.rows.start();self.addCleanup(self.rows.stop)
 def article(self,**extra):
  return {'title':'Bitcoin crypto adoption grows','url':'https://example.com/bitcoin','source':{'name':'Example'},'publishedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'content':'Private full text must not be stored','description':'unused',**extra}
 def test_no_key_search_without_provider_call(self):
  with patch.dict(os.environ,{'NEWS_API_KEY':''}),patch('providers.request_json') as req:d=n.news('bitcoin')
  req.assert_not_called();self.assertFalse(d['available']);self.assertEqual(d['articles'],[]);self.assertIn('news.google.com/search?',d['search_links'][0]['url'])
 def test_production_requires_licensed_configuration(self):
  with patch.dict(os.environ,{'VERCEL':'1'}),patch('providers.request_json') as req:self.assertFalse(n.news('bitcoin')['available'])
  req.assert_not_called()
 def test_filtered_deduplicated_headlines_and_secret_header(self):
  rows=[self.article(),self.article(),self.article(title='BTC ticker only',url='https://example.com/2'),self.article(url='javascript:evil()'),self.article(title='<b>Bitcoin</b> crypto news',url='https://example.com/3'),self.article(publishedAt='1999-01-01T00:00:00Z'),self.article(source={}),self.article(title='Bitcoincash namesake',url='https://example.com/4')]
  with patch('providers.request_json',return_value={'status':'ok','articles':rows}) as req:d=n.news('bitcoin')
  self.assertEqual(len(d['articles']),2);self.assertNotIn('content',str(d));self.assertNotIn('fixture-secret',str(d));self.assertNotIn('fixture-secret',req.call_args.args[0]);self.assertEqual(req.call_args.kwargs['headers']['X-Api-Key'],'fixture-secret');self.assertTrue(all('<b>' not in a['title'] for a in d['articles']))
 def test_outage_preserves_prior_timestamp_and_marks_stale(self):
  with patch('coin_market.time.time',return_value=time.time()-1000),patch('providers.request_json',return_value={'status':'ok','articles':[self.article()]}):first=n.news('bitcoin')
  with patch('providers.request_json',side_effect=ValueError('secret error')):last=n.news('bitcoin')
  self.assertTrue(last['stale']);self.assertEqual(last['fetched_at'],first['fetched_at']);self.assertNotIn('secret error',str(last))
 def test_provider_errors_and_bounds(self):
  for payload in [{'status':'error','message':'secret'},{'status':'ok','articles':[{}]*101},{'status':'ok','articles':{}}]:
   m.CACHE.clear();m.FAILURES.clear()
   with patch('providers.request_json',return_value=payload):
    with self.assertRaises(ValueError):n.news('bitcoin')
if __name__=='__main__':unittest.main()
