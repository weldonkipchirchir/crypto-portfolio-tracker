"""Account profile and private learning notes; all operations are user scoped."""
import hashlib,hmac,json,re,secrets,time

def init(c):
 c.executescript('''CREATE TABLE IF NOT EXISTS account_profiles (user_id INTEGER PRIMARY KEY,name TEXT NOT NULL); CREATE TABLE IF NOT EXISTS learning_notes (user_id INTEGER NOT NULL,note_id TEXT NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,updated_at INTEGER NOT NULL,PRIMARY KEY(user_id,note_id));''')

def state(c,uid):
 user=c.execute('SELECT email FROM users WHERE id=?',(uid,)).fetchone()
 profile=c.execute('SELECT name FROM account_profiles WHERE user_id=?',(uid,)).fetchone()
 return {'email':user['email'],'name':profile['name'] if profile else ''}

def save_profile(c,uid,raw):
 name=raw.get('name','')
 if not isinstance(name,str) or len(name.strip())>80 or any(ord(x)<32 for x in name):raise ValueError('Use a name of up to 80 characters')
 c.execute('INSERT INTO account_profiles(user_id,name) VALUES (?,?) ON CONFLICT (user_id) DO UPDATE SET name=EXCLUDED.name',(uid,name.strip()))
 return state(c,uid)

def change_password(c,uid,raw):
 current=raw.get('current_password');new=raw.get('new_password')
 if not isinstance(current,str) or len(current)>1024 or not isinstance(new,str) or not 12<=len(new)<=1024:raise ValueError('Use your current password and a new password of 12 to 1024 characters')
 row=c.execute('SELECT password FROM users WHERE id=?',(uid,)).fetchone()
 salt,stored=row['password'].split(':',1)
 actual=hashlib.scrypt(current.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
 if not hmac.compare_digest(actual,stored):raise ValueError('Current password is incorrect')
 if current==new:raise ValueError('Choose a different password')
 salt=secrets.token_hex(16);digest=hashlib.scrypt(new.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
 c.execute('UPDATE users SET password=? WHERE id=?',(salt+':'+digest,uid))
 c.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
 return {'ok':True,'sign_in_required':True}

def notes(c,uid):
 return {'notes':[dict(r) for r in c.execute('SELECT note_id,title,body,updated_at FROM learning_notes WHERE user_id=? ORDER BY updated_at DESC,note_id',(uid,))]}

def note_id(value):
 if not isinstance(value,str) or not re.fullmatch(r'[a-f0-9]{32}',value):raise ValueError('Invalid note')
 return value

def save_note(c,uid,raw):
 identity=note_id(raw['note_id']) if raw.get('note_id') else secrets.token_hex(16)
 title=raw.get('title','');body=raw.get('body','')
 if not isinstance(title,str) or not 1<=len(title.strip())<=120 or not isinstance(body,str) or len(body)>20000:raise ValueError('Notes require a title up to 120 characters and text up to 20,000 characters')
 if not c.execute('SELECT note_id FROM learning_notes WHERE user_id=? AND note_id=?',(uid,identity)).fetchone() and c.execute('SELECT COUNT(*) AS n FROM learning_notes WHERE user_id=?',(uid,)).fetchone()['n']>=100:raise ValueError('Keep up to 100 notes')
 c.execute('INSERT INTO learning_notes(user_id,note_id,title,body,updated_at) VALUES (?,?,?,?,?) ON CONFLICT (user_id,note_id) DO UPDATE SET title=EXCLUDED.title,body=EXCLUDED.body,updated_at=EXCLUDED.updated_at',(uid,identity,title.strip(),body,int(time.time())))
 return notes(c,uid)

def delete_note(c,uid,raw):
 c.execute('DELETE FROM learning_notes WHERE user_id=? AND note_id=?',(uid,note_id(raw.get('note_id'))))
 return notes(c,uid)
