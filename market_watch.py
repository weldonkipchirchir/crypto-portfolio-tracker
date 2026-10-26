"""Account-owned market favorites; independent of held wallet favorites."""
import json,time
import coin_market as market

def init(c):
 c.execute('CREATE TABLE IF NOT EXISTS market_favorites (user_id INTEGER NOT NULL,coin_id TEXT NOT NULL,created_at INTEGER NOT NULL,data TEXT NOT NULL,PRIMARY KEY(user_id,coin_id))')

def state(c,uid):
 coins=[]
 for r in c.execute('SELECT coin_id,created_at,data FROM market_favorites WHERE user_id=? ORDER BY created_at DESC,coin_id',(uid,)):
  try:data=json.loads(r['data'])
  except (ValueError,TypeError):continue
  coins.append({'id':r['coin_id'],'name':data.get('name',r['coin_id']),'symbol':data.get('symbol',''),'saved_at':r['created_at']})
 return {'coins':coins,'coverage':'Account-saved CoinGecko coin IDs. Favorites do not imply ownership or purchase history.'}

def resolve(coin_id):
 identity=market.allowed(coin_id)
 try:row=next((c for c in market.listings()['coins'] if c['id']==identity),None)
 except ValueError:row=None
 if row is None:
  import market_intelligence
  row=market_intelligence.catalog_coin(identity)
 if not row:raise ValueError('Choose a known market or narrative coin')
 return {'id':identity,'name':market.text(row.get('name'),100),'symbol':market.text(row.get('symbol'),24)}

def toggle(c,uid,raw,prepared=None):
 identity=market.identifier(raw.get('coin_id'))
 if c.execute('SELECT coin_id FROM market_favorites WHERE user_id=? AND coin_id=?',(uid,identity)).fetchone():
  c.execute('DELETE FROM market_favorites WHERE user_id=? AND coin_id=?',(uid,identity))
 else:
  if not isinstance(prepared,dict) or prepared.get('id')!=identity:raise ValueError('Choose a verified market coin')
  if c.execute('SELECT COUNT(*) AS n FROM market_favorites WHERE user_id=?',(uid,)).fetchone()['n']>=100:raise ValueError('Market watchlist limit reached (100 coins)')
  c.execute('INSERT INTO market_favorites(user_id,coin_id,created_at,data) VALUES (?,?,?,?)',(uid,identity,int(time.time()),json.dumps(prepared)))
 return state(c,uid)
