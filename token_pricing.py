"""Indicative USD quotes matched by network+contract, never by token ticker."""
import time,threading
from decimal import Decimal,InvalidOperation,localcontext
from urllib.parse import quote
import providers
DEX_CHAINS={'Ethereum':'ethereum','Optimism':'optimism','BNB Chain':'bsc','Base':'base','Arbitrum':'arbitrum','Polygon':'polygon','Avalanche':'avalanche','Sonic':'sonic','Gnosis':'gnosischain','Celo':'celo','Arc':'arc','Monad':'monad','Robinhood Chain':'robinhood','Linea':'linea','Solana':'solana'}
MIN_LIQUIDITY=Decimal('10000')
CACHE={};LOCK=threading.Lock()
def decimal(value,positive=False):
 text=str(value)
 if len(text)>350:raise ValueError('Invalid market number')
 try:n=Decimal(text)
 except InvalidOperation:raise ValueError('Invalid market number') from None
 if not n.is_finite() or n<0 or (positive and n==0) or n.adjusted()>78 or not -255<=n.as_tuple().exponent<=78:raise ValueError('Invalid market number')
 return n

def get_quote(chain,contract):
 if chain not in DEX_CHAINS:return None
 contract=providers.validate_address(chain,contract);key=(chain,contract);now=time.time()
 with LOCK:
  cached=CACHE.get(key)
  if cached and now-cached[0]<60:return cached[1]
 dexchain=DEX_CHAINS[chain]
 rows=providers.request_json('https://api.dexscreener.com/token-pairs/v1/'+dexchain+'/'+quote(contract,safe=''))
 if not isinstance(rows,list) or len(rows)>500:raise ValueError('Invalid token price response')
 candidates=[]
 for row in rows:
  try:
   if not isinstance(row,dict) or row.get('chainId')!=dexchain:continue
   base=row.get('baseToken',{}).get('address')
   if providers.validate_address(chain,base)!=contract:continue
   price=decimal(row.get('priceUsd'),True);liquidity=decimal(row.get('liquidity',{}).get('usd'),True)
   if liquidity<MIN_LIQUIDITY or price>Decimal('1e12'):continue
   pair=providers.validate_address(chain,row.get('pairAddress'))
   candidates.append((liquidity,pair,price,row))
  except (ValueError,TypeError,AttributeError):continue
 result=None
 if candidates:
  liquidity,pair,price,selected=max(candidates,key=lambda item:(item[0],item[1]))
  result={'price_usd':str(price),'price_source':'DEX Screener','price_fetched_at':int(now),'price_pair_url':'https://dexscreener.com/'+dexchain+'/'+pair,'price_liquidity_usd':str(liquidity),'price_stale':False}
  result['market_dex']=str(selected.get('dexId') or 'Unknown')[:60]
  result['market_change_24h_pct']=None;result['market_volume_24h_usd']=None
  try:
   volume=decimal(selected.get('volume',{}).get('h24'))
   result['market_volume_24h_usd']=str(volume)
  except (ValueError,AttributeError):pass
  try:
   raw=str(selected.get('priceChange',{}).get('h24'))
   if len(raw)>350:raise ValueError()
   change=Decimal(raw)
   if not change.is_finite() or change<Decimal('-100') or change>Decimal('1e9') or not -255<=change.as_tuple().exponent<=78:raise ValueError()
   result['market_change_24h_pct']=str(change)
  except (ValueError,InvalidOperation,AttributeError):pass
 with LOCK:
  if len(CACHE)>=2000:CACHE.pop(min(CACHE,key=lambda item:CACHE[item][0]),None)
  CACHE[key]=(now,result)
 return result

def enrich(chain,snapshot):
 result={**snapshot,'tokens':[],'price_version':1}
 for original in snapshot.get('tokens',[]):
  token=dict(original);identity_valid=False
  try:
   identity=token.get('contract') or token.get('mint')
   if not identity:raise ValueError('No supported contract identity for pricing')
   expected=providers.validate_address(chain,identity)
   if token.get('asset_id')!=chain+':'+expected:raise ValueError('Token identity does not match this network')
   identity_valid=True
   market=get_quote(chain,expected)
   if market is None:raise ValueError('No eligible contract-specific USD quote with sufficient pool liquidity')
   quantity=decimal(token.get('quantity'))
   with localcontext() as context:
    context.prec=500
    value=quantity*decimal(market['price_usd'],True)
   token.update(market);token['value_usd']=format(value,'f');token.pop('price_error',None)
  except (ValueError,TypeError,KeyError):
   token['price_error']='USD quote unavailable; refresh later or use verified manual valuation.'
   if identity_valid and token.get('price_usd') is not None:
    token['price_stale']=True
    try:
     with localcontext() as context:
      context.prec=500
      token['value_usd']=format(decimal(token['quantity'])*decimal(token['price_usd'],True),'f')
    except (ValueError,KeyError):token['price_usd']=None;token['value_usd']=None
   else:
    token['price_usd']=None;token['value_usd']=None;token['price_source']=None;token['price_fetched_at']=None;token['price_stale']=False
    for field in ('price_liquidity_usd','price_pair_url','market_dex','market_volume_24h_usd','market_change_24h_pct'):token[field]=None
  result['tokens'].append(token)
 return result
