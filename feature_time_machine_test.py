import json
import sqlite3
import unittest
from unittest.mock import patch
import feature_time_machine as tm

class TimeMachineTests(unittest.TestCase):
    def setUp(self):
        self.c=sqlite3.connect(':memory:'); self.c.row_factory=sqlite3.Row
        self.c.executescript('CREATE TABLE portfolio_daily_values(user_id,day,data); CREATE TABLE portfolio_checkpoints(user_id,created_at,id,data); CREATE TABLE wallets(id,user_id,chain,address,label); CREATE TABLE wallet_snapshots(wallet_id,data); CREATE TABLE wallet_tokens(wallet_id,data); CREATE TABLE prices(user_id,symbol,price); CREATE TABLE price_metadata(user_id,symbol,updated_at);')
        tm.init(self.c)
        for uid,day,stamp,value in [(1,'2026-01-01',1767225600,'10'),(1,'2026-01-03',1767398400,'30'),(2,'2026-01-02',1767312000,'999')]:
            self.c.execute('INSERT INTO portfolio_daily_values VALUES (?,?,?)',(uid,day,json.dumps({'observed_at':stamp,'value':value})))
    def test_exact_and_nearest_prior(self):
        exact=tm.read(self.c,1,{'date':'2026-01-03'})['observation']
        self.assertEqual((exact['value'],exact['offset_days']),('30',0))
        prior=tm.read(self.c,1,{'date':'2026-01-02'})['observation']
        self.assertEqual((prior['value'],prior['offset_days'],prior['timestamp']),('10',1,1767225600))
        self.assertIsNone(prior['holdings'])
        self.assertIsNone(tm.read(self.c,1,{'date':'2025-12-31'})['observation'])
        self.assertIsNone(tm.read(self.c,3,{'date':'2026-01-03'})['observation'])
    def test_capture_uses_saved_owner_data_and_cost_unknown(self):
        for uid,value in [(1,'2'),(2,'999')]:
            self.c.execute('INSERT INTO wallets VALUES (?,?,?,?,?)',(uid,uid,'Ethereum','0x'+'1'*40,'wallet'))
            self.c.execute('INSERT INTO wallet_snapshots VALUES (?,?)',(uid,json.dumps({'quantity':value,'updated_at':1767225600})))
            self.c.execute('INSERT INTO prices VALUES (?,?,?)',(uid,'ETH','10'))
            self.c.execute('INSERT INTO price_metadata VALUES (?,?,?)',(uid,'ETH',1767225600))
        with patch.object(tm.time,'time',return_value=1767312000):
            tm.action(self.c,1,{'operation':'capture','user_id':2})
        data=tm.read(self.c,1,{'date':'2026-01-02','source':'detailed'})['observation']
        self.assertEqual(data['value'],'20')
        self.assertEqual(data['holdings'][0]['quantity'],'2')
        self.assertIsNone(data['holdings'][0]['cost_usd'])
        self.assertEqual(data['holdings'][0]['balance_observed_at'],1767225600)
        self.assertIsNone(tm.read(self.c,2,{'date':'2026-01-02','source':'detailed'})['observation'])
    def test_invalid_dates_and_separate_sources(self):
        with self.assertRaises(ValueError): tm.read(self.c,1,{'date':'2026-02-30'})
        self.assertIsNone(tm.read(self.c,1,{'date':'2026-01-03','source':'wallets'})['observation'])

if __name__=='__main__': unittest.main()
