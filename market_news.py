"""Optional licensed headline API; no article bodies or publisher feed scraping."""
import os,re,time,datetime
from urllib.parse import urlencode
import coin_market as market
import providers


def news(coin_id):
 identity=market.allowed(coin_id)
 coin=next(c for c in market.listings()['coins'] if c['id']==identity)
 name=coin['name'];query='"'+name.replace('"','')+'" cryptocurrency'
 links=[{'label':'Search coin news','url':'https://news.google.com/search?'+urlencode({'q':query,'hl':'en-US','gl':'US','ceid':'US:en'})}]
 key=os.environ.get('NEWS_API_KEY','').strip()
 base={'coin_id':identity,'articles':[],'search_links':links,'source':'NewsAPI','coverage':'Headline relevance uses the coin name, not verified token-contract identity. External search results are supplied by Google News.'}
 if not key or (os.environ.get('VERCEL') and os.environ.get('NEWS_API_PRODUCTION_LICENSED')!='1'):
  return {**base,'available':False,'fetched_at':int(time.time()),'stale':False,'coverage':'Live headlines require a configured NewsAPI key with a plan licensed for production. Use the coin news search link to read coverage now.'}
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
