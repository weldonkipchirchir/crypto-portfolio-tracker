"""Manual account-owned market price alerts; accepts trusted provider detail only."""
import json,time,uuid
from decimal import Decimal,InvalidOperation
import coin_market as market
MAX_RULES=50
MAX_EVENTS=200

def init(c):
 c.execute('CREATE TABLE IF NOT EXISTS coin_alerts (id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,coin_id TEXT NOT NULL,data TEXT NOT NULL)')
 c.execute('CREATE INDEX IF NOT EXISTS coin_alerts_user ON coin_alerts(user_id,coin_id)')
 c.execute('CREATE TABLE IF NOT EXISTS coin_alert_events (id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,coin_id TEXT NOT NULL,created_at INTEGER NOT NULL,data TEXT NOT NULL)')
 c.execute('CREATE INDEX IF NOT EXISTS coin_alert_events_user ON coin_alert_events(user_id,created_at)')

def number(v):
 if v is None or isinstance(v,bool):return None
 try:
  n=Decimal(str(v))
  return n if n.is_finite() else None
 except (InvalidOperation,ValueError,TypeError):return None

def state(c,uid,coin_id=None):
 if coin_id is not None:coin_id=market.identifier(coin_id)
 suffix=' AND coin_id=?' if coin_id else '';args=(uid,coin_id) if coin_id else (uid,)
 rules=[json.loads(r['data']) for r in c.execute('SELECT data FROM coin_alerts WHERE user_id=?'+suffix+' ORDER BY id',args)]
 events=[json.loads(r['data']) for r in c.execute('SELECT data FROM coin_alert_events WHERE user_id=?'+suffix+' ORDER BY created_at DESC,id DESC',args)]
 return {'alerts':sorted(rules,key=lambda r:(-r['created_at'],r['id'])),'events':events,'coverage':'In-app USD alerts checked manually against fresh CoinGecko quotes. No background monitoring, email or push delivery. First matching check records an observed condition; later events require leaving and re-entering the condition.'}

def save(c,uid,raw,prepared):
 if not isinstance(raw,dict):raise ValueError('Choose a coin and alert price')
 identity=market.identifier(raw.get('coin_id'));op=raw.get('operator');price=number(raw.get('target_usd'))
 coin=prepared.get('coin',prepared) if isinstance(prepared,dict) else {}
 if coin.get('id')!=identity:raise ValueError('Choose a verified market coin')
 if op not in ('above','below'):raise ValueError('Choose above or below')
 if price is None or price<=0 or price>Decimal('1e12'):raise ValueError('USD threshold must be positive and no greater than 1 trillion')
 allrules=state(c,uid)['alerts']
 if len(allrules)>=MAX_RULES:raise ValueError('Alert limit reached (50 rules)')
 if any(r['coin_id']==identity and r['operator']==op and number(r['target_usd'])==price for r in allrules):raise ValueError('This alert already exists')
 rule={'id':str(uuid.uuid4()),'coin_id':identity,'name':market.text(coin.get('name'),100),'symbol':market.text(coin.get('symbol'),24),'operator':op,'target_usd':str(price),'created_at':int(time.time()),'last_quote_at':None,'condition_met':False}
 c.execute('INSERT INTO coin_alerts(id,user_id,coin_id,data) VALUES (?,?,?,?)',(rule['id'],uid,identity,json.dumps(rule)))
 return rule

def remove(c,uid,raw):
 identity=raw.get('id') if isinstance(raw,dict) else None
 if not isinstance(identity,str) or len(identity)>100:raise ValueError('Choose an alert')
 result=c.execute('DELETE FROM coin_alerts WHERE user_id=? AND id=?',(uid,identity))
 if not result.rowcount:raise ValueError('Alert not found')
 return {'removed':identity}

def evaluate(c,uid,prepared,now=None):
 now=int(time.time()) if now is None else now
 if not isinstance(prepared,dict):raise ValueError('Fresh market quote unavailable')
 coin=prepared.get('coin',prepared);identity=market.identifier(coin.get('id'));price=number(coin.get('current_price'));stamp=number(coin.get('last_updated'))
 if prepared.get('stale') or coin.get('stale') or price is None or price<=0 or price>Decimal('1e12') or stamp is None or stamp!=stamp.to_integral_value() or not 0<=Decimal(str(now))-stamp<=900:raise ValueError('A fresh CoinGecko USD quote within 15 minutes is required. Retry market details later.')
 stamp=int(stamp);evaluated=triggered=0
 for rule in state(c,uid,identity)['alerts']:
  if rule['last_quote_at'] is not None and stamp<=rule['last_quote_at']:continue
  threshold=number(rule['target_usd']);met=price>=threshold if rule['operator']=='above' else price<=threshold
  if met and not rule['condition_met']:
   event={k:rule[k] for k in ('coin_id','name','symbol','operator','target_usd')};event.update(id=str(uuid.uuid4()),alert_id=rule['id'],price_usd=str(price),quote_at=stamp,created_at=now,source='CoinGecko',first_observation=rule['last_quote_at'] is None)
   c.execute('INSERT INTO coin_alert_events(id,user_id,coin_id,created_at,data) VALUES (?,?,?,?,?)',(event['id'],uid,identity,now,json.dumps(event)));triggered+=1
  rule.update(last_quote_at=stamp,condition_met=met)
  c.execute('UPDATE coin_alerts SET data=? WHERE user_id=? AND id=?',(json.dumps(rule),uid,rule['id']));evaluated+=1
 # Keep the newest 200 events across all of this account's coins.
 old=list(c.execute('SELECT id FROM coin_alert_events WHERE user_id=? ORDER BY created_at DESC,id DESC',(uid,)))[MAX_EVENTS:]
 for row in old:c.execute('DELETE FROM coin_alert_events WHERE user_id=? AND id=?',(uid,row['id']))
 return {'evaluated':evaluated,'triggered':triggered,'quote_at':stamp,**state(c,uid,identity)}
