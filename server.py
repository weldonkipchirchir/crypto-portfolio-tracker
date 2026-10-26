from contextlib import contextmanager, nullcontext
import providers
import imports
import token_integrations
import token_discovery
import token_pricing
import advanced_portfolio
import price_targets
import coin_market
import protocol_data
import market_news
import market_intelligence
import market_microstructure
import coin_alerts
import account_features
import exchange_connections
import workspace_features
import wallet_batch
import market_watch
import exchange_charts
import history
import review
import review_accounting
from runtime_security import BoundedHTTPServer, ProviderBudget, BudgetExceeded
PROVIDER_BUDGET=ProviderBudget()
MARKET_BUDGET=ProviderBudget(limit=60,per_user_concurrent=4)
from concurrent.futures import ThreadPoolExecutor
import csv, hashlib, hmac, io, json, os, secrets, sqlite3, time, re, threading
from urllib.parse import urlsplit
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from decimal import Decimal, InvalidOperation
ROOT=Path(__file__).parent
DB=ROOT/'portfolio.sqlite3'
AUTH_ATTEMPTS={}
AUTH_LOCK=threading.Lock()
DUMMY_SALT='0'*32

def allow_auth(address):
 if os.environ.get('DATABASE_URL'):
  import cloud_storage
  return cloud_storage.allowance('auth:'+hashlib.sha256(address.encode()).hexdigest(),30,900)
 now=time.monotonic()
 with AUTH_LOCK:
  for key in list(AUTH_ATTEMPTS):
   if now-AUTH_ATTEMPTS[key][0]>900: del AUTH_ATTEMPTS[key]
  start,count=AUTH_ATTEMPTS.get(address,(now,0))
  if count>=30: return False
  if len(AUTH_ATTEMPTS)>=10000 and address not in AUTH_ATTEMPTS: return False
  AUTH_ATTEMPTS[address]=(start,count+1)
  return True

def symbol_value(value):
 if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,29}',value.strip()): raise ValueError('Invalid token symbol')
 return value.strip().upper()

@contextmanager
def connect():
 if os.environ.get('DATABASE_URL'):
  import cloud_storage
  with cloud_storage.connect() as c:yield c
  return
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
 try:
  with c: yield c
 finally: c.close()
def init():
 with connect() as c:
  if getattr(c,'dialect',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(71420001)')
  c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,email TEXT UNIQUE,password TEXT); CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER,expires REAL); CREATE TABLE IF NOT EXISTS trades(id INTEGER PRIMARY KEY,user_id INTEGER,date TEXT,symbol TEXT,side TEXT,quantity TEXT,price TEXT,fee TEXT,account TEXT); CREATE TABLE IF NOT EXISTS prices(user_id INTEGER,symbol TEXT,price TEXT,PRIMARY KEY(user_id,symbol)); CREATE TABLE IF NOT EXISTS wallets(id INTEGER PRIMARY KEY,user_id INTEGER,chain TEXT,address TEXT,label TEXT,UNIQUE(user_id,chain,address));''')
  c.executescript('''CREATE TABLE IF NOT EXISTS price_metadata(user_id INTEGER,symbol TEXT,source TEXT,updated_at INTEGER,PRIMARY KEY(user_id,symbol)); CREATE TABLE IF NOT EXISTS wallet_snapshots(wallet_id INTEGER PRIMARY KEY,data TEXT); CREATE TABLE IF NOT EXISTS wallet_tokens(wallet_id INTEGER PRIMARY KEY,data TEXT); CREATE TABLE IF NOT EXISTS token_watchlist(wallet_id INTEGER PRIMARY KEY,contracts TEXT); CREATE TABLE IF NOT EXISTS imports(user_id INTEGER,digest TEXT,PRIMARY KEY(user_id,digest)); CREATE TABLE IF NOT EXISTS chain_history(wallet_id INTEGER,event_id TEXT,data TEXT,PRIMARY KEY(wallet_id,event_id)); CREATE TABLE IF NOT EXISTS history_sync(wallet_id INTEGER PRIMARY KEY,data TEXT); CREATE TABLE IF NOT EXISTS review_decisions(user_id INTEGER,review_id TEXT,status TEXT,data TEXT,PRIMARY KEY(user_id,review_id)); CREATE TABLE IF NOT EXISTS asset_bindings(user_id INTEGER,asset_id TEXT,symbol TEXT,PRIMARY KEY(user_id,asset_id),UNIQUE(user_id,symbol));''')
  advanced_portfolio.init(c)
  price_targets.init(c)
  market_watch.init(c)
  coin_alerts.init(c)
  account_features.init(c)
  exchange_connections.init(c)
  workspace_features.init(c)
  c.execute('CREATE TABLE IF NOT EXISTS coin_market_cache (key TEXT PRIMARY KEY,fetched_at INTEGER NOT NULL,data TEXT NOT NULL)')

def market_cache_read(key):
 with connect() as c:
  row=c.execute('SELECT data FROM coin_market_cache WHERE key=?',(json.dumps(key),)).fetchone()
  return json.loads(row['data']) if row else None

def market_cache_write(key,data):
 with connect() as c:
  c.execute('INSERT INTO coin_market_cache(key,fetched_at,data) VALUES (?,?,?) ON CONFLICT (key) DO UPDATE SET fetched_at=EXCLUDED.fetched_at,data=EXCLUDED.data',(json.dumps(key),data['fetched_at'],json.dumps(data)))
  c.execute('DELETE FROM coin_market_cache WHERE key IN (SELECT key FROM coin_market_cache ORDER BY fetched_at DESC LIMIT 10000 OFFSET 400)')

def metadata(c,uid):
 return {r['symbol']:dict(r) for r in c.execute('SELECT m.symbol,m.source,m.updated_at,p.price FROM price_metadata m JOIN prices p ON p.user_id=m.user_id AND p.symbol=m.symbol WHERE m.user_id=?',(uid,))}
def snapshots(c,uid):
 result=[]
 for row in c.execute('SELECT w.id,w.chain,w.address,w.label,s.data,t.data as token_data FROM wallets w LEFT JOIN wallet_snapshots s ON s.wallet_id=w.id LEFT JOIN wallet_tokens t ON t.wallet_id=w.id WHERE w.user_id=?',(uid,)):
  item=dict(row); raw=item.pop('data'); item['snapshot']=json.loads(raw) if raw else None;tokens=item.pop('token_data');item['token_snapshot']=json.loads(tokens) if tokens else None;result.append(item)
 return result
def history_state(c,uid):
 records=[];statuses=[]
 for row in c.execute('SELECT h.wallet_id,h.data,w.label,w.chain FROM chain_history h JOIN wallets w ON w.id=h.wallet_id WHERE w.user_id=?',(uid,)):
  records.append({**json.loads(row['data']),'wallet_id':row['wallet_id'],'wallet_label':row['label'],'chain':row['chain']})
 for row in c.execute('SELECT h.wallet_id,h.data FROM history_sync h JOIN wallets w ON w.id=h.wallet_id WHERE w.user_id=?',(uid,)):
  data=json.loads(row['data']);statuses.append({'wallet_id':row['wallet_id'],'coverage':data.get('coverage',''),'error':data.get('error'),'updated_at':data.get('updated_at'),'has_more':any(data.get('cursors',{}).values()),'adapter_version':data.get('adapter_version')})
 return sorted(records,key=lambda r:r.get('date') or '',reverse=True),statuses

def review_state(c,uid,records):
 statuses={r['review_id']:r['status'] for r in c.execute('SELECT review_id,status FROM review_decisions WHERE user_id=?',(uid,))}
 bindings={r['asset_id']:r['symbol'] for r in c.execute('SELECT asset_id,symbol FROM asset_bindings WHERE user_id=?',(uid,))}
 suggestions=review.build_reviews(records,statuses)
 for item in suggestions:
  for asset in item['sent']+item['received']:
   if asset['asset_id'] in bindings:asset['ledger_symbol']=bindings[asset['asset_id']]
 return suggestions

def network_support():
 coverage={
  'Bitcoin':'Confirmed mainnet BTC address transactions; no xpub or whole-wallet discovery; mixed-input transactions excluded from review',
  'Stellar':'Classic G-address payments and account-creation operations; issuer-qualified assets; no muxed address or complete operation history',
  'Tron':'Confirmed native TRX transfers; contract calls are metadata only; no TRC-20 discovery/history',
  'Arc':'Mainnet USDC native balances (18 decimals); native history requires explorer API access; ERC-20 USDC interface is the same balance',
  'Monad':'Mainnet MON balances; external native history requires explorer API access',
  'Robinhood Chain':'Mainnet ETH balances; native history requires explorer API access; separate from Robinhood exchange accounts',
  'Linea':'Mainnet ETH balances; external native history requires explorer API access',
  'Sonic':'External native S history requires explorer API access; no indexed token history',
  'Gnosis':'External xDAI transactions and ERC-20 transfers; no internal transfers or NFTs',
  'Celo':'External CELO transactions and ERC-20 transfers; alternate fee currencies not normalized',
  'Base':'External native ETH history requires explorer API access (paid plan for Base); no indexed token history',
  'Arbitrum':'External native ETH history requires explorer API access; no indexed token history',
  'Polygon':'External native POL history requires explorer API access; no indexed token history',
  'Avalanche':'C-Chain external AVAX history via public Routescan; no X/P-Chain or indexed token history',
  'Ethereum':'External ETH transactions and ERC-20 transfers; no internal transfers or NFTs',
  'Optimism':'External ETH transactions and ERC-20 transfers; no internal transfers or NFTs',
  'BNB Chain':'External BNB transactions; Etherscan API key and chain access required',
  'Solana':'Finalized SOL/SPL balance changes; 10 transactions per page; provider retention applies',
  'Aptos':'Signed-account transaction windows and recognized APT transfers; incoming and orderless activity incomplete',
  'Sui':'GraphQL address activity; native SUI amounts; unknown token decimals shown as raw units, excluded from review'}
 return [{'chain':chain,'symbol':config[0],'balance':True,'history_configured':chain not in ('BNB Chain','Base','Arbitrum','Polygon','Sonic','Arc','Monad','Robinhood Chain','Linea') or bool(os.environ.get('ETHERSCAN_API_KEY')),'history_coverage':coverage[chain]} for chain,config in providers.CHAINS.items()]

def watched_contracts(c,wallet,raw=None):
 if raw is not None:
  if not isinstance(raw,list) or len(raw)>20:raise ValueError('Supply at most 20 token contract addresses')
  if wallet['chain'] not in providers.EVM_CHAINS and raw:raise ValueError('Manual ERC-20 contracts require an EVM network')
  return list(dict.fromkeys(providers.validate_address(wallet['chain'],address) for address in raw))
 saved=c.execute('SELECT contracts FROM token_watchlist WHERE wallet_id=?',(wallet['id'],)).fetchone()
 return json.loads(saved['contracts']) if saved else []

def persist_tokens(c,wallet,result,contracts):
 previous=c.execute('SELECT data FROM wallet_tokens WHERE wallet_id=?',(wallet['id'],)).fetchone()
 old=json.loads(previous['data']) if previous else {}
 old_prices={token['asset_id']:token for token in old.get('tokens',[])}
 for token in result.get('tokens',[]):
  previous=old_prices.get(token['asset_id'],{})
  for key in ('price_usd','value_usd','price_source','price_fetched_at','price_pair_url','price_liquidity_usd','market_dex','market_change_24h_pct','market_volume_24h_usd'):
   if key in previous:token.setdefault(key,previous[key])
 current={token['asset_id']:token for token in result.get('tokens',[])}
 if result.get('has_more') or result.get('errors'):
  for token in old.get('tokens',[]):
   if token['asset_id'] not in current:current[token['asset_id']]={**token,'stale':True}
 result['tokens']=list(current.values())
 enriched=token_pricing.enrich(wallet['chain'],result)
 result.clear();result.update(enriched)
 c.execute('INSERT OR REPLACE INTO wallet_tokens VALUES (?,?)',(wallet['id'],json.dumps(result)))
 if wallet['chain'] in providers.EVM_CHAINS:c.execute('INSERT OR REPLACE INTO token_watchlist VALUES (?,?)',(wallet['id'],json.dumps(contracts)))

def sync_wallet(w,cutoff=None):
 try:
  with providers.deadline(cutoff or time.monotonic()+15): return w['id'],providers.balance(w['chain'],w['address'])
 except Exception as error: return w['id'],{'error':str(error) if isinstance(error,ValueError) else 'Invalid response from balance provider','attempted_at':int(time.time())}
def password(value,salt=None):
 salt=salt or secrets.token_hex(16)
 return salt+':'+hashlib.scrypt(value.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
def number(value,positive=False):
 try:
  if isinstance(value,bool) or len(str(value))>80: raise ValueError('Invalid number')
  n=Decimal(str(value))
 except InvalidOperation: raise ValueError('Enter valid numbers')
 if not n.is_finite() or (n and (n.adjusted()>24 or n.as_tuple().exponent < -24)) or n<0 or (positive and n==0): raise ValueError('Amounts must be positive; fees may be zero')
 return n
def calculate(rows,prices):
 assets={}
 for t in sorted(rows,key=lambda t:(t['date'],t.get('id',0))):
  s=t['symbol']; a=assets.setdefault(s,dict(symbol=s,quantity=Decimal(0),cost=Decimal(0),realized=Decimal(0),bought=Decimal(0),buy_total=Decimal(0),sold=Decimal(0),sell_total=Decimal(0)))
  q=number(t['quantity'],True); p=number(t['price']); f=number(t['fee'])
  if t['side']=='buy':
   a['quantity']+=q; a['cost']+=q*p+f; a['bought']+=q; a['buy_total']+=q*p
  else:
   if q>a['quantity']: raise ValueError('Sale exceeds available '+s+' holdings. Import earlier purchases first.')
   basis=a['cost']/a['quantity']*q; a['realized']+=q*p-f-basis; a['cost']-=basis; a['quantity']-=q; a['sold']+=q; a['sell_total']+=q*p
 result=[]
 for s,a in assets.items():
  a['average_buy']=a['buy_total']/a['bought'] if a['bought'] else Decimal(0)
  a['average_sell']=a['sell_total']/a['sold'] if a['sold'] else Decimal(0)
  a['price']=Decimal(prices[s]) if s in prices else None
  a['value']=a['quantity']*a['price'] if a['price'] is not None else None
  a['unrealized']=a['value']-a['cost'] if a['value'] is not None else None
  result.append({k:float(v) if isinstance(v,Decimal) else v for k,v in a.items()})
 return result
def trade(raw):
 date=datetime.fromisoformat(str(raw['date']).replace('Z','+00:00'))
 if date.tzinfo: date=datetime.fromtimestamp(date.timestamp(),__import__('datetime').timezone.utc).replace(tzinfo=None)
 symbol=symbol_value(raw['symbol'])
 if not symbol or len(symbol)>30: raise ValueError('Invalid token symbol')
 side=raw['side'].lower()
 if side not in ('buy','sell'): raise ValueError('Side must be buy or sell')
 return dict(date=date.isoformat(),symbol=symbol,side=side,quantity=str(number(raw['quantity'],True)),price=str(number(raw['price'])),fee=str(number(raw.get('fee',0))),account=str(raw.get('account','Manual'))[:100])
class Handler(BaseHTTPRequestHandler):
 def setup(self):
  super().setup(); self.connection.settimeout(15)
 def end_headers(self):
  self.send_header('X-Content-Type-Options','nosniff')
  self.send_header('X-Frame-Options','DENY')
  self.send_header('Referrer-Policy','no-referrer')
  self.send_header('Cache-Control','no-store')
  self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'")
  super().end_headers()
 def valid_host(self):
  try: host=urlsplit('//'+self.headers.get('Host','')).hostname
  except ValueError: return False
  allowed={'127.0.0.1','localhost','::1'} | set(filter(None,os.environ.get('ORBIT_ALLOWED_HOSTS','').split(',')))
  if os.environ.get('VERCEL')=='1':allowed|=set(filter(None,[os.environ.get('VERCEL_URL'),os.environ.get('VERCEL_PROJECT_PRODUCTION_URL')]))
  return host in allowed

 def log_message(self,*args): pass
 def send(self,status,data):
  body=json.dumps(data).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(body)
 def user(self,c):
  token=next((x.strip()[8:] for x in self.headers.get('Cookie','').split(';') if x.strip().startswith('session=')),'')
  row=c.execute('SELECT user_id FROM sessions WHERE token=? AND expires>?',(hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
  return row[0] if row else None
 def do_GET(self):
  if not self.valid_host(): self.send(403,{'error':'Invalid host'}); return
  static={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/portfolio_insights.js':('portfolio_insights.js','text/javascript; charset=utf-8'),'/styles.css':('styles.css','text/css; charset=utf-8'),'/advanced_dashboard.js':('advanced_dashboard.js','text/javascript; charset=utf-8'),'/advanced_dashboard.css':('advanced_dashboard.css','text/css; charset=utf-8'),'/target_dashboard.js':('target_dashboard.js','text/javascript; charset=utf-8'),'/target_dashboard.css':('target_dashboard.css','text/css; charset=utf-8'),'/market_dashboard.js':('market_dashboard.js','text/javascript; charset=utf-8'),'/market_dashboard.css':('market_dashboard.css','text/css; charset=utf-8'),'/market_intelligence.js':('market_intelligence.js','text/javascript; charset=utf-8'),'/trade_chart_markers.js':('trade_chart_markers.js','text/javascript; charset=utf-8'),'/market_intelligence.css':('market_intelligence.css','text/css; charset=utf-8')}
  for filename in ('coin_alerts.js','experience_ui.js','chart_tools.js','experience_ui.css','chart_tools.css'):
   static['/'+filename]=(filename,('text/javascript' if filename.endswith('.js') else 'text/css')+'; charset=utf-8')
  if self.path in static:
   filename,kind=static[self.path];body=(ROOT/filename).read_bytes();
   if filename=='index.html' and os.environ.get('VERCEL')=='1':body=body.replace(b'Local development edition',b'Personal cloud edition').replace(b'Local workspace',b'Cloud workspace').replace(b'Private local accounts',b'Private cloud accounts').replace(b'Development edition',b'Personal preview')
   self.send_response(200); self.send_header('Content-Type',kind); self.end_headers(); self.wfile.write(body); return
  if self.path!='/api/state': self.send(404,{'error':'Not found'}); return
  with connect() as c:
   uid=self.user(c)
   if not uid: self.send(401,{'error':'Sign in to continue'}); return
   rows=[dict(r) for r in c.execute('SELECT * FROM trades WHERE user_id=? ORDER BY date,id',(uid,))]
   prices={r['symbol']:r['price'] for r in c.execute('SELECT * FROM prices WHERE user_id=?',(uid,))}
   records,statuses=history_state(c,uid)
   self.send(200,dict(**advanced_portfolio.state(c,uid),**price_targets.state(c,uid),exchanges=exchange_connections.state(c,uid)['connections'],profile=account_features.state(c,uid),network_support=network_support(),reviews=review_state(c,uid,records),history=records,history_status=statuses,email=c.execute('SELECT email FROM users WHERE id=?',(uid,)).fetchone()[0],trades=rows,assets=calculate(rows,prices),wallets=snapshots(c,uid),price_metadata=metadata(c,uid)))
 def do_POST(self):
  if not self.valid_host(): self.send(403,{'error':'Invalid host'}); return
  origin=self.headers.get('Origin')
  scheme='https' if os.environ.get('ORBIT_SECURE_COOKIE')=='1' else 'http'
  if self.headers.get('Sec-Fetch-Site')=='cross-site' or (origin and origin!=scheme+'://'+self.headers.get('Host','')): self.send(403,{'error':'Invalid origin'}); return
  if self.headers.get('Content-Type','').split(';')[0].strip().lower()!='application/json': self.send(415,{'error':'Use application/json'}); return
  if self.headers.get('Transfer-Encoding'): self.send(400,{'error':'Transfer encoding is unsupported'}); return
  try:
   length=int(self.headers.get('Content-Length',0))
   if length<=0 or length>1000000: raise ValueError('Upload must be under 1 MB')
   try:raw=json.loads(self.rfile.read(length))
   except RecursionError:raise ValueError('JSON nesting is too deep') from None
   if not isinstance(raw,dict): raise ValueError('JSON object required')
   with connect() as c:
    if self.path in ('/api/register','/api/login'):
     if not allow_auth(self.client_address[0]): self.send(429,{'error':'Too many sign-in attempts. Retry in 15 minutes.'}); return
     email=str(raw.get('email','')).strip().lower(); pw=str(raw.get('password',''))
     if len(email)>254 or len(pw)>1024: raise ValueError('Email or password is too long')
     if '@' not in email or len(pw)<12: raise ValueError('Use an email and a password of at least 12 characters')
     if self.path=='/api/register':
      allowed_email=os.environ.get('ORBIT_REGISTRATION_EMAIL','').strip().lower()
      if allowed_email and email!=allowed_email:raise ValueError('Registration is restricted on this deployment')
      try: c.execute('INSERT INTO users(email,password) VALUES (?,?)',(email,password(pw)))
      except sqlite3.IntegrityError: raise ValueError('Account already exists')
     row=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
     if row:
      c.commit()
      if getattr(c,'dialect',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(?)',(row['id'],))
      else:c.execute('BEGIN IMMEDIATE')
      row=c.execute('SELECT * FROM users WHERE id=?',(row['id'],)).fetchone()
     verified=password(pw,row['password'].split(':')[0] if row else DUMMY_SALT)
     if not row or not hmac.compare_digest(verified,row['password']): raise ValueError('Incorrect email or password')
     c.execute('DELETE FROM sessions WHERE expires<=?',(time.time(),))
     token=secrets.token_urlsafe(32); c.execute('INSERT INTO sessions VALUES (?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),row['id'],time.time()+86400))
     c.commit()
     self.send_response(200); self.send_header('Set-Cookie','session='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=86400'+('; Secure' if os.environ.get('ORBIT_SECURE_COOKIE')=='1' else '')); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(b'{"ok":true}'); return
    uid=self.user(c)
    if not uid: self.send(401,{'error':'Sign in to continue'}); return
    market_action=self.path in ('/api/market-listings','/api/market-detail','/api/market-chart','/api/market-fundamentals','/api/market-news','/api/intelligence-overview','/api/intelligence-narrative','/api/intelligence-rsi','/api/intelligence-venues','/api/intelligence-flow','/api/intelligence-derivatives','/api/intelligence-exposures')
    if market_action:budget=__import__('cloud_storage').provider_action(uid,kind='market',limit=60,max_concurrent=4) if os.environ.get('DATABASE_URL') else MARKET_BUDGET.action(uid)
    else:budget=(__import__('cloud_storage').provider_action(uid) if os.environ.get('DATABASE_URL') else PROVIDER_BUDGET.action(uid)) if self.path in ('/api/sync','/api/refresh-prices','/api/wallet-details','/api/history','/api/discover-tokens','/api/market-watch-toggle') else nullcontext()
    with budget, providers.deadline(time.monotonic()+30):
     if market_action:
      c.commit()
      with coin_market.persistence(market_cache_read,market_cache_write):
       if self.path=='/api/market-listings':result={**coin_market.listings(),'exchange_coin_ids':sorted(exchange_charts.ASSETS)}
       elif self.path=='/api/market-detail':result=coin_market.detail(raw.get('coin_id'))
       elif self.path=='/api/market-chart':
        source=raw.get('source','coingecko')
        if source=='coingecko':result=coin_market.chart(raw.get('coin_id'),raw.get('days',30),raw.get('kind','line'))
        elif source in ('binance','coinbase'):result=exchange_charts.chart(raw.get('coin_id'),raw.get('days',30),raw.get('kind','line'),source)
        else:raise ValueError('Choose CoinGecko, Binance or Coinbase chart data')
       elif self.path=='/api/market-news':result=market_news.news(raw.get('coin_id'))
       elif self.path=='/api/intelligence-overview':result=market_intelligence.overview()
       elif self.path=='/api/intelligence-narrative':result=market_intelligence.narratives(raw.get('slug','rwa'))
       elif self.path=='/api/intelligence-rsi':result=market_intelligence.rsi()
       elif self.path=='/api/intelligence-venues':result=market_intelligence.venues(raw.get('coin_id'))
       elif self.path=='/api/intelligence-flow':result=market_microstructure.microstructure(raw.get('coin_id'))
       elif self.path=='/api/intelligence-exposures':result=market_microstructure.exposures(raw.get('coin_id'))
       elif self.path=='/api/intelligence-derivatives':result=market_microstructure.derivatives(raw.get('coin_id'))
       else:result=protocol_data.fundamentals(raw.get('coin_id'))
      self.send(200,result);return
     if self.path=='/api/coin-alert-list':self.send(200,coin_alerts.state(c,uid,raw.get('coin_id')));return
     if self.path in ('/api/coin-alert-save','/api/coin-alert-check','/api/coin-alert-delete'):
      prepared=None
      if self.path!='/api/coin-alert-delete':
       c.commit()
       with (__import__('cloud_storage').provider_action(uid,kind='market',limit=60,max_concurrent=4) if os.environ.get('DATABASE_URL') else MARKET_BUDGET.action(uid)),coin_market.persistence(market_cache_read,market_cache_write):prepared=coin_market.detail(raw.get('coin_id'))
      c.commit()
      if getattr(c,'dialect',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(?)',(uid,))
      else:c.execute('BEGIN IMMEDIATE')
      if self.user(c)!=uid:self.send(401,{'error':'Session expired. Sign in again.'});return
      if self.path=='/api/coin-alert-save':coin_alerts.save(c,uid,raw,prepared);result=coin_alerts.state(c,uid,raw.get('coin_id'))
      elif self.path=='/api/coin-alert-check':result=coin_alerts.evaluate(c,uid,prepared)
      else:result=coin_alerts.remove(c,uid,raw)
      c.commit();self.send(200,result);return
     if self.path in ('/api/profile','/api/learning-notes','/api/exchange-state','/api/chart-setup-load'):
      result={'/api/profile':lambda:account_features.state(c,uid),'/api/learning-notes':lambda:account_features.notes(c,uid),'/api/exchange-state':lambda:exchange_connections.state(c,uid),'/api/chart-setup-load':lambda:workspace_features.load(c,uid,raw)}[self.path]()
      self.send(200,result);return
     if self.path in ('/api/profile-save','/api/password-change','/api/learning-note-save','/api/learning-note-delete','/api/exchange-connect','/api/exchange-sync','/api/exchange-delete','/api/chart-setup-save'):
      if self.path=='/api/password-change' and not allow_auth('password:'+str(uid)):self.send(429,{'error':'Too many password attempts. Retry later.'});return
      prepared=None
      if self.path in ('/api/exchange-connect','/api/exchange-sync'):
       c.commit()
       with (__import__('cloud_storage').provider_action(uid) if os.environ.get('DATABASE_URL') else PROVIDER_BUDGET.action(uid)),coin_market.persistence(market_cache_read,market_cache_write):
        prepared=exchange_connections.prepare(raw) if self.path=='/api/exchange-connect' else exchange_connections.sync_prepare(c,uid,raw)
       c.commit()
      if getattr(c,'dialect',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(?)',(uid,))
      else:c.execute('BEGIN IMMEDIATE')
      if self.user(c)!=uid:self.send(401,{'error':'Session expired. Sign in again.'});return
      actions={'/api/profile-save':lambda:account_features.save_profile(c,uid,raw),'/api/password-change':lambda:account_features.change_password(c,uid,raw),'/api/learning-note-save':lambda:account_features.save_note(c,uid,raw),'/api/learning-note-delete':lambda:account_features.delete_note(c,uid,raw),'/api/exchange-connect':lambda:exchange_connections.add(c,uid,prepared),'/api/exchange-sync':lambda:exchange_connections.sync_save(c,uid,*prepared),'/api/exchange-delete':lambda:exchange_connections.delete(c,uid,raw),'/api/chart-setup-save':lambda:workspace_features.save(c,uid,raw)}
      result=actions[self.path]();c.commit();self.send(200,result);return
     if self.path=='/api/market-watchlist':self.send(200,market_watch.state(c,uid));return
     prepared_watch=None
     if self.path=='/api/market-watch-toggle':
      identity=coin_market.identifier(raw.get('coin_id'))
      exists=c.execute('SELECT coin_id FROM market_favorites WHERE user_id=? AND coin_id=?',(uid,identity)).fetchone();c.commit()
      if not exists:
       with coin_market.persistence(market_cache_read,market_cache_write):prepared_watch=market_watch.resolve(identity)
     if self.path in ('/api/trade','/api/import','/api/delete','/api/review','/api/checkpoint','/api/watch-toggle','/api/target-save','/api/target-remove','/api/market-watch-toggle'):
      if getattr(c,'dialect',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(?)',(uid,))
      else:c.execute('BEGIN IMMEDIATE')
     if self.path=='/api/market-watch-toggle':
      result=market_watch.toggle(c,uid,raw,prepared_watch);c.commit();self.send(200,result);return
     if self.path=='/api/target-save':
      wallets=snapshots(c,uid);quotes=metadata(c,uid)
      target=price_targets.save(c,uid,raw,wallets,quotes)
      evaluation=price_targets.evaluate(c,uid,wallets,quotes)
      c.commit();self.send(200,{'ok':True,'target':target,'evaluation':evaluation});return
     elif self.path=='/api/target-remove':
      result=price_targets.remove(c,uid,raw)
      c.commit();self.send(200,{'ok':True,**result});return
     elif self.path=='/api/checkpoint':
      result=advanced_portfolio.checkpoint(c,uid,snapshots(c,uid),metadata(c,uid))
      c.commit();self.send(200,{'ok':True,'checkpoint':result});return
     elif self.path=='/api/watch-toggle':
      result=advanced_portfolio.toggle_watch(c,uid,raw,snapshots(c,uid))
      c.commit();self.send(200,{'ok':True,**result});return
     elif self.path=='/api/import-preview':
      rows=[dict(r) for r in c.execute('SELECT * FROM trades WHERE user_id=?',(uid,))]
      self.send(200,imports.preview(raw.get('csv'),rows,trade,calculate)); return
     elif self.path=='/api/review':
      records,_=history_state(c,uid)
      candidate=next((r for r in review_state(c,uid,records) if r['id']==raw.get('id')),None)
      if not candidate:raise ValueError('Review item not found for this account')
      if candidate['status']!='pending':raise ValueError('This activity was already reviewed; no trades were added')
      action=raw.get('action')
      if action=='dismiss':
       c.execute('INSERT INTO review_decisions VALUES (?,?,?,?)',(uid,candidate['id'],'dismissed',json.dumps({'candidate':candidate,'reviewed_at':int(time.time())})))
      elif action=='confirm':
       count=review_accounting.confirm(c,uid,candidate,raw,trade,calculate,number,symbol_value)
       c.commit();self.send(200,{'ok':True,'added':count});return
      else:raise ValueError('Choose confirm or dismiss')
     elif self.path=='/api/history':
      wallet=c.execute('SELECT id,chain,address FROM wallets WHERE user_id=? AND id=?',(uid,raw.get('id'))).fetchone()
      if not wallet: raise ValueError('Wallet not found')
      old=c.execute('SELECT data FROM history_sync WHERE wallet_id=?',(wallet['id'],)).fetchone()
      previous=json.loads(old['data']) if old else {}
      more=raw.get('more',False)
      if type(more)!=bool: raise ValueError('more must be true or false')
      if more and not any(previous.get('cursors',{}).values()):raise ValueError('No older history page is available')
      try:
       result=history.fetch_history(wallet['chain'],wallet['address'],previous.get('cursors') if more else None)
       if not isinstance(result.get('items'),list) or len(result['items'])>200:raise ValueError('History provider returned too many records')
       for item in result['items']:
        c.execute('INSERT OR REPLACE INTO chain_history VALUES (?,?,?)',(wallet['id'],item['event_id'],json.dumps(item)))
       details={k:v for k,v in result.items() if k!='items'}
       details['adapter_version']=2
       c.execute('INSERT OR REPLACE INTO history_sync VALUES (?,?)',(wallet['id'],json.dumps(details)))
       c.commit();self.send(200,{'ok':True,'fetched':len(result['items']),'has_more':any(result.get('cursors',{}).values()),'coverage':result.get('coverage','')});return
      except ValueError as error:
       details={**previous,'error':str(error),'attempted_at':int(time.time()),'adapter_version':2}
       c.execute('INSERT OR REPLACE INTO history_sync VALUES (?,?)',(wallet['id'],json.dumps(details)))
       c.commit();self.send(200,{'ok':False,'fetched':0,'error':str(error)});return
     elif self.path=='/api/discover-tokens':
      wallet=c.execute('SELECT id,chain,address FROM wallets WHERE user_id=? AND id=?',(uid,raw.get('id'))).fetchone()
      if not wallet:raise ValueError('Wallet not found')
      watched=watched_contracts(c,wallet,raw.get('contracts'))
      discovery=token_discovery.discover(wallet['chain'],wallet['address'])
      contracts=list(dict.fromkeys(watched+discovery['contracts']))
      overflow=len(contracts)>20;contracts=contracts[:20]
      result=token_integrations.token_balances(wallet['chain'],wallet['address'],contracts,include_metadata=True)
      result['coverage']=discovery['coverage']+' '+result.get('coverage','') if wallet['chain'] in providers.EVM_CHAINS else result.get('coverage',discovery['coverage'])
      result['errors']=result.get('errors',[])+discovery.get('errors',[])
      result['has_more']=bool(discovery.get('has_more') or overflow)
      persist_tokens(c,wallet,result,contracts)
      c.commit();self.send(200,{'ok':True,**result});return
     elif self.path=='/api/wallet-details':
      wallet=c.execute('SELECT id,chain,address FROM wallets WHERE user_id=? AND id=?',(uid,raw.get('id'))).fetchone()
      if not wallet: raise ValueError('Wallet not found')
      contracts=watched_contracts(c,wallet,raw.get('contracts'))
      result=token_integrations.token_balances(wallet['chain'],wallet['address'],contracts,include_metadata=True)
      activity={'items':[],'coverage':'Recent activity is currently available for Solana only'}
      if wallet['chain']=='Solana':
       try:
        activity=token_integrations.recent_activity(wallet['chain'],wallet['address'])
        activity['items']=[{'signature':item['signature'],'slot':item['slot'],'timestamp':datetime.fromtimestamp(item['timestamp'],__import__('datetime').timezone.utc).isoformat() if item['timestamp'] is not None else None,'status':'Failed' if item['failed'] else 'Confirmed'} for item in activity.pop('activities')]
       except (ValueError,KeyError,TypeError,OverflowError):activity={'items':[],'coverage':'Recent activity could not be retrieved; retry later'}
      persist_tokens(c,wallet,result,contracts)
      c.commit();self.send(200,{'tokens':result,'activity':activity}); return
     elif self.path=='/api/sync':
      wallets=[dict(r) for r in c.execute('SELECT id,chain,address FROM wallets WHERE user_id=?',(uid,))]
      if len(wallets)>50: raise ValueError('Sync supports up to 50 wallets per account')
      with ThreadPoolExecutor(max_workers=6) as pool:
       results=list(pool.map(sync_wallet,wallets))
      for wid,result in results:
       if 'error' in result:
        old=c.execute('SELECT data FROM wallet_snapshots WHERE wallet_id=?',(wid,)).fetchone()
        if old: result={**json.loads(old[0]),**result}
       c.execute('INSERT OR REPLACE INTO wallet_snapshots VALUES (?,?)',(wid,json.dumps(result)))
     elif self.path=='/api/refresh-prices':
      symbols=[r[0] for r in c.execute('SELECT DISTINCT symbol FROM trades WHERE user_id=?',(uid,))]
      symbols+= [v[0] for v in providers.CHAINS.values()]
      quotes=providers.market_prices(symbols)
      if not quotes: raise ValueError('No price quotes returned. Please retry later.')
      token_updates=[]
      for row in c.execute('SELECT t.wallet_id,t.data,w.chain FROM wallet_tokens t JOIN wallets w ON w.id=t.wallet_id WHERE w.user_id=?',(uid,)):
       updated=token_pricing.enrich(row['chain'],json.loads(row['data']));token_updates.append((row['wallet_id'],json.dumps(updated)))
      if getattr(c,'dialect',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(?)',(uid,))
      else:c.execute('BEGIN IMMEDIATE')
      for wallet_id,data in token_updates:c.execute('INSERT OR REPLACE INTO wallet_tokens VALUES (?,?)',(wallet_id,data))
      for symbol,quote in quotes.items():
       c.execute('INSERT OR REPLACE INTO prices VALUES (?,?,?)',(uid,symbol,quote['price']))
       c.execute('INSERT OR REPLACE INTO price_metadata VALUES (?,?,?,?)',(uid,symbol,quote['source'],quote['updated_at']))
      evaluation=price_targets.evaluate(c,uid,snapshots(c,uid),metadata(c,uid))
      c.commit();self.send(200,{'ok':True,'target_evaluation':evaluation});return
     elif self.path=='/api/remove-wallet':
      wallet=c.execute('SELECT id FROM wallets WHERE user_id=? AND id=?',(uid,raw['id'])).fetchone()
      if not wallet: raise ValueError('Wallet not found')
      c.execute('DELETE FROM wallet_snapshots WHERE wallet_id=?',(raw['id'],))
      c.execute('DELETE FROM wallet_tokens WHERE wallet_id=?',(raw['id'],))
      c.execute('DELETE FROM token_watchlist WHERE wallet_id=?',(raw['id'],))
      c.execute('DELETE FROM chain_history WHERE wallet_id=?',(raw['id'],))
      c.execute('DELETE FROM history_sync WHERE wallet_id=?',(raw['id'],))
      c.execute('DELETE FROM wallets WHERE user_id=? AND id=?',(uid,raw['id']))
     elif self.path in ('/api/trade','/api/import'):
      if self.path=='/api/import':
       digest=hashlib.sha256(raw['csv'].strip().encode()).hexdigest()
       if c.execute('SELECT 1 FROM imports WHERE user_id=? AND digest=?',(uid,digest)).fetchone(): raise ValueError('This CSV has already been imported')
      rows=[dict(r) for r in c.execute('SELECT * FROM trades WHERE user_id=?',(uid,))]
      summary=None
      if self.path=='/api/import':
       summary=imports.preview(raw.get('csv'),rows,trade,calculate)
       if summary['errors']: raise ValueError('CSV has errors: '+ '; '.join('row '+str(e['row'])+': '+e['error'] for e in summary['errors'][:5]))
       additions=summary['trades']
      else: additions=[trade(raw)]
      if not additions: raise ValueError('No new trades to import; rows may already exist')
      if self.path=='/api/import': c.execute('INSERT INTO imports VALUES (?,?)',(uid,digest))
      for i,t in enumerate(additions): t['id']=1000000000+i
      calculate(rows+additions,{})
      for t in additions: c.execute('INSERT INTO trades(user_id,date,symbol,side,quantity,price,fee,account) VALUES (?,?,?,?,?,?,?,?)',(uid,*(t[k] for k in ('date','symbol','side','quantity','price','fee','account'))))
      if summary:
       c.commit(); self.send(200,{'ok':True,'imported':len(additions),'duplicates':summary['duplicates']}); return
     elif self.path=='/api/price':
      c.execute('INSERT OR REPLACE INTO prices VALUES (?,?,?)',(uid,symbol_value(raw['symbol']),str(number(raw['price']))))
      c.execute('INSERT OR REPLACE INTO price_metadata VALUES (?,?,?,?)',(uid,symbol_value(raw['symbol']),'Manual',int(time.time())))
     elif self.path=='/api/wallet-batch':
      if getattr(c,'dialect',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(?)',(uid,))
      else:c.execute('BEGIN IMMEDIATE')
      if self.user(c)!=uid:self.send(401,{'error':'Session expired. Sign in again.'});return
      result=wallet_batch.add(c,uid,raw);c.commit();self.send(200,result);return
     elif self.path=='/api/wallet':
      if getattr(c,'dialect',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(?)',(uid,))
      else:c.execute('BEGIN IMMEDIATE')
      if self.user(c)!=uid:self.send(401,{'error':'Session expired. Sign in again.'});return
      if c.execute('SELECT COUNT(*) AS n FROM wallets WHERE user_id=?',(uid,)).fetchone()['n']>=50:raise ValueError('Maximum 50 connected addresses per account')
      chain=raw['chain']; address=providers.validate_address(chain,raw['address'])
      if chain not in providers.CHAINS or not 20<=len(address)<=100: raise ValueError('Choose a chain and enter a public address')
      c.execute('INSERT INTO wallets(user_id,chain,address,label) VALUES (?,?,?,?)',(uid,chain,address,str(raw.get('label','Wallet'))[:100]))
     elif self.path=='/api/delete':
      rows=[dict(r) for r in c.execute('SELECT * FROM trades WHERE user_id=? AND id!=?',(uid,raw['id']))]; calculate(rows,{})
      c.execute('DELETE FROM trades WHERE user_id=? AND id=?',(uid,raw['id']))
     elif self.path=='/api/logout':
      c.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
      c.commit(); self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Set-Cookie','session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'); self.end_headers(); self.wfile.write(b'{"ok":true}'); return
     else: self.send(404,{'error':'Not found'}); return
   self.send(200,{'ok':True})
  except sqlite3.OperationalError: self.send(503,{'error':'Portfolio storage is busy. Please retry shortly.'})
  except BudgetExceeded as e: self.send(429,{'error':str(e)})
  except (ValueError,KeyError,TypeError,AttributeError,OverflowError,sqlite3.IntegrityError) as e: self.send(400,{'error':str(e)})
  except Exception: self.send(500,{'error':'Unable to complete request'})
if __name__=='__main__':
 init(); print('Portfolio tracker: http://127.0.0.1:8042',flush=True); BoundedHTTPServer(('127.0.0.1',8042),Handler).serve_forever()

