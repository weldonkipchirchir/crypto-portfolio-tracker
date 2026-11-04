import unittest
import market_intelligence as m
class IntervalTests(unittest.TestCase):
 def test_closed_candles(self):
  for interval,seconds in [('1h',3600),('4h',14400)]:
   now=1800000000;end=now//seconds*seconds
   bars=[{'timestamp':(end-(20-i)*seconds)*1000,'close':str(100+i)} for i in range(20)]
   payload={'interval_code':interval,'candles':bars}
   value,stamp=m.interval_rsi(payload,interval,now);self.assertEqual(value,100);self.assertEqual(stamp,end-seconds)
   with self.assertRaises(ValueError):m.interval_rsi({**payload,'candles':bars[:-1]},interval,now)
   with self.assertRaises(ValueError):m.interval_rsi({**payload,'stale':True},interval,now)
   with self.assertRaises(ValueError):m.interval_rsi({**payload,'candles':bars[-10:]},interval,now)
 def test_invalid_choices(self):
  for interval,limit in [('5m',20),('1h',101),('1d',True)]:
   with self.assertRaises(ValueError):m.rsi(interval,limit)
 def test_supported_count_choices(self):
  from unittest.mock import patch
  for count in (5,8,10,15,20,50,100):
   with patch.object(m.m,'cached',side_effect=lambda key,ttl,load:load()), patch.object(m.exchange_charts,'chart',return_value={'source':'fixture','pair':'BTCUSDT'}), patch.object(m,'interval_rsi',return_value=(50,1800000000)):
    result=m.rsi('1d',count)
    self.assertEqual(len(result['rows']),count)
    self.assertEqual(result['rows'][0]['coin_id'],'bitcoin')
if __name__=='__main__':unittest.main()
