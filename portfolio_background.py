"""Daily price valuations of saved balances. No session or exchange key decryption."""
import copy,hmac,json,os,re,secrets,time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from decimal import Decimal,localcontext
import providers,portfolio_daily,token_pricing,coin_market,exchange_connections
PATH='/api/cron/portfolio-daily'
SCHEDULE='0 23 * * *'

def authorized(headers):
 secret=os.environ.get('CRON_SECRET','')
 return bool(re.fullmatch(r'[A-Za-z0-9_-]{32,256}',secret) and hmac.compare_digest(str(headers.get('Authorization','')).encode(),('Bearer '+secret).encode()))

def init(c):
 c.execute('CREATE TABLE IF NOT EXISTS portfolio_tracking (user_id INTEGER PRIMARY KEY,enabled INTEGER NOT NULL,last_day TEXT,last_attempt INTEGER,last_success INTEGER,error TEXT)')
 c.execute('CREATE TABLE IF NOT EXISTS portfolio_capture_runs (day TEXT PRIMARY KEY,token TEXT NOT NULL,expires INTEGER NOT NULL,completed INTEGER NOT NULL,result TEXT NOT NULL)')

def status(c,uid):
 row=c.execute('SELECT enabled,last_attempt,last_success,error FROM portfolio_tracking WHERE user_id=?',(uid,)).fetchone()
 return {'enabled':bool(row['enabled']) if row else True,'configured':os.environ.get('VERCEL')=='1' and bool(re.fullmatch(r'[A-Za-z0-9_-]{32,256}',os.environ.get('CRON_SECRET',''))),'schedule_utc':'23:00â€“23:59 UTC daily','last_attempt':row['last_attempt'] if row else None,'last_success':row['last_success'] if row else None,'error':row['error'] if row else None,'basis':'Refreshed prices Ã— last synchronized balances. No automatic balance sync or missing-day backfill.'}

def preference(c,uid,raw):
 enabled=raw.get('enabled')
 if type(enabled) is not bool:raise ValueError('Choose whether daily tracking is enabled')
 c.execute('INSERT INTO portfolio_tracking(user_id,enabled) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET enabled=EXCLUDED.enabled',(uid,int(enabled)))
 return status(c,uid)

def fresh_quote(q,now):
 try:
  price=coin_market.numeric(q.get('price'));stamp=portfolio_daily.observed_time(q.get('updated_at'))
  if price is not None and stamp and now-900<=stamp<=now+60:return {'price':price,'updated_at':stamp,'source':'CoinGecko'}
 except (ValueError,TypeError,AttributeError):pass
 return None

def valuation(wallets,exchanges,quotes,token_quotes,now):
 wallets=copy.deepcopy(wallets);exchanges=copy.deepcopy(exchanges)
 for w in wallets:
  for a in (w.get('token_snapshot') or {}).get('tokens',[]):
   identity=a.get('contract') or a.get('mint');q=token_quotes.get((w['chain'],identity))
   try:
    if not q or q.get('price_stale') or a.get('asset_id')!=w['chain']+':'+providers.validate_address(w['chain'],identity):raise ValueError()
    stamp=portfolio_daily.observed_time(q.get('price_fetched_at'))
    if not stamp or not now-900<=stamp<=now+60:raise ValueError()
    with localcontext() as ctx:
     ctx.prec=500;value=token_pricing.decimal(a.get('quantity'))*token_pricing.decimal(q.get('price_usd'),True)
    a.update(q);a['value_usd']=str(value)
   except (ValueError,TypeError):a.update(price_usd=None,value_usd=None,price_stale=True)
 by_id={providers.COINS[s]:q for s,q in quotes.items() if s in providers.COINS}
 for connection in exchanges:
  for a in (connection.get('snapshot') or {}).get('balances',[]):
   q=by_id.get(a.get('coin_id'));amount=a.get('display_quantity') if a.get('valuation_basis')=='verified_earn_underlying' else a.get('quantity') if exchange_connections.display_asset(a.get('asset'))==a.get('asset') else None
   amount=coin_market.numeric(amount)
   if not q or amount is None:a.update(value_usd=None,price_stale=True);continue
   with localcontext() as ctx:ctx.prec=160;value=Decimal(amount)*Decimal(q['price'])
   a.update(value_usd=str(value),price_usd=q['price'],price_updated_at=q['updated_at'],price_stale=False)
 row=portfolio_daily.observation(wallets,quotes,exchanges,now)
 if row:row.update(capture_reason='scheduled_prices',valuation_basis='saved_balances_refreshed_prices')
 return row

def run(connect,read_wallets,*,now=None,seconds=45,max_accounts=200):
 now=int(time.time() if now is None else now);day=datetime.fromtimestamp(now,timezone.utc).date().isoformat();cutoff=time.monotonic()+seconds;token=secrets.token_hex(16)
 with connect() as c:
  lease=c.execute('INSERT INTO portfolio_capture_runs VALUES (?,?,?,0,?) ON CONFLICT(day) DO UPDATE SET token=EXCLUDED.token,expires=EXCLUDED.expires WHERE portfolio_capture_runs.expires<=? AND portfolio_capture_runs.completed=0 RETURNING token',(day,token,now+90,'{}',now)).fetchone()
  if not lease:return {'ok':True,'status':'already_completed_or_running'}
 result={'ok':True,'day':day,'saved':0,'unpriced':0,'pending':False}
 try:
  with connect() as c:
   users=[r['id'] for r in c.execute("SELECT u.id FROM users u LEFT JOIN portfolio_tracking t ON t.user_id=u.id WHERE COALESCE(t.enabled,1)=1 AND COALESCE(t.last_day,'')<>? AND (EXISTS(SELECT 1 FROM wallets w WHERE w.user_id=u.id) OR EXISTS(SELECT 1 FROM exchange_connections e WHERE e.user_id=u.id)) ORDER BY COALESCE(t.last_success,0),u.id LIMIT ?",(day,max_accounts+1))]
   contracts=[]
   if users:
    marks=','.join('?' for _ in users[:max_accounts])
    for r in c.execute('SELECT w.chain,t.data FROM wallets w JOIN wallet_tokens t ON t.wallet_id=w.id WHERE w.user_id IN ('+marks+') ORDER BY w.id LIMIT 32',tuple(users[:max_accounts])):
     if len(r['data'])>2000000:continue
     for a in json.loads(r['data']).get('tokens',[]):
      try:
       address=providers.validate_address(r['chain'],a.get('contract') or a.get('mint'))
       if a.get('asset_id')!=r['chain']+':'+address:continue
       key=(r['chain'],address)
       if key not in contracts:contracts.append(key)
      except (ValueError,TypeError):continue
      if len(contracts)>=12:break
     if len(contracts)>=12:break
  if not users:return result
  with providers.deadline(cutoff-5):raw=providers.market_prices(list(providers.COINS))
  quotes={s:q for s,v in raw.items() if (q:=fresh_quote(v,now)) is not None}
  if not quotes:raise ValueError('Fresh prices unavailable')
  def quote(key):
   try:
    with providers.deadline(cutoff-5):return key,token_pricing.get_quote(*key)
   except Exception:return key,None
  with ThreadPoolExecutor(max_workers=4) as pool:token_quotes=dict(pool.map(quote,contracts))
  for uid in users[:max_accounts]:
   if time.monotonic()>=cutoff-3:result['pending']=True;break
   with connect() as c:
    if getattr(c,'dialect',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(?)',(uid,))
    else:c.execute('BEGIN IMMEDIATE')
    pref=c.execute('SELECT enabled,last_day FROM portfolio_tracking WHERE user_id=?',(uid,)).fetchone()
    if pref and (not pref['enabled'] or pref['last_day']==day):continue
    # Re-read owner-scoped saved data under the write lock. Never persist delayed wallet IDs.
    wallets=read_wallets(c,uid);exchanges=[{'id':r['id'],'snapshot':json.loads(r['snapshot'])} for r in c.execute('SELECT id,snapshot FROM exchange_connections WHERE user_id=?',(uid,))]
    row=valuation(wallets,exchanges,quotes,token_quotes,now)
    if row:
     c.execute('INSERT INTO portfolio_daily_values VALUES (?,?,?) ON CONFLICT(user_id,day) DO UPDATE SET data=EXCLUDED.data',(uid,day,json.dumps(row)));result['saved']+=1
    else:result['unpriced']+=1
    c.execute('INSERT INTO portfolio_tracking VALUES (?,1,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET last_day=EXCLUDED.last_day,last_attempt=EXCLUDED.last_attempt,last_success=COALESCE(EXCLUDED.last_success,portfolio_tracking.last_success),error=EXCLUDED.error',(uid,day,now,now if row else None,None if row else 'No freshly priced holdings'))
  if len(users)>max_accounts:result['pending']=True
  result['ok']=not result['pending']
 except Exception:
  result.update(ok=False,error='Daily capture could not finish; check scheduler logs and retry.')
 finally:
  with connect() as c:
   c.execute('UPDATE portfolio_capture_runs SET expires=0,completed=?,result=? WHERE day=? AND token=?',(int(result['ok'] and not result['pending']),json.dumps(result),day,token))
   c.execute('DELETE FROM portfolio_capture_runs WHERE day<?',(datetime.fromtimestamp(now-31*86400,timezone.utc).date().isoformat(),))
 return result
