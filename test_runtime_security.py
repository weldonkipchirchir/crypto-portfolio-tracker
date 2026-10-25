import socket,threading,unittest
from http.server import BaseHTTPRequestHandler
from runtime_security import BoundedHTTPServer,ProviderBudget,BudgetExceeded

class BudgetTests(unittest.TestCase):
 def test_overlap_limits_and_release_on_failure(self):
  budget=ProviderBudget(limit=2,max_concurrent=1)
  with budget.action(1):
   with self.assertRaises(BudgetExceeded):
    with budget.action(1):pass
   with self.assertRaises(BudgetExceeded):
    with budget.action(2):pass
  with self.assertRaises(RuntimeError):
   with budget.action(1):raise RuntimeError('provider failed')
  with self.assertRaises(BudgetExceeded):
   with budget.action(1):pass
  with budget.action(2):pass
 def test_budget_expires_and_memory_is_bounded(self):
  now=[0];budget=ProviderBudget(limit=1,window=10,max_users=1,clock=lambda:now[0])
  with budget.action(1):pass
  with self.assertRaises(BudgetExceeded):
   with budget.action(2):pass
  now[0]=11
  with budget.action(2):pass
  self.assertEqual(len(budget._users),1)
 def test_different_users_can_run(self):
  budget=ProviderBudget(max_concurrent=2)
  with budget.action(1):
   with budget.action(2):pass

class RuntimeTests(unittest.TestCase):
 def test_overload_and_worker_recovery(self):
  entered=threading.Event();release=threading.Event()
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_GET(self):
    entered.set();release.wait(3)
    self.send_response(200);self.send_header('Content-Length','0');self.end_headers()
  app=BoundedHTTPServer(('127.0.0.1',0),Handler,max_workers=1,socket_timeout=1)
  thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
  first=socket.create_connection(app.server_address,timeout=2)
  try:
   first.sendall(b'GET / HTTP/1.0\r\n\r\n');self.assertTrue(entered.wait(2))
   with socket.create_connection(app.server_address,timeout=2) as second:
    self.assertIn(b'503 Service Unavailable',second.recv(1024))
   release.set();self.assertIn(b'200 OK',first.recv(1024))
  finally:
   release.set();first.close();app.shutdown();app.server_close();thread.join()
  self.assertTrue(app._slots.acquire(blocking=False))
  app._slots.release()

if __name__=='__main__':unittest.main()
