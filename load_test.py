"""Loopback-only burst benchmark. Never reads production DB or calls providers.
Run: python load_test.py --output performance-local.json
"""
import argparse,asyncio,collections,hashlib,json,math,multiprocessing,os,platform,secrets,tempfile,threading,time
from pathlib import Path


def serve(pipe):
 os.environ.pop('DATABASE_URL',None)
 os.environ.pop('VERCEL',None)
 import server
 from runtime_security import BoundedHTTPServer
 with tempfile.TemporaryDirectory(prefix='orbit-load-') as directory:
  server.DB=Path(directory)/'load.sqlite3';server.init()
  tokens=[]
  with server.connect() as c:
   for i in range(100):
    uid=i+1;token=secrets.token_urlsafe(32);tokens.append(token)
    c.execute('INSERT INTO users(id,email,password) VALUES (?,?,?)',(uid,f'load-{uid}@example.test','non-login-test-fixture'))
    c.execute('INSERT INTO sessions VALUES (?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),uid,time.time()+3600))
    for n in range(20):c.execute('INSERT INTO trades(user_id,date,symbol,side,quantity,price,fee,account) VALUES (?,?,?,?,?,?,?,?)',(uid,f'2026-01-{n+1:02}T12:00:00','BTC','buy','0.01','50000','1','Load fixture'))
    c.execute('INSERT INTO prices VALUES (?,?,?)',(uid,'BTC','60000'))
   c.commit()
  app=BoundedHTTPServer(('127.0.0.1',0),server.Handler)
  app.handle_error=lambda *args:None
  worker=threading.Thread(target=app.serve_forever,daemon=True);worker.start()
  pipe.send((app.server_port,tokens))
  pipe.recv();app.shutdown();app.server_close();worker.join()


def percentile(values,p):
 values=sorted(values)
 return round(values[max(0,math.ceil(len(values)*p)-1)]*1000,1) if values else None


async def burst(port,tokens,path,n,timeout):
 gate=asyncio.Event()
 async def one(i):
  await gate.wait();start=time.perf_counter();writer=None
  try:
   async with asyncio.timeout(timeout):
    reader,writer=await asyncio.open_connection('127.0.0.1',port)
    writer.write((f'GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nCookie: session={tokens[i%len(tokens)]}\r\nConnection: close\r\n\r\n').encode());await writer.drain()
    response=await reader.read();status=int(response.split(b' ',2)[1])
    if status==200:
     body=response.split(b'\r\n\r\n',1)[1]
     if path=='/api/state':
      payload=json.loads(body)
      if payload.get('email')!=f'load-{i%len(tokens)+1}@example.test' or len(payload.get('trades',[]))!=20:raise ValueError('Invalid or cross-account response')
     elif b'<html' not in body:raise ValueError('Invalid static response')
    return str(status),time.perf_counter()-start
  except Exception as e:return type(e).__name__,time.perf_counter()-start
  finally:
   if writer:
    writer.close()
    try:await writer.wait_closed()
    except Exception:pass
 tasks=[asyncio.create_task(one(i)) for i in range(n)]
 start=time.perf_counter();gate.set();rows=await asyncio.gather(*tasks);elapsed=time.perf_counter()-start
 good=[duration for status,duration in rows if status=='200'];all_times=[duration for _,duration in rows]
 result={'path':path,'burst_requests':n,'elapsed_seconds':round(elapsed,3),'statuses':dict(collections.Counter(status for status,_ in rows)),'success_percent':round(100*len(good)/n,2),'successful_requests_per_second':round(len(good)/elapsed,2),'all_attempt_latency_ms':{label:percentile(all_times,p) for label,p in [('p50',.5),('p95',.95),('p99',.99)]},'success_latency_ms':{label:percentile(good,p) for label,p in [('p50',.5),('p95',.95),('p99',.99)]}}
 print(json.dumps(result),flush=True);return result


async def run(port,tokens,timeout):
 results=[]
 for n in (20,100,1000):
  for path in ('/app.html','/api/state'):
   results.append(await burst(port,tokens,path,n,timeout))
 recovery=[]
 for _ in range(5):recovery.append(await burst(port,tokens,'/api/state',1,timeout))
 return results,recovery


def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='performance-local.json');parser.add_argument('--timeout',type=float,default=10);args=parser.parse_args()
 if not 1<=args.timeout<=30:parser.error('Timeout must be 1–30 seconds')
 ctx=multiprocessing.get_context('spawn');parent,child=ctx.Pipe();process=ctx.Process(target=serve,args=(child,));process.start()
 try:
  if not parent.poll(30):raise RuntimeError('Fixture startup timed out')
  port,tokens=parent.recv();results,recovery=asyncio.run(run(port,tokens,args.timeout))
  report={'scope':'Local loopback burst only; not Vercel/Neon capacity or a sustained users test','date_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'python':platform.python_version(),'platform':platform.platform(),'cpu_count':os.cpu_count(),'fixture':{'accounts':100,'trades_per_account':20,'wallets':0,'external_provider_calls':0,'database':'temporary SQLite','server_workers':24,'server_backlog':32,'timeout_seconds':args.timeout},'method':'Async clients released together; arrival scheduling is OS-dependent. Separate server process, same machine. One request per client, no retries. Latency includes connect, queue and complete response. HTTP 200 state responses checked for account identity and 20 trades. Static assets use local HTTP server, not production CDN.','results':results,'recovery':recovery}
  Path(args.output).write_text(json.dumps(report,indent=2),encoding='utf-8');print('Report:',str(Path(args.output).resolve()),flush=True)
 finally:
  try:parent.send('stop')
  except (BrokenPipeError,EOFError):pass
  process.join(10)
  if process.is_alive():process.terminate();process.join()
if __name__=='__main__':main()
