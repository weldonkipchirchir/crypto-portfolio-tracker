"""Identity-verified protocol revenue and optional licensed unlock summaries."""
import os,re,time
from urllib.parse import quote
import coin_market as market
import providers

def unavailable(message):return {'available':False,'message':message}

def fundamentals(coin_id):
 identity=market.allowed(coin_id)
 configured=bool(os.environ.get('DEFILLAMA_API_KEY','').strip())
 def revenue_load():
  result={'coin_id':identity,'source':'DefiLlama','revenue':unavailable('No verified protocol revenue coverage for this coin.'),'unlocks':unavailable('Unlock schedules require a configured DefiLlama API subscription. Current supply is not an unlock schedule.')}
  # Slug candidates are only accepted when the provider confirms the same CoinGecko ID.
  try:
   data=providers.request_json('https://api.llama.fi/summary/fees/'+identity+'?dataType=dailyRevenue')
   if isinstance(data,dict) and data.get('gecko_id')==identity:
    values={key:market.numeric(data.get(field)) for key,field in [('day_usd','total24h'),('week_usd','total7d'),('month_usd','total30d')]}
    result['revenue']={'available':any(v is not None for v in values.values()),'protocol':market.text(data.get('displayName') or data.get('name'),100),'source':'DefiLlama','source_url':'https://defillama.com/protocol/'+identity,**values,'definition':'Reported protocol revenue: the portion of fees retained by the protocol. This is not company profit or token-holder income.','observed_at':int(time.time())}
   else:result['revenue']=unavailable('No exact provider coin-ID match. Revenue is not inferred from ticker symbols.')
  except ValueError as error:
   if 'HTTP 404' in str(error):result['revenue']=unavailable('Protocol revenue is not covered for this coin.')
   else:raise ValueError('Protocol revenue provider is temporarily unavailable') from None
  return {'source':'DefiLlama','revenue':result['revenue']}
 def unlock_load():
  result={'unlocks':unavailable('Unlock schedules require a configured DefiLlama API subscription. Current supply is not an unlock schedule.')}
  key=os.environ.get('DEFILLAMA_API_KEY','').strip()
  if key:
   if len(key)>256:raise ValueError('Unlock provider configuration is invalid')
   try:
    rows=providers.request_json('https://pro-api.llama.fi/'+quote(key,safe='')+'/api/emissions')
    if not isinstance(rows,list) or len(rows)>5000:raise ValueError('Invalid emissions response')
    matches=[row for row in rows if isinstance(row,dict) and row.get('gecko_id')==identity]
    if len(matches)==1:
     row=matches[0];result['unlocks']={'available':True,'source':'DefiLlama','source_url':'https://defillama.com/unlocks','project':market.text(row.get('name'),100),'locked_tokens':market.numeric(row.get('totalLocked')),'max_supply':market.numeric(row.get('maxSupply')),'unlocks_per_day':market.numeric(row.get('unlocksPerDay')),'circulating_supply':market.numeric(row.get('circSupply')),'events':[],'message':'Provider emissions summary. A dated event calendar is shown only when verified event fields are available.'}
     for event in (row.get('events') or [])[:100] if isinstance(row.get('events'),list) else []:
      if not isinstance(event,dict):continue
      stamp=market.numeric(event.get('timestamp'))
      if stamp is None:continue
      seconds=float(stamp)
      if seconds!=int(seconds) or not 1230768000<=seconds<=time.time()+315576000:continue
      result['unlocks']['events'].append({'timestamp':int(seconds),'description':market.text(event.get('description') or event.get('label'),240) or 'Provider-reported unlock event'})
    else:result['unlocks']=unavailable('No unique provider coin-ID match for an unlock schedule.')
   except ValueError:raise ValueError('Unlock provider access or data is unavailable. Check the configured API subscription.') from None
   if result['unlocks'].get('available') and not (result['unlocks']['events'] or any(result['unlocks'].get(k) is not None for k in ('locked_tokens','max_supply','unlocks_per_day','circulating_supply'))):
    result['unlocks']=unavailable('The provider returned no supported unlock fields for this coin.')
  return result
 result={'coin_id':identity,'source':'DefiLlama','stale':False}
 for field,loader in [('revenue',revenue_load),('unlocks',unlock_load)]:
  try:
   data=market.cached(('fundamentals',identity,field,configured if field=='unlocks' else False),1800,loader)
   result[field]={**data[field],'fetched_at':data['fetched_at'],'stale':data['stale']}
   result['stale']=result['stale'] or data['stale']
  except ValueError:
   result[field]=unavailable(field.capitalize()+' provider is temporarily unavailable. Retry later.')
 return result
