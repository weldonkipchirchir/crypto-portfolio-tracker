"""Private, explicitly manual income and expense evidence; separate from trade P&L."""
import json,uuid,time
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
KINDS={'staking_reward','earn_reward','funding_received','funding_paid','network_fee','withdrawal_fee'}
INCOME={'staking_reward','earn_reward','funding_received'}
def init(c):
 c.execute('CREATE TABLE IF NOT EXISTS manual_income_records(user_id INTEGER NOT NULL,id TEXT NOT NULL,date TEXT NOT NULL,data TEXT NOT NULL,PRIMARY KEY(user_id,id))')
def amount(value,optional=False):
 if optional and value in (None,''):return None
 if isinstance(value,bool) or not isinstance(value,(str,int)) or len(str(value))>100:raise ValueError('Use a finite nonnegative amount')
 try:n=Decimal(value)
 except InvalidOperation:raise ValueError('Invalid amount') from None
 if not n.is_finite() or n<0 or abs(n.adjusted())>30:raise ValueError('Invalid amount')
 return str(n)
def read(c,uid,raw):
 rows=[json.loads(r['data']) for r in c.execute('SELECT data FROM manual_income_records WHERE user_id=? ORDER BY date DESC,id DESC LIMIT 500',(uid,))]
 received=sum((Decimal(r['usd']) for r in rows if r['usd'] is not None and r['kind'] in INCOME),Decimal(0));paid=sum((Decimal(r['usd']) for r in rows if r['usd'] is not None and r['kind'] not in INCOME),Decimal(0));missing=sum(r['usd'] is None for r in rows)
 return {'records':rows,'received_usd_subtotal':str(received),'paid_usd_subtotal':str(paid),'unknown_usd':missing,'net_usd':str(received-paid) if rows and not missing else None,'coverage':'Manual, user-supplied records only; not independently verified. Amounts and historical USD valuations must come from your statements. These entries do not alter trade P&L, balances or cost basis.'}
def action(c,uid,raw):
 if raw.get('operation')=='delete':
  if raw.get('confirm') is not True:raise ValueError('Confirm removal of this manual record')
  if not isinstance(raw.get('id'),str) or not c.execute('DELETE FROM manual_income_records WHERE user_id=? AND id=?',(uid,raw['id'])).rowcount:raise ValueError('Record not found')
  return {'ok':True}
 if raw.get('operation')!='create':raise ValueError('Unknown income operation')
 if c.execute('SELECT COUNT(*) AS n FROM manual_income_records WHERE user_id=?',(uid,)).fetchone()['n']>=500:raise ValueError('Keep up to 500 manual records')
 kind=raw.get('kind');asset=raw.get('asset');source=raw.get('source');account=raw.get('account','')
 if kind not in KINDS:raise ValueError('Choose an income or expense category')
 if not isinstance(asset,str) or not 1<=len(asset.strip())<=160 or any(ord(x)<32 for x in asset):raise ValueError('Enter the exact asset identity')
 if not isinstance(source,str) or not 1<=len(source.strip())<=500 or any(ord(x)<32 for x in source):raise ValueError('Enter your statement or evidence reference')
 if not isinstance(account,str) or len(account)>80:raise ValueError('Account label is too long')
 try:
  date=datetime.fromisoformat(str(raw.get('date','')).replace('Z','+00:00'))
  if date.tzinfo is None or not 1230768000<=date.timestamp()<=time.time()+60:raise ValueError()
 except (ValueError,OverflowError):raise ValueError('Use a valid UTC date no later than now') from None
 quantity=amount(raw.get('quantity'));usd=amount(raw.get('usd'),True)
 if Decimal(quantity)<=0:raise ValueError('Quantity must be positive')
 identity=uuid.uuid4().hex;record={'id':identity,'date':date.astimezone(timezone.utc).isoformat(),'kind':kind,'asset':asset.strip(),'quantity':quantity,'usd':usd,'account':account,'source':source.strip(),'provenance':'Manually entered; not independently verified'}
 c.execute('INSERT INTO manual_income_records VALUES (?,?,?,?)',(uid,identity,record['date'],json.dumps(record)))
 return {'ok':True,'id':identity}
