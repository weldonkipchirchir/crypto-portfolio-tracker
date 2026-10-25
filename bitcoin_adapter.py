"""Bitcoin mainnet read-only Esplora adapter. No xpubs, signing or custody.
Spec: https://github.com/Blockstream/esplora/blob/master/API.md
Address checks implement BIP173/BIP350 and Base58Check.
"""
import hashlib,re,time
from datetime import datetime,timezone
import providers

BASE='https://mempool.space/api/address/'
B58='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
B32='qpzry9x8gf2tvdw0s3jn54khce6mua7l'

def validate_address(address):
    if not isinstance(address,str) or not 14<=len(address)<=90:raise ValueError('Invalid Bitcoin mainnet address')
    if address.lower().startswith('bc1'):
        if address!=address.lower() and address!=address.upper():raise ValueError('Mixed case Bitcoin address')
        address=address.lower();hrp,encoded=address.rsplit('1',1)
        if hrp!='bc' or len(encoded)<7 or any(c not in B32 for c in encoded):raise ValueError('Invalid Bitcoin SegWit address')
        data=[B32.index(c) for c in encoded];values=[ord(c)>>5 for c in hrp]+[0]+[ord(c)&31 for c in hrp]+data
        chk=1
        for value in values:
            top=chk>>25;chk=((chk&0x1ffffff)<<5)^value
            for i,g in enumerate((0x3b6a57b2,0x26508e6d,0x1ea119fa,0x3d4233dd,0x2a1462b3)):
                if (top>>i)&1:chk^=g
        version=data[0]
        if version>16 or chk!=(1 if version==0 else 0x2bc830a3):raise ValueError('Invalid Bitcoin SegWit checksum')
        accumulator=0;bits=0;program=[]
        for value in data[1:-6]:
            accumulator=((accumulator<<5)|value)&0xfff;bits+=5
            if bits>=8:bits-=8;program.append((accumulator>>bits)&255)
        if bits>=5 or ((accumulator<<(8-bits))&255) or not 2<=len(program)<=40 or (version==0 and len(program) not in (20,32)):
            raise ValueError('Invalid Bitcoin witness program')
        return address
    if any(c not in B58 for c in address):raise ValueError('Invalid Bitcoin address')
    value=0
    for char in address:value=value*58+B58.index(char)
    decoded=b'\0'*(len(address)-len(address.lstrip('1')))+value.to_bytes((value.bit_length()+7)//8,'big')
    if len(decoded)!=25 or decoded[0] not in (0,5) or hashlib.sha256(hashlib.sha256(decoded[:-4]).digest()).digest()[:4]!=decoded[-4:]:
        raise ValueError('Invalid Bitcoin mainnet address checksum')
    return address

def _sat(value):
    if type(value)!=int or not 0<=value<2**64:raise ValueError('Invalid Bitcoin amount')
    return value

def _quantity(value):return str(abs(value)//100000000)+'.'+str(abs(value)%100000000).zfill(8)
def _hash(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value):raise ValueError('Invalid Bitcoin history cursor')
    return value

def balance(address):
    address=validate_address(address);result=providers.request_json(BASE+address)
    try:
        stats=result['chain_stats'];quantity=_sat(stats['funded_txo_sum'])-_sat(stats['spent_txo_sum'])
        if quantity<0:raise ValueError('Invalid Bitcoin balance')
    except (KeyError,TypeError):raise ValueError('Malformed Bitcoin balance response') from None
    return {'symbol':'BTC','quantity':_quantity(quantity),'updated_at':int(time.time()),'coverage':'Confirmed balance for one Bitcoin address; excludes mempool and other HD wallet addresses'}

def fetch_history(address,cursors=None):
    address=validate_address(address)
    if cursors is not None and (not isinstance(cursors,dict) or set(cursors)-{'transactions'}):raise ValueError('Invalid Bitcoin history cursor')
    cursor=(cursors or {}).get('transactions')
    if cursor is not None and (not isinstance(cursor,dict) or set(cursor)!={'last_txid'}):raise ValueError('Invalid Bitcoin history cursor')
    last=_hash(cursor['last_txid']) if cursor else None
    coverage='Bitcoin confirmed address net balance changes, 25 transactions per page. Excludes mempool and other HD addresses; mixed-owner inputs require manual review. No counterparties, purchase cost or trade interpretation.'
    if cursors is not None and 'transactions' in cursors and cursor is None:
        return {'items':[],'cursors':{'transactions':None},'coverage':coverage,'updated_at':int(time.time())}
    result=providers.request_json(BASE+address+'/txs/chain'+('/'+last if last else ''))
    if not isinstance(result,list) or len(result)>25:raise ValueError('Invalid Bitcoin history page')
    items=[]
    for tx in result:
        try:
            txid=_hash(tx['txid']);status=tx['status'];confirmed=status.get('confirmed') is True
            inputs=tx['vin'];outputs=tx['vout']
            if not isinstance(inputs,list) or not isinstance(outputs,list) or len(inputs)>10000 or len(outputs)>10000:raise ValueError('Invalid Bitcoin inputs/outputs')
            owned_in=0;all_owned=bool(inputs)
            for vin in inputs:
                previous=vin.get('prevout')
                if isinstance(previous,dict) and previous.get('scriptpubkey_address')==address:owned_in+=_sat(previous['value'])
                else:all_owned=False
            owned_out=sum(_sat(out['value']) for out in outputs if out.get('scriptpubkey_address')==address)
            fee=_sat(tx['fee']) if all_owned else None
            if all_owned and sum(_sat(out['value']) for out in outputs)+fee!=owned_in:raise ValueError('Inconsistent Bitcoin transaction fee')
            delta=owned_out-owned_in+(fee or 0)
            if not owned_in and not owned_out:continue
            timestamp=status.get('block_time')
            date=datetime.fromtimestamp(timestamp,timezone.utc).isoformat().replace('+00:00','Z') if type(timestamp) is int else None
            items.append({'event_id':'Bitcoin:'+txid+':native','hash':txid,'date':date,'kind':'balance_change',
                'direction':'self' if not confirmed or delta==0 else 'in' if delta>0 else 'out',
                'asset':'BTC','asset_id':'Bitcoin:native','quantity':_quantity(delta) if confirmed else '0',
                'fee':_quantity(fee) if fee is not None else None,'status':'confirmed' if confirmed else 'pending',
                'from_address':None,'to_address':None,'balance_owner':address,'identity_verified':True,
                'review_eligible':confirmed and (owned_in==0 or all_owned)})
        except (KeyError,TypeError,OverflowError,OSError):raise ValueError('Malformed Bitcoin history transaction') from None
    return {'items':items,'cursors':{'transactions':{'last_txid':_hash(result[-1]['txid'])} if len(result)==25 else None},'coverage':coverage,'updated_at':int(time.time())}

