"""Executed-trade footprint and separate top-trader account/position observations."""
import time,os
from decimal import Decimal,ROUND_FLOOR,ROUND_CEILING
from urllib.parse import urlencode
import coin_market as market
import exchange_charts as exchange
import providers

INTERVALS={'1m':60,'5m':300,'15m':900,'1h':3600}
PERIODS={'5m':300,'15m':900,'1h':3600,'4h':14400,'1d':86400}
MAX_PAGES=6

def positive(value):
 raw=market.numeric(value)
 if raw is None or Decimal(raw)<=0:raise ValueError('Invalid positive market value')
 return Decimal(raw)

def identity(coin_id):
 coin=market.identifier(coin_id)
 if coin not in exchange.ASSETS:raise ValueError('Choose a verified exchange-mapped coin')
 market.allowed(coin);return coin,exchange.ASSETS[coin]

def product(base,venue):
 pair=base+'USDT'
 def load():
  if venue=='spot':
   result=exchange.metadata('binance',pair,base,'USDT')
   if result.get('stale'):raise ValueError('Fresh product verification unavailable')
  else:
   raw=providers.request_json('https://fapi.binance.com/fapi/v1/exchangeInfo');rows=raw.get('symbols') if isinstance(raw,dict) else None
   if not isinstance(rows,list):raise ValueError('Invalid perpetual products')
   matched=[r for r in rows if isinstance(r,dict) and r.get('symbol')==pair]
   if len(matched)!=1 or matched[0].get('baseAsset')!=base or matched[0].get('quoteAsset')!='USDT' or matched[0].get('contractType')!='PERPETUAL' or matched[0].get('status')!='TRADING':raise ValueError('Perpetual product identity mismatch')
  return {'pair':pair,'source':'Binance Spot' if venue=='spot' else 'Binance USDT Perpetual'}
 result=market.cached(('fundamentals','footprint-product',base,venue),86400,load)
 if result.get('stale'):raise ValueError('Fresh product verification unavailable')
 return result

def raw_trades(coin,base,venue):
 def load():
  meta=product(base,venue);root='https://data-api.binance.vision/api/v3/aggTrades' if venue=='spot' else 'https://fapi.binance.com/fapi/v1/aggTrades'
  records={};oldest=None;pages=0;now=int(time.time()*1000)
  for _ in range(MAX_PAGES):
   params={'symbol':base+'USDT','limit':1000}
   if oldest is not None:params['fromId']=max(0,oldest-1000)
   rows=providers.request_json(root+'?'+urlencode(params));pages+=1
   if not isinstance(rows,list) or len(rows)>1000:raise ValueError('Invalid aggregate trade sample')
   before=oldest
   for r in rows:
    if not isinstance(r,dict) or type(r.get('a')) is not int or r['a']<0 or type(r.get('m')) is not bool or type(r.get('T')) is not int or not now-86400000<=r['T']<=now+60000:raise ValueError('Invalid aggregate trade identity or timestamp')
    price,quantity=positive(r.get('p')),positive(r.get('q'))
    item={'id':r['a'],'timestamp':r['T'],'price':str(price),'quantity':str(quantity),'side':'sell' if r['m'] else 'buy'}
    if r['a'] in records and records[r['a']]!=item:raise ValueError('Conflicting aggregate trade identity')
    records[r['a']]=item
   if not records:raise ValueError('No executed trades returned')
   oldest=min(records)
   if before is not None and oldest>=before:break
   if oldest==0 or len(rows)<1000:break
  ordered=sorted(records.values(),key=lambda r:(r['timestamp'],r['id']))
  if len(ordered)>6000:raise ValueError('Trade sample exceeds bounded limit')
  ids=sorted(records);gaps=sum(max(0,b-a-1) for a,b in zip(ids,ids[1:]))
  if now-ordered[-1]['timestamp']>300000:raise ValueError('Recent executed trades are outdated')
  return {'trades':ordered,'source':meta['source'],'pages':pages,'id_gaps':gaps,'observed_from':ordered[0]['timestamp'],'observed_to':ordered[-1]['timestamp']}
 # Raw prints stay in the worker cache; persist only the smaller aggregated view.
 with market.persistence(lambda key:None,lambda key,data:None):return market.cached(('fundamentals','footprint-prints-v1',coin,venue),30,load)

def row_step(trades,requested):
 if requested!='auto':
  if str(requested) not in ('0.1','0.5','1','5','10','25','50','100'):raise ValueError('Unsupported footprint price-row size')
  result=Decimal(str(requested))
 else:
  prices=[Decimal(r['price']) for r in trades];width=max(prices)-min(prices)
  raw=max(width/36,min(prices)/Decimal('100000'))
  scale=Decimal(10)**raw.adjusted();ratio=raw/scale
  result=next(v*scale for v in map(Decimal,('1','2','5','10')) if v>=ratio)
 prices=[Decimal(r['price']) for r in trades]
 if (max(prices)-min(prices))/result>180:raise ValueError('Price rows are too small for this sample. Choose Auto or a larger row size.')
 return result

def aggregate(sample,interval='1m',row_size='auto',now=None):
 now=int(time.time()*1000) if now is None else now;seconds=INTERVALS[interval];duration=seconds*1000;trades=sample['trades'];step=row_step(trades,row_size);groups={}
 for r in trades:
  stamp=r['timestamp']//duration*duration;bar=groups.setdefault(stamp,[]);bar.append(r)
 bars=[]
 for stamp,records in sorted(groups.items())[-24:]:
  records=sorted(records,key=lambda r:(r['timestamp'],r['id']));cells={};buy=Decimal(0);sell=Decimal(0);notional=Decimal(0);delta=Decimal(0);minimum=Decimal(0);maximum=Decimal(0)
  for r in records:
   price=Decimal(r['price']);quantity=Decimal(r['quantity']);level=(price/step).to_integral_value(rounding=ROUND_FLOOR)*step;cell=cells.setdefault(level,{'buy':Decimal(0),'sell':Decimal(0),'buy_quote':Decimal(0),'sell_quote':Decimal(0),'prints':0})
   cell[r['side']]+=quantity;cell[r['side']+'_quote']+=price*quantity;cell['prints']+=1;notional+=price*quantity
   if r['side']=='buy':buy+=quantity;delta+=quantity
   else:sell+=quantity;delta-=quantity
   minimum=min(minimum,delta);maximum=max(maximum,delta)
  poc=max(cells,key=lambda p:cells[p]['buy']+cells[p]['sell']);volume=buy+sell;rows=[]
  for level,cell in sorted(cells.items(),reverse=True):rows.append({'price':str(level),**{k:str(v) if isinstance(v,Decimal) else v for k,v in cell.items()},'delta':str(cell['buy']-cell['sell']),'volume':str(cell['buy']+cell['sell']),'poc':level==poc})
  prices=[Decimal(r['price']) for r in records];forming=stamp+duration>now;complete=not forming and sample['observed_from']<=stamp and sample['observed_to']>=stamp+duration and sample.get('id_gaps',0)==0
  bars.append({'timestamp':stamp,'end':stamp+duration,'open':records[0]['price'],'close':records[-1]['price'],'high':str(max(prices)),'low':str(min(prices)),'buy':str(buy),'sell':str(sell),'volume':str(volume),'delta':str(buy-sell),'notional':str(notional),'vwap':str(notional/volume),'prints':len(records),'avg_size':str(volume/len(records)),'min_delta':str(minimum),'max_delta':str(maximum),'poc':str(poc),'forming':forming,'complete':complete,'rows':rows})
 return {'bars':bars,'row_size':str(step)}

def footprint(coin_id='bitcoin',venue='perp',interval='1m',row_size='auto'):
 if not isinstance(venue,str) or not isinstance(interval,str) or venue not in ('spot','perp') or interval not in INTERVALS:raise ValueError('Choose spot/perpetual and 1m, 5m, 15m or 1h')
 if str(row_size) not in ('auto','0.1','0.5','1','5','10','25','50','100'):raise ValueError('Unsupported footprint row size')
 coin,base=identity(coin_id);context={'coin_id':coin,'base_currency':base,'quote_currency':'USDT','pair':base+'USDT','venue':venue,'interval':interval,'source':'Binance Spot' if venue=='spot' else 'Binance USDT Perpetual'}
 def load():
  sample=raw_trades(coin,base,venue)
  if sample.get('stale'):raise ValueError('Executed-trade provider refresh unavailable')
  result=aggregate(sample,interval,str(row_size))
  return dict(context,available=True,**result,observed_from=sample['observed_from'],observed_to=sample['observed_to'],sample_size=len(sample['trades']),id_gaps=sample['id_gaps'],pages=sample['pages'],coverage='Executed aggregate-trade sample, up to 6,000 records across six pages. Bid column = taker sells; ask column = taker buys. Counts and average size refer to aggregate prints, not individual fills. Incomplete boundary/forming bars are marked. Gaps are not filled; no candle volume is allocated to invented price levels. USDT is not USD. This is not a complete historical footprint archive.')
 try:return market.cached(('fundamentals','footprint-view-v1',coin,venue,interval,str(row_size)),30,load)
 except ValueError as e:return dict(context,available=False,message=str(e)+' Spot and perpetual feeds are separate; switch market or retry.',bars=[])


def top_traders(coin_id='bitcoin',period='1h'):
 if not isinstance(period,str) or period not in PERIODS:raise ValueError('Choose 5m, 15m, 1h, 4h or 1d')
 coin,base=identity(coin_id);pair=base+'USDT';feeds={}
 for kind,path in [('accounts','topLongShortAccountRatio'),('positions','topLongShortPositionRatio')]:
  def load(path=path):
   product(base,'perp');headers={'X-MBX-APIKEY':os.environ['BINANCE_MARKET_DATA_API_KEY']} if os.environ.get('BINANCE_MARKET_DATA_API_KEY') else None
   rows=providers.request_json('https://fapi.binance.com/futures/data/'+path+'?'+urlencode({'symbol':pair,'period':period,'limit':30}),headers=headers)
   if not isinstance(rows,list) or not 1<=len(rows)<=30:raise ValueError('Invalid top-trader response')
   points={};now=int(time.time()*1000)
   for r in rows:
    if not isinstance(r,dict) or r.get('symbol')!=pair or type(r.get('timestamp')) is not int or not now-31*86400000<=r['timestamp']<=now+60000:raise ValueError('Top-trader identity or timestamp mismatch')
    long=market.numeric(r.get('longAccount'));short=market.numeric(r.get('shortAccount'));declared=market.numeric(r.get('longShortRatio'))
    if None in (long,short,declared):raise ValueError('Invalid top-trader fractions')
    l,s,d=map(Decimal,(long,short,declared))
    if not 0<=l<=1 or not 0<s<=1 or abs(l+s-1)>Decimal('.002') or abs(l/s-d)>Decimal('.02'):raise ValueError('Inconsistent top-trader fractions')
    point={'timestamp':r['timestamp'],'long_fraction':str(l),'short_fraction':str(s),'ratio':str(d)}
    if r['timestamp'] in points and points[r['timestamp']]!=point:raise ValueError('Conflicting top-trader observations')
    points[r['timestamp']]=point
   history=[points[t] for t in sorted(points)]
   if now-history[-1]['timestamp']>(PERIODS[period]*2+300)*1000:raise ValueError('Top-trader observation is outdated')
   return {'history':history,'latest':history[-1],'source':'Binance USDT Perpetual'}
  try:feeds[kind]=dict(market.cached(('fundamentals','top-traders-v1',kind,coin,period),60,load),available=True)
  except ValueError:feeds[kind]={'available':False,'message':'Binance top-trader feed unavailable. Regional restrictions, rate limits or an API-key requirement may apply. No ratio is estimated.'}
 return {'coin_id':coin,'pair':pair,'period':period,**feeds,'coverage':'Binance top 20% users by margin balance. Accounts count each net-long/net-short account once; positions measure the groupâ€™s reported net-long/net-short position proportions. These are distinct cohorts/metrics, not named traders, all-market exposure or a prediction. Up to 30 observations per feed; no missing intervals are interpolated.'}


def candle_history(coin_id='bitcoin',venue='perp',days='30'):
 if not isinstance(venue,str) or venue not in ('spot','perp'):raise ValueError('Unsupported footprint market')
 if str(days) not in ('1','7','30','365','max'):raise ValueError('Unsupported footprint history range')
 coin,base=identity(coin_id);days=str(days)
 interval={'1':'1m','7':'15m','30':'1h','365':'1d','max':'1w'}[days]
 seconds=exchange.INTERVALS[interval]
 def load():
  meta=product(base,venue);now=int(time.time());start=0 if days=='max' else now-int(days)*86400
  root='https://data-api.binance.vision/api/v3/klines' if venue=='spot' else 'https://fapi.binance.com/fapi/v1/klines'
  points={};cursor=start*1000;done=False
  for page in range(6):
   rows=providers.request_json(root+'?'+urlencode({'symbol':meta['pair'],'interval':interval,'startTime':cursor,'endTime':now*1000,'limit':1000}))
   if not isinstance(rows,list) or len(rows)>1000:raise ValueError('Invalid historical candle response')
   for row in rows:
    point=exchange.candle(row,'binance',cursor,now*1000+60000)
    if point is None or any(Decimal(point[k])<=0 for k in ('open','high','low','close')):raise ValueError('Invalid historical OHLC candle')
    points[point['timestamp']]=point
   if len(rows)<1000:done=True;break
   next_cursor=max(points)+seconds*1000
   if next_cursor<=cursor:raise ValueError('Historical candle pagination did not advance')
   cursor=next_cursor
   if cursor>now*1000:done=True;break
  if not done:raise ValueError('History exceeds the bounded candle window')
  candles=[points[k] for k in sorted(points)]
  if not candles:raise ValueError('No historical candles available')
  return {'available':True,'candles':candles,'interval':interval,'venue':venue,'pair':meta['pair'],'source':meta['source'],'coverage':'Available '+meta['source']+' '+meta['pair']+' '+interval+' candles. Exchange-pair history only; historical bid/ask footprints are not available. Latest candle may be forming.'}
 return market.cached(('chart','footprint-history-v1',coin,venue,days),60 if days=='1' else 300,load)
