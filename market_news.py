"""Optional licensed headline API; no article bodies or publisher feed scraping."""
import os,re,time,datetime,urllib.request,urllib.error,xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
import coin_market as market
import providers


def news(coin_id=None):
 if coin_id is None:return feed_news('all',None,{'coin_id':None,'search_links':[]})
 identity=market.allowed(coin_id)
 try:coin=next((c for c in market.listings()['coins'] if c['id']==identity),None)
 except ValueError:coin=None
 if coin is None:
  import market_intelligence
  coin=market_intelligence.catalog_coin(identity)
 if not coin:raise ValueError('Coin news identity is unavailable')
 name=coin['name'];query='"'+name.replace('"','')+'" cryptocurrency'
 links=[{'label':'Search coin news','url':'https://news.google.com/search?'+urlencode({'q':query,'hl':'en-US','gl':'US','ceid':'US:en'})}]
 key=os.environ.get('NEWS_API_KEY','').strip()
 base={'coin_id':identity,'articles':[],'search_links':links,'source':'NewsAPI','coverage':'Headline relevance uses the coin name, not verified token-contract identity. External search results are supplied by Google News.'}
 if not key or (os.environ.get('VERCEL') and os.environ.get('NEWS_API_PRODUCTION_LICENSED')!='1'):
  return public_news(identity,name,base)
 if len(key)>256 or any(ord(c)<33 for c in key):raise ValueError('News provider configuration is invalid')
 def load():
  params={'q':'"'+name.replace('"','')+'" AND (crypto OR cryptocurrency OR blockchain OR token)','language':'en','sortBy':'publishedAt','searchIn':'title','from':datetime.datetime.fromtimestamp(time.time()-30*86400,datetime.timezone.utc).date().isoformat(),'pageSize':30,'page':1}
  payload=providers.request_json('https://newsapi.org/v2/everything?'+urlencode(params),headers={'X-Api-Key':key})
  if not isinstance(payload,dict) or payload.get('status')!='ok' or not isinstance(payload.get('articles'),list) or len(payload['articles'])>100:raise ValueError('Invalid news provider response')
  articles=[];seen=set();now=time.time()
  # Name boundary avoids short-symbol collisions; search relevance is still imperfect.
  pattern=re.compile(r'(?<!\w)'+re.escape(name)+r'(?!\w)',re.IGNORECASE)
  for row in payload['articles']:
   if not isinstance(row,dict):continue
   title=market.text(row.get('title'),240);link=market.url(row.get('url'));published=market.stamp(row.get('publishedAt'))
   source=row.get('source');source=market.text(source.get('name'),100) if isinstance(source,dict) else ''
   if not title or not pattern.search(title) or not link or not source or published is None or not now-30*86400<=published<=now+60:continue
   fingerprint=title.casefold()
   if link in seen or fingerprint in seen:continue
   seen.update((link,fingerprint));articles.append({'title':title,'url':link,'source':source,'published_at':published})
  articles.sort(key=lambda a:a['published_at'],reverse=True)
  return {**base,'available':True,'articles':articles[:12],'coverage':'Recent English headlines supplied by NewsAPI, filtered by coin name in the title; keyword matches can include unrelated namesakes. No full article text is stored. Coverage is not exhaustive.'}
 return market.cached(('fundamentals','news',identity),900,load)


def public_news(identity,name,base):
 """Public GDELT index metadata only; articles remain on publishers' sites."""
 rss=feed_news(identity,name,base)
 if rss.get("articles"):return rss
 def load():
  # Strip query operators from provider-supplied names before using a quoted phrase.
  phrase=re.sub(r'[^\w .-]','',name)[:100]
  params={'query':'"'+phrase+'" (crypto OR cryptocurrency OR blockchain) sourcelang:english','mode':'artlist','format':'json','maxrecords':30,'timespan':'7d','sort':'datedesc'}
  payload=providers.request_json('https://api.gdeltproject.org/api/v2/doc/doc?'+urlencode(params))
  if not isinstance(payload,dict) or not isinstance(payload.get('articles'),list) or len(payload['articles'])>250:raise ValueError('Public news index is unavailable')
  articles=[];seen=set();now=time.time();pattern=re.compile(r'(?<!\w)'+re.escape(name)+r'(?!\w)',re.I)
  for row in payload['articles']:
   if not isinstance(row,dict):continue
   title=market.text(row.get('title'),240);link=market.url(row.get('url'));source=market.text(row.get('domain'),100)
   try:published=int(datetime.datetime.strptime(str(row.get('seendate')),'%Y%m%dT%H%M%SZ').replace(tzinfo=datetime.timezone.utc).timestamp())
   except (ValueError,TypeError):continue
   if not title or not pattern.search(title) or not link or not source or link in seen or title.casefold() in seen or not now-8*86400<=published<=now+60:continue
   seen.update((link,title.casefold()));articles.append({'title':title,'url':link,'source':source,'published_at':published})
  return {**base,'source':'GDELT','source_url':'https://www.gdeltproject.org/','available':True,'articles':sorted(articles,key=lambda a:a['published_at'],reverse=True)[:12],'coverage':'GDELT public news index · English title matches over 7 days. Dates indicate first observed by the index, not verified publication time. Open the publisher for the full report; keyword matches may be unrelated.'}
 try:return market.cached(('fundamentals','public-news',identity),1800,load)
 except ValueError:return {**base,'source':'GDELT','available':False,'articles':[],'fetched_at':int(time.time()),'stale':False,'coverage':'The public news index is temporarily unavailable or rate limited. Open coin news search below or retry later.'}


FEEDS=(('CoinDesk','https://www.coindesk.com/arc/outboundfeeds/rss/'),('Cointelegraph','https://cointelegraph.com/rss'))

def read_feed(url):
 if url not in {u for _,u in FEEDS}:raise ValueError('Unsupported news feed')
 try:
  request=urllib.request.Request(url,headers={'User-Agent':'OrbitPortfolio/1.0 (headline reader)','Accept':'application/rss+xml, application/xml, text/xml'})
  with urllib.request.urlopen(request,timeout=8) as response:
   body=response.read(750001)
  if len(body)>750000:raise ValueError('News feed is too large')
  return body
 except (OSError,urllib.error.URLError,TimeoutError):raise ValueError('News feed unavailable') from None

def parse_feed(body,source,now=None):
 if not isinstance(body,bytes) or len(body)>750000 or b'<!DOCTYPE' in body.upper() or b'<!ENTITY' in body.upper():raise ValueError('Invalid news feed')
 try:root=ET.fromstring(body)
 except ET.ParseError:raise ValueError('Invalid news feed') from None
 now=time.time() if now is None else now;articles=[];seen=set()
 for row in root.findall('./channel/item')[:100]:
  title=market.text(row.findtext('title'),240);url=market.url(row.findtext('link'))
  try:published=parsedate_to_datetime(row.findtext('pubDate') or '').timestamp()
  except (ValueError,TypeError,OverflowError,AttributeError):continue
  if not title or not url or not now-14*86400<=published<=now+60 or url in seen or title.casefold() in seen:continue
  seen.update((url,title.casefold()));articles.append({'title':title,'url':url,'source':source,'published_at':int(published)})
 return articles

def feed_news(identity,name,base):
 def load():
  def fetch(feed):
   source,url=feed
   try:return parse_feed(read_feed(url),source)
   except ValueError:return []
  with ThreadPoolExecutor(max_workers=2) as pool:groups=list(pool.map(fetch,FEEDS))
  articles=[];seen=set()
  for article in sorted([a for group in groups for a in group],key=lambda a:a['published_at'],reverse=True):
   if article['url'] in seen or article['title'].casefold() in seen:continue
   seen.update((article['url'],article['title'].casefold()));articles.append(article)
  if not articles:raise ValueError('Publisher headline feeds unavailable')
  return {'articles':articles[:50],'source':'Publisher RSS','available':True,'coverage':'Publisher-provided headlines and publication dates. Articles open on the original publisher website; no article bodies are copied. Coin matches use names in headlines and may be incomplete.'}
 try:data=market.cached(('fundamentals','publisher-news-v1'),600,load)
 except ValueError:return {**base,'articles':[],'source':'Publisher RSS','available':False,'fetched_at':int(time.time()),'coverage':'Publisher feeds are temporarily unavailable. Retry later.'}
 articles=data['articles']
 if name:
  pattern=re.compile(r'(?<!\w)'+re.escape(name)+r'(?!\w)',re.I);articles=[a for a in articles if pattern.search(a['title'])]
 return {**base,**data,'articles':articles[:12]}
