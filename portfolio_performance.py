"""Recorded weighted-average realized P&L by UTC sale date; no inferred prices."""
from decimal import Decimal

def realized_calendar(rows):
 holdings={};days={};start=None
 for row in sorted(rows,key=lambda r:(r['date'],r.get('id',0))):
  day=row['date'][:10];start=min(start,day) if start else day
  symbol=row['symbol'];quantity=Decimal(str(row['quantity']));price=Decimal(str(row['price']));fee=Decimal(str(row['fee']))
  position=holdings.setdefault(symbol,{'quantity':Decimal(0),'cost':Decimal(0)})
  if row['side']=='buy':position['quantity']+=quantity;position['cost']+=quantity*price+fee
  else:
   if quantity>position['quantity']:raise ValueError('Sale exceeds available holdings')
   basis=position['cost']/position['quantity']*quantity
   profit=quantity*price-fee-basis;position['quantity']-=quantity;position['cost']-=basis
   item=days.setdefault(day,{'realized':Decimal(0),'sales':0});item['realized']+=profit;item['sales']+=1
 return {'start_date':start,'days':[{'date':day,'realized':float(value['realized']),'sales':value['sales']} for day,value in sorted(days.items())],'coverage':'Realized P&L on recorded sale dates, UTC. Weighted-average cost includes buy and sell fees. Days without sales have no realized observation; daily unrealized P&L is not inferred.'}
