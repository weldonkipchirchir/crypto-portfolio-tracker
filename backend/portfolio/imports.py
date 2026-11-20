"""CSV preview and normalized overlap detection, without mutating the ledger."""
import csv,io,re
from datetime import datetime,timedelta,timezone
from decimal import InvalidOperation
from decimal import Decimal,localcontext
FIELDS=('date','symbol','side','quantity','price','fee','account')
def key(row):
 return tuple(str(Decimal(str(row[field])).normalize()) if field in ('quantity','price','fee') else str(row[field]) for field in FIELDS)
def binance_order(values,headers,offset,rate):
 if len(values)!=len(headers):raise ValueError('Row has a different number of values than its header')
 cells={name:values[i].strip() for i,name in enumerate(headers)}
 if cells['status'].upper()!='FILLED':return None
 pair=cells['pair'].upper()
 quote=next((q for q in ('USDT','USD') if pair.endswith(q)),None)
 if not quote:raise ValueError('This order is not quoted in USD or USDT. Convert its execution value to USD before importing.')
 symbol=pair[:-len(quote)]
 if not re.fullmatch(r'[A-Z0-9_.-]{1,30}',symbol):raise ValueError('Invalid Binance trading pair')
 amount=cells['executed']
 if not amount.upper().endswith(symbol):raise ValueError('Executed amount does not match the pair base asset')
 quantity=amount[:-len(symbol)].strip()
 price=cells['average price']
 if price.upper().endswith(quote):price=price[:-len(quote)].strip()
 try:
  qty=Decimal(quantity);average=Decimal(price)
  if not qty.is_finite() or qty<=0 or not average.is_finite() or average<=0 or any(n.adjusted()>30 or n.as_tuple().exponent< -30 for n in (qty,average)):raise ValueError('Filled orders require positive executed amounts and average prices')
 except InvalidOperation:raise ValueError('Invalid executed amount or average execution price') from None
 # The final Time column is the execution time, rather than order placement.
 date=datetime.fromisoformat(cells['time'])
 if date.tzinfo is None:date=date.replace(tzinfo=timezone(timedelta(minutes=offset)))
 with localcontext() as ctx:
  ctx.prec=128;usd_price=average*(rate if quote=='USDT' else Decimal(1))
 return dict(date=date.astimezone(timezone.utc).isoformat(),symbol=symbol,side=cells['side'].lower(),quantity=str(qty),price=str(usd_price),fee='0',account='Binance Spot CSV')

def preview(text,existing,normalize,calculate,options=None):
 if not isinstance(text,str):raise ValueError('CSV must be text')
 if options is not None and not isinstance(options,dict):raise ValueError('Invalid CSV import options')
 reader=csv.reader(io.StringIO(text.lstrip('\ufeff')));header=next(reader,[])
 names=[re.sub('[¹²³]','',name).strip().lower() for name in header]
 binance={'pair','executed','average price','status','side','time','order price','order amount'}.issubset(names)
 warnings=[];offset=0;rate=Decimal(1);options=options or {}
 if binance:
  offset=options.get('utc_offset_minutes')
  if type(offset) is not int or not -720<=offset<=840:raise ValueError('Choose the Binance CSV timezone before previewing (UTC offset hours).')
  try:
   rate=Decimal(str(options.get('usdt_usd_rate','1')))
   if not rate.is_finite() or not Decimal('.5')<=rate<=Decimal('2'):raise ValueError()
  except (ValueError,InvalidOperation):raise ValueError('Enter a USD-per-USDT rate between 0.5 and 2.') from None
  warnings=['Binance order-level averages are imported, not individual fills. Only FILLED orders are included.', 'This file has no fees. Imported fees are zero; profit/loss will exclude any missing fees.', 'USDT execution prices are converted using '+str(rate)+' USD per USDT. A rate of 1 is a parity estimate, not verified historical FX.', 'Naive execution times use UTC offset '+str(offset/60)+' hours and are stored in UTC.']
 elif not {'date','symbol','side','quantity','price'}.issubset(header):raise ValueError('Use an Orbit CSV with date, symbol, side, quantity and price columns, or a Binance Spot Order History export.')
 elif len(set(header))!=len(header):raise ValueError('Orbit CSV headers must not be duplicated')
 seen={key(row) for row in existing};additions=[];errors=[];duplicates=0;skipped=0
 for index,values in enumerate(reader,start=2):
  if index>10001:raise ValueError('Import at most 10,000 rows at a time')
  if not values or not any(v.strip() for v in values):continue
  try:
   if len(values)>len(header):raise ValueError('Row has more values than the header')
   if binance:
    raw=binance_order(values,names,offset,rate)
    if raw is None:skipped+=1;continue
   else:raw=dict(zip(header,values))
   if raw.get('fee') in ('',None):raw['fee']='0'
   if raw.get('account') in ('',None):raw['account']='Manual'
   row=normalize(raw);identity=key(row)
   if identity in seen:duplicates+=1;continue
   seen.add(identity);additions.append(row)
  except (ValueError,KeyError,TypeError,AttributeError) as error:errors.append({'row':index,'error':str(error)})
 if not errors and additions:
  try:calculate(existing+[{**row,'id':1000000000+i} for i,row in enumerate(additions)],{})
  except ValueError as error:errors.append({'row':0,'error':str(error)})
 return {'trades':additions,'count':len(additions),'duplicates':duplicates,'skipped':skipped,'errors':errors,'source':'Binance Spot Order History' if binance else 'Orbit CSV','requires_acknowledgement':binance,'warnings':warnings,'warning':'Exact matches of date, asset, side, amount, price, fee and account are skipped. Review identical legitimate fills before importing.'}
