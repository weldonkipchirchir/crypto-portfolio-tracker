"""Build only explicitly public files for Vercel CDN delivery."""
from pathlib import Path
from static_assets import STATIC_FILES
ROOT=Path(__file__).parent

def build(destination=None):
 destination=Path(destination) if destination else ROOT/'public'
 destination.mkdir(parents=True,exist_ok=True)
 for filename,kind in STATIC_FILES.values():
  body=(ROOT/filename).read_bytes()
  if kind.startswith('text/html') and filename!='app.html':
   # The public stylesheet is tiny: inline it to remove the blocking CSS round trip.
   css=(ROOT/'public_site.css').read_bytes()
   body=body.replace(b'<link rel="stylesheet" href="/public_site.css">',b'<style>'+css+b'</style>')
  if filename=='app.html':
   for old,new in ((b'Local development edition',b'Personal cloud edition'),(b'Local workspace',b'Cloud workspace'),(b'Private local accounts',b'Private cloud accounts'),(b'Development edition',b'Personal preview')):body=body.replace(old,new)
  (destination/filename).parent.mkdir(parents=True,exist_ok=True)
  (destination/filename).write_bytes(body)
if __name__=='__main__':build()
