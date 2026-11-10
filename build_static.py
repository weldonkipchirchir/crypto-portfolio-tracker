"""Build only explicitly public files for Vercel CDN delivery."""
from pathlib import Path
import os,hashlib,re
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
   if filename=='index.html':body=body.replace(b'<link rel="stylesheet" href="/landing.css">',b'<style>'+(ROOT/'landing.css').read_bytes()+b'</style>')
  if filename=='app.html':
   def version_asset(match):
    attr,path=match.group(1),match.group(2).decode()
    if path not in STATIC_FILES:return match.group(0)
    source=ROOT/STATIC_FILES[path][0]
    digest=hashlib.sha256(source.read_bytes()).hexdigest()[:16]
    return attr+b'="'+path.encode()+b'?v='+digest.encode()+b'"'
   # A changed asset receives a new URL even when a browser retains the previous response.
   body=re.sub(rb'(src|href)="(/[^"?]+\.(?:js|css))"',version_asset,body)
   body=body.replace(b'name="orbit-registration" content="local"',b'name="orbit-registration" content="'+(b'public' if os.environ.get('ORBIT_PUBLIC_REGISTRATION')=='1' else b'restricted')+b'"')
   for old,new in ((b'Local development edition',b'Personal cloud edition'),(b'Local workspace',b'Cloud workspace'),(b'Private local accounts',b'Private cloud accounts'),(b'Development edition',b'Personal preview')):body=body.replace(old,new)
  if kind.startswith('text/html') and os.environ.get('ORBIT_PUBLIC_REGISTRATION')=='1':
   body=body.replace(b'Hosted access is currently restricted to the deployment owner. Public guides are available to everyone.',b'Create an account to start your own private portfolio workspace. Public guides are available to everyone.')
   body=body.replace(b'Hosted registration is currently restricted to the deployment owner; this site is not offering unrestricted public account creation.',b'Public account creation is available. Each account has its own authenticated portfolio workspace.')
  (destination/filename).parent.mkdir(parents=True,exist_ok=True)
  (destination/filename).write_bytes(body)
if __name__=='__main__':build()
