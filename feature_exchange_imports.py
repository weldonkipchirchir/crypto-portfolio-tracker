"""Bounded historical Binance Spot fills, always reviewed before ledger import."""
import hashlib,hmac,json,re,time,urllib.request
from urllib.parse import urlencode
from decimal import Decimal
import exchange_connections as ex
import exchange_trade_imports as fills

def cursor(value):
 if not isinstance(value,str) or not re.fullmatch(r'0|[1-9][0-9]{0,18}',value) or int(value)>9223372036854775806:
  raise ValueError('Enter a trade ID from 0 to 9223372036854775806')
 return int(value)

def fetch(credentials,pair,start):
 params={'symbol':pair,'fromId':start,'limit':1000,'timestamp':int(time.time()*1000),'recvWindow':5000}
 query=urlencode(params);signature=hmac.new(credentials['api_secret'].encode(),query.encode(),hashlib.sha256).hexdigest()
 request=urllib.request.Request('https://api.binance.com/api/v3/myTrades?'+query+'&signature='+signature,headers={'X-MBX-APIKEY':credentials['api_key'],'User-Agent':'OrbitPortfolio/1.0'})
 cutoff=getattr(ex.providers._REQUEST_CONTEXT,'cutoff',None);timeout=min(10,cutoff-time.monotonic()) if cutoff else 10
 if timeout<=0:raise ValueError('Exchange request deadline reached')
 try:
  with urllib.request.build_opener(ex.NoRedirect).open(request,timeout=max(.1,timeout)) as response:body=response.read(2*1024*1024+1)
  if len(body)>2*1024*1024:raise ValueError()
  rows=json.loads(body)
 except Exception:raise ValueError('Binance history is unavailable. Check connection permissions, region, rate limits and server clock.') from None
 if not isinstance(rows,list) or len(rows)>1000:raise ValueError('Invalid Binance history response')
 return rows

def read(c,uid,raw):
 if raw.get('operation')!='preview':
  return {'connections':[{'id':r['id'],'label':r['label']} for r in c.execute('SELECT id,label FROM exchange_connections WHERE user_id=? ORDER BY label,id',(uid,))]}
 identity=ex.identity(raw);pair=str(raw.get('pair','')).strip().upper()
 if not re.fullmatch(r'[A-Z0-9]{1,26}USDT',pair):raise ValueError('Enter a USDT Spot pair such as BTCUSDT')
 start=cursor(raw.get('from_id','0'));rate=fills.amount(raw.get('usdt_usd_rate'),True)
 if not Decimal('.5')<=rate<=Decimal('2'):raise ValueError('USD per USDT must be between 0.5 and 2')
 row=c.execute('SELECT credentials FROM exchange_connections WHERE user_id=? AND id=?',(uid,identity)).fetchone()
 if not row:raise ValueError('Exchange connection not found')
 rows=fetch(ex.crypt(uid,identity,row['credentials'],True),pair,start)
 last=start-1
 for item in rows:
  if not isinstance(item,dict) or type(item.get('id')) is not int or not start<=item['id']<=9223372036854775806 or item['id']<=last:raise ValueError('Binance returned unordered or repeated trade IDs')
  last=item['id']
 csv=fills.normalize(rows,pair,rate,'Binance API '+identity)
 return {'csv':csv,'count':len(rows),'pair':pair,'from_id':str(start),'next_from_id':str(last+1) if rows and last<9223372036854775806 else None,'at_limit':len(rows)==1000,'first_time':rows[0]['time'] if rows else None,'last_time':rows[-1]['time'] if rows else None,'coverage':'One page of up to 1,000 Spot fills for this pair, starting at the supplied trade ID. Start at 0 for older available history. A short page does not guarantee complete exchange history. Transfers, deposits, withdrawals, Earn and other pairs are excluded. USD prices and USDT fees use your supplied conversion rate, not historical FX. Non-USDT fees require manual valuation. Review overlaps before importing.'}

# Activity endpoints are a separate read-only timeline, never trade CSV.
import csv as csv_module,io
from datetime import datetime,timezone
ACTIVITY_PATHS={
 'deposits':'/sapi/v1/capital/deposit/hisrec',
 'withdrawals':'/sapi/v1/capital/withdraw/history',
 'flexible_rewards':'/sapi/v1/simple-earn/flexible/history/rewardsRecord',
 'locked_rewards':'/sapi/v1/simple-earn/locked/history/rewardsRecord'}
ACTIVITY_FIELDS=('datetime_utc','activity','asset','amount_native','fee_native','fee_asset','status','status_code','txid','source','reference','reward_type')
DEPOSIT_STATUS={0:'Pending',1:'Success',2:'Rejected',6:'Credited; withdrawal restricted',7:'Wrong deposit',8:'Awaiting user confirmation'}
WITHDRAWAL_STATUS={0:'Email sent',2:'Awaiting approval',3:'Rejected',4:'Processing',6:'Completed'}

def activity_window(raw,kind):
 values=[]
 for key in ('start_utc','end_utc'):
  value=raw.get(key)
  if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}',value):raise ValueError('Choose explicit start and end times in UTC')
  try:values.append(int(datetime.strptime(value,'%Y-%m-%dT%H:%M').replace(tzinfo=timezone.utc).timestamp()*1000))
  except ValueError:raise ValueError('Invalid activity date') from None
 start,end=values;now=int(time.time()*1000);day=86400000
 if not now-90*day<=start<end<=now:raise ValueError('Activity dates must be within the last 90 days and end after start')
 if end-start>=90*day:raise ValueError('Choose an activity window shorter than 90 days')
 if kind.endswith('_rewards') and end-start>30*day:raise ValueError('Earn reward windows must be at most 30 days')
 return start,end

def activity_fetch(credentials,kind,start,end,page=1):
 if kind not in ACTIVITY_PATHS:raise ValueError('Unsupported exchange activity')
 params={'startTime':start,'endTime':end,'timestamp':int(time.time()*1000),'recvWindow':5000}
 if kind.endswith('_rewards'):
  if type(page) is not int or not 1<=page<=10:raise ValueError('Choose reward page 1 to 10')
  params.update(current=page,size=100)
  if kind=='flexible_rewards':params['type']='ALL'
 else:params.update(offset=0,limit=1000)
 query=urlencode(params);signature=hmac.new(credentials['api_secret'].encode(),query.encode(),hashlib.sha256).hexdigest()
 request=urllib.request.Request('https://api.binance.com'+ACTIVITY_PATHS[kind]+'?'+query+'&signature='+signature,headers={'X-MBX-APIKEY':credentials['api_key'],'User-Agent':'OrbitPortfolio/1.0'},method='GET')
 cutoff=getattr(ex.providers._REQUEST_CONTEXT,'cutoff',None);timeout=min(10,cutoff-time.monotonic()) if cutoff else 10
 if timeout<=0:raise ValueError('Exchange request deadline reached')
 try:
  with urllib.request.build_opener(ex.NoRedirect).open(request,timeout=max(.1,timeout)) as response:body=response.read(2*1024*1024+1)
  if len(body)>2*1024*1024:raise ValueError()
  result=json.loads(body)
 except Exception:raise ValueError('Binance activity unavailable. Check read permissions, IP restrictions, region or rate limits. Credentials were not changed.') from None
 if kind.endswith('_rewards'):
  if not isinstance(result,dict) or 'code' in result or type(result.get('total')) is not int or not 0<=result['total']<=1000000000:raise ValueError('Invalid Binance reward response')
  rows=result.get('rows');total=result['total']
 else:rows=result;total=None
 limit=100 if kind.endswith('_rewards') else 1000
 if not isinstance(rows,list) or len(rows)>limit:raise ValueError('Invalid Binance activity response')
 if total is not None and total<(page-1)*limit+len(rows) and rows:raise ValueError('Inconsistent Binance reward count')
 return rows,total

def activity_text(value,limit=256,optional=False):
 if optional and value in (None,''):return ''
 if type(value) is int:value=str(value)
 if not isinstance(value,str) or not 1<=len(value)<=limit or any(ord(ch)<32 or ord(ch)==127 for ch in value):raise ValueError('Invalid Binance activity text')
 return value

def native_amount(value):
 # Decimal bounds reject NaN, infinities, exponent bombs and rounded floats.
 if not isinstance(value,str) or not re.fullmatch(r'[0-9]{1,31}(?:\.[0-9]{1,30})?',value):raise ValueError('Invalid Binance native asset amount')
 fills.amount(value)
 return value

def normalize_activity(rows,kind,start,end):
 events=[]
 for row in rows:
  if not isinstance(row,dict):raise ValueError('Invalid Binance activity row')
  reward=kind.endswith('_rewards');asset=activity_text(row.get('asset' if reward else 'coin'),64)
  if not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}',asset):raise ValueError('Invalid Binance activity asset')
  amount=native_amount(row.get('rewards' if kind=='flexible_rewards' else 'amount'))
  if kind=='withdrawals':
   date=activity_text(row.get('applyTime'),19)
   try:stamp=int(datetime.strptime(date,'%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()*1000)
   except ValueError:raise ValueError('Invalid Binance withdrawal UTC time') from None
  else:stamp=row.get('time' if reward else 'insertTime')
  if type(stamp) is not int or not start<=stamp<=end:raise ValueError('Activity timestamp is outside the requested window')
  code=row.get('status') if not reward else None
  if not reward and (type(code) is not int or not 0<=code<=10000):raise ValueError('Invalid Binance activity status')
  status='Recorded reward (settlement status not supplied)' if reward else (DEPOSIT_STATUS if kind=='deposits' else WITHDRAWAL_STATUS).get(code,'Unknown exchange status '+str(code))
  fee=native_amount(row.get('transactionFee')) if kind=='withdrawals' else ''
  event=dict(datetime_utc=datetime.fromtimestamp(stamp/1000,timezone.utc).isoformat(),activity='reward' if reward else kind[:-1],asset=asset,amount_native=amount,fee_native=fee,fee_asset=asset if fee!='' else '',status=status,status_code=str(code) if code is not None else '',txid=activity_text(row.get('txId'),512,True) if not reward else '',source='Binance Simple Earn '+('Flexible' if kind=='flexible_rewards' else 'Locked') if reward else 'Binance '+kind,reference=activity_text(row.get('projectId' if kind=='flexible_rewards' else 'positionId' if reward else 'id'),128,True),reward_type=activity_text(row.get('type'),80,True) if reward else '')
  events.append(event)
 events.sort(key=lambda item:item['datetime_utc'],reverse=True)
 return events

def activity_csv(events):
 out=io.StringIO();writer=csv_module.writer(out);writer.writerow(ACTIVITY_FIELDS)
 # Preserve exact JSON values; neutralize spreadsheet formula prefixes in CSV.
 for event in events:writer.writerow(["'"+str(event[key]) if str(event[key]).startswith(('=','+','-','@')) else event[key] for key in ACTIVITY_FIELDS])
 return out.getvalue()

_fills_read=read
def read(c,uid,raw):
 if raw.get('operation')!='activity':return _fills_read(c,uid,raw)
 kind=raw.get('activity')
 if not isinstance(kind,str) or kind not in ACTIVITY_PATHS:raise ValueError('Choose deposits, withdrawals, Flexible rewards or Locked rewards')
 identity=ex.identity(raw);start,end=activity_window(raw,kind)
 page=raw.get('page','1')
 if not isinstance(page,str) or not re.fullmatch(r'[1-9]|10',page):raise ValueError('Choose reward page 1 to 10')
 page=int(page)
 if not kind.endswith('_rewards') and page!=1:raise ValueError('Deposits and withdrawals use one page; narrow the date window')
 row=c.execute('SELECT credentials FROM exchange_connections WHERE user_id=? AND id=?',(uid,identity)).fetchone()
 if not row:raise ValueError('Exchange connection not found')
 rows,total=activity_fetch(ex.crypt(uid,identity,row['credentials'],True),kind,start,end,page)
 events=normalize_activity(rows,kind,start,end);limit=100 if kind.endswith('_rewards') else 1000
 return dict(activity=kind,events=events,csv=activity_csv(events),count=len(events),page=page,total=total,at_limit=len(events)==limit,more_available=(page*limit<total) if total is not None else len(events)==limit,next_page=str(page+1) if total is not None and page*limit<total and page<10 else None,coverage='Observed read-only activity only; no ledger or profit/loss changes. Deposits are not automatically income, withdrawals are not automatically sales. Rewards exclude subscriptions and redemptions of Earn principal. Native asset amounts only; blank fees mean not supplied, not zero. Withdrawal time is request time (UTC); deposit time is exchange insertion time. One request, one account, one activity, one page. Deposit/withdrawal cap: 1,000; reward cap: 100 per page, pages 1–10 (1,000 maximum per window). A short page does not guarantee complete history. Narrow the date window if truncated. No USD valuation or tax classification is inferred.')
