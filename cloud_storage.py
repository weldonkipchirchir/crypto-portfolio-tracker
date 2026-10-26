"""PostgreSQL persistence for the existing SQLite-shaped application queries."""
import os,re,sqlite3
from contextlib import contextmanager
UPSERTS={
 'wallet_tokens':(('wallet_id','data'),('wallet_id',)),
 'token_watchlist':(('wallet_id','contracts'),('wallet_id',)),
 'wallet_snapshots':(('wallet_id','data'),('wallet_id',)),
 'chain_history':(('wallet_id','event_id','data'),('wallet_id','event_id')),
 'history_sync':(('wallet_id','data'),('wallet_id',)),
 'prices':(('user_id','symbol','price'),('user_id','symbol')),
 'price_metadata':(('user_id','symbol','source','updated_at'),('user_id','symbol'))}
class Row(dict):
 def __getitem__(self,key):return tuple(self.values())[key] if isinstance(key,int) else super().__getitem__(key)
def row_factory(cursor):
 names=[column.name for column in (cursor.description or [])]
 return lambda values:Row(zip(names,values))
class Cursor:
 def __init__(self,cursor,lastrowid=None):self.cursor=cursor;self.lastrowid=lastrowid
 def fetchone(self):return self.cursor.fetchone()
 def fetchall(self):return self.cursor.fetchall()
 def __iter__(self):return iter(self.cursor)
 @property
 def rowcount(self):return self.cursor.rowcount
class Connection:
 dialect='postgres'
 def __init__(self,url):
  import psycopg
  self.psycopg=psycopg
  self.raw=psycopg.connect(url,connect_timeout=10,row_factory=row_factory,**({'sslmode':'require'} if os.environ.get('VERCEL')=='1' else {}))
  self.raw.execute("SET statement_timeout='35s'")
  self.raw.execute("SET lock_timeout='5s'")
 def execute(self,sql,params=()):
  sql=sql.strip();insert_id=bool(re.match(r'INSERT INTO (users|trades|wallets)\(',sql,re.I))
  replace=re.match(r'INSERT OR REPLACE INTO (\w+) VALUES',sql,re.I)
  if replace:
   table=replace[1];columns,keys=UPSERTS[table]
   sql=sql.replace('INSERT OR REPLACE','INSERT',1)+' ON CONFLICT ('+','.join(keys)+') DO UPDATE SET '+','.join(c+'=EXCLUDED.'+c for c in columns if c not in keys)
  elif sql.startswith('INSERT OR IGNORE'):
   sql=sql.replace('INSERT OR IGNORE','INSERT',1)+' ON CONFLICT DO NOTHING'
  sql=sql.replace('?','%s')
  if insert_id:sql+=' RETURNING id'
  try:
   cursor=self.raw.execute(sql,params)
   return Cursor(cursor,cursor.fetchone()[0] if insert_id else None)
  except self.psycopg.IntegrityError:raise sqlite3.IntegrityError('Record conflicts with an existing entry') from None
  except self.psycopg.Error:raise sqlite3.OperationalError('Cloud storage unavailable') from None
 def executescript(self,script):
  for sql in script.split(';'):
   if not sql.strip():continue
   if re.search(r'CREATE TABLE IF NOT EXISTS (users|trades|wallets)\(',sql):sql=sql.replace('id INTEGER PRIMARY KEY','id BIGSERIAL PRIMARY KEY',1)
   self.execute(sql.replace('expires REAL','expires DOUBLE PRECISION'))
 def commit(self):self.raw.commit()
 def close(self):self.raw.close()
 def __enter__(self):return self
 def __exit__(self,kind,error,tb):
  if kind:self.raw.rollback()
  else:self.raw.commit()
@contextmanager
def connect(url=None):
 connection=Connection(url or os.environ['DATABASE_URL'])
 try:
  with connection:yield connection
 finally:connection.close()
def initialize_limits():
 with connect() as c:
  c.execute('SELECT pg_advisory_xact_lock(71420002)')
  c.execute('CREATE TABLE IF NOT EXISTS orbit_limits (key TEXT PRIMARY KEY, hits INTEGER NOT NULL, expires DOUBLE PRECISION NOT NULL)')
  c.execute('CREATE TABLE IF NOT EXISTS orbit_leases (key TEXT PRIMARY KEY, token TEXT NOT NULL, expires DOUBLE PRECISION NOT NULL)')
def allowance(key,limit,seconds):
 with connect() as c:
  row=c.execute('INSERT INTO orbit_limits VALUES (?,1,EXTRACT(EPOCH FROM clock_timestamp())+?) ON CONFLICT (key) DO UPDATE SET hits=CASE WHEN orbit_limits.expires<=EXTRACT(EPOCH FROM clock_timestamp()) THEN 1 ELSE orbit_limits.hits+1 END, expires=CASE WHEN orbit_limits.expires<=EXTRACT(EPOCH FROM clock_timestamp()) THEN EXCLUDED.expires ELSE orbit_limits.expires END RETURNING hits',(key,seconds)).fetchone()
  c.execute('DELETE FROM orbit_limits WHERE expires<EXTRACT(EPOCH FROM clock_timestamp())-86400')
  return row['hits']<=limit
@contextmanager
def provider_action(uid,*,kind='provider',limit=12,max_concurrent=1):
 import secrets
 from runtime_security import BudgetExceeded
 if max_concurrent not in (1,4):raise ValueError('Invalid operation concurrency')
 key=kind+':'+str(uid);token=secrets.token_hex(16)
 if not allowance(key,limit,60):raise BudgetExceeded('Provider request budget reached. Retry shortly.')
 with connect() as c:
  leased=None
  for slot in range(max_concurrent):
   candidate=key if max_concurrent==1 else key+':slot:'+str(slot)
   row=c.execute('INSERT INTO orbit_leases VALUES (?,?,EXTRACT(EPOCH FROM clock_timestamp())+60) ON CONFLICT (key) DO UPDATE SET token=EXCLUDED.token,expires=EXCLUDED.expires WHERE orbit_leases.expires<=EXTRACT(EPOCH FROM clock_timestamp()) RETURNING key',(candidate,token)).fetchone()
   if row:leased=candidate;break
  if leased is None:raise BudgetExceeded('A provider operation is already running for this account')
 key=leased
 try:yield
 finally:
  with connect() as c:c.execute('DELETE FROM orbit_leases WHERE key=? AND token=?',(key,token))
