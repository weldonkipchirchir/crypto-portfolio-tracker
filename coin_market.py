"""Bounded CoinGecko market discovery; historical data is never synthesized."""
import copy,datetime,html,os,re,threading,time
from decimal import Decimal,InvalidOperation
from html.parser import HTMLParser
from urllib.parse import urlencode,urlsplit
import providers

BASE='https://api.coingecko.com/api/v3'
CACHE={};LOCK=threading.RLock();FAILURES={};STORE=threading.local()
from contextlib import contextmanager
@contextmanager
def persistence(read,write):
 prior=getattr(STORE,"callbacks",None);STORE.callbacks=(read,write)
 try:yield
 finally:STORE.callbacks=prior
AVAILABILITY={'revenue':'Unavailable from this provider; no revenue estimate is inferred.','unlocks':'Unavailable from this provider; current supply is not an unlock schedule.','historical_supply':'Unavailable from this provider; current supply is a snapshot.'}

class Plain(HTMLParser):
 def __init__(self):super().__init__();self.parts=[];self.hidden=0
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style'):self.hidden+=1
 def handle_endtag(self,tag):
  if tag in ('script','style'):self.hidden=max(0,self.hidden-1)
 def handle_data(self,data):
  if not self.hidden:self.parts.append(data)

def text(value,limit):
 if not isinstance(value,str):return ''
 parser=Plain();parser.feed(value[:20000]);clean=re.sub(r'\s+',' ',html.unescape(' '.join(parser.parts))).strip();return (clean[:limit].rsplit(' ',1)[0]+'…') if len(clean)>limit else clean

def url(value):
 if not isinstance(value,str) or len(value)>1500:return None
 try:
  parsed=urlsplit(value)
  if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or any(ord(ch)<33 for ch in value):return None
 except ValueError:return None
 return value

def numeric(value,signed=False):
 if value is None or isinstance(value,bool):return None
 try:
  raw=str(value)
  if len(raw)>100:return None
  n=Decimal(raw)
  if not n.is_finite() or abs(n)>Decimal('1e40') or (not signed and n<0) or not -100<=n.as_tuple().exponent<=40:return None
  return str(n)
 except (ValueError,InvalidOperation):return None

def identifier(value):
 if not isinstance(value,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,99}',value):raise ValueError('Invalid CoinGecko coin ID')
 return value

def stamp(value):
 try:
  if not isinstance(value,str) or len(value)>50:return None
  dt=datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
  if dt.tzinfo is None:return None
  seconds=int(dt.timestamp())
  return seconds if 1230768000<=seconds<=time.time()+60 else None
 except (ValueError,OverflowError):return None

def request(path):
 key=os.environ.get('COINGECKO_DEMO_API_KEY','').strip()
 return providers.request_json(BASE+path,headers={'x-cg-demo-api-key':key} if key else None)

KEY_LOCKS={}
@contextmanager
def key_lock(key):
 # Retain locks only while used; unrelated feeds do not wait behind slow HTTP.
 with LOCK:
  lock,users=KEY_LOCKS.get(key,(threading.RLock(),0));KEY_LOCKS[key]=(lock,users+1)
 try:
  with lock:yield
 finally:
  with LOCK:
   lock,users=KEY_LOCKS[key]
   if users==1:del KEY_LOCKS[key]
   else:KEY_LOCKS[key]=(lock,users-1)

def cached(key,ttl,loader,force=False):
 with key_lock(key):
  now=time.time()
  with LOCK:prior=CACHE.get(key);failed=FAILURES.get(key,0)
  callbacks=getattr(STORE,'callbacks',None)
  if prior is None and callbacks:
   try:
    saved=callbacks[0](key)
    if isinstance(saved,dict) and isinstance(saved.get('fetched_at'),int) and 0<=now-saved['fetched_at']<604800:
     prior=(saved['fetched_at'],saved)
     # Hydrate the warm worker cache: otherwise every poll repeats a cloud DB read.
     with LOCK:
      if len(CACHE)<400:CACHE[key]=prior
   except Exception:pass
  if prior and (now-prior[0]<ttl or (force and now-prior[0]<30)):return copy.deepcopy(prior[1])
  if now-failed<30:
   if prior:return dict(copy.deepcopy(prior[1]),stale=True,error='Provider unavailable; showing the last saved market response.')
   raise ValueError('Market provider is temporarily unavailable. Retry shortly.')
  try:
   data=loader();data.update(source=data.get('source','CoinGecko'),fetched_at=int(time.time()),stale=False)
  except (ValueError,TypeError,KeyError,AttributeError):
   with LOCK:
    if len(FAILURES)>=200:FAILURES.pop(next(iter(FAILURES)))
    FAILURES[key]=time.time()
   if prior:return dict(copy.deepcopy(prior[1]),stale=True,error='Provider unavailable; showing the last saved market response.')
   raise ValueError('Market provider is temporarily unavailable. Retry shortly.') from None
  with LOCK:
   prefix=key[0];cap={'list':1,'detail':100,'chart':80,'fundamentals':100}[prefix]
   related=[k for k in CACHE if k[0]==prefix]
   if key not in CACHE and len(related)>=cap:CACHE.pop(min(related,key=lambda k:CACHE[k][0]))
   CACHE[key]=(time.time(),data);FAILURES.pop(key,None)
  if callbacks:
   try:callbacks[1](key,data)
   except Exception:pass
  return copy.deepcopy(data)

def coin_row(raw):
 if not isinstance(raw,dict):return None
 try:identity=identifier(raw.get('id'))
 except ValueError:return None
 rank=raw.get('market_cap_rank')
 if isinstance(rank,bool) or not isinstance(rank,int) or not 1<=rank<=100000:return None
 row={'id':identity,'name':text(raw.get('name'),100),'symbol':text(raw.get('symbol'),24).upper(),'image':url(raw.get('image')),'market_cap_rank':rank,'last_updated':stamp(raw.get('last_updated'))}
 if not row['name'] or not row['symbol']:return None
 for field in ('current_price','market_cap','total_volume','circulating_supply','total_supply','max_supply','fully_diluted_valuation','ath','atl'):
  row[field]=numeric(raw.get(field))
 row['price_change_percentage_24h']=numeric(raw.get('price_change_percentage_24h'),True)
 row['price_change_percentage_7d']=numeric(raw.get('price_change_percentage_7d_in_currency'),True)
 row['price_change_percentage_30d']=numeric(raw.get('price_change_percentage_30d_in_currency'),True)
 return row

def listings(force=False):
 def load():
  payload=request('/coins/markets?'+urlencode({'vs_currency':'usd','order':'market_cap_desc','per_page':250,'page':1,'sparkline':'false','price_change_percentage':'24h,7d,30d'}))
  if not isinstance(payload,list) or not 1<=len(payload)<=250:raise ValueError('Invalid markets response')
  seen=set();rows=[]
  for raw in payload:
   row=coin_row(raw)
   if row and row['id'] not in seen:seen.add(row['id']);rows.append(row)
  if not rows:raise ValueError('No valid market records')
  rows.sort(key=lambda r:(r['market_cap_rank'],r['id']))
  return {'coins':rows,'availability':dict(AVAILABILITY),'coverage':'Top 250 provider-ranked coins; available rows may be fewer.'}
 return cached(('list','periods-v2'),300,load,force)

def allowed(coin_id):
 identity=identifier(coin_id)
 try:known=any(c['id']==identity for c in listings()['coins'])
 except ValueError:known=False
 if not known:
  import market_intelligence
  if not market_intelligence.catalog_coin(identity):raise ValueError('Choose a coin from the market listings or a recently loaded narrative')
 return identity

def detail(coin_id):
 identity=allowed(coin_id)
 def load():
  payload=request('/coins/'+identity+'?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false')
  if not isinstance(payload,dict) or payload.get('id')!=identity:raise ValueError('Coin identity mismatch')
  market=payload.get('market_data')
  if not isinstance(market,dict):raise ValueError('Missing market data')
  raw={k:payload.get(k) for k in ('id','symbol','name','market_cap_rank','last_updated')}
  raw['image']=(payload.get('image') or {}).get('large')
  for field in ('current_price','market_cap','total_volume','fully_diluted_valuation','ath','atl'):raw[field]=(market.get(field) or {}).get('usd')
  for field in ('circulating_supply','total_supply','max_supply','price_change_percentage_24h'):raw[field]=market.get(field)
  row=coin_row(raw)
  if not row:raise ValueError('Invalid coin detail')
  platforms=payload.get('platforms',{})
  row['platforms']={k:v for k,v in platforms.items() if isinstance(k,str) and re.fullmatch(r'[a-z0-9-]{1,80}',k) and isinstance(v,str) and 1<=len(v)<=100} if isinstance(platforms,dict) else {}
  row['categories']=[text(x,80) for x in (payload.get('categories') or [])[:12] if isinstance(x,str)]
  row['description']=text((payload.get('description') or {}).get('en'),1000)
  websites=(payload.get('links') or {}).get('homepage') or []
  row['website']=next((u for u in map(url,websites[:10]) if u),None) if isinstance(websites,list) else None
  return {'coin':row,'availability':dict(AVAILABILITY)}
 return cached(('detail',identity),600,load)

def chart(coin_id,days,kind='line'):
 if isinstance(days,bool) or str(days) not in ('1','7','30','90','365','max'):raise ValueError('Chart range must be 1, 7, 30, 90, 365 or max')
 if kind not in ('line','candles'):raise ValueError('Chart type must be line or candles')
 identity=allowed(coin_id)
 requested='max' if days=='max' else int(days);effective=365 if requested=='max' else requested
 def load():
  endpoint='ohlc' if kind=='candles' else 'market_chart'
  payload=request('/coins/'+identity+'/'+endpoint+'?'+urlencode({'vs_currency':'usd','days':effective}))
  rows=payload if kind=='candles' else payload.get('prices') if isinstance(payload,dict) else None
  if not isinstance(rows,list) or not 1<=len(rows)<=3000:raise ValueError('Invalid chart response')
  now=int(time.time()*1000);minimum=now-(effective*86400+21600)*1000;points={}
  for row in rows:
   if not isinstance(row,list) or len(row)!=(5 if kind=='candles' else 2):continue
   ts=numeric(row[0]);values=[numeric(v) for v in row[1:]]
   if ts is None or any(v is None for v in values):continue
   ts=Decimal(ts)
   if ts!=ts.to_integral_value() or not minimum<=ts<=now+60000:continue
   ts=int(ts)
   if kind=='candles':
    opening,high,low,closing=map(Decimal,values)
    if low>high or not low<=opening<=high or not low<=closing<=high:continue
    point=dict(timestamp=ts,**dict(zip(('open','high','low','close'),values)))
   else:point={'timestamp':ts,'price':values[0]}
   if ts not in points:points[ts]=point
  if len(points)<2:raise ValueError('Not enough valid historical points')
  ordered=[points[ts] for ts in sorted(points)]
  granularity=('30-minute' if effective<=2 else '4-hour' if effective<=30 else '4-day') if kind=='candles' else ('5-minute' if effective==1 else 'hourly' if effective<=90 else 'daily')
  coverage=('ALL is all history accessible through the current provider, limited to the past 365 days; it is not necessarily history since launch. ' if requested=='max' else '')
  coverage+='CoinGecko Demo historical USD '+('OHLC candles' if kind=='candles' else 'prices')+'; automatic '+granularity+' intervals. No interpolated or generated '+('candles' if kind=='candles' else 'points')+'.'
  if kind=='candles':coverage+=' Candle timestamps are close times.'
  return {'coin_id':identity,'days':requested,'effective_days':effective,'kind':kind,'chart_type':kind,'history_limit_days':365,'observed_from':ordered[0]['timestamp'],'observed_to':ordered[-1]['timestamp'],'candles' if kind=='candles' else 'points':ordered,'coverage':coverage}
 return cached(('chart',identity,requested,kind),300,load)
