"""Read-only exchange snapshots. Orders, account ratios, and trades are distinct measures."""
import time
from decimal import Decimal
from urllib.parse import urlencode
import coin_market as market
import exchange_charts as exchange
import providers

DEFINITION='Long/short account ratio counts accounts, not position size or future price direction. One-hour observation; venue definitions and instrument coverage differ.'

def identity(coin_id):
 value=market.identifier(coin_id)
 if value not in exchange.ASSETS:raise ValueError('No verified exchange identity mapping for this coin')
 market.allowed(value)
 return value,exchange.ASSETS[value]

def positive(value):
 value=market.numeric(value)
 if value is None or Decimal(value)<=0:raise ValueError('Invalid positive exchange value')
 return Decimal(value)

def timestamp(value):
 n=positive(value)
 if n!=n.to_integral_value() or not (time.time()-172800)*1000<=n<=(time.time()+60)*1000:raise ValueError('Invalid or outdated exchange observation')
 return int(n)

def feed(key,loader,**context):
 try:return dict(market.cached(('fundamentals','microstructure')+key,60,loader),available=True,**context)
 except ValueError:return dict(available=False,message='This exchange feed is unavailable or has no verified coverage. Retry later; regional restrictions may apply.',**context)

def spot_metadata(base):
 meta=exchange.metadata('binance',base+'USDT',base,'USDT')
 if meta.get('stale'):raise ValueError('Fresh exchange identity verification unavailable')

def microstructure(coin_id,venue='binance'):
 if venue!='binance':raise ValueError('Only Binance spot snapshots are supported')
 coin,base=identity(coin_id);pair=base+'USDT'
 context={'source':'Binance','pair':pair,'base_currency':base,'quote_currency':'USDT','source_url':'https://www.binance.com/en/trade/'+base+'_USDT'}
 def book():
  spot_metadata(base)
  raw=providers.request_json('https://data-api.binance.vision/api/v3/depth?'+urlencode({'symbol':pair,'limit':100}))
  if not isinstance(raw,dict):raise ValueError('Invalid depth')
  result={}
  for side,reverse in [('bids',True),('asks',False)]:
   rows=raw.get(side)
   if not isinstance(rows,list) or not 1<=len(rows)<=100:raise ValueError('Invalid depth size')
   levels={}
   for row in rows:
    if not isinstance(row,list) or len(row)!=2:raise ValueError('Invalid depth level')
    price,quantity=map(positive,row)
    if price in levels:raise ValueError('Duplicate depth price')
    levels[price]=quantity
   total=Decimal(0);out=[]
   for price in sorted(levels,reverse=reverse):
    quantity=levels[price];total+=quantity
    out.append({'price':str(price),'quantity':str(quantity),'cumulative_quantity':str(total),'notional':str(price*quantity)})
   result[side]=out
  if Decimal(result['bids'][0]['price'])>=Decimal(result['asks'][0]['price']):raise ValueError('Crossed depth snapshot')
  result.update(source='Binance',observed_at=int(time.time()*1000),coverage='Top 100 resting bid and ask levels on one spot pair; quantities are in '+base+'. Snapshot received time, not exchange event time. USDT is not USD. Cancellable orders are not executed trades; this is not a liquidation heatmap.')
  return result
 def trades():
  spot_metadata(base)
  rows=providers.request_json('https://data-api.binance.vision/api/v3/trades?'+urlencode({'symbol':pair,'limit':100}))
  if not isinstance(rows,list) or len(rows)>100:raise ValueError('Invalid recent trades')
  out=[];seen=set();observed=[]
  for row in rows:
   if not isinstance(row,dict) or not isinstance(row.get('id'),int) or isinstance(row['id'],bool) or type(row.get('isBuyerMaker')) is not bool:raise ValueError('Invalid trade identity')
   ts=timestamp(row.get('time'));price=positive(row.get('price'));qty=positive(row.get('qty'));notional=price*qty
   if row['id'] in seen:continue
   seen.add(row['id']);observed.append(ts)
   if notional>=100000:out.append({'id':row['id'],'timestamp':ts,'price':str(price),'quantity':str(qty),'notional':str(notional),'direction':'sell' if row['isBuyerMaker'] else 'buy'})
  return {'source':'Binance','trades':sorted(out,key=lambda r:r['timestamp'],reverse=True),'threshold':'100000','sample_size':len(seen),'observed_from':min(observed) if observed else None,'observed_to':max(observed) if observed else None,'coverage':'Executed trades of at least 100,000 USDT in the latest 100-trade sample, refreshed on request. Direction is taker/aggressor side. Not wallet identification, on-chain whale alerts, a complete time window, or background monitoring. USDT is not USD.'}
 return {'coin_id':coin,'orderbook':feed(('book',coin),book,**context),'large_trades':feed(('trades',coin),trades,**context)}

def ratio(long,short,stamp):
 raw=market.numeric(long)
 if raw is None:raise ValueError('Invalid long account fraction')
 l=Decimal(raw);s=positive(short)
 if l>1 or s>1 or abs(l+s-1)>Decimal('.002'):raise ValueError('Invalid account fractions')
 return {'long_fraction':str(l),'short_fraction':str(s),'ratio':str(l/s),'observed_at':timestamp(stamp)}

def derivatives(coin_id):
 coin,base=identity(coin_id);pair=base+'USDT'
 def binance():
  spot_metadata(base)
  rows=providers.request_json('https://fapi.binance.com/futures/data/globalLongShortAccountRatio?'+urlencode({'symbol':pair,'period':'1h','limit':1}))
  if not isinstance(rows,list) or len(rows)!=1 or not isinstance(rows[0],dict) or rows[0].get('symbol')!=pair:raise ValueError('Invalid Binance futures ratio identity')
  r=rows[0];out=ratio(r.get('longAccount'),r.get('shortAccount'),r.get('timestamp'))
  declared=positive(r.get('longShortRatio'))
  if abs(declared-Decimal(out['ratio']))>Decimal('.01'):raise ValueError('Ratio inconsistent')
  return dict(out,source='Binance',pair=pair,coverage='USD-margined futures global long/short accounts for '+pair)
 def bybit():
  meta=providers.request_json('https://api.bybit.com/v5/market/instruments-info?'+urlencode({'category':'linear','symbol':pair}))
  rows=meta.get('result',{}).get('list') if isinstance(meta,dict) and meta.get('retCode')==0 else None
  if not isinstance(rows,list) or len(rows)!=1 or rows[0].get('symbol')!=pair or rows[0].get('baseCoin')!=base or rows[0].get('quoteCoin')!='USDT':raise ValueError('Bybit product mismatch')
  raw=providers.request_json('https://api.bybit.com/v5/market/account-ratio?'+urlencode({'category':'linear','symbol':pair,'period':'1h','limit':1}))
  rows=raw.get('result',{}).get('list') if isinstance(raw,dict) and raw.get('retCode')==0 else None
  if not isinstance(rows,list) or len(rows)!=1 or rows[0].get('symbol')!=pair:raise ValueError('Bybit ratio identity mismatch')
  r=rows[0]
  return dict(ratio(r.get('buyRatio'),r.get('sellRatio'),r.get('timestamp')),source='Bybit',pair=pair,coverage='Linear USDT-contract long/short account holders for '+pair)
 def okx():
  inst=base+'-USDT-SWAP'
  meta=providers.request_json('https://www.okx.com/api/v5/public/instruments?'+urlencode({'instType':'SWAP','instId':inst}))
  rows=meta.get('data') if isinstance(meta,dict) and meta.get('code')=='0' else None
  if not isinstance(rows,list) or len(rows)!=1 or rows[0].get('instId')!=inst or rows[0].get('ctValCcy')!=base or rows[0].get('settleCcy')!='USDT':raise ValueError('OKX identity mismatch')
  now=int(time.time()*1000)
  raw=providers.request_json('https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio?'+urlencode({'ccy':base,'period':'1H','begin':now-7200000,'end':now}))
  rows=raw.get('data') if isinstance(raw,dict) and raw.get('code')=='0' else None
  if not isinstance(rows,list) or not 1<=len(rows)<=1000:raise ValueError('Invalid OKX ratio')
  valid=[]
  for r in rows:
   if not isinstance(r,list) or len(r)!=2:raise ValueError('Invalid OKX observation')
   ts=timestamp(r[0]);n=positive(r[1]);valid.append((ts,n))
  ts,n=max(valid);short=1/(1+n);long=n/(1+n)
  return dict(ratio(long,short,ts),source='OKX',pair=base+' contracts',coverage='Currency-wide long/short contract account ratio for '+base+'; not solely the USDT perpetual. Fractions derived from reported account ratio.')
 venues=[]
 for name,loader,url in [('binance',binance,'https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Long-Short-Ratio'),('bybit',bybit,'https://bybit-exchange.github.io/docs/v5/market/long-short-ratio'),('okx',okx,'https://www.okx.com/docs-v5/en/#trading-statistics-rest-api-get-contract-long-short-ratio')]:
  venues.append(feed(('ratio',name,coin),loader,venue=name,definition=DEFINITION,source_url=url))
 return {'coin_id':coin,'venues':venues,'coverage':DEFINITION+' Independent public snapshots; no execution or account access. Liquidation heatmaps require a separately licensed data source and are not inferred from spot orders.'}

def exposures(coin_id):
 """Provider-reported funding and open interest; never normalize USDT into USD."""
 coin,base=identity(coin_id);pair=base+'USDT';inst=base+'-USDT-SWAP'
 def number(value,signed=False):
  raw=market.numeric(value,signed)
  if raw is None:raise ValueError('Missing derivatives numeric field')
  return raw
 def funding(value):
  raw=number(value,True)
  if abs(Decimal(raw))>1:raise ValueError('Invalid fractional funding rate')
  return raw
 def future(value):
  raw=positive(value);now=time.time()*1000
  if raw!=raw.to_integral_value() or not now-60000<=raw<=now+172800000:raise ValueError('Invalid funding schedule')
  return int(raw)
 def recent(value):
  ts=timestamp(value)
  if time.time()*1000-ts>600000:raise ValueError('Outdated derivatives snapshot')
  return ts
 def binance():
  spot_metadata(base)
  p=providers.request_json('https://fapi.binance.com/fapi/v1/premiumIndex?'+urlencode({'symbol':pair}))
  o=providers.request_json('https://fapi.binance.com/fapi/v1/openInterest?'+urlencode({'symbol':pair}))
  if not isinstance(p,dict) or not isinstance(o,dict) or p.get('symbol')!=pair or o.get('symbol')!=pair:raise ValueError('Futures symbol mismatch')
  observed=min(recent(p.get('time')),recent(o.get('time')))
  return {'source':'Binance','pair':pair,'quote_currency':'USDT','funding_rate':funding(p.get('lastFundingRate')),'next_funding_at':future(p.get('nextFundingTime')),'open_interest':number(o.get('openInterest')),'open_interest_unit':base,'mark_price':str(positive(p.get('markPrice'))),'observed_at':observed,'coverage':'USD-margined '+pair+' perpetual. Funding is the provider current/last funding-rate snapshot per funding period, not annualized. Open interest is reported base-asset quantity. USDT mark price is not USD; no converted or aggregated OI is inferred.'}
 def bybit():
  meta=providers.request_json('https://api.bybit.com/v5/market/instruments-info?'+urlencode({'category':'linear','symbol':pair}))
  rows=meta.get('result',{}).get('list') if isinstance(meta,dict) and meta.get('retCode')==0 else None
  if not isinstance(rows,list) or len(rows)!=1 or rows[0].get('symbol')!=pair or rows[0].get('baseCoin')!=base or rows[0].get('quoteCoin')!='USDT' or rows[0].get('contractType')!='LinearPerpetual':raise ValueError('Bybit perpetual mismatch')
  raw=providers.request_json('https://api.bybit.com/v5/market/tickers?'+urlencode({'category':'linear','symbol':pair}))
  rows=raw.get('result',{}).get('list') if isinstance(raw,dict) and raw.get('retCode')==0 else None
  if not isinstance(rows,list) or len(rows)!=1 or rows[0].get('symbol')!=pair:raise ValueError('Bybit ticker mismatch')
  r=rows[0]
  return {'source':'Bybit','pair':pair,'quote_currency':'USDT','funding_rate':funding(r.get('fundingRate')),'next_funding_at':future(r.get('nextFundingTime')),'open_interest':number(r.get('openInterest')),'open_interest_unit':base,'open_interest_quote':number(r.get('openInterestValue')),'mark_price':str(positive(r.get('markPrice'))),'observed_at':recent(raw.get('time')),'coverage':'Linear USDT perpetual '+pair+'. Current funding rate per period, not annualized. Ticker openInterest/openInterestValue are provider-reported totals (both sides); not directly comparable to single-side OI conventions. Base quantity and USDT value shown separately. USDT is not USD.'}
 def okx():
  meta=providers.request_json('https://www.okx.com/api/v5/public/instruments?'+urlencode({'instType':'SWAP','instId':inst}))
  rows=meta.get('data') if isinstance(meta,dict) and meta.get('code')=='0' else None
  if not isinstance(rows,list) or len(rows)!=1 or rows[0].get('instId')!=inst or rows[0].get('ctValCcy')!=base or rows[0].get('settleCcy')!='USDT':raise ValueError('OKX perpetual mismatch')
  f=providers.request_json('https://www.okx.com/api/v5/public/funding-rate?'+urlencode({'instId':inst}))
  o=providers.request_json('https://www.okx.com/api/v5/public/open-interest?'+urlencode({'instType':'SWAP','instId':inst}))
  fr=f.get('data') if isinstance(f,dict) and f.get('code')=='0' else None
  oi=o.get('data') if isinstance(o,dict) and o.get('code')=='0' else None
  if not isinstance(fr,list) or len(fr)!=1 or not isinstance(oi,list) or len(oi)!=1 or fr[0].get('instId')!=inst or oi[0].get('instId')!=inst:raise ValueError('OKX derivatives identity mismatch')
  r=fr[0];interest=oi[0]
  # fundingTime is the upcoming settlement for fundingRate; nextFundingTime is the following period.
  return {'source':'OKX','pair':inst,'quote_currency':'USDT','funding_rate':funding(r.get('fundingRate')),'next_funding_at':future(r.get('fundingTime')),'open_interest':number(interest.get('oi')),'open_interest_unit':'contracts','open_interest_usd':number(interest.get('oiUsd')),'observed_at':min(recent(r.get('ts')),recent(interest.get('ts'))),'coverage':'USDT-settled '+inst+' perpetual. Current fundingRate applies at fundingTime (the upcoming settlement); estimate may change. OI is contracts; USD value is the provider-reported oiUsd field, not a USDT conversion. Different venue sizing conventions are not aggregated.'}
 venues=[]
 for name,loader,url in [('binance',binance,'https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Mark-Price'),('bybit',bybit,'https://bybit-exchange.github.io/docs/v5/market/tickers'),('okx',okx,'https://www.okx.com/docs-v5/en/#public-data-rest-api-get-open-interest')]:
  venues.append(feed(('exposures',name,coin),loader,venue=name,source_url=url))
 return {'coin_id':coin,'venues':venues,'coverage':'Public perpetual-futures funding and open-interest snapshots. Funding fractions apply per provider period, not annualized returns. Positive funding generally means longs pay shorts; negative means shorts pay longs. Venue totals and units differ; no cross-exchange aggregate, liquidation estimate, or trading execution.'}
