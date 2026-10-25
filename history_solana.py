"""Read-only Solana history from finalized transaction owner balance changes.

Official specification: https://solana.com/docs/rpc/http/gettransaction and
https://solana.com/docs/rpc/http/getsignaturesforaddress . Balance deltas include
rent/rewards and are not asserted trades or counterparty transfers.
"""
import os,time
from datetime import datetime,timezone
from decimal import Decimal,localcontext
import providers

ALPHABET='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
LIMIT=10

def _signature(value):
    if not isinstance(value,str) or not 64<=len(value)<=88 or any(c not in ALPHABET for c in value):raise ValueError('Invalid Solana history signature')
    number=0
    for char in value:number=number*58+ALPHABET.index(char)
    if (number.bit_length()+7)//8+len(value)-len(value.lstrip('1'))!=64:raise ValueError('Invalid Solana history signature')
    return value

def _uint(value,bits=64):
    if type(value) is int:
        result=value
    elif isinstance(value,str) and value.isascii() and value.isdigit() and len(value)<=78:result=int(value)
    else:raise ValueError('Invalid Solana history units')
    if not 0<=result<2**bits:raise ValueError('Invalid Solana history units')
    return result

def _quantity(value,decimals):
    with localcontext() as ctx:
        ctx.prec=340
        return format(Decimal(abs(value))/(Decimal(10)**decimals),'f')

def _rpc(method,params):
    _,_,env,default=providers.CHAINS['Solana']
    result=providers.request_json(os.environ.get(env,default),{'jsonrpc':'2.0','id':1,'method':method,'params':params})
    if not isinstance(result,dict) or 'result' not in result:raise ValueError('Invalid Solana history response')
    return result['result']

def _parse(address,signature,tx):
    if not isinstance(tx,dict) or not isinstance(tx.get('meta'),dict):raise ValueError('Solana transaction details unavailable; retry this history page')
    meta=tx['meta'];keys=tx['transaction']['message']['accountKeys']
    if not isinstance(keys,list) or len(keys)>512:raise ValueError('Invalid Solana account keys')
    keys=[providers.validate_address('Solana',key['pubkey'] if isinstance(key,dict) else key) for key in keys]
    timestamp=tx.get('blockTime')
    date=datetime.fromtimestamp(timestamp,timezone.utc).isoformat().replace('+00:00','Z') if type(timestamp) is int else None
    failed=meta.get('err') is not None
    status='failed' if failed else 'confirmed'
    fee=_uint(meta['fee']) if keys and keys[0]==address else 0
    def event(asset_id,asset,delta,decimals,native=False):
        return {'event_id':'Solana:'+signature+':'+asset_id,'hash':signature,'date':date,
            'kind':'balance_change','direction':'self' if failed or delta==0 else 'in' if delta>0 else 'out',
            'asset':asset,'asset_id':asset_id,'quantity':_quantity(delta,decimals) if not failed else '0',
            'fee':_quantity(fee,9) if native else None,'status':status,
            'from_address':None,'to_address':None,'identity_verified':native,
            'balance_owner':address}
    items=[]
    if address in keys:
        index=keys.index(address)
        before=meta['preBalances'];after=meta['postBalances']
        if len(before)!=len(keys) or len(after)!=len(keys):raise ValueError('Invalid Solana native balances')
        delta=_uint(after[index])-_uint(before[index])+fee
        if delta or fee or failed:items.append(event('Solana:native','SOL',delta,9,True))
    if failed:return items
    sides=[];decimals_by_mint={}
    for side in ('preTokenBalances','postTokenBalances'):
        entries=meta.get(side,[])
        if not isinstance(entries,list) or len(entries)>512:raise ValueError('Invalid Solana token balances')
        totals={};seen=set()
        for entry in entries:
            if entry.get('owner')!=address:continue
            mint=providers.validate_address('Solana',entry['mint']);index=_uint(entry['accountIndex'])
            if index>=len(keys) or index in seen:raise ValueError('Invalid Solana token account index')
            seen.add(index);amount=entry['uiTokenAmount'];decimals=amount['decimals']
            if type(decimals)!=int or not 0<=decimals<=255:raise ValueError('Invalid Solana decimals')
            if mint in decimals_by_mint and decimals_by_mint[mint]!=decimals:raise ValueError('Inconsistent Solana mint decimals')
            decimals_by_mint[mint]=decimals;totals[mint]=totals.get(mint,0)+_uint(amount['amount'])
        sides.append(totals)
    for mint in sorted(set(sides[0])|set(sides[1])):
        delta=sides[1].get(mint,0)-sides[0].get(mint,0)
        if delta:items.append(event('Solana:'+mint,mint,delta,decimals_by_mint[mint]))
    return items

def fetch_history(address,cursors=None):
    """Return standard history envelope; cursor key signatures contains before.

    Ten signatures/details per page and 30-second deadline. A missing transaction
    or request failure aborts the page without advancing its persisted cursor.
    """
    address=providers.validate_address('Solana',address)
    if cursors is not None and (not isinstance(cursors,dict) or set(cursors)-{'signatures'}):raise ValueError('Invalid Solana history cursor')
    cursor=(cursors or {}).get('signatures')
    if cursor is not None and (not isinstance(cursor,dict) or set(cursor)!={'before'}):raise ValueError('Invalid Solana history cursor')
    before=_signature(cursor['before']) if cursor else None
    coverage='Solana finalized owner balance changes, 10 signatures per page; provider retention varies. Rent/rewards may affect SOL. No counterparties, instruction interpretation, token symbols or purchase costs. Missing owner metadata can omit token changes.'
    if cursors is not None and 'signatures' in cursors and cursor is None:
        return {'items':[],'cursors':{'signatures':None},'coverage':coverage,'updated_at':int(time.time())}
    options={'limit':LIMIT,'commitment':'finalized'}
    if before:options['before']=before
    items=[]
    with providers.deadline(time.monotonic()+30):
        signatures=_rpc('getSignaturesForAddress',[address,options])
        if not isinstance(signatures,list) or len(signatures)>LIMIT:raise ValueError('Invalid Solana signature page')
        for entry in signatures:
            try:
                signature=_signature(entry['signature'])
                tx=_rpc('getTransaction',[signature,{'encoding':'jsonParsed','commitment':'finalized','maxSupportedTransactionVersion':0}])
                items.extend(_parse(address,signature,tx))
            except (KeyError,TypeError,IndexError,OverflowError,OSError):raise ValueError('Malformed Solana transaction; retry this history page') from None
    return {'items':items,'cursors':{'signatures':{'before':_signature(signatures[-1]['signature'])} if len(signatures)==LIMIT else None},'coverage':coverage,'updated_at':int(time.time())}
