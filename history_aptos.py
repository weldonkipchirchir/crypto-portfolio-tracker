"""Bounded Aptos signed-account history; transfers never imply purchases."""
import os,re,time
from datetime import datetime,timezone
from decimal import Decimal,localcontext
from urllib.parse import urlsplit
import providers

STREAM='transactions'
COVERAGE='Aptos account-signed sequence-number transactions only, up to 25 per page. Incoming transfers and orderless transactions are not complete. Only verified native APT transfers are decoded; fungible assets, swaps and purchase cost are not inferred. Fees are native APT.'

def _uint(value):
    if type(value) not in (str,int) or not re.fullmatch(r'[0-9]{1,20}',str(value)) or int(value)>2**64-1:raise ValueError('Invalid Aptos unsigned integer')
    return int(value)

def _units(value):
    with localcontext() as ctx:
        ctx.prec=80
        return format(Decimal(value)/Decimal(10**8),'f')

def _tag(value):
    if not isinstance(value,str):return ''
    parts=value.replace(' ','').split('::')
    if len(parts)!=3:return ''
    try:return providers.validate_address('Aptos',parts[0])+'::'+parts[1]+'::'+parts[2]
    except ValueError:return ''

APT=_tag('0x1::aptos_coin::AptosCoin')
TRANSFER=_tag('0x1::aptos_account::transfer')
COIN_TRANSFER=_tag('0x1::coin::transfer')

def fetch_history(address,cursors=None):
    address=providers.validate_address('Aptos',address)
    if cursors is not None and (not isinstance(cursors,dict) or set(cursors)-{STREAM}):raise ValueError('Invalid Aptos history cursor')
    cursor=(cursors or {}).get(STREAM)
    if cursors is not None and STREAM in cursors and cursor is None:return {'items':[],'cursors':{STREAM:None},'coverage':COVERAGE,'updated_at':int(time.time())}
    if cursor is not None:
        if not isinstance(cursor,dict) or set(cursor)!={'end'}:raise ValueError('Invalid Aptos history cursor')
        end=_uint(cursor['end'])
    base=os.environ.get('APT_HISTORY_URL','https://fullnode.mainnet.aptoslabs.com/v1').rstrip('/')
    parsed=urlsplit(base)
    if parsed.scheme!='https' or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:raise ValueError('Invalid Aptos history provider configuration')
    if cursor is None:
        account=providers.request_json(base+'/accounts/'+address)
        if not isinstance(account,dict):raise ValueError('Invalid Aptos account response')
        end=_uint(account.get('sequence_number'))
    if not end:return {'items':[],'cursors':{STREAM:None},'coverage':COVERAGE,'updated_at':int(time.time())}
    start=max(0,end-25)
    rows=providers.request_json(base+'/accounts/'+address+'/transactions?limit='+str(end-start)+'&start='+str(start))
    if not isinstance(rows,list) or len(rows)>25:raise ValueError('Invalid Aptos history page')
    items=[];seen=set()
    for row in rows:
        try:
            if not isinstance(row,dict) or row.get('type')!='user_transaction':raise ValueError()
            sender=providers.validate_address('Aptos',row['sender']);seq=_uint(row['sequence_number'])
            if sender!=address or not start<=seq<end or seq in seen:raise ValueError()
            seen.add(seq)
            txhash=row['hash']
            if not isinstance(txhash,str) or not re.fullmatch(r'0x[0-9a-fA-F]{64}',txhash):raise ValueError()
            success=row['success']
            if type(success)!=bool:raise ValueError()
            stamp=_uint(row['timestamp'])
            date=datetime.fromtimestamp(stamp//1000000,timezone.utc).isoformat().replace('+00:00','Z')
            fee=_units(_uint(row['gas_used'])*_uint(row['gas_unit_price']))
            item={'event_id':'Aptos:transaction:'+txhash,'hash':txhash,'date':date,'kind':'contract_activity','direction':'self','asset':'APT','asset_id':'Aptos:native','quantity':'0','fee':fee,'status':'confirmed' if success else 'failed','from_address':address,'to_address':None,'identity_verified':True}
            payload=row.get('payload') or {}
            if not isinstance(payload,dict):raise ValueError()
            function=_tag(payload.get('function'));types=payload.get('type_arguments',[])
            native=payload.get('type')=='entry_function_payload' and (function==TRANSFER or (function==COIN_TRANSFER and isinstance(types,list) and len(types)==1 and _tag(types[0])==APT))
            if success and native:
                args=payload['arguments']
                if not isinstance(args,list) or len(args)!=2:raise ValueError()
                target=providers.validate_address('Aptos',args[0]);amount=_uint(args[1])
                item.update(kind='native_transfer',direction='self' if target==address else 'out',quantity=_units(amount),to_address=target)
            items.append(item)
        except (ValueError,KeyError,TypeError,OverflowError,OSError):raise ValueError('History provider returned malformed Aptos transaction data') from None
    # Sequence windows move backwards without skipping the boundary or repeating latest rows.
    return {'items':sorted(items,key=lambda x:x['date'],reverse=True),'cursors':{STREAM:{'end':str(start)} if start else None},'coverage':COVERAGE,'updated_at':int(time.time())}
