"""Read-only mainnet balance and USD price adapters; no signing or custody."""
import json,os,re,time,urllib.request,urllib.error,threading
from contextlib import contextmanager
_REQUEST_CONTEXT=threading.local()
@contextmanager
def deadline(cutoff):
 previous=getattr(_REQUEST_CONTEXT,"cutoff",None)
 _REQUEST_CONTEXT.cutoff=cutoff
 try:yield
 finally:_REQUEST_CONTEXT.cutoff=previous
from decimal import Decimal
CHAINS={
 'Ethereum':('ETH',18,'ETH_RPC_URL','https://ethereum-rpc.publicnode.com'),
 'Optimism':('ETH',18,'OP_RPC_URL','https://mainnet.optimism.io'),
 'BNB Chain':('BNB',18,'BNB_RPC_URL','https://bsc-dataseed.bnbchain.org'),
 'Solana':('SOL',9,'SOL_RPC_URL','https://api.mainnet-beta.solana.com'),
 'Aptos':('APT',8,'APT_RPC_URL','https://fullnode.mainnet.aptoslabs.com/v1/view'),
 'Sui':('SUI',9,'SUI_GRAPHQL_URL','https://graphql.mainnet.sui.io/graphql'),
 'Base':('ETH',18,'BASE_RPC_URL','https://mainnet.base.org'),
 'Arbitrum':('ETH',18,'ARB_RPC_URL','https://arb1.arbitrum.io/rpc'),
 'Polygon':('POL',18,'POLYGON_RPC_URL','https://polygon.publicnode.com'),
 'Avalanche':('AVAX',18,'AVAX_RPC_URL','https://api.avax.network/ext/bc/C/rpc'),
 'Sonic':('S',18,'SONIC_RPC_URL','https://rpc.soniclabs.com'),
 'Gnosis':('XDAI',18,'GNOSIS_RPC_URL','https://rpc.gnosischain.com'),
 'Celo':('CELO',18,'CELO_RPC_URL','https://forno.celo.org'),
 'Arc':('USDC',18,'ARC_RPC_URL','https://rpc.mainnet.arc.io'),
 'Monad':('MON',18,'MONAD_RPC_URL','https://rpc.monad.xyz'),
 'Robinhood Chain':('ETH',18,'RH_RPC_URL','https://rpc.mainnet.chain.robinhood.com'),
 'Linea':('ETH',18,'LINEA_RPC_URL','https://rpc.linea.build'),
 'Bitcoin':('BTC',8,'BTC_API_URL','https://mempool.space/api'),
 'Stellar':('XLM',7,'STELLAR_API_URL','https://horizon.stellar.org'),
 'Tron':('TRX',6,'TRON_API_URL','https://api.trongrid.io')}
EVM_CHAINS=('Ethereum','Optimism','BNB Chain','Base','Arbitrum','Polygon','Avalanche','Sonic','Gnosis','Celo','Arc','Monad','Robinhood Chain','Linea')
LEDGER_ALIASES={'Bitcoin':'BTC','Stellar':'XLM','Tron':'TRX','Arc':'USDC_ARC','Monad':'MON','Robinhood Chain':'ETH_RH','Linea':'ETH_LINEA','Sonic':'S','Gnosis':'XDAI','Celo':'CELO','Ethereum':'ETH','Optimism':'ETH_OP','BNB Chain':'BNB','Solana':'SOL','Aptos':'APT','Sui':'SUI','Base':'ETH_BASE','Arbitrum':'ETH_ARB','Polygon':'POL','Avalanche':'AVAX'}
COINS={'XLM':'stellar','TRX':'tron','MON':'monad','USDC_ARC':'usd-coin','ETH_RH':'ethereum','ETH_LINEA':'ethereum','S':'sonic-3','XDAI':'xdai','CELO':'celo','ETH_BASE':'ethereum','ETH_ARB':'ethereum','POL':'polygon-ecosystem-token','AVAX':'avalanche-2','ETH_OP':'ethereum','BTC':'bitcoin','ETH':'ethereum','SOL':'solana','BNB':'binancecoin','APT':'aptos','SUI':'sui','OP':'optimism','USDC':'usd-coin','USDT':'tether'}
def validate_address(chain,address):
 if chain not in CHAINS: raise ValueError('Unsupported chain')
 address=str(address).strip()
 if chain in ('Bitcoin','Stellar','Tron'):
  import importlib
  module={'Bitcoin':'bitcoin_adapter','Stellar':'stellar_adapter','Tron':'tron_adapter'}[chain]
  return importlib.import_module(module).validate_address(address)
 if chain in EVM_CHAINS:
  if not re.fullmatch(r'0x[0-9a-fA-F]{40}',address): raise ValueError('This chain requires a 0x address with 40 hexadecimal characters')
  return address.lower()
 if chain in ('Sui','Aptos'):
  if not re.fullmatch(r'0x[0-9a-fA-F]{1,64}',address): raise ValueError('Enter a valid hexadecimal account address')
  return '0x'+address[2:].lower().zfill(64)
 alphabet='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
 try:
  value=0
  for char in address:value=value*58+alphabet.index(char)
  size=(value.bit_length()+7)//8+len(address)-len(address.lstrip('1'))
  if size!=32: raise ValueError()
 except ValueError:raise ValueError('Solana requires a base58 encoded 32-byte public address')
 return address
def request_json(url,payload=None,headers=None):
 req=urllib.request.Request(url,data=json.dumps(payload).encode() if payload is not None else None,headers={'Content-Type':'application/json','User-Agent':'OrbitPortfolio/0.2',**(headers or {})})
 cutoff=getattr(_REQUEST_CONTEXT,'cutoff',None)
 timeout=min(12,cutoff-time.monotonic()) if cutoff is not None else 12
 if timeout<=0:raise ValueError('Provider operation deadline reached. Inspect fewer contracts or retry later.')
 try:
  with urllib.request.urlopen(req,timeout=max(0.1,timeout)) as response:
   body=response.read(4*1024*1024+1)
   if len(body)>4*1024*1024:raise ValueError('Provider response exceeds allowed size')
   result=json.loads(body)
 except urllib.error.HTTPError as e:raise ValueError('Provider returned HTTP '+str(e.code)+'. Try again later or configure a provider endpoint.') from None
 except (OSError,ValueError):raise ValueError('Provider unavailable or response invalid. Try again later.') from None
 if isinstance(result,dict) and ('error' in result or result.get('errors')):raise ValueError('Provider rejected the query. Check the network or provider configuration.')
 return result
def balance(chain,address):
 address=validate_address(chain,address)
 if chain in ('Bitcoin','Stellar','Tron'):
  import importlib
  module={'Bitcoin':'bitcoin_adapter','Stellar':'stellar_adapter','Tron':'tron_adapter'}[chain]
  return importlib.import_module(module).balance(address)
 symbol,decimals,env,default=CHAINS[chain];url=os.environ.get(env,default)
 if chain=='Aptos':
  result=request_json(url,{'function':'0x1::coin::balance','type_arguments':['0x1::aptos_coin::AptosCoin'],'arguments':[address]});amount=int(result[0])
 elif chain=='Sui':
  query='query Balance($owner: SuiAddress!) { address(address: $owner) { balance(coinType: "0x2::sui::SUI") { totalBalance } } }'
  result=request_json(url,{'query':query,'variables':{'owner':address}});value=result['data']['address']['balance'];amount=int(value['totalBalance']) if value else 0
 else:
  method='getBalance' if chain=='Solana' else 'eth_getBalance'
  params=[address,{'commitment':'finalized'}] if chain=='Solana' else [address,'latest']
  result=request_json(url,{'jsonrpc':'2.0','id':1,'method':method,'params':params})['result'];amount=int(result['value']) if chain=='Solana' else int(result,16)
 if amount<0:raise ValueError('Provider returned an invalid balance')
 return {'symbol':symbol,'quantity':str(Decimal(amount)/(10**decimals)),'updated_at':int(time.time()),'coverage':'native token only'}
def market_prices(symbols):
 selected={s:COINS[s] for s in set(symbols) if s in COINS}
 if not selected:return {}
 url='https://api.coingecko.com/api/v3/simple/price?ids='+','.join(sorted(set(selected.values())))+'&vs_currencies=usd&include_last_updated_at=true'
 key=os.environ.get('COINGECKO_DEMO_API_KEY');headers={'x-cg-demo-api-key':key} if key else {}
 response=request_json(url,headers=headers);prices={}
 for symbol,coin in selected.items():
  data=response.get(coin,{})
  if data.get('usd') is None or not data.get('last_updated_at'):continue
  price=Decimal(str(data['usd']));stamp=int(data['last_updated_at'])
  if not price.is_finite() or price<0:continue
  prices[symbol]={'price':str(price),'updated_at':stamp,'source':'CoinGecko'}
 return prices
