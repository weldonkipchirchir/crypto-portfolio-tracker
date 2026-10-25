"""Explicit, atomic promotion of reviewed events into the existing trade ledger."""
from decimal import Decimal,localcontext
import json,time
import providers,imports

def bind_asset(c,uid,asset,chain,requested,validate_symbol):
 symbol=validate_symbol(requested)
 native=asset['asset_id']==chain+':native'
 if native:
  expected=providers.LEDGER_ALIASES.get(chain)
  if symbol!=expected:raise ValueError('Use '+str(expected)+' for the native asset')
 elif symbol in providers.COINS:raise ValueError('Use a unique ledger alias such as TOKEN_'+asset['asset_id'][-8:]+'. Market symbols are reserved for native or manually tracked assets.')
 previous=c.execute('SELECT symbol FROM asset_bindings WHERE user_id=? AND asset_id=?',(uid,asset['asset_id'])).fetchone()
 if previous and previous['symbol']!=symbol:raise ValueError('This asset is already linked to ledger symbol '+previous['symbol'])
 occupied=c.execute('SELECT asset_id FROM asset_bindings WHERE user_id=? AND symbol=?',(uid,symbol)).fetchone()
 if occupied and occupied['asset_id']!=asset['asset_id']:raise ValueError('This ledger symbol belongs to another chain asset; choose a unique alias')
 c.execute('INSERT OR IGNORE INTO asset_bindings VALUES (?,?,?)',(uid,asset['asset_id'],symbol))
 return symbol

def confirm(c,uid,candidate,raw,normalize,calculate,number,validate_symbol):
 if raw.get('acknowledge') is not True:raise ValueError('Confirm the asset identities, original cost, date and absence of previously imported trades')
 kind=candidate['kind']
 if kind not in ('swap_candidate','acquisition_review'):raise ValueError('This activity needs manual trade entry; it cannot be confirmed automatically')
 if len(candidate['received'])!=1 or (kind=='swap_candidate' and len(candidate['sent'])!=1) or (kind=='acquisition_review' and candidate['sent']):raise ValueError('Only a single acquisition or a simple two-asset swap can be confirmed')
 total=number(raw.get('usd_value'),kind=='swap_candidate');fee=number(raw.get('fee_usd',0));date=raw.get('date')
 if not date:raise ValueError('Enter the original purchase date or swap date')
 received=candidate['received'][0];received_symbol=bind_asset(c,uid,received,candidate['chain'],raw.get('received_symbol'),validate_symbol)
 account='Reviewed wallet '+str(candidate['wallet_id'])+' ('+candidate['chain']+')'
 def entry(asset,symbol,side,entry_fee):
  quantity=number(asset['quantity'],True)
  with localcontext() as context:
   context.prec=100
   unit_price=(total/quantity).quantize(Decimal('1e-24'))
  if total>0 and unit_price==0:raise ValueError('Price is below supported precision; enter this trade manually')
  return normalize(dict(date=date,symbol=symbol,side=side,quantity=str(quantity),price=str(unit_price),fee=str(entry_fee),account=account))
 additions=[]
 if kind=='swap_candidate':
  sent=candidate['sent'][0];sent_symbol=bind_asset(c,uid,sent,candidate['chain'],raw.get('sent_symbol'),validate_symbol)
  if sent_symbol==received_symbol:raise ValueError('Swap assets must have different ledger symbols')
  additions.append(entry(sent,sent_symbol,'sell',fee));additions.append(entry(received,received_symbol,'buy',0))
 else:additions.append(entry(received,received_symbol,'buy',fee))
 rows=[dict(r) for r in c.execute('SELECT * FROM trades WHERE user_id=?',(uid,))]
 def signature(t):return imports.key({**t,'account':''})
 existing={signature(t) for t in rows}
 if any(signature(t) in existing for t in additions):raise ValueError('A matching trade already exists. Review the ledger rather than importing it again.')
 for i,t in enumerate(additions):t['id']=1000000000+i
 calculate(rows+additions,{})
 trade_ids=[]
 for t in additions:
  cursor=c.execute('INSERT INTO trades(user_id,date,symbol,side,quantity,price,fee,account) VALUES (?,?,?,?,?,?,?,?)',(uid,*(t[k] for k in ('date','symbol','side','quantity','price','fee','account'))));trade_ids.append(cursor.lastrowid)
 details={'candidate':candidate,'trade_ids':trade_ids,'original_date':date,'usd_value':str(total),'fee_usd':str(fee),'confirmed_at':int(time.time())}
 c.execute('INSERT INTO review_decisions VALUES (?,?,?,?)',(uid,candidate['id'],'confirmed',json.dumps(details)))
 return len(additions)
