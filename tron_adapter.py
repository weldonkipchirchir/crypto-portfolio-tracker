"""Read-only TRON mainnet native balance and bounded top-level transaction history.

Official API: https://developers.tron.network/reference/get-transaction-info-by-account-address
No signing, broadcasting, token approvals, or client-supplied provider URLs.
"""
import hashlib,hmac,os,re,time
from datetime import datetime,timezone,timedelta
from decimal import Decimal,localcontext
from urllib.parse import urlencode
import providers

BASE='https://api.trongrid.io'
ALPHABET='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def _encode(payload):
 raw=payload+hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
 value=int.from_bytes(raw,'big');out=''
 while value:value,digit=divmod(value,58);out=ALPHABET[digit]+out
 return '1'*(len(raw)-len(raw.lstrip(b'\0')))+out

def validate_address(address):
 if not isinstance(address,str):raise ValueError('Enter a TRON mainnet address')
 address=address.strip()
 if re.fullmatch(r'41[0-9a-fA-F]{40}',address):return _encode(bytes.fromhex(address))
 if not re.fullmatch(r'T[1-9A-HJ-NP-Za-km-z]{33}',address):raise ValueError('TRON requires a mainnet T address or 41-prefixed hexadecimal address')
 value=0
 for char in address:value=value*58+ALPHABET.index(char)
 raw=value.to_bytes((value.bit_length()+7)//8,'big')
 if len(raw)!=25 or raw[0]!=0x41 or not hmac.compare_digest(raw[-4:],hashlib.sha256(hashlib.sha256(raw[:-4]).digest()).digest()[:4]):raise ValueError('Invalid TRON address checksum')
 return address

def _headers():
 key=os.environ.get('TRON_PRO_API_KEY')
 return {'TRON-PRO-API-KEY':key} if key else {}

def _request(url,payload=None):
 response=providers.request_json(url,payload,headers=_headers())
 if not isinstance(response,dict) or response.get('Error') or response.get('error') or response.get('success') is False:raise ValueError('TRON provider rejected the request. Configure TRON_PRO_API_KEY or retry later.')
 return response

def _integer(value):
 if type(value) not in (int,str) or not re.fullmatch(r'[0-9]{1,78}',str(value)):raise ValueError('TRON provider returned an invalid amount')
 return int(value)

def _units(value):
 with localcontext() as ctx:
  ctx.prec=100
  return format(Decimal(value)/Decimal(10**6),'f')

def _fingerprint(value):
 if value is None:return None
 if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_+/=\-]{1,2048}',value):raise ValueError('Invalid TRON history cursor')
 return value

def balance(address):
 address=validate_address(address);result=_request(BASE+'/wallet/getaccount',{'address':address,'visible':True})
 if result.get('address') and validate_address(result['address'])!=address:raise ValueError('TRON provider returned another account')
 if result and 'address' not in result:raise ValueError('TRON provider returned malformed account data')
 amount=_integer(result.get('balance',0))
 return {'symbol':'TRX','quantity':_units(amount),'updated_at':int(time.time()),'coverage':'Liquid native TRX only, latest head state; excludes staked TRX, TRC-10 and TRC-20 balances.'}

def coverage():
 return 'TRON confirmed top-level transaction history, 20 per page. Native TransferContract amounts use 6 decimals. Other calls are metadata only, excluded from review. No TRC-20, TRC-10, internal transfers, staking balances, swap interpretation or original purchase cost. Fees are unknown unless explicitly provided in a receipt.'

def fetch_history(address,cursors=None):
 address=validate_address(address)
 if cursors is not None and (not isinstance(cursors,dict) or set(cursors)!={'transactions'}):raise ValueError('Invalid TRON history cursor')
 cursor=_fingerprint(cursors['transactions']) if cursors is not None else None
 if cursors is not None and cursor is None:return {'items':[],'cursors':{'transactions':None},'coverage':coverage(),'updated_at':int(time.time())}
 params={'only_confirmed':'true','limit':20,'order_by':'block_timestamp,desc'}
 if cursor:params['fingerprint']=cursor
 result=_request(BASE+'/v1/accounts/'+address+'/transactions?'+urlencode(params))
 try:
  rows=result['data'];meta=result['meta']
  if not isinstance(rows,list) or len(rows)>20 or not isinstance(meta,dict):raise ValueError('TRON provider returned an invalid history page')
  following=_fingerprint(meta.get('fingerprint'))
  if following and following==cursor:raise ValueError('TRON history cursor did not advance')
  items=[]
  for row in rows:
   txid=row['txID']
   if not isinstance(txid,str) or not re.fullmatch(r'[0-9a-fA-F]{64}',txid):raise ValueError('Invalid TRON transaction identifier')
   stamp=_integer(row['block_timestamp'])
   if stamp>253402300799999:raise ValueError('Invalid TRON timestamp')
   date=(datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(milliseconds=stamp)).isoformat()
   contracts=row['raw_data']['contract']
   if not isinstance(contracts,list) or not 1<=len(contracts)<=16:raise ValueError('Invalid TRON transaction contracts')
   ret=row.get('ret',[])
   if not isinstance(ret,list) or len(ret)>16:raise ValueError('Invalid TRON execution status')
   outcomes=[item.get('contractRet') for item in ret if isinstance(item,dict)]
   status='confirmed' if len(outcomes)==len(contracts) and all(v=='SUCCESS' for v in outcomes) else 'failed' if any(v not in (None,'SUCCESS') for v in outcomes) else 'unknown'
   for index,contract in enumerate(contracts):
    kind=contract['type'];value=contract['parameter']['value']
    source=validate_address(value['owner_address']) if value.get('owner_address') else None
    target=validate_address(value['to_address']) if value.get('to_address') else None
    if source!=address and target!=address:
     # Some contract transactions reference an address in events/internal effects;
     # retain metadata without claiming a transfer or counterparty.
     if kind=='TransferContract':raise ValueError('TRON provider returned another wallet transfer')
    native=kind=='TransferContract' and len(contracts)==1
    quantity=_units(_integer(value['amount'])) if native else None
    fee=None;receipt=row.get('receipt')
    if source==address and isinstance(receipt,dict) and 'energy_fee' in receipt and 'net_fee' in receipt:
     fee=_units(_integer(receipt['energy_fee'])+_integer(receipt['net_fee']))
    items.append({'event_id':'Tron:transaction:'+txid.lower()+':'+str(index),'hash':txid.lower(),'date':date,'kind':'native_transfer' if native else 'contract_activity',
     'direction':'self' if source==target==address else 'out' if source==address else 'in' if target==address else 'unknown',
     'asset':'TRX' if native else str(kind)[:100],'asset_id':'Tron:native' if native else 'Tron:activity:'+str(kind)[:100],
     'quantity':quantity,'fee':fee,'status':status,'from_address':source,'to_address':target,'identity_verified':native,
     'review_eligible':native and status=='confirmed','decimals':6 if native else None,'contract_type':str(kind)[:100],
     'note':'Top-level native transfer; no purchase cost inferred.' if native else 'Transaction metadata only; token transfers and internal value changes are not decoded.'})
  return {'items':items,'cursors':{'transactions':following},'coverage':coverage(),'updated_at':int(time.time())}
 except (KeyError,TypeError,AttributeError,OverflowError):raise ValueError('TRON provider returned malformed transaction data') from None
