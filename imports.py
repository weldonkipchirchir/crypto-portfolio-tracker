"""CSV preview and normalized overlap detection, without mutating the ledger."""
import csv,io
from decimal import Decimal
FIELDS=('date','symbol','side','quantity','price','fee','account')
def key(row):
 return tuple(str(Decimal(str(row[field])).normalize()) if field in ('quantity','price','fee') else str(row[field]) for field in FIELDS)
def preview(text,existing,normalize,calculate):
 if not isinstance(text,str):raise ValueError('CSV must be text')
 reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
 if not reader.fieldnames or not {'date','symbol','side','quantity','price'}.issubset(reader.fieldnames):raise ValueError('CSV requires date, symbol, side, quantity and price columns')
 seen={key(row) for row in existing}; additions=[];errors=[];duplicates=0
 for index,raw in enumerate(reader,start=2):
  if index>10001:raise ValueError('Import at most 10,000 rows at a time')
  if None in raw:errors.append({'row':index,'error':'Row has more values than the header'});continue
  try:
   if raw.get('fee') in ('',None):raw['fee']='0'
   if raw.get('account') in ('',None):raw['account']='Manual'
   row=normalize(raw);identity=key(row)
   if identity in seen:duplicates+=1;continue
   seen.add(identity);additions.append(row)
  except (ValueError,KeyError,TypeError,AttributeError) as error:errors.append({'row':index,'error':str(error)})
 if not errors and additions:
  try:calculate(existing+[{**row,'id':1000000000+i} for i,row in enumerate(additions)],{})
  except ValueError as error:errors.append({'row':0,'error':str(error)})
 return {'trades':additions,'count':len(additions),'duplicates':duplicates,'errors':errors,'warning':'Exact matches of date, asset, side, amount, price, fee and account are skipped. Review identical legitimate fills before importing.'}
