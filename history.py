"""Bounded public Ethereum history. Transfers are never automatically treated as trades."""
import re,time
from decimal import Decimal,localcontext
from urllib.parse import urlencode
import providers

STREAMS=('transactions','token-transfers')
CURSOR_KEYS={'block_number','index','items_count','transaction_index','log_index','batch_block_hash','batch_transaction_hash','batch_log_index','index_in_batch','token_id','value','inserted_at','hash','block_hash','transaction_hash','fee'}

def _cursor(value):
    if value is None:return None
    if not isinstance(value,dict) or len(value)>16:raise ValueError('Invalid history cursor')
    for key,item in value.items():
        if key not in CURSOR_KEYS or type(item) not in (str,int,bool) or len(str(item))>160 or not re.fullmatch(r'[a-zA-Z0-9_.:+\-]*',str(item)):
            raise ValueError('Invalid history cursor')
    return value

def _units(value,decimals):
    value=str(value)
    if not value.isascii() or not value.isdigit() or len(value)>78 or type(decimals)!=int or not 0<=decimals<=255:raise ValueError('Invalid history units')
    with localcontext() as ctx:
        ctx.prec=340
        return format(Decimal(value)/(Decimal(10)**decimals),'f')

def _address(value):
    if value is None:return None
    if not isinstance(value,dict):raise ValueError('Invalid history address')
    return providers.validate_address('Ethereum',value['hash'])

def fetch_blockscout(chain,address,cursors=None):
    """One page per Ethereum stream. Explicit None cursor skips an exhausted stream.

    Returns items, cursors, coverage, updated_at. Missing cursors starts both streams.
    No transactions are written, no cost basis inferred; failed transactions remain
    metadata and are marked failed. ERC20 identity is always unverified.
    """
    address=providers.validate_address(chain,address)
    hosts={'Gnosis':'https://gnosis.blockscout.com','Celo':'https://celo.blockscout.com','Ethereum':'https://eth.blockscout.com','Optimism':'https://optimism.blockscout.com'}
    if chain not in hosts:raise ValueError('Unsupported Blockscout network')
    if cursors is not None and (not isinstance(cursors,dict) or any(k not in STREAMS for k in cursors)):
        raise ValueError('Invalid history stream cursor')
    for value in (cursors or {}).values():_cursor(value)
    items=[];following={}
    for stream in STREAMS:
        if cursors is not None and stream in cursors and cursors[stream] is None:
            following[stream]=None;continue
        cursor=(cursors or {}).get(stream)
        url=hosts[chain]+'/api/v2/addresses/'+address+'/'+stream
        if cursor:url+='?'+urlencode(cursor)
        result=providers.request_json(url)
        if not isinstance(result,dict) or not isinstance(result.get('items'),list) or len(result['items'])>50:
            raise ValueError('History provider returned an invalid page')
        following[stream]=_cursor(result.get('next_page_params'))
        for row in result['items']:
            if not isinstance(row,dict):raise ValueError('History provider returned malformed transaction data')
            try:
                source=_address(row.get('from'));target=_address(row.get('to'))
                if source!=address and target!=address:raise ValueError('History provider returned another wallet')
                txhash=row.get('hash') if stream=='transactions' else row.get('transaction_hash')
                if not isinstance(txhash,str) or not re.fullmatch(r'0x[0-9a-fA-F]{64}',txhash):raise ValueError('Invalid history hash')
                date=row.get('timestamp')
                if date is not None and (not isinstance(date,str) or len(date)>40):raise ValueError('Invalid history timestamp')
                direction='self' if source==target else 'out' if source==address else 'in'
                fee=None;asset=providers.CHAINS[chain][0];asset_id=chain+':native';kind='native_transfer'
                event_id=chain+':transaction:'+txhash
                if stream=='transactions':
                    quantity=_units(row.get('value','0'),18)
                    if chain!='Celo' and source==address and isinstance(row.get('fee'),dict) and row['fee'].get('type')!='maximum':fee=_units(row['fee'].get('value','0'),18)
                    status='confirmed' if row.get('status') in ('ok','success') else 'failed' if row.get('status') in ('error','failed') else 'pending' if row.get('timestamp') is None else 'unknown'
                    if quantity=='0':kind='contract_activity'
                else:
                    token=row['token'];contract=providers.validate_address(chain,token['address_hash'])
                    if token.get('type')!='ERC-20':continue
                    total=row['total'];quantity=_units(total['value'],int(total['decimals']))
                    asset=str(token.get('symbol') or 'Unknown token')[:40];asset_id=chain+':'+contract
                    logindex=row['log_index']
                    if type(logindex)!=int or logindex<0:raise ValueError('Invalid token event index')
                    event_id=chain+':token:'+txhash+':'+str(logindex);kind='token_transfer';status='confirmed'
                items.append({'event_id':event_id,'hash':txhash,'date':date,'kind':kind,'direction':direction,
                    'asset':asset,'asset_id':asset_id,'quantity':quantity,'fee':fee,'status':status,
                    'from_address':source,'to_address':target,'identity_verified':stream=='transactions'})
            except (KeyError,TypeError,ValueError):
                raise ValueError('History provider returned malformed transaction data') from None
    return {'items':items,'cursors':following,'coverage':chain+' external transactions and ERC-20 transfers only; 50 per stream per page. No internal transfers, NFTs, swap interpretation or purchase cost. Transfers are not buys or sells.'+(' Celo alternate fee currencies are not normalized; fee shown unavailable.' if chain=='Celo' else ''),'updated_at':int(time.time())}




def fetch_history(chain,address,cursors=None):
    address=providers.validate_address(chain,address)
    if chain in ('Ethereum','Optimism','Gnosis','Celo'):return fetch_blockscout(chain,address,cursors)
    if chain=='Solana':
        import history_solana
        return history_solana.fetch_history(address,cursors)
    if chain=='Aptos':
        import history_aptos
        return history_aptos.fetch_history(address,cursors)
    if chain=='Sui':
        import history_sui
        return history_sui.fetch_history(address,cursors)
    if chain in ('Bitcoin','Stellar','Tron'):
        import importlib
        module={'Bitcoin':'bitcoin_adapter','Stellar':'stellar_adapter','Tron':'tron_adapter'}[chain]
        return importlib.import_module(module).fetch_history(address,cursors)
    if chain in ('BNB Chain','Base','Arbitrum','Polygon','Avalanche','Sonic','Arc','Monad','Robinhood Chain','Linea'):
        import history_bnb
        return history_bnb.fetch_history(address,cursors,chain=chain)
    raise ValueError('History is unavailable for this network')
