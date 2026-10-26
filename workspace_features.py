"""Account-scoped bounded chart setups; declarative configuration, never executable scripts."""
import json,re,time

def init(c):
 c.execute('CREATE TABLE IF NOT EXISTS chart_setups (user_id INTEGER NOT NULL,setup_key TEXT NOT NULL,data TEXT NOT NULL,updated_at INTEGER NOT NULL,PRIMARY KEY(user_id,setup_key))')

def key(raw):
 value=raw.get('key')
 if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_:/.-]{1,160}',value):raise ValueError('Invalid chart setup key')
 return value

def load(c,uid,raw):
 row=c.execute('SELECT data FROM chart_setups WHERE user_id=? AND setup_key=?',(uid,key(raw))).fetchone()
 return {'value':json.loads(row['data']) if row else None}

def save(c,uid,raw):
 identity=key(raw);value=raw.get('value')
 if not isinstance(value,dict):raise ValueError('Invalid chart setup')
 try:data=json.dumps(value,allow_nan=False)
 except (TypeError,ValueError,OverflowError):raise ValueError('Invalid chart setup') from None
 if len(data)>50000:raise ValueError('Chart setup is too large')
 exists=c.execute('SELECT setup_key FROM chart_setups WHERE user_id=? AND setup_key=?',(uid,identity)).fetchone()
 if not exists and c.execute('SELECT COUNT(*) AS n FROM chart_setups WHERE user_id=?',(uid,)).fetchone()['n']>=100:raise ValueError('Keep up to 100 coin chart setups')
 c.execute('INSERT INTO chart_setups(user_id,setup_key,data,updated_at) VALUES (?,?,?,?) ON CONFLICT (user_id,setup_key) DO UPDATE SET data=EXCLUDED.data,updated_at=EXCLUDED.updated_at',(uid,identity,data,int(time.time())))
 return {'ok':True}
