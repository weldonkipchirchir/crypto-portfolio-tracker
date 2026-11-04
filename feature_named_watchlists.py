"""Private named watchlists. Mutations use only the locally saved market catalog."""
import json
import uuid
import coin_market as market

COLUMNS = ('current_price','price_change_percentage_24h','price_change_percentage_7d','price_change_percentage_30d','market_cap_rank','total_volume')

def init(c):
    c.execute('CREATE TABLE IF NOT EXISTS named_watchlists(user_id INTEGER NOT NULL,id TEXT NOT NULL,name TEXT NOT NULL,columns TEXT NOT NULL,PRIMARY KEY(user_id,id))')
    c.execute('CREATE TABLE IF NOT EXISTS named_watchlist_entries(user_id INTEGER NOT NULL,list_id TEXT NOT NULL,coin_id TEXT NOT NULL,note TEXT NOT NULL,PRIMARY KEY(user_id,list_id,coin_id))')

def catalog(c):
    rows = {}
    with market.LOCK:
        saved = market.CACHE.get(('list','periods-v3-500'))
        if saved:
            rows.update({r['id']:r for r in saved[1].get('coins',[])})
    # The shared cache table is initialized by the server for both database engines.
    row = c.execute('SELECT data FROM coin_market_cache WHERE key=?',(json.dumps(('list','periods-v3-500')),)).fetchone()
    if row:
        try: rows.update({r['id']:r for r in json.loads(row['data']).get('coins',[])})
        except (ValueError,TypeError,KeyError): pass
    return rows

def action(c,uid,raw):
    op=raw.get('operation'); identity=raw.get('id')
    if op=='create':
        if c.execute('SELECT COUNT(*) AS n FROM named_watchlists WHERE user_id=?',(uid,)).fetchone()['n']>=20: raise ValueError('Use up to 20 watchlists')
    else:
        if not isinstance(identity,str) or not c.execute('SELECT id FROM named_watchlists WHERE user_id=? AND id=?',(uid,identity)).fetchone(): raise ValueError('Watchlist not found')
    if op in ('create','rename'):
        name=raw.get('name')
        if not isinstance(name,str) or not 1<=len(name.strip())<=80 or any(ord(x)<32 for x in name): raise ValueError('Use a name of 1 to 80 characters')
        if op=='create':
            identity=uuid.uuid4().hex
            c.execute('INSERT INTO named_watchlists VALUES (?,?,?,?)',(uid,identity,name.strip(),json.dumps(COLUMNS)))
        else: c.execute('UPDATE named_watchlists SET name=? WHERE user_id=? AND id=?',(name.strip(),uid,identity))
    elif op=='delete':
        if raw.get('confirm') is not True: raise ValueError('Confirm deletion of this list and its private notes')
        c.execute('DELETE FROM named_watchlist_entries WHERE user_id=? AND list_id=?',(uid,identity))
        c.execute('DELETE FROM named_watchlists WHERE user_id=? AND id=?',(uid,identity))
    elif op=='columns':
        columns=raw.get('columns')
        if not isinstance(columns,list) or len(columns)>len(COLUMNS) or any(x not in COLUMNS for x in columns): raise ValueError('Invalid columns')
        c.execute('UPDATE named_watchlists SET columns=? WHERE user_id=? AND id=?',(json.dumps(list(dict.fromkeys(columns))),uid,identity))
    elif op in ('add','remove','note'):
        coin=market.identifier(raw.get('coin_id'))
        existing=c.execute('SELECT coin_id FROM named_watchlist_entries WHERE user_id=? AND list_id=? AND coin_id=?',(uid,identity,coin)).fetchone()
        if op=='add':
            if coin not in catalog(c): raise ValueError('Choose an exact CoinGecko ID from the loaded market catalog')
            if not existing:
                if c.execute('SELECT COUNT(*) AS n FROM named_watchlist_entries WHERE user_id=? AND list_id=?',(uid,identity)).fetchone()['n']>=100: raise ValueError('Use up to 100 coins per list')
                c.execute('INSERT INTO named_watchlist_entries VALUES (?,?,?,?)',(uid,identity,coin,''))
        elif op=='remove':
            if raw.get('confirm') is not True: raise ValueError('Confirm removal of this coin and its private note')
            c.execute('DELETE FROM named_watchlist_entries WHERE user_id=? AND list_id=? AND coin_id=?',(uid,identity,coin))
        else:
            if not existing: raise ValueError('Coin not found in this watchlist')
            note=raw.get('note')
            if not isinstance(note,str) or len(note)>2000 or '\x00' in note: raise ValueError('Use a plain text note of up to 2000 characters')
            c.execute('UPDATE named_watchlist_entries SET note=? WHERE user_id=? AND list_id=? AND coin_id=?',(note,uid,identity,coin))
    else: raise ValueError('Unknown watchlist operation')
    return {'ok':True,'id':identity}

def read(c,uid,raw):
    try: feed=market.listings()
    except ValueError: feed={'coins':list(catalog(c).values()),'stale':True}
    quotes={row['id']:row for row in feed['coins']}
    lists=[]
    for row in c.execute('SELECT id,name,columns FROM named_watchlists WHERE user_id=? ORDER BY name,id',(uid,)):
        item=dict(row);item['columns']=json.loads(item['columns']);item['coins']=[]
        for entry in c.execute('SELECT coin_id,note FROM named_watchlist_entries WHERE user_id=? AND list_id=? ORDER BY coin_id',(uid,item['id'])):
            item['coins'].append({'id':entry['coin_id'],'note':entry['note'],'market':quotes.get(entry['coin_id'])})
        lists.append(item)
    return {'lists':lists,'catalog':[{'id':r['id'],'name':r.get('name',r['id'])} for r in feed['coins']],'stale':feed.get('stale',False),'fetched_at':feed.get('fetched_at'),'coverage':'Private account watchlists. CoinGecko top 500 catalog; USD snapshot prices may be stale. Missing market values are unavailable. Notes are private plain text.'}
