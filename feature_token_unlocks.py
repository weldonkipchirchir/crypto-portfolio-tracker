"""Account-private, manually sourced unlock events. No provider calls or supply inference."""
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
import ipaddress
import re
import uuid

PROVENANCE = 'Manually entered; not independently verified by Orbit.'

def init(c):
    c.execute('CREATE TABLE IF NOT EXISTS token_unlock_events(user_id INTEGER NOT NULL,id TEXT NOT NULL,coin_id TEXT NOT NULL,unlock_date TEXT NOT NULL,amount TEXT NOT NULL,recipient TEXT NOT NULL,source_url TEXT NOT NULL,circulating TEXT,snapshot_asof TEXT,created_at TEXT NOT NULL,PRIMARY KEY(user_id,id))')

def number(value):
    if isinstance(value, bool) or not isinstance(value, (str,int,float)) or len(str(value))>80: raise ValueError('Use a positive finite token amount')
    try: n=Decimal(str(value))
    except InvalidOperation: raise ValueError('Use a positive finite token amount')
    if not n.is_finite() or n<=0 or n>Decimal('1e30') or n.as_tuple().exponent < -18: raise ValueError('Use a positive amount up to 1e30 and 18 decimal places')
    return format(n,'f')

def day(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value): raise ValueError('Use a UTC date YYYY-MM-DD')
    try: date.fromisoformat(value)
    except ValueError: raise ValueError('Use a valid UTC calendar date')
    return value

def source(value):
    if not isinstance(value,str) or len(value)>2000 or any(ord(x)<=32 for x in value) or any(x in value for x in '\\<>"'): raise ValueError('Use a public HTTPS source URL')
    try:
        u=urlsplit(value); host=u.hostname
        if u.scheme!='https' or not host or u.username or u.password or u.port not in (None,443): raise ValueError()
        if not re.fullmatch(r'[A-Za-z0-9.-]+',host) or '.' not in host or host.endswith('.') or host.lower().endswith(('.localhost','.local','.internal')): raise ValueError()
        try:
            if not ipaddress.ip_address(host).is_global: raise ValueError()
        except ValueError:
            if re.fullmatch(r'[0-9.]+',host) or ':' in host: raise ValueError()
    except (ValueError,TypeError): raise ValueError('Use a public HTTPS source URL without credentials')
    return value

def action(c,uid,raw):
    op=raw.get('operation'); identity=raw.get('id')
    if op=='delete':
        if raw.get('confirm') is not True: raise ValueError('Confirm deletion of the saved event')
        if not c.execute('SELECT id FROM token_unlock_events WHERE user_id=? AND id=?',(uid,identity)).fetchone(): raise ValueError('Event not found')
        c.execute('DELETE FROM token_unlock_events WHERE user_id=? AND id=?',(uid,identity))
        return {'ok':True}
    if op!='create': raise ValueError('Unknown unlock operation')
    if c.execute('SELECT COUNT(*) AS n FROM token_unlock_events WHERE user_id=?',(uid,)).fetchone()['n']>=500: raise ValueError('Use up to 500 saved unlock events')
    coin=raw.get('coin_id'); recipient=raw.get('recipient')
    if not isinstance(coin,str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,99}',coin): raise ValueError('Use an exact lowercase coin ID, not a ticker')
    if not isinstance(recipient,str) or not 1<=len(recipient.strip())<=100 or any(ord(x)<32 for x in recipient): raise ValueError('Use a recipient category of 1 to 100 characters')
    snapshot=raw.get('circulating'); asof=raw.get('snapshot_asof')
    if snapshot in ('',None) and asof in ('',None): snapshot=asof=None
    elif snapshot in ('',None) or asof in ('',None): raise ValueError('Supply snapshot and its UTC as-of date are both required')
    else: snapshot=number(snapshot); asof=day(asof)
    identity=uuid.uuid4().hex
    c.execute('INSERT INTO token_unlock_events VALUES (?,?,?,?,?,?,?,?,?,?)',(uid,identity,coin,day(raw.get('unlock_date')),number(raw.get('amount')),recipient.strip(),source(raw.get('source_url')),snapshot,asof,datetime.now(timezone.utc).isoformat()))
    return {'ok':True,'id':identity}

def read(c,uid,raw):
    today=datetime.now(timezone.utc).date().isoformat(); events=[]
    for row in c.execute('SELECT id,coin_id,unlock_date,amount,recipient,source_url,circulating,snapshot_asof,created_at FROM token_unlock_events WHERE user_id=? ORDER BY unlock_date,id LIMIT 500',(uid,)):
        item=dict(row);item['provenance']=PROVENANCE;item['upcoming']=item['unlock_date']>=today
        item['percent_circulating']=format(Decimal(item['amount'])/Decimal(item['circulating'])*100,'.6f') if item['circulating'] else None
        events.append(item)
    return {'events':events,'today':today,'provider':{'configured':False,'status':'Unconfigured: no licensed provider connected. No subscription required for manual entries.'},'coverage':PROVENANCE+' These are your saved events, not a complete unlock schedule. UTC dates have no intraday time. Amounts are tokens, not USD. Supply never implies an unlock schedule.'}
