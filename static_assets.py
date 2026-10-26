"""Explicit public asset allowlist; never publish the repository directory."""
STATIC_FILES={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/portfolio_insights.js':('portfolio_insights.js','text/javascript; charset=utf-8'),'/styles.css':('styles.css','text/css; charset=utf-8'),'/advanced_dashboard.js':('advanced_dashboard.js','text/javascript; charset=utf-8'),'/advanced_dashboard.css':('advanced_dashboard.css','text/css; charset=utf-8'),'/target_dashboard.js':('target_dashboard.js','text/javascript; charset=utf-8'),'/target_dashboard.css':('target_dashboard.css','text/css; charset=utf-8'),'/market_dashboard.js':('market_dashboard.js','text/javascript; charset=utf-8'),'/market_dashboard.css':('market_dashboard.css','text/css; charset=utf-8'),'/market_intelligence.js':('market_intelligence.js','text/javascript; charset=utf-8'),'/trade_chart_markers.js':('trade_chart_markers.js','text/javascript; charset=utf-8'),'/market_intelligence.css':('market_intelligence.css','text/css; charset=utf-8')}
for filename in ('indicator_library.js','studio_storage.js','chart_panels.js','pine_bridge.js','pine_editor.js','coin_alerts.js','experience_ui.js','chart_tools.js','experience_ui.css','chart_tools.css'):
 STATIC_FILES['/'+filename]=(filename,('text/javascript' if filename.endswith('.js') else 'text/css')+'; charset=utf-8')

# Crawlable public content, separate from the authenticated workspace.
for filename in ('crypto-portfolio-tracker.html', 'guides/crypto-profit-loss.html', 'guides/wallet-tracking.html', 'about-orbit.html'):
 STATIC_FILES["/"+filename]=(filename,"text/html; charset=utf-8")
STATIC_FILES.update({"/public_site.css":("public_site.css","text/css; charset=utf-8"),"/robots.txt":("robots.txt","text/plain; charset=utf-8"),"/sitemap.xml":("sitemap.xml","application/xml; charset=utf-8")})

STATIC_FILES.update({"/app.html":("app.html","text/html; charset=utf-8"),"/favicon.svg":("favicon.svg","image/svg+xml"),"/orbit-preview.png":("orbit-preview.png","image/png")})

STATIC_FILES["/favicon.ico"]=("favicon.ico","image/x-icon")
for filename in ("favicon-32.png","favicon-48.png","favicon-96.png","apple-touch-icon.png","favicon-192.png","favicon-512.png"):
 STATIC_FILES["/"+filename]=(filename,"image/png")

STATIC_FILES.update({"/guides/import-crypto-trades-csv.html":("guides/import-crypto-trades-csv.html","text/html; charset=utf-8"),"/examples/orbit-trades.csv":("examples/orbit-trades.csv","text/csv; charset=utf-8")})
