import tempfile,unittest,threading,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from api.index import handler
from static_assets import STATIC_FILES
from build_static import build

class HostedAssetsTests(unittest.TestCase):
 def test_static_assets_survive_database_failure(self):
  server=ThreadingHTTPServer(('127.0.0.1',0),handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with patch('api.index.initialize',side_effect=RuntimeError('database down')) as initialize:
    for name in ('chart_panels.js','chart_tools.js','indicator_library.js'):
     with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/'+name) as response:
      self.assertEqual(response.status,200);self.assertIn('javascript',response.headers['Content-Type']);self.assertTrue(response.read())
    initialize.assert_not_called()
    with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/state')
    self.assertEqual(error.exception.code,503)
    with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/.env')
    self.assertEqual(error.exception.code,404)
  finally:server.shutdown();server.server_close();thread.join()
 def test_persistent_cache_hydrates_worker(self):
  import coin_market,time
  key=('detail','hosted-cache-regression')
  saved={'fetched_at':int(time.time()),'value':42}
  try:
   with patch('coin_market.STORE') as store:
    from unittest.mock import Mock
    read=Mock(return_value=saved);store.callbacks=(read,Mock())
    for _ in range(2):self.assertEqual(coin_market.cached(key,60,lambda:self.fail('unexpected upstream request'))['value'],42)
    self.assertEqual(read.call_count,1)
  finally:coin_market.CACHE.pop(key,None)
 def test_build_publishes_only_allowlisted_files(self):
  with tempfile.TemporaryDirectory() as directory:
   build(directory)
   self.assertEqual({p.relative_to(directory).as_posix() for p in Path(directory).rglob('*') if p.is_file()},{filename for filename,kind in STATIC_FILES.values()})
   self.assertIn('Personal cloud edition',Path(directory,'index.html').read_text(encoding='utf-8'))
if __name__=='__main__':unittest.main()
