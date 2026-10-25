"""Account-scoped valuation checkpoints and held-asset favorites; no inferred returns."""
import hashlib,json,time,uuid
from decimal import Decimal,InvalidOperation,localcontext
import providers

CAVEAT='Known wallet value only. Transfers, balance changes, wallet membership and incomplete coverage affect comparisons; changes are not investment returns or P&L.'

def init(c):
 c.execute('CREATE TABLE IF NOT EXISTS portfolio_checkpoints (id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,created_at INTEGER NOT NULL,data TEXT NOT NULL)')
 c.execute('CREATE INDEX IF NOT EXISTS portfolio_checkpoint_user ON portfolio_checkpoints(user_id,created_at)')
 c.execute('CREATE TABLE IF NOT EXISTS portfolio_favorites (id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,asset_id TEXT NOT NULL,data TEXT NOT NULL,UNIQUE(user_id,asset_id))')

def state(c,uid):
 return {'checkpoints':[json.loads(r['data']) for r in c.execute('SELECT data FROM portfolio_checkpoints WHERE user_id=? ORDER BY created_at DESC,id',(uid,))], 'watchlist':[json.loads(r['data']) for r in c.execute('SELECT data FROM portfolio_favorites WHERE user_id=? ORDER BY asset_id',(uid,))]}

def number(value):
 try:
  text=str(value)
  if len(text)>350:return None
  value=Decimal(text)
  if not value.is_finite() or value<0 or value.adjusted()>78 or not -255 <= value.as_tuple().exponent <= 78:return None
  return value
 except (InvalidOperation,TypeError,ValueError):return None

def canonical(chain,contract):
 if not isinstance(contract,str):raise ValueError('Invalid token identity')
 value=providers.validate_address(chain,contract)
 return value.lower() if chain in providers.EVM_CHAINS else value

def assets(wallets):
 """Yield canonical owned observations; never accept a symbol as token identity."""
 for w in wallets:
  chain=w.get('chain')
  if chain not in providers.CHAINS:continue
  native=w.get('snapshot') or {}
  yield {'asset_id':chain+':native','chain':chain,'contract':None,'symbol':providers.CHAINS[chain][0],'name':providers.CHAINS[chain][0],'quantity':native.get('quantity'),'native':True,'row':native,'wallet':w}
  for t in (w.get('token_snapshot') or {}).get('tokens',[]):
   try:contract=canonical(chain,t.get('contract') or t.get('mint'))
   except (ValueError,TypeError):continue
   identity=chain+':'+contract
   if t.get('asset_id')!=identity:continue
   yield {'asset_id':identity,'chain':chain,'contract':contract,'symbol':str(t.get('symbol') or 'Token')[:32],'name':str(t.get('name') or t.get('symbol') or 'Token')[:120],'quantity':t.get('quantity'),'native':False,'row':t,'wallet':w}

def stale(stamp,now):
 value=number(stamp)
 return value is None or value>now+60 or value<now-900

def checkpoint(c,uid,wallets,quotes):
 now=int(time.time())
 previous=c.execute('SELECT created_at,data FROM portfolio_checkpoints WHERE user_id=? ORDER BY created_at DESC,id LIMIT 1',(uid,)).fetchone()
 if previous and now-previous['created_at']<60:raise ValueError('Wait one minute between checkpoints')
 count=c.execute('SELECT COUNT(*) AS n FROM portfolio_checkpoints WHERE user_id=?',(uid,)).fetchone()['n']
 if count>=365:raise ValueError('Checkpoint limit reached (365)')
 if not wallets:raise ValueError('Add a wallet before saving a checkpoint')
 # Membership uses chain and address rather than display labels or database IDs.
 members=sorted(set((str(w.get('chain')),str(w.get('address')).lower() if w.get('chain') in providers.EVM_CHAINS else str(w.get('address'))) for w in wallets))
 fingerprint=hashlib.sha256(json.dumps(members,separators=(',',':')).encode()).hexdigest()
 total=Decimal(0);chains={};balances={};priced=unpriced=old=token_count=0;truncated=False;seen=set()
 with localcontext() as ctx:
  ctx.prec=700
  for a in assets(wallets):
   address=str(a['wallet'].get('address'));address=address.lower() if a['chain'] in providers.EVM_CHAINS else address
   observation=(a['chain'],address,a['asset_id'])
   if observation in seen:continue
   seen.add(observation)
   if not a['native']:
    token_count+=1
    if token_count>200:truncated=True;continue
   quantity=number(a['quantity'])
   if quantity is None:unpriced+=1;continue
   key=json.dumps(observation,separators=(',',':'))
   balances[key]=str(quantity)
   if quantity==0:continue
   row=a['row'];quote=(quotes.get(providers.CHAINS[a['chain']][0]) or quotes.get(providers.LEDGER_ALIASES.get(a['chain']),{})) if a['native'] else row
   price=number(quote.get('price') if a['native'] else quote.get('price_usd'))
   if price is None or price==0:unpriced+=1;continue
   value=quantity*price;total+=value;chains[a['chain']]=chains.get(a['chain'],Decimal(0))+value;priced+=1
   balance_stamp=row.get('updated_at') if a['native'] else (a['wallet'].get('token_snapshot') or {}).get('updated_at')
   if row.get('error') or row.get('stale') or row.get('price_stale') or stale(quote.get('updated_at') if a['native'] else row.get('price_fetched_at'),now) or stale(balance_stamp,now):old+=1
 if not priced:raise ValueError('No priced wallet holdings available for a checkpoint')
 balance_hash=hashlib.sha256(json.dumps(balances,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 prior=json.loads(previous['data']) if previous else {}
 data={'id':str(uuid.uuid4()),'created_at':now,'value_usd':str(total),'chain_values':{k:str(v) for k,v in sorted(chains.items())},'priced_count':priced,'unpriced_count':unpriced,'stale_count':old,'wallet_count':len(members),'wallet_fingerprint':fingerprint,'balance_fingerprint':balance_hash,'membership_changed':bool(prior and prior.get('wallet_fingerprint')!=fingerprint),'balances_changed':bool(prior and prior.get('balance_fingerprint')!=balance_hash),'partial':True,'truncated':truncated,'caveat':CAVEAT}
 c.execute('INSERT INTO portfolio_checkpoints(id,user_id,created_at,data) VALUES (?,?,?,?)',(data['id'],uid,now,json.dumps(data)))
 return data

def toggle_watch(c,uid,raw,wallets):
 identity=raw.get('asset_id') if isinstance(raw,dict) else None
 if not isinstance(identity,str) or len(identity)>200:raise ValueError('Choose a held asset identity')
 current=c.execute('SELECT id FROM portfolio_favorites WHERE user_id=? AND asset_id=?',(uid,identity)).fetchone()
 if current:
  c.execute('DELETE FROM portfolio_favorites WHERE user_id=? AND asset_id=?',(uid,identity));watching=False
 else:
  found=next((a for a in assets(wallets) if a['asset_id']==identity and number(a['quantity']) is not None and number(a['quantity'])>0),None)
  if not found:raise ValueError('Only nonzero holdings in your wallets can be watched')
  count=c.execute('SELECT COUNT(*) AS n FROM portfolio_favorites WHERE user_id=?',(uid,)).fetchone()['n']
  if count>=50:raise ValueError('Watchlist limit reached (50)')
  data={k:found[k] for k in ('asset_id','chain','contract','symbol','name')};data['added_at']=int(time.time())
  c.execute('INSERT INTO portfolio_favorites(id,user_id,asset_id,data) VALUES (?,?,?,?) ON CONFLICT (user_id,asset_id) DO NOTHING',(str(uuid.uuid4()),uid,identity,json.dumps(data)));watching=True
 return {'asset_id':identity,'watching':watching,'watchlist':state(c,uid)['watchlist']}
