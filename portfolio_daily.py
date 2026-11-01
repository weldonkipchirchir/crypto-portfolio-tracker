"""Daily connected-portfolio valuations; never infer trade returns or missing days."""
import json,time,hashlib
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import advanced_portfolio,providers

def init(c):
 c.execute('CREATE TABLE IF NOT EXISTS portfolio_daily_values (user_id INTEGER NOT NULL,day TEXT NOT NULL,data TEXT NOT NULL,PRIMARY KEY(user_id,day))')

def observation(wallets,quotes,exchanges,now=None):
 now=int(time.time() if now is None else now);total=Decimal(0);priced=unpriced=0;positions={};seen=set()
 for a in advanced_portfolio.assets(wallets):
  w=a['wallet'];address=str(w.get('address',''));address=address.lower() if a['chain'] in providers.EVM_CHAINS else address
  key='wallet:'+a['chain']+':'+address+':'+a['asset_id']
  if key in seen:continue
  seen.add(key);quantity=advanced_portfolio.number(a['quantity'])
  if quantity==0:continue
  quote=quotes.get(providers.CHAINS[a['chain']][0],{}) if a['native'] else a['row']
  price=advanced_portfolio.number(quote.get('price') if a['native'] else quote.get('price_usd'))
  positions[key]=str(quantity) if quantity is not None else 'unknown'
  if quantity is None or price is None:unpriced+=1;continue
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
   if value is None:unpriced+=1;continue
   total+=value;priced+=1
 if not priced:return None
 return {'date':datetime.fromtimestamp(now,timezone.utc).date().isoformat(),'value':str(total),'observed_at':now,'priced':priced,'unpriced':unpriced,'balance_fingerprint':hashlib.sha256(json.dumps(positions,sort_keys=True).encode()).hexdigest()}

def record(c,uid,wallets,quotes,exchanges,now=None):
 value=observation(wallets,quotes,exchanges,now)
 if value:c.execute('INSERT INTO portfolio_daily_values(user_id,day,data) VALUES (?,?,?) ON CONFLICT(user_id,day) DO UPDATE SET data=EXCLUDED.data',(uid,value['date'],json.dumps(value)))
 return value

def calendar(c,uid,now=None):
 today=datetime.fromtimestamp(int(time.time() if now is None else now),timezone.utc).date().isoformat()
 rows=[json.loads(r['data']) for r in c.execute('SELECT data FROM portfolio_daily_values WHERE user_id=? ORDER BY day',(uid,))];by_day={r['date']:r for r in rows};days=[]
 for row in rows:
  previous=by_day.get((datetime.fromisoformat(row['date']).date()-timedelta(days=1)).isoformat())
  coverage=bool(previous and row['unpriced']==previous['unpriced']==0)
  change=Decimal(row['value'])-Decimal(previous['value']) if coverage else None
  days.append({**row,'change':str(change) if change is not None else None,'previous_value':previous['value'] if previous else None,'percentage':str(change/Decimal(previous['value'])*100) if change is not None and Decimal(previous['value'])>0 else None,'balances_changed':bool(previous and previous['balance_fingerprint']!=row['balance_fingerprint']),'provisional':row['date']==today})
 return {'days':days,'start_date':rows[0]['date'] if rows else None,'coverage':'Connected wallets and exchanges only. Last saved valuation per UTC day; today is provisional. Changes include deposits, withdrawals and balance changes, and are not flow-adjusted investment returns. Missing days and incomplete price coverage have no daily gain/loss.'}
