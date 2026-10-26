import unittest,threading,time
from concurrent.futures import ThreadPoolExecutor
import coin_market as m
class CacheConcurrencyTests(unittest.TestCase):
 def setUp(self):m.CACHE.clear();m.FAILURES.clear()
 def test_unrelated_feed_does_not_block(self):
  entered=threading.Event();release=threading.Event()
  def slow():entered.set();release.wait(2);return {'ok':1}
  with ThreadPoolExecutor(max_workers=2) as pool:
   first=pool.submit(m.cached,('fundamentals','slow'),60,slow);self.assertTrue(entered.wait(1))
   second=pool.submit(m.cached,('fundamentals','fast'),60,lambda:{'ok':2})
   try:self.assertEqual(second.result(timeout=.5)['ok'],2)
   finally:release.set()
   first.result()
  self.assertEqual(m.KEY_LOCKS,{})
 def test_same_key_still_coalesces(self):
  calls=[]
  def load():calls.append(1);time.sleep(.02);return {'ok':1}
  with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(lambda _:m.cached(('fundamentals','same'),60,load),range(4)))
  self.assertEqual(len(calls),1);self.assertEqual(len(results),4);self.assertEqual(m.KEY_LOCKS,{})

 def test_market_budget_bounded_parallelism(self):
  from contextlib import ExitStack
  from runtime_security import ProviderBudget,BudgetExceeded
  b=ProviderBudget(limit=60,per_user_concurrent=4)
  with ExitStack() as stack:
   for _ in range(4):stack.enter_context(b.action(1))
   with self.assertRaises(BudgetExceeded):
    with b.action(1):pass
  with b.action(1):pass
