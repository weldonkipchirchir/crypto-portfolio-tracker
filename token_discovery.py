"""Bounded ERC20 discovery; never claims complete coverage or verified identity.
Official API: https://www.alchemy.com/docs/data/token-api/token-api-endpoints/alchemy-get-token-balances
Etherscan: https://docs.etherscan.io/api-reference/endpoint/tokentx
Only operator environment endpoints are accepted; provider secrets never returned.
"""
import os,re,time
from urllib.parse import urlencode,urlsplit
import providers

ENV_NAMES={'Ethereum':'ALCHEMY_ETH_RPC_URL','Optimism':'ALCHEMY_OP_RPC_URL','BNB Chain':'ALCHEMY_BNB_RPC_URL','Base':'ALCHEMY_BASE_RPC_URL','Arbitrum':'ALCHEMY_ARB_RPC_URL','Polygon':'ALCHEMY_POLYGON_RPC_URL','Avalanche':'ALCHEMY_AVAX_RPC_URL','Sonic':'ALCHEMY_SONIC_RPC_URL','Gnosis':'ALCHEMY_GNOSIS_RPC_URL','Celo':'ALCHEMY_CELO_RPC_URL','Arc':'ALCHEMY_ARC_RPC_URL','Monad':'ALCHEMY_MONAD_RPC_URL','Robinhood Chain':'ALCHEMY_RH_RPC_URL','Linea':'ALCHEMY_LINEA_RPC_URL'}
CHAIN_IDS={'Ethereum':1,'Optimism':10,'BNB Chain':56,'Base':8453,'Arbitrum':42161,'Polygon':137,'Avalanche':43114,'Sonic':146,'Gnosis':100,'Celo':42220,'Arc':5042,'Monad':143,'Robinhood Chain':4663,'Linea':59144}
CATALOG={'Robinhood Chain':['0x39dbed3a2bd333467115de45665cc57f813c4571']}

def _result(contracts,coverage,errors,more):
    unique=list(dict.fromkeys(contracts))
    return {'contracts':unique[:20],'coverage':coverage,'errors':errors,'has_more':bool(more or len(unique)>20)}

def discover(chain,wallet):
    wallet=providers.validate_address(chain,wallet)
    if chain not in ENV_NAMES:
        return _result([], 'ERC-20 discovery is not supported for this chain',[],False)
    errors=[];url=os.environ.get(ENV_NAMES[chain])
    if url:
        try:
            parsed=urlsplit(url)
            if parsed.scheme!='https' or not parsed.hostname:raise ValueError('Invalid configured endpoint')
            with providers.deadline(time.monotonic()+15):
                response=providers.request_json(url,{'jsonrpc':'2.0','id':1,'method':'alchemy_getTokenBalances','params':[wallet,'erc20',{'maxCount':100}]})
            if not isinstance(response,dict):raise ValueError('Invalid index response')
            result=response['result']
            if not isinstance(result,dict):raise ValueError('Invalid index result')
            if providers.validate_address(chain,result['address'])!=wallet:raise ValueError('Wrong result owner')
            rows=result['tokenBalances']
            if not isinstance(rows,list) or len(rows)>100:raise ValueError('Invalid result size')
            contracts=[];partial=False
            for row in rows:
                if not isinstance(row,dict):raise ValueError('Invalid token row')
                if row.get('error'):partial=True;continue
                amount=row['tokenBalance']
                if not isinstance(amount,str) or not re.fullmatch(r'0x[0-9a-fA-F]{1,64}',amount):raise ValueError('Invalid result units')
                contract=providers.validate_address(chain,row['contractAddress'])
                if int(amount,16)>0:contracts.append(contract)
            if partial:errors.append('Some indexed token balances were unavailable')
            return _result(contracts,'One Alchemy ERC-20 index page, up to 100 indexed entries and 20 contracts checked; chain/provider coverage varies. Token identities are unverified.',errors,bool(result.get('pageKey')) or partial)
        except (ValueError,KeyError,TypeError):errors.append('Configured token indexer unavailable or response invalid; using fallback discovery')
    key=os.environ.get('ETHERSCAN_API_KEY')
    if key:
        try:
            query={'chainid':CHAIN_IDS[chain],'module':'account','action':'tokentx','address':wallet,'page':1,'offset':100,'sort':'desc','apikey':key}
            with providers.deadline(time.monotonic()+15):response=providers.request_json('https://api.etherscan.io/v2/api?'+urlencode(query))
            if not isinstance(response,dict):raise ValueError('Invalid explorer response')
            rows=response.get('result')
            if response.get('status')=='0' and rows==[]:rows=[]
            elif response.get('status')!='1':raise ValueError('Unavailable provider')
            if not isinstance(rows,list) or len(rows)>100:raise ValueError('Invalid result size')
            contracts=[]
            for row in rows:
                source=providers.validate_address(chain,row['from']);target=providers.validate_address(chain,row['to'])
                if wallet not in (source,target):raise ValueError('Wrong owner history')
                contracts.append(providers.validate_address(chain,row['contractAddress']))
            return _result(contracts,'Contracts seen in at most 100 latest indexed ERC-20 transfers; partial history discovery, not a complete holdings list. Up to 20 contracts checked; current balances must be queried.',errors,True)
        except (ValueError,KeyError,TypeError):errors.append('Explorer token discovery unavailable or not included in configured API plan')
    contracts=CATALOG.get(chain,[])
    coverage=('Limited known-token catalog (PONS on Robinhood Chain); checks only listed contracts and does not discover every token. Configure a compatible token indexer for wider discovery.' if contracts else 'Automatic token discovery requires a compatible indexer; native balance is available. No full token inventory is available.')
    return _result(contracts,coverage,errors,True)

