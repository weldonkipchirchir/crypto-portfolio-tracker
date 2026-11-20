import importlib,unittest
from pathlib import Path
from backend import server
from backend.core.paths import PROJECT_ROOT,source_paths,source_path
from backend.web.static_assets import STATIC_FILES
from api.index import handler

class ProjectStructureTests(unittest.TestCase):
 def test_entry_points_use_the_same_application_module(self):
  self.assertTrue(issubclass(handler,server.Handler))
  self.assertIs(importlib.import_module('server').main,server.main)
  self.assertEqual(server.ROOT,PROJECT_ROOT)
 def test_static_boundary_remains_frontend_only(self):
  for url,(filename,kind) in STATIC_FILES.items():
   path=(PROJECT_ROOT/filename).resolve()
   self.assertTrue(path.is_relative_to(PROJECT_ROOT/'frontend'),url)
   self.assertTrue(path.is_file(),url)
  for private in ('/server.py','/backend/server.py','/config/source_paths.json','/.env','/tests/backend/test_security.py'):
   self.assertNotIn(private,STATIC_FILES)
 def test_source_map_has_no_missing_or_external_targets(self):
  for logical in source_paths():
   path=source_path(logical).resolve()
   self.assertTrue(path.is_relative_to(PROJECT_ROOT),logical)
   self.assertTrue(path.is_file(),logical)
 def test_stable_asset_urls_resolve_to_organized_sources(self):
  self.assertEqual(STATIC_FILES['/app.js'][0],'frontend/scripts/app/app.js')
  self.assertEqual(STATIC_FILES['/app.html'][0],'frontend/pages/app.html')
  self.assertEqual(STATIC_FILES['/guides/wallet-tracking.html'][0],'frontend/pages/guides/wallet-tracking.html')
  self.assertEqual(STATIC_FILES['/coin-logos/btc.png'][0],'frontend/assets/coin-logos/btc.png')
