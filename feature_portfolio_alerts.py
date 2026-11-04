"""Manual account-owned ledger alerts, evaluated exclusively from saved records."""
import json,time,uuid
from decimal import Decimal,InvalidOperation

COVERAGE='Manual in-app checks of the recorded-trades portfolio using saved USD quotes no older than 15 minutes. No background monitoring or email delivery. Connected holdings are a separate view. Missing or stale quotes suppress checks without resetting crossing state. Unrealized return uses recorded remaining weighted-average cost, not tax or investment returns. Drawdown is unavailable: saved totals do not establish fresh comparable historical quotes.'

def init(c):
 c.execute('CREATE TABLE IF NOT EXISTS portfolio_alert_rules(user_id INTEGER NOT NULL,id TEXT NOT NULL,data TEXT NOT NULL,PRIMARY KEY(user_id,id))')
 c.execute('CREATE TABLE IF NOT EXISTS portfolio_alert_events(user_id INTEGER NOT NULL,id TEXT NOT NULL,created_at INTEGER NOT NULL,data TEXT NOT NULL,PRIMARY KEY(user_id,id))')

def number(v):
 if v is None or isinstance(v,bool) or len(str(v))>100:return None
 try:
  n=Decimal(str(v));return n if n.is_finite() and abs(n)<=Decimal('1e30') else None
 except (InvalidOperation,ValueError,TypeError):return None

def read(c,uid,raw=None):
 return {'rules':[json.loads(r['data']) for r in c.execute('SELECT data FROM portfolio_alert_rules WHERE user_id=? ORDER BY id',(uid,))], 'events':[json.loads(r['data']) for r in c.execute('SELECT data FROM portfolio_alert_events WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT 200',(uid,))], 'assets':[r['symbol'] for r in c.execute('SELECT DISTINCT symbol FROM trades WHERE user_id=? ORDER BY symbol',(uid,))], 'coverage':COVERAGE}

def snapshot(c,uid,now):
 # Reuse the established remaining weighted-average ledger accounting; no provider calls.
 from server import calculate
 rows=[dict(r) for r in c.execute('SELECT * FROM trades WHERE user_id=?',(uid,))]
 prices={r['symbol']:r['price'] for r in c.execute('SELECT symbol,price FROM prices WHERE user_id=?',(uid,))}
 meta={r['symbol']:r['updated_at'] for r in c.execute('SELECT symbol,updated_at FROM price_metadata WHERE user_id=?',(uid,))}
 try:positions=calculate(rows,prices)
 except (ValueError,TypeError,ArithmeticError):return None,'Ledger accounting unavailable'
 held=[p for p in positions if p['quantity']!=0]
 if not held:return None,'No open ledger holdings'
 for p in held:
  stamp=number(meta.get(p['symbol']));price=number(prices.get(p['symbol']))
  if stamp is None or not 0<=Decimal(now)-stamp<=900 or price is None or price<=0 or number(p['value']) is None:return None,'Missing, invalid or stale saved quote for '+p['symbol']
 total=sum((number(p['value']) for p in held),Decimal(0));cost=sum((number(p['cost']) for p in held),Decimal(0))
 if total<=0:return None,'Portfolio value unavailable'
 return {'value':total,'unrealized_return':(total-cost)/cost*100 if cost>0 else None,'allocation':{p['symbol']:number(p['value'])/total*100 for p in held}},None

def action(c,uid,raw):
 op=raw.get('operation');data=read(c,uid)
 if op=='create':
  metric=raw.get('metric');operator=raw.get('operator');threshold=number(raw.get('threshold'));asset=raw.get('asset') if metric=='allocation' else None
  if metric not in ('value','allocation','unrealized_return') or operator not in ('above','below') or threshold is None:raise ValueError('Choose a metric, direction and finite threshold')
  if metric=='value' and threshold<0 or metric=='allocation' and not 0<=threshold<=100:raise ValueError('Use a nonnegative USD value or allocation from 0 to 100 percent')
  if metric=='allocation' and asset not in data['assets']:raise ValueError('Choose an exact ledger symbol from this account')
  if len(data['rules'])>=50:raise ValueError('Use up to 50 rules')
  if any(r['metric']==metric and r['operator']==operator and number(r['threshold'])==threshold and r.get('asset')==asset for r in data['rules']):raise ValueError('This rule already exists')
  rule={'id':uuid.uuid4().hex,'metric':metric,'operator':operator,'threshold':str(threshold),'asset':asset,'condition_met':False,'evaluated_at':None,'status':'Not evaluated','observed':None}
  c.execute('INSERT INTO portfolio_alert_rules VALUES (?,?,?)',(uid,rule['id'],json.dumps(rule)))
 elif op=='delete':
  if not isinstance(raw.get('id'),str) or not c.execute('DELETE FROM portfolio_alert_rules WHERE user_id=? AND id=?',(uid,raw['id'])).rowcount:raise ValueError('Rule not found')
 elif op=='evaluate':
  now=int(time.time());values,reason=snapshot(c,uid,now)
  for rule in data['rules']:
   observed=(values['allocation'].get(rule['asset'],Decimal(0)) if rule['metric']=='allocation' else values.get(rule['metric'])) if values else None
   rule.update(evaluated_at=now,status=reason or ('Metric unavailable' if observed is None else 'Checked saved quotes'),observed=str(observed) if observed is not None else None)
   if observed is not None:
    met=observed>=number(rule['threshold']) if rule['operator']=='above' else observed<=number(rule['threshold'])
    if met and not rule['condition_met']:
     event={'id':uuid.uuid4().hex,'rule_id':rule['id'],'metric':rule['metric'],'asset':rule['asset'],'operator':rule['operator'],'threshold':rule['threshold'],'observed':str(observed),'created_at':now,'first_observation':rule.get('last_valid_at') is None}
     c.execute('INSERT INTO portfolio_alert_events VALUES (?,?,?,?)',(uid,event['id'],now,json.dumps(event)))
    rule.update(condition_met=met,last_valid_at=now)
   c.execute('UPDATE portfolio_alert_rules SET data=? WHERE user_id=? AND id=?',(json.dumps(rule),uid,rule['id']))
  for r in list(c.execute('SELECT id FROM portfolio_alert_events WHERE user_id=? ORDER BY created_at DESC,id DESC',(uid,)))[200:]:c.execute('DELETE FROM portfolio_alert_events WHERE user_id=? AND id=?',(uid,r['id']))
 else:raise ValueError('Unknown portfolio alert operation')
 return read(c,uid)
