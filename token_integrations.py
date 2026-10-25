"""Bounded read-only ERC-20 balances; no signing, discovery, prices or cost basis."""
import os, time
from decimal import Decimal, localcontext
import providers


def decode_metadata(raw,max_length=128):
    if not isinstance(raw,str) or not raw.startswith('0x') or len(raw)>8194 or len(raw)%2:raise ValueError('Invalid token metadata')
    try:body=bytes.fromhex(raw[2:])
    except ValueError:raise ValueError('Invalid token metadata') from None
    if len(body)==32:data=body.rstrip(b'\x00')
    elif len(body)>=64:
        offset=int.from_bytes(body[:32],'big')
        if offset%32 or offset+32>len(body):raise ValueError('Invalid token metadata offset')
        length=int.from_bytes(body[offset:offset+32],'big')
        if length>256 or offset+32+length>len(body):raise ValueError('Invalid token metadata length')
        data=body[offset+32:offset+32+length]
    else:raise ValueError('Invalid token metadata')
    try:text=data.decode('utf-8').strip()
    except UnicodeDecodeError:raise ValueError('Invalid token metadata encoding') from None
    if not text or len(text)>max_length or any(ord(char)<32 or 127<=ord(char)<=159 or char in '\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069' for char in text):raise ValueError('Invalid token metadata text')
    return text

def token_metadata(chain,contract):
    _,_,env,default=providers.CHAINS[chain];result={}
    for field,selector,limit in [('symbol','0x95d89b41',40),('name','0x06fdde03',128)]:
        try:
            response=providers.request_json(os.environ.get(env,default),{'jsonrpc':'2.0','id':1,'method':'eth_call','params':[{'to':contract,'data':selector},'latest']})
            if not isinstance(response,dict):raise ValueError('Invalid metadata response')
            result[field]=decode_metadata(response.get('result'),limit)
        except ValueError:pass
    return result

def token_balances(chain, address, contracts=None, include_metadata=False):
    """Read up to 20 explicit ERC-20 contracts. Return tokens/errors/coverage/updated_at.

    Never infer verified identity or purchase history from a contract balance.
    Unsupported chains return an explicit coverage explanation and empty tokens.
    """
    address = providers.validate_address(chain, address)
    if chain == 'Solana':
        return solana_tokens(address)
    contracts = [] if contracts is None else contracts
    if not isinstance(contracts, list) or len(contracts) > 20:
        raise ValueError('Supply at most 20 token contract addresses')
    tokens, errors = [], []
    coverage = 'Token discovery is not yet supported for this chain'
    if chain in providers.EVM_CHAINS:
        contracts = list(dict.fromkeys(providers.validate_address(chain, c) for c in contracts))
        if chain=='Arc':contracts=[c for c in contracts if c!='0x3600000000000000000000000000000000000000']
        _, _, env, default = providers.CHAINS[chain]
        def read(contract, data):
            result = providers.request_json(os.environ.get(env, default), {'jsonrpc':'2.0',
                'id':1, 'method':'eth_call', 'params':[{'to':contract,'data':data},'latest']})
            raw = result.get('result') if isinstance(result, dict) else None
            if not isinstance(raw, str) or len(raw) != 66 or not raw.startswith('0x'):
                raise ValueError('Contract returned an invalid token response')
            try: return int(raw, 16)
            except ValueError: raise ValueError('Contract returned invalid token units') from None
        for contract in contracts:
            try:
                amount = read(contract, '0x70a08231'+address[2:].zfill(64))
                decimals = read(contract, '0x313ce567')
                if not 0 <= decimals <= 255:
                    raise ValueError('Contract returned invalid token decimals')
                with localcontext() as ctx:
                    ctx.prec = 340
                    quantity = format(Decimal(amount)/(Decimal(10)**decimals), 'f')
                tokens.append({'asset_id':chain+':'+contract,'contract':contract,
                    'quantity':quantity,'decimals':decimals,'identity_verified':False,**(token_metadata(chain,contract) if include_metadata else {})})
            except ValueError as exc:
                errors.append({'asset_id':chain+':'+contract,'error':str(exc)})
        coverage = 'Explicit ERC-20 contracts only; no discovery, token prices, or purchase history'+('. Arc USDC ERC-20 interface shares the native balance and is excluded to avoid double counting.' if chain=='Arc' else '')
    return {'tokens':tokens,'errors':errors,'coverage':coverage,'updated_at':int(time.time())}

TOKEN_PROGRAMS = ('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb')

def solana_tokens(address):
    address=providers.validate_address('Solana',address)
    tokens, errors=[],[]
    _,_,env,default=providers.CHAINS['Solana']
    for program in TOKEN_PROGRAMS:
        try:
            result=providers.request_json(os.environ.get(env,default),{'jsonrpc':'2.0','id':1,
                'method':'getTokenAccountsByOwner','params':[address,{'programId':program},{'encoding':'jsonParsed','commitment':'finalized'}]})
            accounts=result['result']['value']
            if not isinstance(accounts,list) or len(accounts)>1000:raise ValueError('Token account limit exceeded')
            totals={}
            for account in accounts:
                info=account['account']['data']['parsed']['info']
                if info.get('owner')!=address:raise ValueError('Provider returned an unexpected owner')
                mint=providers.validate_address('Solana',info['mint'])
                units=info['tokenAmount']; decimals=units['decimals']; raw=units['amount']
                if type(decimals)!=int or not 0<=decimals<=255 or not isinstance(raw,str) or not raw.isascii() or not raw.isdigit() or len(raw)>20 or int(raw)>=2**64:
                    raise ValueError('Provider returned invalid SPL units')
                previous=totals.get(mint,(0,decimals))
                if previous[1]!=decimals:raise ValueError('Provider returned inconsistent mint decimals')
                totals[mint]=(previous[0]+int(raw),decimals)
            batch=[]
            for mint,(raw,decimals) in totals.items():
                if raw:
                    with localcontext() as ctx:
                        ctx.prec=340
                        quantity=format(Decimal(raw)/(Decimal(10)**decimals),'f')
                    batch.append({'asset_id':'Solana:'+mint,'mint':mint,'program':program,'quantity':quantity,'decimals':decimals,'identity_verified':False})
            tokens.extend(batch)
        except (ValueError,KeyError,TypeError) as exc:
            errors.append({'program':program,'error':str(exc) if isinstance(exc,ValueError) else 'Provider returned malformed token accounts'})
    return {'tokens':tokens,'errors':errors,'coverage':'Legacy SPL and Token-2022 accounts; maximum 1000 accounts per program. No prices, NFT classification, or purchase history.','updated_at':int(time.time())}


def recent_activity(chain,address,limit=25,before=None):
    """Solana finalized signature metadata, not interpreted buys/sells or complete history."""
    address=providers.validate_address(chain,address)
    if type(limit)!=int or not 1<=limit<=100:raise ValueError('Activity limit must be between 1 and 100')
    if chain!='Solana':raise ValueError('Recent activity currently supports Solana only')
    options={'limit':limit,'commitment':'finalized'}
    if before is not None:
        alphabet='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
        if not isinstance(before,str) or not 64<=len(before)<=88 or any(c not in alphabet for c in before):raise ValueError('Invalid signature cursor')
        options['before']=before
    _,_,env,default=providers.CHAINS[chain]
    result=providers.request_json(os.environ.get(env,default),{'jsonrpc':'2.0','id':1,'method':'getSignaturesForAddress','params':[address,options]})
    items=result.get('result') if isinstance(result,dict) else None
    if not isinstance(items,list) or len(items)>limit:raise ValueError('Provider returned invalid activity')
    activities=[]
    for item in items:
        if not isinstance(item,dict) or not isinstance(item.get('signature'),str) or type(item.get('slot'))!=int:raise ValueError('Provider returned malformed activity')
        activities.append({'signature':item['signature'],'slot':item['slot'],'timestamp':item.get('blockTime'),'failed':item.get('err') is not None})
    return {'activities':activities,'next_cursor':activities[-1]['signature'] if len(activities)==limit else None,
        'coverage':'Recent Solana signature metadata only; provider retention varies. Does not classify trades or establish cost basis.','updated_at':int(time.time())}

