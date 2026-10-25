"""Read-only Sui net balance history using the live-verified mainnet GraphQL schema.

Source: https://docs.sui.io/develop/accessing-data/graphql/query-with-graphql
Balance changes are net effects, not swap execution or original purchase records.
"""
import os,re,time
from decimal import Decimal,localcontext
from datetime import datetime
import providers

QUERY='''query OrbitHistory($owner:SuiAddress!,$before:String){
 transactions(last:10,before:$before,filter:{affectedAddress:$owner}){
  pageInfo{hasPreviousPage startCursor}
  nodes{digest gasInput{gasSponsor{address}} effects{timestamp status
   gasEffects{gasSummary{computationCost storageCost storageRebate}}
   balanceChanges(first:20){pageInfo{hasNextPage} nodes{owner{address} coinType{repr} amount}}
  }}
 }
}'''
NATIVE='0x2::sui::SUI'

def cursor_value(value):
 if value is None:return None
 if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_+/=\-]{1,2048}',value):raise ValueError('Invalid Sui history cursor')
 return value

def integer(value,signed=True):
 if type(value) not in (str,int) or not re.fullmatch(r'-?[0-9]{1,78}' if signed else r'[0-9]{1,78}',str(value)):raise ValueError('Invalid Sui balance amount')
 return int(value)

def units(value):
 with localcontext() as ctx:
  ctx.prec=100
  return format(Decimal(value)/Decimal(10**9),'f')

def coin_type(value):
 if not isinstance(value,str) or len(value)>500 or not re.fullmatch(r'0x[0-9a-fA-F]{1,64}::[A-Za-z_][A-Za-z0-9_]*::[A-Za-z_][A-Za-z0-9_]*(?:<[A-Za-z0-9_:, <>]+>)?',value):raise ValueError('Invalid Sui coin type')
 address,module,name=value.split('::',2)
 return '0x'+address[2:].lower().lstrip('0')+'::'+module+'::'+name

def fetch_history(address,cursors=None):
 address=providers.validate_address('Sui',address)
 if cursors is not None and (not isinstance(cursors,dict) or set(cursors)!={'transactions'}):raise ValueError('Invalid Sui history cursor')
 before=cursor_value(cursors['transactions']) if cursors is not None else None
 if cursors is not None and before is None:return {'items':[],'cursors':{'transactions':None},'coverage':coverage(),'updated_at':int(time.time())}
 response=providers.request_json(os.environ.get('SUI_GRAPHQL_URL',providers.CHAINS['Sui'][3]),{'query':QUERY,'variables':{'owner':address,'before':before}})
 try:
  connection=response['data']['transactions'];nodes=connection['nodes'];info=connection['pageInfo']
  if not isinstance(nodes,list) or len(nodes)>10 or type(info['hasPreviousPage'])!=bool:raise ValueError('Invalid Sui history page')
  following=cursor_value(info['startCursor']) if info['hasPreviousPage'] else None
  if info['hasPreviousPage'] and (following is None or following==before):raise ValueError('Sui history pagination did not advance')
  items=[]
  for tx in nodes:
   digest=tx['digest']
   if not isinstance(digest,str) or not re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]{32,64}',digest):raise ValueError('Invalid Sui transaction digest')
   effects=tx['effects'];stamp=effects['timestamp']
   if stamp is not None:
    if not isinstance(stamp,str) or len(stamp)>40:raise ValueError('Invalid Sui timestamp')
    datetime.fromisoformat(stamp.replace('Z','+00:00'))
   status={'SUCCESS':'confirmed','FAILURE':'failed'}.get(effects['status'],'unknown')
   changes=effects['balanceChanges']
   if not isinstance(changes['nodes'],list) or len(changes['nodes'])>20:raise ValueError('Invalid Sui balance changes')
   if changes['pageInfo']['hasNextPage'] is not False:raise ValueError('Sui transaction exceeds 20 balance changes; use a dedicated indexer to inspect this transaction')
   gas_payer=(tx.get('gasInput') or {}).get('gasSponsor')
   gas_payer=providers.validate_address('Sui',gas_payer['address']) if gas_payer else None
   summary=(effects.get('gasEffects') or {}).get('gasSummary');gas=None
   if summary is not None:gas=integer(summary['computationCost'],False)+integer(summary['storageCost'],False)-integer(summary['storageRebate'],False)
   aggregate={}
   for change in changes['nodes']:
    if not change.get('owner'):continue
    owner=providers.validate_address('Sui',change['owner']['address'])
    if owner!=address:continue
    token=coin_type(change['coinType']['repr']);aggregate[token]=aggregate.get(token,0)+integer(change['amount'])
   for token,raw in sorted(aggregate.items()):
    native=token==NATIVE;amount=raw;gas_inclusive=native and (gas is None or gas_payer is None)
    if native and gas is not None and gas_payer==address:amount+=gas
    if amount==0 and not (native and gas_payer==address and gas is not None):continue
    eligible=native and not gas_inclusive and status=='confirmed'
    items.append({'event_id':'Sui:balance:'+digest+':'+token,'hash':digest,'date':stamp,'kind':'contract_activity' if amount==0 else 'native_transfer' if native else 'token_balance_change',
     'direction':'out' if amount<0 else 'in' if amount>0 else 'self','asset':'SUI' if native else token,'asset_id':'Sui:native' if native else 'Sui:'+token,
     'quantity':units(abs(amount)) if native else None,'raw_quantity':str(abs(raw)),'decimals':9 if native else None,
     'fee':units(gas) if native and gas_payer==address and gas is not None and gas>=0 else None,'gas_net_cost':units(gas) if native and gas_payer==address and gas is not None else None,
     'gas_inclusive':gas_inclusive,'review_eligible':eligible,'status':status,'identity_verified':native,'balance_change':True,
     'note':'Net balance change; token decimals unavailable, raw units only.' if not native else 'Net balance change includes gas; excluded from review.' if gas_inclusive else 'Native balance change adjusted for actual payer gas cost; no swap interpretation.'})
  return {'items':items,'cursors':{'transactions':following},'coverage':coverage(),'updated_at':int(time.time())}
 except (KeyError,TypeError,AttributeError,OverflowError):raise ValueError('Sui history provider returned malformed transaction data') from None

def coverage():
 return 'Sui net balance changes, 10 transactions per page and at most 20 balance changes per transaction. Native SUI has 9 decimals. Other coins show raw integer units only and are excluded from accounting review. Gas is restored only with known payer and gas summary. No original cost, NFT history, internal call interpretation or swap verification.'
