"""Run temporary-database tests with explicit test-only environment and loopback networking."""
import os,socket,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
# Tests must never inherit hosted database or exchange encryption credentials.
allowed={k:os.environ[k] for k in ('SystemRoot','PATH','COMSPEC','ORBIT_TEST_DATABASE_URL') if k in os.environ}
if allowed.get('ORBIT_TEST_DATABASE_URL'):
 from urllib.parse import urlsplit
 if urlsplit(allowed['ORBIT_TEST_DATABASE_URL']).hostname not in ('127.0.0.1','localhost','::1'):raise SystemExit('Test PostgreSQL must be on loopback')
os.environ.clear();os.environ.update(allowed)
original_connect=socket.socket.connect;original_connect_ex=socket.socket.connect_ex;original_dns=socket.getaddrinfo
loopback=lambda address:isinstance(address,tuple) and address[0] in ('127.0.0.1','::1','localhost')
def connect(sock,address):
 if not loopback(address):raise OSError('Tests allow loopback networking only')
 return original_connect(sock,address)
def connect_ex(sock,address):
 if not loopback(address):raise OSError('Tests allow loopback networking only')
 return original_connect_ex(sock,address)
def dns(host,*args,**kwargs):
 if host not in ('127.0.0.1','::1','localhost',None):raise OSError('Tests prohibit external DNS')
 return original_dns(host,*args,**kwargs)
socket.socket.connect=connect;socket.socket.connect_ex=connect_ex;socket.getaddrinfo=dns;socket.setdefaulttimeout(30)
with tempfile.TemporaryDirectory(prefix='orbit-tests-') as scratch:
 os.environ.update(TEMP=scratch,TMP=scratch)
 if len(sys.argv)>1:suite=unittest.defaultTestLoader.loadTestsFromNames(['tests.backend.'+name.removeprefix('tests.backend.') for name in sys.argv[1:]])
 else:suite=unittest.defaultTestLoader.discover(str(ROOT/'tests/backend'),pattern='*test*.py',top_level_dir=str(ROOT))
 result=unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
