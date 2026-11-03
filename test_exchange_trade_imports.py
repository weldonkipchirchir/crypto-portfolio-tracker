import csv,io,sqlite3,unittest
from decimal import Decimal
from unittest.mock import patch
import exchange_trade_imports as m
import exchange_connections as ex
import imports,server

def fill(**kw):return dict(symbol='BTCUSDT',id=1,time=1700000000000,isBuyer=True,qty='2',price='10',commission='0.1',commissionAsset='USDT',**kw)
class ImportTests(unittest.TestCase):
 def test_values_and_dedup_preview(self):
  csvtext=m.normalize([fill()], 'BTCUSDT',Decimal('.99'),'Binance API test')
  row=list(csv.DictReader(io.StringIO(csvtext)))[0]
  self.assertEqual(row['price'],'9.90');self.assertEqual(row['fee'],'0.099');self.assertEqual(row['date'],'2023-11-14T22:13:20+00:00')
  first=imports.preview(csvtext,[],server.trade,server.calculate)
  self.assertEqual(first['count'],1)
  self.assertEqual(imports.preview(csvtext,first['trades'],server.trade,server.calculate)['duplicates'],1)
 def test_bad_fill_and_unvalued_fees(self):
  for key,value in [('qty','NaN'),('price','0'),('commission','-1'),('isBuyer',1),('symbol','ETHUSDT'),('time',True),('commissionAsset','BNB')]:
   row=fill();row[key]=value
   with self.assertRaises(ValueError):m.normalize([row],'BTCUSDT',Decimal(1),'a')
  with self.assertRaises(ValueError):m.normalize([fill(),fill()],'BTCUSDT',Decimal(1),'a')
  other=fill();other['id']=2
  with self.assertRaises(ValueError):m.normalize([fill(),other],'BTCUSDT',Decimal(1),'a')
 def test_owner_scoped_and_no_writes(self):
  c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;ex.init(c)
  identity='a'*32;c.execute('INSERT INTO exchange_connections VALUES (?,?,?,?,?)',(1,identity,'label','encrypted','{}'));c.commit()
  with patch.object(ex,'crypt',return_value={'api_key':'key','api_secret':'secret'}),patch.object(ex,'signed',return_value=[fill()]) as signed:
   result=m.preview(c,1,{'id':identity,'pair':'btcusdt','usdt_usd_rate':'1'})
   self.assertEqual(result['count'],1);self.assertFalse(c.in_transaction);self.assertNotIn('secret',str(result));self.assertEqual(signed.call_args.kwargs['symbol'],'BTCUSDT')
   with self.assertRaises(ValueError):m.preview(c,2,{'id':identity,'pair':'BTCUSDT','usdt_usd_rate':'1'})
  for pair in ['BTCBTC','../../secret','BTCUSDT&x=1']:
   with self.assertRaises(ValueError):m.preview(c,1,{'id':identity,'pair':pair,'usdt_usd_rate':'1'})
if __name__=='__main__':unittest.main()
