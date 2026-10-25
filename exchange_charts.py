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
 return dict(timestamp=int(stamp),**dict(zip(('open','high','low','close'),values)))

def chart(coin_id,days,kind='line',source='binance'):
 if not isinstance(source,str) or source not in ROOTS:raise ValueError('Unsupported exchange chart provider')
 if isinstance(days,bool) or str(days) not in ('1','7','30','90','365','max'):raise ValueError('Unsupported chart range')
 if kind not in ('line','candles'):raise ValueError('Unsupported chart type')
 identity=market.identifier(coin_id)
 if identity not in ASSETS:raise ValueError('This coin has no verified exchange product mapping; select CoinGecko')
 market.allowed(identity)
 requested='max' if days=='max' else int(days)
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
  if source=='binance':
   interval='1w' if requested=='max' else '30m' if requested==1 else '4h' if requested in (7,30) else '1d'
   start=0 if requested=='max' else now-requested*86400
   rows=providers.request_json(ROOTS[source]+'/api/v3/klines?'+urlencode({'symbol':pair,'interval':interval,'startTime':start*1000,'endTime':now*1000,'limit':1000}))
   if isinstance(rows,list) and len(rows)==1000:raise ValueError('Exchange history exceeds bounded response; complete ALL history cannot be confirmed')
   collect(rows,max(1230768000,start-7*86400 if interval=='1w' else start),now+60);chunks=1
   granularity={'1w':'weekly','30m':'30-minute','4h':'4-hour','1d':'daily'}[interval]
  else:
   interval=3600 if requested==1 else 21600 if requested in (7,30) else 86400
   start=COINBASE_START if requested=='max' else now-requested*86400
   # Never return a partially fetched ALL response as complete.
   required=(now-start+interval*299-1)//(interval*299)
   if required>MAX_CHUNKS:raise ValueError('Requested history exceeds the bounded Coinbase history window')
   cursor=start
   while cursor<now:
    end=min(now,cursor+interval*299)
    rows=providers.request_json(ROOTS[source]+'/products/'+pair+'/candles?'+urlencode({'granularity':interval,'start':iso(cursor),'end':iso(end)}))
    collect(rows,cursor,end);cursor=end;chunks+=1
   granularity={3600:'hourly',21600:'6-hour',86400:'daily'}[interval]
  ordered=[points[t] for t in sorted(points)]
  if len(ordered)<2:raise ValueError('Not enough valid exchange historical candles')
  if len(ordered)>5000:raise ValueError('Exchange history exceeds bounded point limit')
  coverage=(('ALL queries available '+pair+' history from '+('the earliest exchange candles' if source=='binance' else '2015-01-01')+'; all requested pages completed. ') if requested=='max' else '')
  coverage+=source.title()+' '+pair+' spot '+granularity+' OHLC; '+quote+' quote units'+(' (USDT is not USD)' if quote=='USDT' else '')+'. Timestamps are bucket open times; the latest candle may still be forming. Missing trade buckets are not filled. Exchange-pair history is not the full history of the coin.'
  return {'coin_id':identity,'days':requested,'kind':kind,'chart_type':kind,'source':('Binance' if source=='binance' else 'Coinbase Exchange'),'pair':pair,'quote_currency':quote,'base_currency':base,'interval':granularity,'history_start_requested':start*1000,'observed_from':ordered[0]['timestamp'],'observed_to':ordered[-1]['timestamp'],'complete_request':True,'request_chunks':chunks,'coverage':coverage,('candles' if kind=='candles' else 'points'):(ordered if kind=='candles' else [{'timestamp':p['timestamp'],'price':p['close']} for p in ordered])}
 return market.cached(('chart','exchange',source,identity,requested,kind),300,load)
