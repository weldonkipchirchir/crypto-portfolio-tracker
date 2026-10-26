"""Atomic, idempotent public-address registration across explicitly selected networks."""
import providers

def add(c,uid,raw):
 chains=raw.get('chains')
 if not isinstance(chains,list) or not 1<=len(chains)<=len(providers.CHAINS):raise ValueError('Select at least one supported network')
 if not all(isinstance(x,str) for x in chains):raise ValueError('Invalid network selection')
 if len(set(str(x) for x in chains))!=len(chains):raise ValueError('Duplicate network selection')
 label=raw.get('label','Wallet')
 if not isinstance(label,str) or not label.strip() or len(label)>100:raise ValueError('Enter a wallet label under 100 characters')
 validated=[(chain,providers.validate_address(chain,raw.get('address',''))) for chain in chains]
 # All selected addresses must validate before any insert occurs.
 existing={(r['chain'],r['address']) for r in c.execute('SELECT chain,address FROM wallets WHERE user_id=?',(uid,))}
 new=[pair for pair in validated if pair not in existing]
 if len(existing)+len(new)>50:raise ValueError('Maximum 50 connected addresses per account')
 added=[];skipped=[]
 for chain,address in validated:
  if (chain,address) in existing:skipped.append(chain);continue
  c.execute('INSERT INTO wallets(user_id,chain,address,label) VALUES (?,?,?,?) ON CONFLICT (user_id,chain,address) DO NOTHING',(uid,chain,address,label.strip()))
  added.append(chain)
 return {'ok':True,'added':added,'skipped':skipped}
