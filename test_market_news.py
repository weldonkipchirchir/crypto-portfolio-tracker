import os,time,datetime,unittest
from unittest.mock import patch
import coin_market as m,market_news as n
class NewsTests(unittest.TestCase):
 def setUp(self):
  m.CACHE.clear();m.FAILURES.clear()
  rss=patch('market_news.feed_news',return_value={'articles':[],'available':False});rss.start();self.addCleanup(rss.stop)
  self.env=patch.dict(os.environ,{'NEWS_API_KEY':'fixture-secret','VERCEL':'','NEWS_API_PRODUCTION_LICENSED':''});self.env.start();self.addCleanup(self.env.stop)
  self.ids=patch('coin_market.allowed',return_value='bitcoin');self.ids.start();self.addCleanup(self.ids.stop)
  self.rows=patch('coin_market.listings',return_value={'coins':[{'id':'bitcoin','name':'Bitcoin','symbol':'BTC'}]});self.rows.start();self.addCleanup(self.rows.stop)
 def article(self,**extra):
  return {'title':'Bitcoin crypto adoption grows','url':'https://example.com/bitcoin','source':{'name':'Example'},'publishedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'content':'Private full text must not be stored','description':'unused',**extra}
 def test_no_key_public_index_fallback(self):
  with patch.dict(os.environ,{'NEWS_API_KEY':''}),patch('providers.request_json',side_effect=ValueError('rate limited')) as req:d=n.news('bitcoin')
  req.assert_called_once();self.assertFalse(d['available']);self.assertEqual(d['articles'],[]);self.assertIn('news.google.com/search?',d['search_links'][0]['url'])
 def test_production_requires_licensed_configuration(self):
  with patch.dict(os.environ,{'VERCEL':'1'}),patch('providers.request_json',side_effect=ValueError('unavailable')) as req:self.assertFalse(n.news('bitcoin')['available'])
  req.assert_called_once()
 def test_filtered_deduplicated_headlines_and_secret_header(self):
  rows=[self.article(),self.article(),self.article(title='BTC ticker only',url='https://example.com/2'),self.article(url='javascript:evil()'),self.article(title='<b>Bitcoin</b> crypto news',url='https://example.com/3'),self.article(publishedAt='1999-01-01T00:00:00Z'),self.article(source={}),self.article(title='Bitcoincash namesake',url='https://example.com/4')]
  with patch('providers.request_json',return_value={'status':'ok','articles':rows}) as req:d=n.news('bitcoin')
  self.assertEqual(len(d['articles']),2);self.assertNotIn('content',str(d));self.assertNotIn('fixture-secret',str(d));self.assertNotIn('fixture-secret',req.call_args.args[0]);self.assertEqual(req.call_args.kwargs['headers']['X-Api-Key'],'fixture-secret');self.assertTrue(all('<b>' not in a['title'] for a in d['articles']))
 def test_outage_preserves_prior_timestamp_and_marks_stale(self):
  with patch('coin_market.time.time',return_value=time.time()-1000),patch('providers.request_json',return_value={'status':'ok','articles':[self.article()]}):first=n.news('bitcoin')
  with patch('providers.request_json',side_effect=ValueError('secret error')):last=n.news('bitcoin')
  self.assertTrue(last['stale']);self.assertEqual(last['fetched_at'],first['fetched_at']);self.assertNotIn('secret error',str(last))
 def test_public_index_metadata_only(self):
  payload={'articles':[{'title':'Bitcoin blockchain news','url':'https://example.com/new','domain':'example.com','seendate':datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'),'content':'never copy this'}]}
  with patch.dict(os.environ,{'NEWS_API_KEY':''}),patch('providers.request_json',return_value=payload):d=n.news('bitcoin')
  self.assertTrue(d['available']);self.assertEqual(d['source'],'GDELT');self.assertEqual(len(d['articles']),1);self.assertNotIn('content',d['articles'][0])
 def test_category_identity_news_survives_rankings_outage(self):
  import market_intelligence
  with patch('coin_market.listings',side_effect=ValueError('provider outage')),patch.object(market_intelligence,'catalog_coin',return_value={'id':'bitcoin','name':'Bitcoin'}),patch.dict(os.environ,{'NEWS_API_KEY':''}),patch('providers.request_json',return_value={'articles':[]}):d=n.news('bitcoin')
  self.assertTrue(d['available']);self.assertEqual(d['coin_id'],'bitcoin')
 def test_provider_errors_and_bounds(self):
  for payload in [{'status':'error','message':'secret'},{'status':'ok','articles':[{}]*101},{'status':'ok','articles':{}}]:
   m.CACHE.clear();m.FAILURES.clear()
   with patch('providers.request_json',return_value=payload):
    with self.assertRaises(ValueError):n.news('bitcoin')
if __name__=='__main__':unittest.main()


class PublisherFeedTests(unittest.TestCase):
 def setUp(self):m.CACHE.clear();m.FAILURES.clear()
 def feed(self):
  from email.utils import formatdate
  return ('<rss><channel><item><title>Bitcoin adoption grows</title><link>https://publisher.test/bitcoin</link><pubDate>'+formatdate(time.time(),usegmt=True)+'</pubDate><description>Do not store full text</description></item><item><title>Bitcoin adoption grows</title><link>https://publisher.test/bitcoin</link><pubDate>'+formatdate(time.time(),usegmt=True)+'</pubDate></item><item><title>Unsafe</title><link>javascript:alert(1)</link><pubDate>'+formatdate(time.time(),usegmt=True)+'</pubDate></item></channel></rss>').encode()
 def test_feed_is_metadata_only_and_deduplicated(self):
  rows=n.parse_feed(self.feed(),'Publisher');self.assertEqual(len(rows),1);self.assertEqual(rows[0]['source'],'Publisher');self.assertNotIn('description',str(rows));self.assertNotIn('full text',str(rows))
 def test_malformed_xml_entities_size_and_source_guards(self):
  for body in [b'<broken',b'\x00<rss/>',b'<!DOCTYPE rss [<!ENTITY x "secret">]><rss/>',b'x'*750001]:
   with self.assertRaises(ValueError):n.parse_feed(body,'Publisher')
  with self.assertRaises(ValueError):n.read_feed('http://127.0.0.1/private')
 def test_general_news_does_not_require_market_listing(self):
  with patch('market_news.read_feed',return_value=self.feed()),patch('coin_market.allowed',side_effect=AssertionError('No coin identity required')):data=n.news()
  self.assertTrue(data['available']);self.assertEqual(len(data['articles']),1);self.assertIn(data['articles'][0]['source'],['CoinDesk','Cointelegraph'])
 def test_one_feed_outage_keeps_other_headlines(self):
  def read(url):
   if 'coindesk' in url:raise ValueError('unavailable')
   return self.feed()
  with patch('market_news.read_feed',side_effect=read):data=n.feed_news('bitcoin','Bitcoin',{})
  self.assertTrue(data['available']);self.assertEqual(data['articles'][0]['source'],'Cointelegraph')
 def test_coin_name_filter_does_not_match_namesakes(self):
  with patch('market_news.read_feed',return_value=self.feed()):self.assertEqual(n.feed_news('bitcoin-cash','Bitcoin Cash',{})['articles'],[])
