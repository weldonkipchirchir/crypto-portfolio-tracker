"""BNB external transaction history through Etherscan V2 (server API key required)."""
import os,re,time
from datetime import datetime,timezone
from decimal import Decimal,localcontext
from urllib.parse import urlencode
import providers

def units(value):
 value=str(value)
 if not re.fullmatch(r'[0-9]{1,78}',value):raise ValueError('Invalid BNB transaction quantity')
 with localcontext() as context:
  context.prec=100
  return format(Decimal(value)/(10**18),'f')
def fetch_history(address,cursors=None,chain="BNB Chain"):
 chain_ids={'Arc':5042,'Monad':143,'Robinhood Chain':4663,'Linea':59144,'Sonic':146,'BNB Chain':56,'Base':8453,'Arbitrum':42161,'Polygon':137,'Avalanche':43114}
 if chain not in chain_ids:raise ValueError('Unsupported explorer network')
 address=providers.validate_address(chain,address)
 key=os.environ.get('ETHERSCAN_API_KEY')
 if not key and chain!='Avalanche':raise ValueError(chain+' history needs ETHERSCAN_API_KEY with access to this chain; Base requires a paid plan. Balances and token inspection remain available.')
 endblock=9999999999;page=1
 if cursors is not None:
  if not isinstance(cursors,dict) or set(cursors)!={'transactions'}:raise ValueError('Invalid BNB history cursor')
  value=cursors['transactions']
  if value is None:return {'items':[],'cursors':{'transactions':None},'coverage':'BNB history page exhausted','updated_at':int(time.time())}
  if not isinstance(value,dict) or set(value)!={'endblock','page'} or type(value['endblock'])!=int or not 0<=value['endblock']<9999999999 or type(value['page'])!=int or not 2<=value['page']<=1000000:raise ValueError('Invalid BNB history cursor')
  endblock=value['endblock'];page=value['page']
 query={'chainid':chain_ids[chain],'module':'account','action':'txlist','address':address,'startblock':0,'endblock':endblock,'page':page,'offset':50,'sort':'desc','apikey':key}
 if chain=='Avalanche':
  query.pop('apikey',None);query.pop('chainid',None)
  endpoint='https://api.routescan.io/v2/network/mainnet/evm/43114/etherscan/api?'
 else:endpoint='https://api.etherscan.io/v2/api?'
 data=providers.request_json(endpoint+urlencode(query))
 if not isinstance(data,dict):raise ValueError('Invalid BNB history response')
 rows=data.get('result')
 if data.get('status')!='1':
  if rows==[] and str(data.get('message','')).lower().startswith('no transactions'):rows=[]
  else:raise ValueError(chain+' explorer rejected history access. Check API key permissions, plan and rate limits.')
 if not isinstance(rows,list) or len(rows)>50:raise ValueError('Invalid BNB history page')
 items=[];blocks=[]
 for row in rows:
  source=providers.validate_address(chain,row['from']);target=providers.validate_address(chain,row['to']) if row.get('to') else None
  if source!=address and target!=address:raise ValueError('BNB provider returned another wallet')
  txhash=row.get('hash')
  if not isinstance(txhash,str) or not re.fullmatch(r'0x[0-9a-fA-F]{64}',txhash):raise ValueError('Invalid BNB transaction hash')
  block=int(row['blockNumber']);blocks.append(block)
  quantity=units(row['value']);fee=units(int(row['gasUsed'])*int(row['gasPrice'])) if source==address else None
  items.append({'event_id':chain+':transaction:'+txhash,'hash':txhash,'date':datetime.fromtimestamp(int(row['timeStamp']),timezone.utc).isoformat(),'kind':'native_transfer' if Decimal(quantity) else 'contract_activity','direction':'self' if source==target else 'out' if source==address else 'in','asset':providers.CHAINS[chain][0],'asset_id':chain+':native','quantity':quantity,'fee':fee,'status':'failed' if row.get('isError')=='1' else 'confirmed','from_address':source,'to_address':target,'identity_verified':True})
 # Freeze the initial upper block so newer blocks do not shift older pages.
 following={'endblock':max(blocks) if page==1 else endblock,'page':page+1} if len(rows)==50 else None
 return {'items':items,'cursors':{'transactions':following},'coverage':chain+' external native transactions only, 50 per page. No token transfers, internals, NFTs or automatic swaps. '+('Public Routescan API; rate limits apply.' if chain=='Avalanche' else 'Etherscan API plan access required.'),'updated_at':int(time.time())}
