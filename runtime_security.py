"""Bounded local HTTP serving and per-account outbound-operation budgets."""
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
import threading
import time

class BoundedHTTPServer(ThreadingHTTPServer):
 daemon_threads=True
 allow_reuse_address=True
 request_queue_size=32
 def __init__(self,server_address,RequestHandlerClass,bind_and_activate=True,*,max_workers=24,socket_timeout=15):
  if max_workers<1 or socket_timeout<=0:raise ValueError('Invalid server limits')
  self._slots=threading.BoundedSemaphore(max_workers)
  self.socket_timeout=socket_timeout
  super().__init__(server_address,RequestHandlerClass,bind_and_activate)
 def get_request(self):
  request,address=super().get_request()
  request.settimeout(self.socket_timeout)
  return request,address
 def process_request(self,request,client_address):
  if not self._slots.acquire(blocking=False):
   try:
    request.settimeout(0.1)
    request.sendall(b'HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\nRetry-After: 5\r\nContent-Length: 0\r\nCache-Control: no-store\r\n\r\n')
   except OSError:pass
   finally:self.shutdown_request(request)
   return
  try:super().process_request(request,client_address)
  except BaseException:
   self._slots.release()
   raise
 def process_request_thread(self,request,client_address):
  try:super().process_request_thread(request,client_address)
  finally:self._slots.release()

class BudgetExceeded(ValueError):
 pass

class ProviderBudget:
 """One outbound action per user; bounded actions per window and global concurrency.

 Acquire before opening write transactions. The budget is process-local and does
 not replace durable production quotas. Failed actions count to prevent retry storms.
 """
 def __init__(self,*,limit=12,window=60,max_concurrent=6,per_user_concurrent=1,max_users=10000,clock=time.monotonic):
  if min(limit,window,max_concurrent,per_user_concurrent,max_users)<=0:raise ValueError('Invalid budget limits')
  self.limit=limit;self.window=window;self.max_users=max_users;self.clock=clock
  self.per_user_concurrent=per_user_concurrent
  self._lock=threading.Lock();self._users={};self._active={}
  self._slots=threading.BoundedSemaphore(max_concurrent)
 @contextmanager
 def action(self,user_id):
  now=self.clock()
  with self._lock:
   for key,(start,count) in list(self._users.items()):
    if now-start>=self.window and key not in self._active:del self._users[key]
   if self._active.get(user_id,0)>=self.per_user_concurrent:raise BudgetExceeded('A provider operation is already running for this account')
   start,count=self._users.get(user_id,(now,0))
   if count>=self.limit:raise BudgetExceeded('Provider request budget reached. Retry shortly.')
   if user_id not in self._users and len(self._users)>=self.max_users:raise BudgetExceeded('Provider capacity reached. Retry shortly.')
   if not self._slots.acquire(blocking=False):raise BudgetExceeded('Providers are busy. Retry shortly.')
   self._users[user_id]=(start,count+1);self._active[user_id]=self._active.get(user_id,0)+1
  try:yield
  finally:
   with self._lock:
    self._active[user_id]-=1
    if not self._active[user_id]:del self._active[user_id]
   self._slots.release()
