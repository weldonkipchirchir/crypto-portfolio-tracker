"""Account-owned, opt-in email alerts with a durable idempotent outbox."""
import os,json,time,sqlite3,urllib.request,urllib.error,smtplib,ssl
from email.message import EmailMessage
from email.utils import parseaddr

def init(c):
 c.execute('CREATE TABLE IF NOT EXISTS alert_email_preferences (user_id INTEGER PRIMARY KEY,enabled INTEGER NOT NULL)')
 c.execute('CREATE TABLE IF NOT EXISTS alert_email_outbox (id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,status TEXT NOT NULL,created_at INTEGER NOT NULL,attempts INTEGER NOT NULL,last_attempt INTEGER NOT NULL,data TEXT NOT NULL)')
 c.execute('CREATE INDEX IF NOT EXISTS alert_email_user ON alert_email_outbox(user_id,created_at)')

def configured():return bool(os.environ.get('ALERT_EMAIL_FROM') and (os.environ.get('RESEND_API_KEY') or os.environ.get('SMTP_HOST') and os.environ.get('SMTP_USER') and os.environ.get('SMTP_PASSWORD')))
def state(c,uid):
 pref=c.execute('SELECT enabled FROM alert_email_preferences WHERE user_id=?',(uid,)).fetchone()
 try:row=c.execute('SELECT email FROM users WHERE id=?',(uid,)).fetchone();recipient=row['email'] if row else None
 except sqlite3.OperationalError:recipient=None
 events=[dict(r) for r in c.execute('SELECT id,status,created_at,attempts FROM alert_email_outbox WHERE user_id=? ORDER BY created_at DESC LIMIT 20',(uid,))]
 return {'enabled':bool(pref and pref['enabled']),'configured':configured(),'recipient':recipient,'events':events,'coverage':'Triggered alerts can be emailed to your signed-in account address. Checks run on request and during active portfolio price refresh, not while the app is closed. Accepted means the mail service accepted the message, not confirmed inbox delivery.'}

def preference(c,uid,raw):
 if type(raw.get('enabled')) is not bool:raise ValueError('Choose whether to email your alerts')
 c.execute('INSERT INTO alert_email_preferences(user_id,enabled) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET enabled=EXCLUDED.enabled',(uid,int(raw['enabled'])))
 return state(c,uid)

def enqueue(c,uid,event):
 settings=state(c,uid)
 if not settings['enabled'] or not settings['configured'] or not settings['recipient']:return False
 now=int(time.time());count=c.execute('SELECT COUNT(*) AS n FROM alert_email_outbox WHERE user_id=? AND created_at>?',(uid,now-86400)).fetchone()['n']
 if count>=20:return False
 data={k:event.get(k) for k in ('symbol','operator','target_usd','price_usd','quote_at','source')}
 c.execute('INSERT INTO alert_email_outbox(id,user_id,status,created_at,attempts,last_attempt,data) VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING',(event['id'],uid,'pending',now,0,0,json.dumps(data)))
 return True

def send(recipient,event,event_id):
 sender=os.environ.get('ALERT_EMAIL_FROM','');address=parseaddr(sender)[1]
 if not address or '@' not in address or any(ch in sender+recipient for ch in '\r\n'):raise ValueError('Invalid mail addresses')
 symbol=str(event.get('symbol') or 'Coin')[:30]
 text=(symbol+' price condition observed.\nCondition: at or '+str(event.get('operator'))+' $'+str(event.get('target_usd'))+' USD.\nObserved price: $'+str(event.get('price_usd'))+' USD.\nProvider: '+str(event.get('source'))+'.\nThis is an observed price alert, not an order or trading recommendation.\nManage email alerts inside Orbit. Maximum 20 alerts per account per day.')
 subject='Orbit price alert: '+symbol
 if os.environ.get('RESEND_API_KEY'):
  body=json.dumps({'from':sender,'to':[recipient],'subject':subject,'text':text}).encode()
  request=urllib.request.Request('https://api.resend.com/emails',data=body,headers={'Authorization':'Bearer '+os.environ['RESEND_API_KEY'],'Content-Type':'application/json','Idempotency-Key':'orbit-alert-'+event_id},method='POST')
  with urllib.request.urlopen(request,timeout=8) as response:result=json.loads(response.read(10000))
  if not isinstance(result,dict) or not result.get('id'):raise ValueError('Mail service did not accept the alert')
 else:
  message=EmailMessage();message['From']=sender;message['To']=recipient;message['Subject']=subject;message['Message-ID']='<orbit-'+event_id+'@'+address.split('@')[-1]+'>';message.set_content(text)
  host=os.environ.get('SMTP_HOST');port=int(os.environ.get('SMTP_PORT','587'))
  if port not in (465,587):raise ValueError('Use TLS SMTP port 465 or 587')
  client=smtplib.SMTP_SSL(host,port,timeout=8,context=ssl.create_default_context()) if port==465 else smtplib.SMTP(host,port,timeout=8)
  with client:
   if port==587:client.starttls(context=ssl.create_default_context())
   client.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD']);refused=client.send_message(message)
   if refused:raise ValueError('Mail service did not accept the recipient')

def deliver(c,uid):
 settings=state(c,uid);now=int(time.time())
 if not settings['enabled'] or not settings['configured'] or not settings['recipient']:return settings
 if os.environ.get('RESEND_API_KEY'):c.execute("UPDATE alert_email_outbox SET status='pending' WHERE user_id=? AND status='sending' AND last_attempt<?",(uid,now-120))
 c.execute("UPDATE alert_email_outbox SET status='expired' WHERE user_id=? AND status='pending' AND created_at<?",(uid,now-3600));c.commit()
 rows=list(c.execute("SELECT * FROM alert_email_outbox WHERE user_id=? AND status='pending' AND attempts<3 AND last_attempt<? ORDER BY created_at LIMIT 3",(uid,now-60)))
 for row in rows:
  claimed=c.execute("UPDATE alert_email_outbox SET status='sending',attempts=attempts+1,last_attempt=? WHERE user_id=? AND id=? AND status='pending'",(now,uid,row['id']));c.commit()
  if not claimed.rowcount:continue
  try:send(settings['recipient'],json.loads(row['data']),row['id']);status='accepted'
  except Exception:status='pending' if os.environ.get('RESEND_API_KEY') and row['attempts']<2 else 'failed'
  c.execute('UPDATE alert_email_outbox SET status=? WHERE user_id=? AND id=?',(status,uid,row['id']));c.commit()
 return state(c,uid)
