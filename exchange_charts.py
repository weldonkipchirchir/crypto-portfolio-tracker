"""Read-only venue charts with curated CoinGecko IDs and explicit quote units."""
import datetime,time
from decimal import Decimal
from urllib.parse import urlencode
import coin_market as market
import providers

# Deliberate identity mapping, never inferred from a portfolio ticker or token contract.
ASSETS={'bitcoin':'BTC','ethereum':'ETH','solana':'SOL','ripple':'XRP','cardano':'ADA','dogecoin':'DOGE','avalanche-2':'AVAX','chainlink':'LINK','aave':'AAVE','litecoin':'LTC','bitcoin-cash':'BCH','stellar':'XLM','polkadot':'DOT','uniswap':'UNI','near':'NEAR','cosmos':'ATOM','sui':'SUI','aptos':'APT','optimism':'OP','arbitrum':'ARB'}
ROOTS={'binance':'https://data-api.binance.vision','coinbase':'https://api.exchange.coinbase.com'}
COINBASE_START=1420070400 # 2015-01-01, before the Coinbase Exchange launch.
MAX_CHUNKS=16
INTERVALS={'15m':900,'1h':3600,'4h':14400,'1d':86400,'1w':604800}
INTERVAL_LABELS={'15m':'15-minute','1h':'hourly','4h':'4-hour','1d':'daily','1w':'weekly'}

def iso(seconds):return datetime.datetime.fromtimestamp(seconds,datetime.timezone.utc).isoformat().replace('+00:00','Z')

def metadata(source,pair,base,quote):
 def load():
  path='/api/v3/exchangeInfo?'+urlencode({'symbol':pair}) if source=='binance' else '/products/'+pair
  payload=providers.request_json(ROOTS[source]+path)
  if source=='binance':
   rows=payload.get('symbols') if isinstance(payload,dict) else None
   if not isinstance(rows,list) or len(rows)!=1:raise ValueError('Exchange product unavailable')
   item=rows[0]
   valid=isinstance(item,dict) and item.get('symbol')==pair and item.get('baseAsset')==base and item.get('quoteAsset')==quote
  else:valid=isinstance(payload,dict) and payload.get('id')==pair and payload.get('base_currency')==base and payload.get('quote_currency')==quote
  if not valid:raise ValueError('Exchange product identity mismatch')
  return {'source':source,'pair':pair,'base_currency':base,'quote_currency':quote}
 return market.cached(('chart','exchange-meta',source,pair),86400,load)

def candle(row,source,minimum,maximum):
 if not isinstance(row,list) or len(row)!=(12 if source=='binance' else 6):return None
 ts=market.numeric(row[0])
 values=[market.numeric(row[i]) for i in ((1,2,3,4) if source=='binance' else (3,2,1,4))]
 if ts is None or any(v is None for v in values):return None
 stamp=Decimal(ts)*(1 if source=='binance' else 1000)
 if stamp!=stamp.to_integral_value() or not minimum<=stamp<=maximum:return None
 opening,high,low,closing=map(Decimal,values)
 if low>high or not low<=opening<=high or not low<=closing<=high:return None
 result=dict(timestamp=int(stamp),**dict(zip(('open','high','low','close'),values)))
 volume=market.numeric(row[5])
 if volume is not None:result['volume']=volume
 return result

def chart(coin_id,days,kind='line',source='binance',interval=None):
 if not isinstance(source,str) or source not in ROOTS:raise ValueError('Unsupported exchange chart provider')
 if isinstance(days,bool) or str(days) not in ('1','7','30','90','365','max'):raise ValueError('Unsupported chart range')
 if kind not in ('line','candles'):raise ValueError('Unsupported chart type')
 if interval is not None and (not isinstance(interval,str) or interval not in INTERVALS):raise ValueError('Unsupported candle interval')
 identity=market.identifier(coin_id)
 if identity not in ASSETS:raise ValueError('This coin has no verified exchange product mapping; select CoinGecko')
 market.allowed(identity)
 requested='max' if days=='max' else int(days)
 if interval is not None:
  now=int(time.time());seconds=INTERVALS[interval]
  start=(1502928000 if source=='binance' else COINBASE_START) if requested=='max' else bucket_start(now-requested*86400,seconds)
  base_seconds=3600 if source=='coinbase' and interval=='4h' else 86400 if source=='coinbase' and interval=='1w' else seconds
  if (now-start)//base_seconds+1>(6000 if source=='binance' else MAX_CHUNKS*299):raise ValueError('This interval needs too many candles; choose a shorter range or larger interval')
 base=ASSETS[identity];quote='USDT' if source=='binance' else 'USD';pair=base+quote if source=='binance' else base+'-'+quote
 def load():
  meta=metadata(source,pair,base,quote)
  if meta.get('stale'):raise ValueError('Fresh exchange identity verification unavailable')
  now=int(time.time());points={};chunks=0
  def collect(rows,lo,hi):
   if not isinstance(rows,list) or len(rows)>(1000 if source=='binance' else 300):raise ValueError('Invalid exchange candle response')
   for row in rows:
    point=candle(row,source,lo*1000,min(hi*1000,now*1000+60000))
    if point and point['timestamp'] not in points:points[point['timestamp']]=point
  if interval is not None:
   return explicit_chart(identity,requested,kind,source,pair,base,quote,interval,now)
  if source=='binance':
   auto_interval='1w' if requested=='max' else '30m' if requested==1 else '4h' if requested in (7,30) else '1d'
   start=0 if requested=='max' else now-requested*86400
   rows=providers.request_json(ROOTS[source]+'/api/v3/klines?'+urlencode({'symbol':pair,'interval':auto_interval,'startTime':start*1000,'endTime':now*1000,'limit':1000}))
   if isinstance(rows,list) and len(rows)==1000:raise ValueError('Exchange history exceeds bounded response; complete ALL history cannot be confirmed')
   collect(rows,max(1230768000,start-7*86400 if auto_interval=='1w' else start),now+60);chunks=1
   granularity={'1w':'weekly','30m':'30-minute','4h':'4-hour','1d':'daily'}[auto_interval]
  else:
   auto_interval=3600 if requested==1 else 21600 if requested in (7,30) else 86400
   start=COINBASE_START if requested=='max' else now-requested*86400
   # Never return a partially fetched ALL response as complete.
   required=(now-start+auto_interval*299-1)//(auto_interval*299)
   if required>MAX_CHUNKS:raise ValueError('Requested history exceeds the bounded Coinbase history window')
   cursor=start
   while cursor<now:
    end=min(now,cursor+auto_interval*299)
    rows=providers.request_json(ROOTS[source]+'/products/'+pair+'/candles?'+urlencode({'granularity':auto_interval,'start':iso(cursor),'end':iso(end)}))
    collect(rows,cursor,end);cursor=end;chunks+=1
   granularity={3600:'hourly',21600:'6-hour',86400:'daily'}[auto_interval]
  ordered=[points[t] for t in sorted(points)]
  if len(ordered)<2:raise ValueError('Not enough valid exchange historical candles')
  if len(ordered)>5000:raise ValueError('Exchange history exceeds bounded point limit')
  coverage=(('ALL queries available '+pair+' history from '+('the earliest exchange candles' if source=='binance' else '2015-01-01')+'; all requested pages completed. ') if requested=='max' else '')
  coverage+=source.title()+' '+pair+' spot '+granularity+' OHLC; '+quote+' quote units'+(' (USDT is not USD)' if quote=='USDT' else '')+'. Timestamps are bucket open times; the latest candle may still be forming. Missing trade buckets are not filled. Exchange-pair history is not the full history of the coin.'
  return {'coin_id':identity,'days':requested,'kind':kind,'chart_type':kind,'source':('Binance' if source=='binance' else 'Coinbase Exchange'),'pair':pair,'quote_currency':quote,'base_currency':base,'interval':granularity,'interval_code':auto_interval if source=='binance' else {3600:'1h',21600:'6h',86400:'1d'}[auto_interval],'interval_seconds':{'1w':604800,'30m':1800,'4h':14400,'1d':86400}[auto_interval] if source=='binance' else auto_interval,'history_start_requested':start*1000,'observed_from':ordered[0]['timestamp'],'observed_to':ordered[-1]['timestamp'],'complete_request':True,'request_chunks':chunks,'coverage':coverage,('candles' if kind=='candles' else 'points'):(ordered if kind=='candles' else [{'timestamp':p['timestamp'],'price':p['close']} for p in ordered])}
 return market.cached(('chart','exchange',source,identity,requested,kind)+((interval,) if interval is not None else ()),300,load)


def bucket_start(stamp,seconds):
 # Weekly exchange bars open Monday 00:00 UTC, rather than epoch Thursday.
 anchor=345600 if seconds==604800 else 0
 return (stamp-anchor)//seconds*seconds+anchor


def aggregate(points,seconds,base_seconds,now):
 """Only complete, consecutive UTC buckets; never fabricate missing trades."""
 groups={}
 for point in points:
  stamp=point['timestamp']//1000
  if stamp%base_seconds:continue
  groups.setdefault(bucket_start(stamp,seconds),{})[stamp]=point
 result=[];omitted=0
 for start,group in sorted(groups.items()):
  required=list(range(start,start+seconds,base_seconds))
  if start+seconds>now or any(t not in group for t in required):
   omitted+=1;continue
  ordered=[group[t] for t in required]
  combined={'timestamp':start*1000,'open':ordered[0]['open'],'high':str(max(Decimal(p['high']) for p in ordered)),'low':str(min(Decimal(p['low']) for p in ordered)),'close':ordered[-1]['close']}
  if all(p.get('volume') is not None for p in ordered):combined['volume']=str(sum(Decimal(p['volume']) for p in ordered))
  result.append(combined)
 return result,omitted


def explicit_chart(identity,requested,kind,source,pair,base,quote,interval,now):
 seconds=INTERVALS[interval]
 start=(0 if source=='binance' else COINBASE_START) if requested=='max' else now-requested*86400
 if requested!='max':start=bucket_start(start,seconds)
 points={};chunks=0;omitted=0
 def collect(rows,lo,hi,limit):
  if not isinstance(rows,list) or len(rows)>limit:raise ValueError('Invalid exchange candle response')
  for row in rows:
   point=candle(row,source,lo*1000,min(hi*1000,now*1000))
   if point:points.setdefault(point['timestamp'],point)
 if source=='binance':
  # A whole ALL request must fit the bounded six-page budget, including launch-era history.
  earliest=1502928000 if requested=='max' else start
  if (now-earliest)//seconds+1>6000:raise ValueError('This interval needs too many candles; choose a shorter range or larger interval')
  cursor=start*1000
  while cursor<=now*1000:
   rows=providers.request_json(ROOTS[source]+'/api/v3/klines?'+urlencode({'symbol':pair,'interval':interval,'startTime':cursor,'endTime':now*1000,'limit':1000}))
   collect(rows,cursor//1000,now,1000);chunks+=1
   if len(rows)<1000:break
   stamps=[p['timestamp'] for p in points.values() if p['timestamp']>=cursor]
   if not stamps or max(stamps)+seconds*1000<=cursor:raise ValueError('Exchange candle pagination did not advance')
   cursor=max(stamps)+seconds*1000
   if chunks>=6 and cursor<=now*1000:raise ValueError('Exchange history exceeds bounded candle limit')
  ordered=[points[t] for t in sorted(points) if points[t]['timestamp']%(seconds*1000)==(345600000 if interval=='1w' else 0)]
 else:
  base_seconds=3600 if interval=='4h' else 86400 if interval=='1w' else seconds
  required=(now-start+base_seconds*299-1)//(base_seconds*299)
  if required>MAX_CHUNKS:raise ValueError('This interval needs too many candles; choose a shorter range or larger interval')
  cursor=start
  while cursor<now:
   end=min(now,cursor+base_seconds*299)
   rows=providers.request_json(ROOTS[source]+'/products/'+pair+'/candles?'+urlencode({'granularity':base_seconds,'start':iso(cursor),'end':iso(end)}))
   collect(rows,cursor,end,300);chunks+=1;cursor=end
  ordered=[points[t] for t in sorted(points) if t%(base_seconds*1000)==0]
  if seconds!=base_seconds:ordered,omitted=aggregate(ordered,seconds,base_seconds,now)
 if len(ordered)<2:raise ValueError('Not enough complete exchange candles; choose a longer range or smaller interval')
 if len(ordered)>6000:raise ValueError('Exchange history exceeds bounded candle limit')
 coverage=source.title()+' '+pair+' spot '+INTERVAL_LABELS[interval]+' OHLC; '+quote+' quote units'+(' (USDT is not USD)' if quote=='USDT' else '')+'. UTC bucket open times. Missing trade buckets are not filled. '
 if source=='coinbase' and interval in ('4h','1w'):coverage+='Aggregated from consecutive '+('hourly' if interval=='4h' else 'daily')+' exchange candles; incomplete and still-forming buckets omitted ('+str(omitted)+'). '
 else:coverage+='Latest candle may still be forming. '
 coverage+='All requested pages completed; exchange-pair history is not the full history of the coin.'
 return {'coin_id':identity,'days':requested,'kind':kind,'chart_type':kind,'source':'Binance' if source=='binance' else 'Coinbase Exchange','pair':pair,'quote_currency':quote,'base_currency':base,'interval':INTERVAL_LABELS[interval],'interval_code':interval,'interval_seconds':seconds,'history_start_requested':start*1000,'observed_from':ordered[0]['timestamp'],'observed_to':ordered[-1]['timestamp'],'complete_request':True,'request_chunks':chunks,'omitted_buckets':omitted,'coverage':coverage,('candles' if kind=='candles' else 'points'):ordered if kind=='candles' else [{'timestamp':p['timestamp'],'price':p['close']} for p in ordered]}
