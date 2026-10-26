"""Sourced read-only market sentiment, category discovery and daily RSI."""
import time
from decimal import Decimal
from urllib.parse import urlencode
import coin_market as m
import exchange_charts
import providers

NARRATIVES={
 'rwa':('Real World Assets (RWA)','real-world-assets-rwa'),
 'ai':('Artificial Intelligence (AI)','artificial-intelligence'),
 'defi':('Decentralized Finance (DeFi)','decentralized-finance-defi'),
 'gaming':('Gaming','gaming'),'meme':('Meme','meme-token'),
 'layer1':('Layer 1','layer-1'),'layer2':('Layer 2','layer-2')}
# Deliberate exclusions, not symbol guesses; this list cannot classify every new wrapper.
EXCLUDED=set('tether usd-coin dai ethena-usde usds first-digital-usd paypal-usd true-usd frax usdd usual-usd ripple-usd global-dollar usd1 wrapped-bitcoin wrapped-steth staked-ether wrapped-eeth coinbase-wrapped-btc binance-staked-sol jupiter-staked-sol renzo-restaked-eth ether-fi-staked-eth rocket-pool-eth mantle-staked-ether susds ethena-staked-usde pax-gold tether-gold'.split())
RSI_ASSETS=('bitcoin','ethereum','solana','ripple','dogecoin','chainlink','cardano','avalanche-2')

def category_options():
 return [{'id':key,'name':v[0],'category_id':v[1]} for key,v in NARRATIVES.items()]

def safe(load,source):
 try:return load()
 except ValueError:return {'available':False,'source':source,'coverage':'Provider unavailable. Retry shortly; no estimate is substituted.','stale':False,'fetched_at':None}

def fear_greed():
 def load():
  payload=providers.request_json('https://api.alternative.me/fng/?limit=30&format=json')
  rows=payload.get('data') if isinstance(payload,dict) else None
  if not isinstance(rows,list) or not 1<=len(rows)<=30:raise ValueError('Invalid sentiment response')
  points={};now=int(time.time())
  for raw in rows:
   if not isinstance(raw,dict):continue
   v=m.numeric(raw.get('value'));t=m.numeric(raw.get('timestamp'))
   if v is None or t is None:continue
   value=Decimal(v);stamp=Decimal(t)
   if value!=value.to_integral_value() or not 0<=value<=100 or stamp!=stamp.to_integral_value() or not 1514764800<=stamp<=now+60:continue
   points[int(stamp)]={'value':int(value),'classification':m.text(raw.get('value_classification'),50),'timestamp':int(stamp)}
  if not points:raise ValueError('No valid sentiment observations')
  history=[points[t] for t in sorted(points,reverse=True)];latest=history[0]
  return {'available':True,'value':latest['value'],'classification':latest['classification'],'observed_at':latest['timestamp'],'history':history,'source':'Alternative.me','source_url':'https://alternative.me/crypto/fear-and-greed-index/','coverage':'Alternative.me Bitcoin-oriented Fear & Greed Index; daily observations, not a whole-market forecast.'}
 return m.cached(('fundamentals','intelligence-fear'),1800,load)

def breadth():
 def load():
  raw=m.request('/coins/markets?'+urlencode({'vs_currency':'usd','order':'market_cap_desc','per_page':100,'page':1,'sparkline':'false','price_change_percentage':'30d'}))
  if not isinstance(raw,list) or not 1<=len(raw)<=100:raise ValueError('Invalid breadth response')
  seen=set();valid=[]
  for item in raw:
   row=m.coin_row(item)
   if row and row['id'] not in seen:
    seen.add(row['id']);valid.append((row,m.numeric(item.get('price_change_percentage_30d_in_currency'),True)))
  bitcoin=next((v for row,v in valid if row['id']=='bitcoin'),None)
  if bitcoin is None:raise ValueError('Bitcoin comparison unavailable')
  candidates=[(r,v) for r,v in valid if r['id']!='bitcoin' and r['id'] not in EXCLUDED]
  eligible=[(r,v) for r,v in candidates if v is not None];winners=sum(Decimal(v)>Decimal(bitcoin) for _,v in eligible)
  return {'available':len(eligible)>=10,'value':round(100*winners/len(eligible),2) if len(eligible)>=10 else None,'outperforming':winners,'eligible':len(eligible),'missing':len(candidates)-len(eligible),'excluded':sum(r['id'] in EXCLUDED for r,_ in valid),'bitcoin_change_30d':bitcoin,'window_days':30,'source':'CoinGecko','coverage':'Orbit 30-day altcoin breadth: share outperforming Bitcoin in a current top-100 snapshot. Curated stablecoin, wrapped/staked and tokenized-gold exclusions; exclusions may not cover every new asset. Missing returns excluded from denominator; minimum 10 comparisons. This is not the CoinMarketCap 90-day Altcoin Season Index; survivor bias applies.'}
 return m.cached(('fundamentals','intelligence-breadth'),900,load)

def overview():
 return {'fear_greed':safe(fear_greed,'Alternative.me'),'altcoin_breadth':safe(breadth,'CoinGecko'),'alt_season':safe(alt_season,'CoinMarketCap'),'narratives':category_options()}

def narratives(slug):
 if not isinstance(slug,str) or slug not in NARRATIVES:raise ValueError('Unsupported narrative')
 name,category=NARRATIVES[slug]
 def load():
  raw=m.request('/coins/markets?'+urlencode({'vs_currency':'usd','order':'market_cap_desc','per_page':250,'page':1,'sparkline':'false','price_change_percentage':'24h,7d','category':category}))
  if not isinstance(raw,list) or not 1<=len(raw)<=250:raise ValueError('Invalid category response')
  rows=[];seen=set()
  for item in raw:
   row=m.coin_row(item)
   if row and row['id'] not in seen:seen.add(row['id']);rows.append(row)
  if not rows:raise ValueError('No ranked category coins available')
  rows.sort(key=lambda r:r['market_cap_rank'])
  return {'narrative':{'id':slug,'name':name,'category_id':category},'coins':rows,'coverage':'CoinGecko category taxonomy; up to 250 ranked assets. Categories overlap and are not an endorsement. This is a discovery list, not a complete sector census.'}
 return m.cached(('fundamentals','intelligence-narrative',slug),900,load)

def venues(coin_id):
 identity=m.allowed(coin_id)
 def load():
  raw=m.request('/coins/'+identity+'/tickers?'+urlencode({'order':'volume_desc','page':1,'depth':'false','dex_pair_format':'symbol'}))
  items=raw.get('tickers') if isinstance(raw,dict) else None
  if not isinstance(items,list) or len(items)>100:raise ValueError('Invalid venue response')
  rows=[];seen=set()
  for r in items:
   if not isinstance(r,dict) or r.get('coin_id')!=identity or r.get('is_stale') is True or r.get('is_anomaly') is True:continue
   venue=r.get('market');volume=r.get('converted_volume');last=r.get('converted_last')
   if not isinstance(venue,dict):continue
   name=m.text(venue.get('name'),80);exchange=m.text(venue.get('identifier'),100);base=m.text(r.get('base'),100);quote=m.text(r.get('target'),100)
   stamp=m.stamp(r.get('last_traded_at')) or m.stamp(r.get('timestamp'))
   if not name or not exchange or not base or not quote or not stamp:continue
   key=(exchange,base,quote)
   if key in seen:continue
   seen.add(key);rows.append({'exchange':name,'exchange_id':exchange,'base':base,'quote':quote,'price_usd':m.numeric(last.get('usd')) if isinstance(last,dict) else None,'volume_usd':m.numeric(volume.get('usd')) if isinstance(volume,dict) else None,'spread_percentage':m.numeric(r.get('bid_ask_spread_percentage')),'trade_url':m.url(r.get('trade_url')),'observed_at':stamp})
  rows.sort(key=lambda r:Decimal(r['volume_usd']) if r['volume_usd'] is not None else Decimal(-1),reverse=True)
  return {'coin_id':identity,'venues':rows[:30],'source':'CoinGecko','coverage':'Up to 30 trading pairs from the first 100 provider tickers, ordered by reported USD volume. Stale/anomalous pairs are filtered; not every listing is included. Venue links are informational; no orders are placed.'}
 return m.cached(('fundamentals','intelligence-venues',identity),600,load)

def wilder(closes,period=14):
 if len(closes)<period+1:raise ValueError('At least 15 consecutive daily closes are required')
 values=[]
 for x in closes:
  raw=m.numeric(x)
  if raw is None:raise ValueError('Invalid closing price')
  values.append(Decimal(raw))
 changes=[b-a for a,b in zip(values,values[1:])]
 gain=sum(max(d,Decimal(0)) for d in changes[:period])/period
 loss=sum(max(-d,Decimal(0)) for d in changes[:period])/period
 for d in changes[period:]:gain=(gain*(period-1)+max(d,Decimal(0)))/period;loss=(loss*(period-1)+max(-d,Decimal(0)))/period
 return 50.0 if gain==loss==0 else 100.0 if loss==0 else float(100-100/(1+gain/loss))

def daily_rsi(payload,now=None):
 now=int(time.time()) if now is None else now
 if payload.get('interval')!='daily' or payload.get('stale'):raise ValueError('Fresh daily candles required')
 raw=payload.get('candles')
 if not isinstance(raw,list) or len(raw)>1000:raise ValueError('Invalid daily candles')
 points={}
 for r in raw:
  if not isinstance(r,dict):continue
  ts=m.numeric(r.get('timestamp'));close=m.numeric(r.get('close'))
  if ts is None or close is None:continue
  stamp=Decimal(ts)
  if stamp!=stamp.to_integral_value() or stamp%86400000 or stamp<1230768000000:continue
  if stamp/1000+86400<=now:points[int(stamp)]=close
 ordered=sorted(points)
 if len(ordered)<15:raise ValueError('Insufficient closed daily candles')
 # Use only the most recent consecutive segment after the last missing day.
 start=0
 for i in range(1,len(ordered)):
  if ordered[i]-ordered[i-1]!=86400000:start=i
 ordered=ordered[start:]
 if len(ordered)<15 or now-ordered[-1]/1000>3*86400:raise ValueError('Missing or outdated daily candles')
 return wilder([points[t] for t in ordered]),ordered[-1]//1000

def rsi():
 def load():
  from concurrent.futures import ThreadPoolExecutor
  from contextlib import nullcontext
  callbacks=getattr(m.STORE,'callbacks',None);cutoff=getattr(providers._REQUEST_CONTEXT,'cutoff',None) or time.monotonic()+25
  # Bounded parallelism; preserve request deadline and public-cache persistence.
  def observe(identity):
   with providers.deadline(cutoff), (m.persistence(*callbacks) if callbacks else nullcontext()):
    row={'coin_id':identity,'symbol':exchange_charts.ASSETS[identity],'available':False,'value':None,'signal':None,'source':None,'pair':None,'observed_at':None}
    for source in ('binance','coinbase'):
     try:
      payload=exchange_charts.chart(identity,90,'candles',source);value,stamp=daily_rsi(payload)
      row.update(available=True,value=round(value,2),signal='overbought' if value>=70 else 'oversold' if value<=30 else 'neutral',source=payload.get('source'),pair=payload.get('pair'),observed_at=stamp);break
     except ValueError:pass
    if not row['available']:row['error']='Verified consecutive daily candles unavailable.'
    return row
  with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(observe,RSI_ASSETS))
  if not any(r['available'] for r in rows):raise ValueError('Daily RSI providers unavailable')
  return {'rows':rows,'period':14,'interval':'daily','source':'Exchange spot candles','coverage':'Wilder RSI(14), latest completed UTC daily candle, eight curated spot assets. Binance USDT with Coinbase USD fallback; venue and pair are shown per asset. At least 15 consecutive closes required; no interpolated gaps. Overbought >=70, oversold <=30; not a trade recommendation.'}
 return m.cached(('fundamentals','intelligence-rsi'),900,load)

def alt_season():
 def load():
  payload=providers.request_json('https://pro-api.coinmarketcap.com/public-api/v1/altcoin-season-index/latest')
  if not isinstance(payload,dict) or not isinstance(payload.get('status'),dict) or payload['status'].get('error_code')!=0:raise ValueError('Altcoin season unavailable')
  raw=payload.get('data')
  if not isinstance(raw,dict):raise ValueError('Invalid altcoin season payload')
  value=m.numeric(raw.get('altcoin_index'));stamp=m.stamp(raw.get('snapshot_time'))
  if value is None or not 0<=Decimal(value)<=100 or stamp is None:raise ValueError('Invalid altcoin season observation')
  return {'available':True,'value':float(value),'observed_at':stamp,'classification':'Altcoin season' if Decimal(value)>=75 else 'Bitcoin season' if Decimal(value)<=25 else 'Mixed market','window_days':90,'source':'CoinMarketCap','source_url':'https://coinmarketcap.com/charts/altcoin-season-index/','coverage':'CoinMarketCap Altcoin Season Index: top 100 eligible coins compared with Bitcoin over 90 days. Provider exclusions and methodology apply; index >=75 generally signals altcoin season and <=25 Bitcoin season. This is a market indicator, not a forecast.'}
 return m.cached(('fundamentals','intelligence-alt-season'),900,load)


def catalog_coin(identity):
 """Read validated previously discovered category rows, without upstream requests."""
 identity=m.identifier(identity);now=time.time()
 for slug in NARRATIVES:
  key=('fundamentals','intelligence-narrative',slug)
  with m.LOCK:
   saved=m.CACHE.get(key);payload=saved[1] if saved else None
   callbacks=getattr(m.STORE,'callbacks',None)
   if payload is None and callbacks:
    try:payload=callbacks[0](key)
    except Exception:payload=None
  if not isinstance(payload,dict):continue
  stamp=payload.get('fetched_at')
  if isinstance(stamp,bool) or not isinstance(stamp,int) or not 0<=now-stamp<=86400:continue
  coins=payload.get('coins')
  if not isinstance(coins,list) or len(coins)>250:continue
  for raw in coins:
   if not isinstance(raw,dict) or raw.get('id')!=identity:continue
   row=m.coin_row(raw)
   if row:
    row['price_change_percentage_7d']=m.numeric(raw.get('price_change_percentage_7d'),True)
    return row
 return None


