"""Read-only bounded Binance fills exported into Orbit's reviewed CSV flow."""
import csv,io,re,time
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation,localcontext
import exchange_connections as ex

def amount(value,positive=False):
 if isinstance(value,bool) or not isinstance(value,(str,int)) or len(str(value))>80:raise ValueError('Invalid exchange fill amount')
 try:n=Decimal(value)
 except InvalidOperation:raise ValueError('Invalid exchange fill amount') from None
 if not n.is_finite() or n<0 or positive and n<=0 or abs(n.adjusted())>30:raise ValueError('Invalid exchange fill amount')
 return n

def normalize(rows,pair,rate,account):
 if not isinstance(rows,list) or len(rows)>1000:raise ValueError('Invalid Binance fill response')
 base=pair[:-4];seen=set();fingerprints=set();out=io.StringIO();writer=csv.writer(out);writer.writerow(['date','symbol','side','quantity','price','fee','account'])
 with localcontext() as ctx:
  ctx.prec=100
  for row in rows:
   if not isinstance(row,dict) or row.get('symbol')!=pair or type(row.get('id')) is not int or row['id']<0 or type(row.get('isBuyer')) is not bool:raise ValueError('Invalid Binance fill identity')
   if row['id'] in seen:raise ValueError('Repeated Binance fill identity')
   seen.add(row['id']);stamp=row.get('time')
   if type(stamp) is not int or not 1230768000000<=stamp<=int(time.time()*1000)+60000:raise ValueError('Invalid Binance fill timestamp')
   qty=amount(row.get('qty'),True);price=amount(row.get('price'),True);fee=amount(row.get('commission'))
   if fee and row.get('commissionAsset')!='USDT':raise ValueError('A fill has fees in '+str(row.get('commissionAsset','another asset'))[:20]+'. Historical fee valuation is required; no fills were imported. Use a reviewed CSV with USD fees.')
   fingerprint=(stamp,row['isBuyer'],qty,price,fee)
   if fingerprint in fingerprints:raise ValueError('Distinct fills have identical ledger values. Import requires manual review to avoid treating a genuine fill as a duplicate.')
   fingerprints.add(fingerprint)
   writer.writerow([datetime.fromtimestamp(stamp/1000,timezone.utc).isoformat(),base,'buy' if row['isBuyer'] else 'sell',str(qty),str(price*rate),str(fee*rate),account])
 return out.getvalue()

def preview(c,uid,raw):
 identity=ex.identity(raw);pair=str(raw.get('pair','')).strip().upper()
 if not re.fullmatch(r'[A-Z0-9]{1,26}USDT',pair):raise ValueError('Enter a USDT Spot pair such as BTCUSDT')
 rate=amount(raw.get('usdt_usd_rate'),True)
 if not Decimal('.5')<=rate<=Decimal('2'):raise ValueError('USD per USDT must be between 0.5 and 2')
 row=c.execute('SELECT credentials FROM exchange_connections WHERE user_id=? AND id=?',(uid,identity)).fetchone()
 if not row:raise ValueError('Exchange connection not found')
 credentials=ex.crypt(uid,identity,row['credentials'],True)
 rows=ex.signed(ex.PATHS[4],credentials['api_key'],credentials['api_secret'],symbol=pair)
 return {'csv':normalize(rows,pair,rate,'Binance API '+identity),'count':len(rows),'coverage':'Latest up to 1,000 Spot fills for '+pair+'. Older fills, other pairs, transfers and Earn income are not included. USD conversion uses your supplied rate, not historical FX. Review for overlap with prior CSV imports before confirming.','at_limit':len(rows)==1000}
