import json, sqlite3, unittest
from unittest.mock import patch
import feature_named_watchlists as f

class WatchlistTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
  self.c.execute('CREATE TABLE coin_market_cache(key TEXT,data TEXT)');f.init(self.c)
  self.coins=[{'id':'coin-'+str(i),'name':'Coin '+str(i)} for i in range(101)]+[{'id':'bitcoin','name':'Bitcoin','current_price':'1'},{'id':'bitcoin-cash','name':'Bitcoin Cash'}]
  self.c.execute('INSERT INTO coin_market_cache VALUES (?,?)',(json.dumps(('list','periods-v3-500')),json.dumps({'coins':self.coins})))
  self.id=f.action(self.c,1,{'operation':'create','name':'Private'})['id']
 def act(self,op,**kw):return f.action(self.c,1,dict(operation=op,id=self.id,**kw))
 def test_exact_ids_private_notes_and_persistence(self):
  with patch.object(f.market,'listings',side_effect=AssertionError('No network in action')):
   self.act('add',coin_id='bitcoin');self.act('add',coin_id='bitcoin-cash');self.act('note',coin_id='bitcoin',note='<script>"private"</script>')
   with self.assertRaises(ValueError):self.act('add',coin_id='btc')
   with self.assertRaises(ValueError):self.act('add',coin_id='BITCOIN')
  self.c.commit()
  with patch.object(f.market,'listings',side_effect=ValueError('offline')):
   data=f.read(self.c,1,{})
   self.assertEqual(data['lists'][0]['coins'][0]['note'],'<script>"private"</script>')
   self.assertEqual([r['id'] for r in data['lists'][0]['coins']],['bitcoin','bitcoin-cash'])
   self.assertEqual(f.read(self.c,2,{})['lists'],[])
   self.assertTrue(data['stale'])
  for op in ('rename','delete','add','remove','note','columns'):
   with self.assertRaises(ValueError):f.action(self.c,2,{'operation':op,'id':self.id,'name':'stolen','coin_id':'bitcoin','note':'stolen','confirm':True,'columns':[]})
 def test_limits_and_delete_confirmation(self):
  for i in range(100):self.act('add',coin_id='coin-'+str(i))
  self.act('add',coin_id='coin-0')
  with self.assertRaises(ValueError):self.act('add',coin_id='coin-100')
  self.act('note',coin_id='coin-0',note='x'*2000)
  with self.assertRaises(ValueError):self.act('note',coin_id='coin-0',note='x'*2001)
  with self.assertRaises(ValueError):self.act('remove',coin_id='coin-0')
  self.act('remove',coin_id='coin-0',confirm=True)
  with self.assertRaises(ValueError):self.act('delete')
  with self.assertRaises(ValueError):self.act('columns',columns=['guessed'])
  self.act('columns',columns=[]);self.act('rename',name='Renamed')
  for i in range(19):f.action(self.c,1,{'operation':'create','name':str(i)})
  with self.assertRaises(ValueError):f.action(self.c,1,{'operation':'create','name':'over'})
  self.act('delete',confirm=True)
  self.assertEqual(self.c.execute('SELECT COUNT(*) FROM named_watchlist_entries').fetchone()[0],0)
 def test_unavailable_quotes_are_not_guessed(self):
  self.act('add',coin_id='bitcoin')
  with patch.object(f.market,'listings',return_value={'coins':[],'stale':False}):
   self.assertIsNone(f.read(self.c,1,{})['lists'][0]['coins'][0]['market'])
if __name__=='__main__':unittest.main()
