"""Named account-scoped views of existing holdings; groups never own trades."""
import json
import uuid
from decimal import Decimal
import portfolio_daily
from advanced_portfolio import number

COVERAGE = 'Saved balances and saved USD quotes only; values may be stale. Unpriced holdings are excluded. Connected and ledger values are separate overlapping views and must not be added. No trade linkage, cost basis or returns are inferred.'

def init(c):
    c.execute('CREATE TABLE IF NOT EXISTS portfolio_groups (user_id INTEGER NOT NULL,id TEXT NOT NULL,name TEXT NOT NULL,kind TEXT NOT NULL,members TEXT NOT NULL,PRIMARY KEY(user_id,id))')

def sources(c, uid):
    wallets = []
    for r in c.execute('SELECT w.id,w.chain,w.address,w.label,s.data,t.data AS token_data FROM wallets w LEFT JOIN wallet_snapshots s ON s.wallet_id=w.id LEFT JOIN wallet_tokens t ON t.wallet_id=w.id WHERE w.user_id=?', (uid,)):
        w = dict(r)
        w['snapshot'] = json.loads(w.pop('data') or 'null')
        w['token_snapshot'] = json.loads(w.pop('token_data') or 'null')
        wallets.append(w)
    exchanges = [dict(id=r['id'],label=r['label'],snapshot=json.loads(r['snapshot'])) for r in c.execute('SELECT id,label,snapshot FROM exchange_connections WHERE user_id=?',(uid,))]
    accounts = [r['account'] for r in c.execute('SELECT DISTINCT account FROM trades WHERE user_id=? ORDER BY account',(uid,))]
    return wallets, exchanges, accounts

def validated(raw, wallets, exchanges, accounts):
    kind = raw.get('kind')
    if kind not in ('connected','ledger'): raise ValueError('Choose connected or ledger')
    name = raw.get('name')
    if not isinstance(name,str) or not 1 <= len(name.strip()) <= 80 or any(ord(ch)<32 for ch in name): raise ValueError('Use a name of 1 to 80 characters')
    members = raw.get('members')
    if not isinstance(members,dict) or set(members)-{'wallets','exchanges','accounts'}: raise ValueError('Invalid memberships')
    allowed = {'wallets':{w['id'] for w in wallets},'exchanges':{e['id'] for e in exchanges},'accounts':set(accounts)}
    result = {}
    for key in allowed:
        ids = members.get(key,[])
        if not isinstance(ids,list) or len(ids)>1000 or any(type(v) not in (str,int) or v not in allowed[key] for v in ids): raise ValueError('Membership is not available for this account')
        result[key] = list(dict.fromkeys(ids))
    if kind=='connected' and result['accounts'] or kind=='ledger' and (result['wallets'] or result['exchanges']): raise ValueError('Keep connected and ledger memberships separate')
    return name.strip(),kind,result

def action(c, uid, raw):
    operation = raw.get('operation','save')
    identity = raw.get('id')
    existing = c.execute('SELECT id FROM portfolio_groups WHERE user_id=? AND id=?',(uid,identity)).fetchone() if isinstance(identity,str) else None
    if identity is not None and existing is None: raise ValueError('Portfolio group not found')
    if operation=='delete':
        if not existing: raise ValueError('Portfolio group not found')
        c.execute('DELETE FROM portfolio_groups WHERE user_id=? AND id=?',(uid,identity))
        return {'ok':True}
    if operation!='save': raise ValueError('Unknown operation')
    name,kind,members = validated(raw,*sources(c,uid))
    if not existing and c.execute('SELECT COUNT(*) AS n FROM portfolio_groups WHERE user_id=?',(uid,)).fetchone()['n']>=20: raise ValueError('Use up to 20 portfolio groups')
    identity = identity or uuid.uuid4().hex
    c.execute('INSERT INTO portfolio_groups(user_id,id,name,kind,members) VALUES (?,?,?,?,?) ON CONFLICT(user_id,id) DO UPDATE SET name=EXCLUDED.name,kind=EXCLUDED.kind,members=EXCLUDED.members',(uid,identity,name,kind,json.dumps(members)))
    return {'ok':True,'id':identity}

def read(c, uid, raw):
    wallets, exchanges, accounts = sources(c,uid)
    quotes = {r['symbol']:{'price':r['price']} for r in c.execute('SELECT symbol,price FROM prices WHERE user_id=?',(uid,))}
    trades = [dict(r) for r in c.execute('SELECT account,symbol,quantity,side FROM trades WHERE user_id=?',(uid,))]
    groups = [dict(r) for r in c.execute('SELECT id,name,kind,members FROM portfolio_groups WHERE user_id=? ORDER BY name,id',(uid,))]
    def valuation(kind,members):
        if kind=='connected':
            selected_wallets=[w for w in wallets if w['id'] in members['wallets']]
            selected_exchanges=[e for e in exchanges if e['id'] in members['exchanges']]
            observation=portfolio_daily.observation(selected_wallets,quotes,selected_exchanges)
            missing=sum(not w.get('snapshot') or bool((w.get('snapshot') or {}).get('error')) for w in selected_wallets)
            return {'value':observation['value'] if observation else None,'unpriced':(observation['unpriced'] if observation else None),'missing_snapshots':missing,'source':'Saved connected observations'}
        quantities={}
        for t in trades:
            if t['account'] in members['accounts']:
                quantities[t['symbol']]=quantities.get(t['symbol'],Decimal(0))+Decimal(t['quantity'])*(1 if t['side']=='buy' else -1)
        total=Decimal(0);priced=unpriced=0
        for symbol,quantity in quantities.items():
            if not quantity: continue
            price=number(quotes.get(symbol,{}).get('price'))
            if price is None: unpriced+=1
            else: total+=quantity*price;priced+=1
        return {'value':str(total) if priced else None,'unpriced':unpriced,'source':'Ledger net quantities × saved USD quotes'}
    union={k:set() for k in ('wallets','exchanges','accounts')}
    for group in groups:
        group['members']=json.loads(group['members'])
        # Remove deleted sources from valuation, while preserving explicit saved membership for editing.
        group['valuation']=valuation(group['kind'],group['members'])
        for key in union: union[key].update(group['members'].get(key,[]))
    combined={kind:valuation(kind,union) for kind in ('connected','ledger')}
    return {'groups':groups,'combined':combined,'sources':{'wallets':[{'id':w['id'],'label':w['label']} for w in wallets],'exchanges':[{'id':e['id'],'label':e['label']} for e in exchanges],'accounts':[{'id':a,'label':a or '(Unnamed account)'} for a in accounts]},'coverage':COVERAGE}
