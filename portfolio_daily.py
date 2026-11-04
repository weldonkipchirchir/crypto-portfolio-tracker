"""Daily connected-portfolio valuations; never infer trade returns or missing days."""
import json,time,hashlib,math
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import advanced_portfolio,providers

def init(c):
 c.execute('CREATE TABLE IF NOT EXISTS portfolio_daily_values (user_id INTEGER NOT NULL,day TEXT NOT NULL,data TEXT NOT NULL,PRIMARY KEY(user_id,day))')

def freshness(stamps,now):
 unknown=False;old=False
 for stamp in stamps:
  if isinstance(stamp,bool) or not isinstance(stamp,(str,int,float)):
   unknown=True;continue
  try:
   value=float(stamp)
   if not math.isfinite(value) or value<=0:unknown=True
   elif not 0<=now-value<=900:old=True
  except (ValueError,TypeError):unknown=True
 return unknown,old

def observation(wallets,quotes,exchanges,now=None):
 now=int(time.time() if now is None else now);total=Decimal(0);priced=unpriced=stale_count=unknown_freshness=0;positions={};coverage={};seen=set()
 for a in advanced_portfolio.assets(wallets):
  w=a['wallet'];address=str(w.get('address',''));address=address.lower() if a['chain'] in providers.EVM_CHAINS else address
  key='wallet:'+a['chain']+':'+address+':'+a['asset_id']
  if key in seen:continue
  seen.add(key);quantity=advanced_portfolio.number(a['quantity'])
  if quantity==0:continue
  quote=quotes.get(providers.CHAINS[a['chain']][0],{}) if a['native'] else a['row']
  price=advanced_portfolio.number(quote.get('price') if a['native'] else quote.get('price_usd'))
  positions[key]=str(quantity) if quantity is not None else 'unknown'
  coverage[key]=quantity is not None and price is not None
  if quantity is None or price is None:unpriced+=1;continue
  unknown,old=freshness([(w.get('snapshot') or {}).get('updated_at') if a['native'] else (w.get('token_snapshot') or {}).get('updated_at'),quote.get('updated_at') if a['native'] else quote.get('price_updated_at')],now)
  unknown_freshness+=int(unknown);stale_count+=int(old or bool(quote.get('price_stale')) or bool((w.get('snapshot') or {}).get('error')))
  total+=quantity*price;priced+=1
 accounts=set()
 for connection in sorted(exchanges,key=lambda e:int((e.get('snapshot') or {}).get('updated_at') or 0),reverse=True):
  snap=connection.get('snapshot') or {};account=snap.get('account_key') or connection.get('id')
  if account in accounts:continue
  accounts.add(account)
  if not snap or snap.get('error') or snap.get('earn_status') in ('partial','error'):unpriced+=1
  for a in snap.get('balances',[]):
   key='exchange:'+str(account)+':'+str(a.get('asset'))+':'+str(a.get('account_type','Spot'))+':'+str(a.get('earn_kind',''))
   if key in seen:continue
   seen.add(key);quantity=advanced_portfolio.number(a.get('display_quantity',a.get('quantity')))
   if quantity==0:continue
   value=advanced_portfolio.number(a.get('value_usd'));positions[key]=str(quantity) if quantity is not None else 'unknown'
   coverage[key]=value is not None
   if value is None:unpriced+=1;continue
   unknown,old=freshness([snap.get('updated_at'),a.get('price_updated_at')],now)
   unknown_freshness+=int(unknown);stale_count+=int(old or bool(a.get('price_stale')))
   total+=value;priced+=1
 if not priced:return None
 return {'date':datetime.fromtimestamp(now,timezone.utc).date().isoformat(),'value':str(total),'observed_at':now,'priced':priced,'unpriced':unpriced,'stale_count':stale_count,'freshness_verified':unknown_freshness==0,'unknown_freshness':unknown_freshness,'coverage_fingerprint':hashlib.sha256(json.dumps(coverage,sort_keys=True).encode()).hexdigest(),'balance_fingerprint':hashlib.sha256(json.dumps(positions,sort_keys=True).encode()).hexdigest()}

def record(c,uid,wallets,quotes,exchanges,now=None):
 value=observation(wallets,quotes,exchanges,now)
 if value:c.execute('INSERT INTO portfolio_daily_values(user_id,day,data) VALUES (?,?,?) ON CONFLICT(user_id,day) DO UPDATE SET data=EXCLUDED.data',(uid,value['date'],json.dumps(value)))
 return value

def calendar(c,uid,now=None):
 today=datetime.fromtimestamp(int(time.time() if now is None else now),timezone.utc).date().isoformat()
 rows=[json.loads(r['data']) for r in c.execute('SELECT data FROM portfolio_daily_values WHERE user_id=? ORDER BY day',(uid,))];by_day={r['date']:r for r in rows};days=[]
 for row in rows:
  previous=by_day.get((datetime.fromisoformat(row['date']).date()-timedelta(days=1)).isoformat())
  coverage=bool(previous and (row['unpriced']==previous['unpriced']==0 or row.get('coverage_fingerprint') and row.get('coverage_fingerprint')==previous.get('coverage_fingerprint') and row['unpriced']==previous['unpriced']))
  change=Decimal(row['value'])-Decimal(previous['value']) if coverage else None
  days.append({**row,'partial':row['unpriced']>0,'change':str(change) if change is not None else None,'previous_value':previous['value'] if previous else None,'percentage':str(change/Decimal(previous['value'])*100) if change is not None and Decimal(previous['value'])>0 else None,'balances_changed':bool(previous and previous['balance_fingerprint']!=row['balance_fingerprint']),'provisional':row['date']==today})
 return {'days':days,'start_date':rows[0]['date'] if rows else None,'coverage':'Connected wallets and exchanges only. Last saved valuation per UTC day; today is provisional. Changes include deposits, withdrawals and balance changes, and are not flow-adjusted investment returns. Unpriced assets are excluded. Partial daily comparisons require unchanged pricing coverage; missing days or changed coverage have no daily gain/loss.'}
