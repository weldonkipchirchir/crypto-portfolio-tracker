"""In-app USD price targets evaluated only against saved, fresh identity-bound quotes."""
import json,time,uuid
from decimal import Decimal
import advanced_portfolio as portfolio
import providers

MAX_TARGETS=30
MAX_EVENTS=200

def init(c):
 c.execute('CREATE TABLE IF NOT EXISTS price_targets (id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,data TEXT NOT NULL)')
 c.execute('CREATE INDEX IF NOT EXISTS price_targets_user ON price_targets(user_id)')
 c.execute('CREATE TABLE IF NOT EXISTS price_target_events (id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,target_id TEXT NOT NULL,created_at INTEGER NOT NULL,data TEXT NOT NULL)')
 c.execute('CREATE INDEX IF NOT EXISTS price_target_events_user ON price_target_events(user_id,created_at)')

def state(c,uid):
 targets=[json.loads(r['data']) for r in c.execute('SELECT data FROM price_targets WHERE user_id=? ORDER BY id',(uid,))]
 events=[json.loads(r['data']) for r in c.execute('SELECT data FROM price_target_events WHERE user_id=? ORDER BY created_at DESC,id',(uid,))]
 return {'price_targets':sorted(targets,key=lambda t:(-t['created_at'],t['id'])),'target_events':events}

def owned(wallets):
 return [a for a in portfolio.assets(wallets) if portfolio.number(a['quantity']) is not None and portfolio.number(a['quantity'])>0]

def save(c,uid,raw,wallets,quotes):
 if not isinstance(raw,dict):raise ValueError('Choose a held asset and USD price target')
 identity=raw.get('asset_id');operator=raw.get('operator');price=portfolio.number(raw.get('target_usd'))
 if operator not in ('above','below'):raise ValueError('Target operator must be above or below')
 if price is None or price<=0 or price>Decimal('1e12'):raise ValueError('Target USD price must be positive and no greater than 1 trillion')
 if not isinstance(identity,str) or len(identity)>200:raise ValueError('Choose a held asset identity')
 asset=next((a for a in owned(wallets) if a['asset_id']==identity),None)
 if asset is None:raise ValueError('Price targets require a nonzero asset held in your wallets')
 rules=state(c,uid)['price_targets']
 if len(rules)>=MAX_TARGETS:raise ValueError('Price target limit reached (30)')
 if any(r['asset_id']==identity and r['operator']==operator and portfolio.number(r['target_usd'])==price for r in rules):raise ValueError('This price target already exists')
 data={k:asset[k] for k in ('asset_id','symbol','chain','contract')}
 data.update(id=str(uuid.uuid4()),operator=operator,target_usd=str(price),created_at=int(time.time()),last_quote_at=None,condition_met=False,event_limit_reached=False)
 c.execute('INSERT INTO price_targets(id,user_id,data) VALUES (?,?,?)',(data['id'],uid,json.dumps(data)))
 return data

def remove(c,uid,raw):
 identity=raw.get('id') if isinstance(raw,dict) else None
 if not isinstance(identity,str) or len(identity)>100:raise ValueError('Choose a price target to remove')
 result=c.execute('DELETE FROM price_targets WHERE user_id=? AND id=?',(uid,identity))
 if not result.rowcount:raise ValueError('Price target not found')
 return {'removed':identity}

def quote_for(asset,quotes,now):
 row=asset['row']
 quote=(quotes.get(providers.CHAINS[asset['chain']][0]) or quotes.get(providers.LEDGER_ALIASES.get(asset['chain']),{})) if asset['native'] else row
 source=quote.get('source') if asset['native'] else quote.get('price_source')
 if source!=('CoinGecko' if asset['native'] else 'DEX Screener'):return None
 if quote.get('price_stale') or quote.get('price_error'):return None
 price=portfolio.number(quote.get('price') if asset['native'] else quote.get('price_usd'))
 stamp=portfolio.number(quote.get('updated_at') if asset['native'] else quote.get('price_fetched_at'))
 if price is None or price<=0 or price>Decimal('1e12') or stamp is None or stamp!=stamp.to_integral_value() or portfolio.stale(stamp,now):return None
 return price,int(stamp),source

def evaluate(c,uid,wallets,quotes):
 now=int(time.time());observations={};conflicts={}
 # The freshest valid quote for a canonical identity wins across owned wallet observations.
 for asset in owned(wallets):
  quote=quote_for(asset,quotes,now)
  if not quote:continue
  identity=asset['asset_id'];prior=observations.get(identity)
  if prior is None or quote[1]>prior[1]:
   observations[identity]=quote;conflicts.pop(identity,None)
  elif quote[1]==prior[1] and quote[0]!=prior[0]:conflicts[identity]=quote[1]
 for identity in conflicts:observations.pop(identity,None)
 count=c.execute('SELECT COUNT(*) AS n FROM price_target_events WHERE user_id=?',(uid,)).fetchone()['n']
 evaluated=triggered=0;limited=False
 for target in state(c,uid)['price_targets']:
  quote=observations.get(target['asset_id'])
  if not quote:continue
  price,stamp,source=quote
  if target['last_quote_at'] is not None and stamp<=target['last_quote_at']:continue
  threshold=portfolio.number(target['target_usd'])
  if threshold is None or threshold<=0:continue
  met=price>=threshold if target['operator']=='above' else price<=threshold
  crossing=met and not target['condition_met']
  target['last_quote_at']=stamp;target['condition_met']=met;evaluated+=1
  if crossing and count>=MAX_EVENTS:
   target['event_limit_reached']=True;limited=True
  elif crossing:
   event={k:target[k] for k in ('asset_id','symbol','chain','contract','operator','target_usd')}
   event.update(id=str(uuid.uuid4()),target_id=target['id'],price_usd=str(price),quote_at=stamp,source=source,created_at=now)
   c.execute('INSERT INTO price_target_events(id,user_id,target_id,created_at,data) VALUES (?,?,?,?,?)',(event['id'],uid,target['id'],now,json.dumps(event)))
   count+=1;triggered+=1
  c.execute('UPDATE price_targets SET data=? WHERE user_id=? AND id=?',(json.dumps(target),uid,target['id']))
 return {'evaluated':evaluated,'triggered':triggered,'event_limit_reached':limited or count>=MAX_EVENTS}
