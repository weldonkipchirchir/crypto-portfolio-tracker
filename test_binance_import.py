import unittest
import imports,server
HEADER='Time,OrderNo,Pair,Type¹,Side,Order Price,Order Amount,Time,Executed²,Average Price,Trading total³,Status'
ROW='2024-01-02 12:00:00,123,NEARUSDT,Limit,BUY,999,9NEAR,2024-01-02 13:45:00,2NEAR,10,20USDT,FILLED'
OPTIONS={'utc_offset_minutes':180,'usdt_usd_rate':'1'}
class BinanceImportTests(unittest.TestCase):
 def preview(self,text,existing=None,options=None):return imports.preview(text,existing or [],server.trade,server.calculate,OPTIONS if options is None else options)
 def test_execution_time_amount_average_and_utc(self):
  result=self.preview(HEADER+'\n'+ROW);self.assertEqual(result['errors'],[]);row=result['trades'][0]
  self.assertEqual(row['date'],'2024-01-02T10:45:00');self.assertEqual(row['quantity'],'2');self.assertEqual(row['price'],'10');self.assertEqual(row['symbol'],'NEAR');self.assertEqual(row['fee'],'0');self.assertTrue(result['requires_acknowledgement']);self.assertEqual(result['source'],'Binance Spot Order History')
 def test_conversion_and_overlap(self):
  result=self.preview(HEADER+'\n'+ROW,options={**OPTIONS,'usdt_usd_rate':'.99'});self.assertEqual(result['trades'][0]['price'],'9.90')
  again=self.preview(HEADER+'\n'+ROW,existing=result['trades'],options={**OPTIONS,'usdt_usd_rate':'.99'});self.assertEqual(again['duplicates'],1);self.assertEqual(again['count'],0)
 def test_skip_open_cancelled_and_reject_unsupported_quote(self):
  result=self.preview(HEADER+'\n'+ROW.replace('FILLED','CANCELED')+'\n'+ROW.replace('FILLED','NEW'));self.assertEqual(result['skipped'],2);self.assertEqual(result['count'],0)
  result=self.preview(HEADER+'\n'+ROW.replace('NEARUSDT','NEARBTC'));self.assertTrue(result['errors'])
 def test_bad_options_and_amounts(self):
  for options in [{},{'utc_offset_minutes':True},{**OPTIONS,'usdt_usd_rate':'NaN'},{**OPTIONS,'usdt_usd_rate':'3'}]:
   with self.assertRaises(ValueError):self.preview(HEADER+'\n'+ROW,options=options)
  for old,new in [('2NEAR','2ETH'),('10','0'),('10','1e999999')]:self.assertTrue(self.preview(HEADER+'\n'+ROW.replace(old,new))['errors'])
 def test_orbit_still_supported_and_duplicate_headers_rejected(self):
  result=self.preview('date,symbol,side,quantity,price\n2026-01-01,ETH,buy,1,100');self.assertFalse(result['requires_acknowledgement']);self.assertEqual(result['count'],1)
  with self.assertRaises(ValueError):self.preview('date,symbol,side,quantity,price,price\n2026-01-01,ETH,buy,1,100,200')
