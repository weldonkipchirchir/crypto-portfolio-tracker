"""Vercel entry point. No ephemeral SQLite fallback in hosted mode."""
import os,threading
from server import Handler,init
import cloud_storage
_ready=False
_lock=threading.Lock()
def initialize():
 global _ready
 with _lock:
  if _ready:return
  if not os.environ.get('DATABASE_URL'):raise RuntimeError('DATABASE_URL is required')
  if os.environ.get('ORBIT_SECURE_COOKIE')!='1':raise RuntimeError('HTTPS session cookies must be enabled')
  if not os.environ.get('ORBIT_REGISTRATION_EMAIL'):raise RuntimeError('Set the owner registration email')
  init();cloud_storage.initialize_limits();_ready=True
class handler(Handler):
 def dispatch(self,method):
  try:initialize()
  except Exception:self.send(503,{'error':'Hosted storage is not configured or unavailable'});return
  try:getattr(super(),method)()
  except Exception:self.send(503,{'error':'Service temporarily unavailable'})
 def do_GET(self):self.dispatch('do_GET')
 def do_POST(self):self.dispatch('do_POST')
