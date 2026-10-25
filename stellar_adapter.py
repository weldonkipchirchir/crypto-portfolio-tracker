"""Read-only Stellar classic-account native balance and bounded payment history."""
import base64,binascii,re,time
from decimal import Decimal,localcontext
from urllib.parse import urlencode
import providers
BASE='https://horizon.stellar.org'
STREAM='payments'
COVERAGE='Stellar Horizon payment operations, up to 25 per page. Native XLM payments and account funding plus issuer-qualified classic assets; other operations remain metadata. No complete swap, Soroban, purchase-cost or fee accounting. Fees are unavailable in payment records; transfers are not purchases.'

def validate_address(address):
    if not isinstance(address,str):raise ValueError('Enter a Stellar public G address')
    address=address.strip()
    if address.startswith('M'):raise ValueError('Use the underlying classic Stellar G address; muxed M addresses are not supported yet')
    if not re.fullmatch(r'G[A-Z2-7]{55}',address):raise ValueError('Enter a valid Stellar public G address, never a secret seed')
    try:raw=base64.b32decode(address)
    except binascii.Error:raise ValueError('Invalid Stellar public address') from None
    if len(raw)!=35 or raw[0]!=48 or binascii.crc_hqx(raw[:-2],0).to_bytes(2,'little')!=raw[-2:] or base64.b32encode(raw).decode()!=address:raise ValueError('Invalid Stellar public address checksum')
    return address

def _amount(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]{1,12}\.[0-9]{7}',value):raise ValueError('Invalid Stellar amount')
    with localcontext() as ctx:
        ctx.prec=40
        if Decimal(value)>Decimal('922337203685.4775807'):raise ValueError('Invalid Stellar amount')
    return value

def _not_found(error):return str(error).startswith('Provider returned HTTP 404.')

def balance(address):
    address=validate_address(address)
    try:result=providers.request_json(BASE+'/accounts/'+address)
    except ValueError as error:
        if _not_found(error):return {'symbol':'XLM','quantity':'0.0000000','updated_at':int(time.time()),'coverage':'Unfunded or nonexistent classic account; Horizon returned 404. Native XLM only.'}
        raise
    if not isinstance(result,dict) or result.get('account_id')!=address or not isinstance(result.get('balances'),list):raise ValueError('Invalid Stellar account response')
    native=[item for item in result['balances'] if isinstance(item,dict) and item.get('asset_type')=='native']
    if len(native)!=1:raise ValueError('Missing or duplicate Stellar native balance')
    return {'symbol':'XLM','quantity':_amount(native[0].get('balance')),'updated_at':int(time.time()),'coverage':'Native XLM only; total balance includes reserve requirements and may not all be spendable.'}

def _cursor(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]{1,32}',value):raise ValueError('Invalid Stellar history cursor')
    return value

def fetch_history(address,cursors=None):
    address=validate_address(address)
    if cursors is not None and (not isinstance(cursors,dict) or set(cursors)-{STREAM}):raise ValueError('Invalid Stellar stream cursor')
    cursor=(cursors or {}).get(STREAM)
    if cursors is not None and STREAM in cursors and cursor is None:return {'items':[],'cursors':{STREAM:None},'coverage':COVERAGE,'updated_at':int(time.time())}
    params={'order':'desc','limit':'25'}
    if cursor is not None:params['cursor']=_cursor(cursor)
    try:result=providers.request_json(BASE+'/accounts/'+address+'/payments?'+urlencode(params))
    except ValueError as error:
        if _not_found(error):return {'items':[],'cursors':{STREAM:None},'coverage':COVERAGE+' Account not funded or absent.','updated_at':int(time.time())}
        raise
    if not isinstance(result,dict) or not isinstance(result.get('_embedded'),dict) or not isinstance(result['_embedded'].get('records'),list):raise ValueError('Invalid Stellar payment page')
    rows=result['_embedded']['records']
    if len(rows)>25:raise ValueError('Invalid Stellar payment page size')
    items=[];previous=int(cursor) if cursor else None
    for row in rows:
        try:
            if not isinstance(row,dict):raise ValueError()
            paging=_cursor(row['paging_token'])
            if previous is not None and int(paging)>=previous:raise ValueError()
            previous=int(paging)
            txhash=row['transaction_hash']
            if not isinstance(txhash,str) or not re.fullmatch(r'[0-9a-fA-F]{64}',txhash):raise ValueError()
            date=row['created_at']
            if not isinstance(date,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z',date):raise ValueError()
            successful=row['transaction_successful']
            if type(successful)!=bool:raise ValueError()
            kind=row.get('type');source=target=None
            item={'event_id':'Stellar:operation:'+paging,'hash':txhash,'date':date,'kind':'contract_activity','direction':'self','asset':'Unknown','asset_id':'Stellar:operation','quantity':'0','fee':None,'status':'confirmed' if successful else 'failed','from_address':None,'to_address':None,'identity_verified':False,'review_eligible':False}
            if kind in ('payment','create_account'):
                source=validate_address(row['from'] if kind=='payment' else row['funder']);target=validate_address(row['to'] if kind=='payment' else row['account'])
                if source!=address and target!=address:raise ValueError()
                amount=_amount(row['amount'] if kind=='payment' else row['starting_balance'])
                item.update(from_address=source,to_address=target)
                if successful:
                    item.update(kind='native_transfer' if kind=='create_account' or row.get('asset_type')=='native' else 'token_transfer',direction='self' if source==target else 'out' if source==address else 'in',quantity=amount)
                    if kind=='create_account' or row.get('asset_type')=='native':item.update(asset='XLM',asset_id='Stellar:native',identity_verified=True,review_eligible=True)
                    else:
                        asset_type=row.get('asset_type');code=row.get('asset_code');issuer=validate_address(row['asset_issuer'])
                        if asset_type not in ('credit_alphanum4','credit_alphanum12') or not isinstance(code,str) or not re.fullmatch(r'[a-zA-Z0-9]{1,12}',code) or (asset_type=='credit_alphanum4' and len(code)>4):raise ValueError()
                        item.update(asset=code,asset_id='Stellar:'+code+':'+issuer,review_eligible=True)
            items.append(item)
        except (ValueError,KeyError,TypeError):raise ValueError('History provider returned malformed Stellar payment data') from None
    return {'items':items,'cursors':{STREAM:rows[-1]['paging_token'] if len(rows)==25 else None},'coverage':COVERAGE,'updated_at':int(time.time())}
