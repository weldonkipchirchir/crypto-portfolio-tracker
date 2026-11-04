import copy
import sqlite3
import unittest
from unittest.mock import patch
import feature_orderbook_history as f

class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.c=sqlite3.connect(':memory:'); self.c.row_factory=sqlite3.Row; f.init(self.c)
        self.now=1800000000000
        self.book={'available':True,'pair':'BTC-USD','base_currency':'BTC','quote_currency':'USD','observed_at':self.now,'bids':[{'price':'99','quantity':'2','notional':'99999'}],'asks':[{'price':'101','quantity':'3'}]}
    def capture(self, uid=1, now=None, book=None):
        with patch.object(f.time,'time',return_value=(now or self.now)/1000),patch.object(f.micro,'microstructure',return_value={'orderbook':book or self.book}) as fetch:
            result=f.read(self.c,uid,{'operation':'capture'})
            return result,fetch.call_count
    def test_empty_no_fetch_and_tenant(self):
        with patch.object(f.micro,'microstructure',side_effect=AssertionError('history must not fetch')):
            self.assertEqual(f.read(self.c,1,{})['samples'],[])
        self.capture()
        self.assertEqual(f.read(self.c,2,{})['samples'],[])
        self.assertEqual(f.read(self.c,1,{'venue':'binance'})['samples'],[])
    def test_math_gap_and_throttle(self):
        first,_=self.capture(); self.assertEqual(first['samples'][0]['bids'][0]['notional'],'198')
        result,calls=self.capture(now=self.now+10000); self.assertEqual(calls,0); self.assertEqual(len(result['samples']),1)
        book=dict(self.book,observed_at=self.now+180000)
        result,_=self.capture(now=self.now+180000,book=book)
        self.assertEqual(result['samples'][1]['gap_ms'],180000)
    def test_bad_snapshot(self):
        for changes in ({'pair':'ETH-USD'},{'quote_currency':'USDT'},{'available':False},{'observed_at':self.now-120001},{'observed_at':True},{'asks':[{'price':'98','quantity':'1'}]},{'bids':[{'price':'99','quantity':'-1'}]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                f.validate(dict(self.book,**changes),'bitcoin','coinbase',self.now)
        self.assertEqual(f.read(self.c,1,{})['samples'],[])
    def test_retention_is_instrument_and_tenant_scoped(self):
        self.capture(uid=2)
        for i in range(122):
            stamp=self.now+i*60000
            self.capture(now=stamp,book=dict(self.book,observed_at=stamp))
        rows=f.read(self.c,1,{})['samples']
        self.assertEqual(len(rows),120);self.assertEqual(rows[0]['observed_at'],self.now+2*60000)
        self.assertEqual(len(f.read(self.c,2,{})['samples']),1)
    def test_client_payload_never_used(self):
        with patch.object(f.micro,'microstructure',return_value={'orderbook':dict(self.book,available=False)}):
            with self.assertRaises(ValueError):f.read(self.c,1,{'operation':'capture','snapshot':self.book})
        self.assertEqual(f.read(self.c,1,{})['samples'],[])

if __name__=='__main__':unittest.main()
