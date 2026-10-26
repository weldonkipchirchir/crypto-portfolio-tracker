"""Public, same-venue price snapshots for chart reference lines (never FX converted)."""
import time
from decimal import Decimal
from urllib.parse import urlencode
import coin_market as market
import exchange_charts as exchange
import providers


def positive(value):
 result=market.numeric(value)
 if result is None or Decimal(result)<=0:raise ValueError('Invalid current price')
 return result


def quote(coin_id,source='coingecko'):
 identity=market.identifier(coin_id)
 if not isinstance(source,str) or source not in ('coingecko','binance','coinbase'):raise ValueError('Unsupported quote provider')
 if source!='coingecko' and identity not in exchange.ASSETS:raise ValueError('No verified exchange product mapping')
 market.allowed(identity)
 def load():
  now=int(time.time())
  if source=='coingecko':
   payload=market.request('/simple/price?'+urlencode({'ids':identity,'vs_currencies':'usd','include_last_updated_at':'true'}))
   coin=payload.get(identity) if isinstance(payload,dict) else None
   if not isinstance(coin,dict):raise ValueError('Coin price identity unavailable')
   stamp=coin.get('last_updated_at')
   if isinstance(stamp,bool) or not isinstance(stamp,(int,float)) or not now-900<=stamp<=now+60:raise ValueError('Current coin price is outdated')
   return {'coin_id':identity,'source':'CoinGecko','price':positive(coin.get('usd')),'quote_currency':'USD','pair':None,'observed_at':int(stamp),'received_at':int(time.time()),'timestamp_kind':'provider_update','coverage':'CoinGecko aggregate USD price; provider update time, not an exchange trade. Public provider caching applies.'}
  base=exchange.ASSETS[identity];unit='USDT' if source=='binance' else 'USD';pair=base+unit if source=='binance' else base+'-'+unit
  meta=exchange.metadata(source,pair,base,unit)
  if meta.get('stale') or meta.get('source')!=source or meta.get('pair')!=pair or meta.get('base_currency')!=base or meta.get('quote_currency')!=unit:raise ValueError('Fresh exchange identity unavailable')
  path='/api/v3/ticker/price?'+urlencode({'symbol':pair}) if source=='binance' else '/products/'+pair+'/ticker'
  payload=providers.request_json(exchange.ROOTS[source]+path)
  if not isinstance(payload,dict):raise ValueError('Invalid quote response')
  now=int(time.time())
  if source=='binance':
   if payload.get('symbol')!=pair:raise ValueError('Exchange quote symbol mismatch')
   stamp=None;kind='received';coverage='Binance spot last price in USDT (not USD). Receipt time only: this endpoint supplies no exchange event timestamp.'
  else:
   stamp=market.stamp(payload.get('time'))
   if stamp is None or not now-900<=stamp<=now+60:raise ValueError('Exchange last trade is outdated')
   kind='last_trade';coverage='Coinbase Exchange spot last trade in USD; event time may precede receipt time.'
  return {'coin_id':identity,'source':'Binance' if source=='binance' else 'Coinbase Exchange','price':positive(payload.get('price')),'base_currency':base,'quote_currency':unit,'pair':pair,'observed_at':stamp,'received_at':now,'timestamp_kind':kind,'coverage':coverage}
 return market.cached(('chart','current-quote-v2',source,identity),60 if source=='coingecko' else 4,load)
