"""Encrypted, read-only Binance spot snapshots. Never places orders or transfers."""
import base64,hashlib,hmac,json,os,re,secrets,time,unicodedata,urllib.request,urllib.error
from urllib.parse import urlencode
from decimal import Decimal,InvalidOperation,localcontext
import providers
import exchange_charts
import coin_market
PERMISSIONS=('enableWithdrawals','enableInternalTransfer','enableMargin','enableFutures','permitsUniversalTransfer','enableVanillaOptions','enableFixApiTrade','enableSpotAndMarginTrading','enablePortfolioMarginTrading')
PATHS=('/sapi/v1/account/apiRestrictions','/api/v3/account')

def init(c):
 c.execute('CREATE TABLE IF NOT EXISTS exchange_connections (user_id INTEGER NOT NULL,id TEXT NOT NULL,label TEXT NOT NULL,credentials TEXT NOT NULL,snapshot TEXT NOT NULL,PRIMARY KEY(user_id,id))')

def master_key():
 try:
  value=os.environ.get('ORBIT_EXCHANGE_KEY','');key=base64.b64decode(value,altchars=b'-_',validate=True)
  if len(key)!=32:raise ValueError()
  return key
 except (ValueError,TypeError):raise ValueError('Exchange connections are not configured. Set ORBIT_EXCHANGE_KEY on the server.') from None

def encryption_keys():
 current=os.environ.get('ORBIT_EXCHANGE_KEY_ID','primary')
 if not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',current):raise ValueError('Exchange encryption key ID is invalid')
 try:
  previous=json.loads(os.environ.get('ORBIT_EXCHANGE_PREVIOUS_KEYS','{}'))
  if not isinstance(previous,dict) or len(previous)>8:raise ValueError()
  keys={}
  for kid,value in previous.items():
   if not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',kid):raise ValueError()
   decoded=base64.b64decode(value,altchars=b'-_',validate=True)
   if len(decoded)!=32 or kid==current:raise ValueError()
   keys[kid]=decoded
  keys[current]=master_key()
  return current,keys
 except (ValueError,TypeError):raise ValueError('Exchange encryption key configuration is invalid') from None

def crypt(uid,identity,value,decrypt=False):
 try:
  from cryptography.hazmat.primitives.ciphers.aead import AESGCM
 except ImportError:raise ValueError('Exchange encryption dependency is unavailable') from None
 current,keys=encryption_keys();binding='orbit:binance:'+str(uid)+':'+identity
 try:
  if decrypt:
   if not isinstance(value,str) or len(value)>8192:raise ValueError()
   if ':' in value:
    version,kid,encoded=value.split(':',2)
    if version!='v1' or kid not in keys:raise ValueError()
    aad=(binding+':v1:'+kid).encode();key=keys[kid]
   else:
    # Legacy records used the unversioned active key and binding.
    encoded=value;aad=binding.encode();key=keys[current]
   blob=base64.b64decode(encoded,altchars=b'-_',validate=True)
   if len(blob)<28:raise ValueError()
   result=json.loads(AESGCM(key).decrypt(blob[:12],blob[12:],aad))
   if not isinstance(result,dict):raise ValueError()
   return result
  nonce=secrets.token_bytes(12);aad=(binding+':v1:'+current).encode()
  encrypted=base64.urlsafe_b64encode(nonce+AESGCM(keys[current]).encrypt(nonce,json.dumps(value).encode(),aad)).decode()
  return 'v1:'+current+':'+encrypted
 except Exception:raise ValueError('Exchange credentials could not be decrypted. Reconnect this account.') from None

def rewrap_credentials(c,uid):
 """Re-encrypt an owner's records with the active key; caller owns transaction.
 Retain previous keys until every account and required backup has been migrated.
 """
 rows=list(c.execute('SELECT id,credentials FROM exchange_connections WHERE user_id=?',(uid,)))
 updates=[(crypt(uid,row['id'],crypt(uid,row['id'],row['credentials'],True)),uid,row['id']) for row in rows]
 for encrypted,owner,identity in updates:c.execute('UPDATE exchange_connections SET credentials=? WHERE user_id=? AND id=?',(encrypted,owner,identity))
 return len(updates)

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def signed(path,key,secret):
 if path not in PATHS:raise ValueError('Unsupported exchange operation')
 params={'timestamp':int(time.time()*1000),'recvWindow':5000}
 if path==PATHS[1]:params['omitZeroBalances']='true'
 query=urlencode(params)
 signature=hmac.new(secret.encode(),query.encode(),hashlib.sha256).hexdigest()
 req=urllib.request.Request('https://api.binance.com'+path+'?'+query+'&signature='+signature,headers={'X-MBX-APIKEY':key,'User-Agent':'OrbitPortfolio/1.0'})
 cutoff=getattr(providers._REQUEST_CONTEXT,'cutoff',None);timeout=min(10,cutoff-time.monotonic()) if cutoff else 10
 if timeout<=0:raise ValueError('Exchange request deadline reached')
 try:
  with urllib.request.build_opener(NoRedirect).open(req,timeout=max(.1,timeout)) as response:
   body=response.read(2*1024*1024+1)
   if len(body)>2*1024*1024:raise ValueError()
   result=json.loads(body)
  if not isinstance(result,dict) or 'code' in result:raise ValueError()
  return result
 except Exception:raise ValueError('Binance could not verify this read-only key. Check its permissions, IP restrictions, region and server clock.') from None

def validate_credentials(raw):
 key=raw.get('api_key');secret=raw.get('api_secret')
 if not all(isinstance(x,str) and re.fullmatch(r'[A-Za-z0-9]{32,128}',x) for x in (key,secret)):raise ValueError('Enter a Binance HMAC API key and secret')
 return key,secret

def snapshot(key,secret):
 permissions=signed(PATHS[0],key,secret)
 # Official Binance apiRestrictions schema lists these flags. Omission is not
 # proof that a potentially dangerous permission is disabled. Fail closed.
 if not isinstance(permissions,dict):raise ValueError('Invalid Binance permission response')
 if permissions.get('enableReading') is not True:raise ValueError('Enable Reading on this Binance API key')
 if any(x not in permissions or type(permissions[x]) is not bool for x in PERMISSIONS):raise ValueError('Binance did not provide all permission flags. This key cannot be verified as read-only; reconnect a standard Binance HMAC key.')
 if any(permissions[x] for x in PERMISSIONS) or any((type(v) is not bool or v is True) and k.startswith(('enable','permits')) and k not in ('enableReading','enableFixReadOnly') for k,v in permissions.items()):raise ValueError('Use a reading-only key. Disable trading, withdrawals, margin, futures, options and transfers.')
 account=signed(PATHS[1],key,secret)
 if not isinstance(account,dict):raise ValueError('Invalid Binance balance response (BALANCE_OBJECT)')
 rows=account.get('balances')
 if not isinstance(rows,list) or len(rows)>5000:raise ValueError('Invalid Binance balance response (BALANCE_LIST)')
 balances=[];seen=set()
 for row in rows:
  reason='BALANCE_ROW'
  try:
   if not isinstance(row,dict):raise ValueError()
   reason='BALANCE_AMOUNT'
   if not all(isinstance(row.get(k),str) and 0<len(row[k])<=80 for k in ('free','locked')):raise ValueError()
   free=Decimal(row['free']);locked=Decimal(row['locked'])
   if not all(n.is_finite() and n>=0 and n.adjusted()<=30 and n.as_tuple().exponent>=-30 for n in (free,locked)):raise ValueError()
   with localcontext() as context:
    context.prec=128
    quantity=free+locked
   # Binance may return zero rows despite the requested filter. No asset
   # metadata is needed for a zero position; it must not reject real holdings.
   if not quantity:continue
   reason='BALANCE_ASSET'
   asset=row.get('asset')
   # Preserve the exact exchange identity. Never normalize it into a priced
   # known symbol; unfamiliar names remain unpriced. Exclude controls/markup.
   if not isinstance(asset,str) or not 1<=len(asset)<=64 or not all(unicodedata.category(ch)[0] in ('L','N') or ch in '_.-' for ch in asset):raise ValueError()
   reason='BALANCE_DUPLICATE'
   if asset in seen:raise ValueError()
   seen.add(asset)
   balances.append({'asset':asset,'free':str(free),'locked':str(locked),'quantity':str(quantity)})
  except (ValueError,KeyError,TypeError,InvalidOperation):raise ValueError('Invalid Binance balance response ('+reason+')') from None
 # Curated exchange asset IDs only. Unknown symbols remain explicitly unpriced.
 identities={symbol:identity for identity,symbol in exchange_charts.ASSETS.items()};identities.update(USDC='usd-coin',USDT='tether',BNB='binancecoin')
 try:quotes={r['id']:r for r in coin_market.listings()['coins']}
 except ValueError:quotes={}
 for row in balances:
  identity=identities.get(row['asset']);quote=quotes.get(identity,{})
  row['coin_id']=identity;row['price_usd']=quote.get('current_price');row['change_24h_pct']=quote.get('price_change_percentage_24h');row['price_updated_at']=quote.get('last_updated')
  with localcontext() as context:
   context.prec=160
   row['value_usd']=str(Decimal(row['quantity'])*Decimal(str(row['price_usd']))) if row['price_usd'] is not None else None
 return {'balances':balances,'updated_at':int(time.time()),'coverage':'Binance Spot free + locked balances only. Earn, futures, margin and historical cost basis are not included. Manual refresh.','permissions_verified':True,'ip_restricted':permissions.get('ipRestrict') is True}

def state(c,uid):
 try:encryption_keys();configured=True
 except ValueError:configured=False
 connections=[]
 for row in c.execute('SELECT id,label,snapshot FROM exchange_connections WHERE user_id=? ORDER BY label,id',(uid,)):
  connections.append({'id':row['id'],'label':row['label'],'exchange':'binance','snapshot':json.loads(row['snapshot'])})
 return {'configured':configured,'connections':connections}

def prepare(raw):
 master_key();key,secret=validate_credentials(raw);label=raw.get('label','Binance')
 if not isinstance(label,str) or not 1<=len(label.strip())<=80:raise ValueError('Use an exchange label of 1 to 80 characters')
 return {'label':label.strip(),'credentials':{'api_key':key,'api_secret':secret},'snapshot':snapshot(key,secret)}

def add(c,uid,prepared):
 if c.execute('SELECT COUNT(*) AS n FROM exchange_connections WHERE user_id=?',(uid,)).fetchone()['n']>=5:raise ValueError('Connect up to five exchange accounts')
 identity=secrets.token_hex(16);encrypted=crypt(uid,identity,prepared['credentials'])
 c.execute('INSERT INTO exchange_connections(user_id,id,label,credentials,snapshot) VALUES (?,?,?,?,?)',(uid,identity,prepared['label'],encrypted,json.dumps(prepared['snapshot'])))
 return state(c,uid)

def identity(raw):
 value=raw.get('id')
 if not isinstance(value,str) or not re.fullmatch(r'[a-f0-9]{32}',value):raise ValueError('Invalid exchange connection')
 return value

def sync_prepare(c,uid,raw):
 value=identity(raw);row=c.execute('SELECT credentials FROM exchange_connections WHERE user_id=? AND id=?',(uid,value)).fetchone()
 if not row:raise ValueError('Exchange connection not found')
 credentials=crypt(uid,value,row['credentials'],True)
 return value,snapshot(credentials['api_key'],credentials['api_secret'])

def sync_save(c,uid,value,result):
 c.execute('UPDATE exchange_connections SET snapshot=? WHERE user_id=? AND id=?',(json.dumps(result),uid,value))
 return state(c,uid)

def delete(c,uid,raw):
 c.execute('DELETE FROM exchange_connections WHERE user_id=? AND id=?',(uid,identity(raw)))
 return state(c,uid)
