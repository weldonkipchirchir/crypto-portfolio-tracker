import json
import sqlite3
import unittest
import feature_transfer_reconciliation as feature

class TransferReviewTests(unittest.TestCase):
    def setUp(self):
        self.c = sqlite3.connect(':memory:')
        self.c.row_factory = sqlite3.Row
        self.c.executescript('CREATE TABLE wallets(id INTEGER,user_id INTEGER,chain TEXT,address TEXT,label TEXT); CREATE TABLE chain_history(wallet_id INTEGER,data TEXT); CREATE TABLE review_decisions(user_id INTEGER,review_id TEXT,status TEXT,data TEXT,PRIMARY KEY(user_id,review_id));')
        self.wallets = [{'id': 1, 'chain': 'Ethereum', 'address': '0xaaa', 'label': '<Sender>'}, {'id': 2, 'chain': 'Ethereum', 'address': '0xbbb', 'label': 'Receiver'}]
        for w in self.wallets:
            self.c.execute('INSERT INTO wallets VALUES (?,?,?,?,?)', (w['id'], 7, w['chain'], w['address'], w['label']))
        base = dict(status='confirmed', kind='token_transfer', hash='hash', event_id='Ethereum:token:hash:1', asset='USD', asset_id='Ethereum:0xtoken', from_address='0xaaa', to_address='0xbbb', quantity='1.000', date='2026-01-01')
        self.rows = [{**base, 'wallet_id': 1, 'direction': 'out'}, {**base, 'wallet_id': 2, 'direction': 'in'}]
    def test_exact_evidence_and_no_mutation(self):
        self.assertEqual(len(feature.candidates(self.wallets, self.rows)), 1)
        self.assertEqual(self.rows[0]['quantity'], '1.000')
    def test_missing_or_conflicting_evidence_never_matches(self):
        for field, value in [('asset_id','Ethereum:other'), ('hash','different'), ('event_id','other-log'), ('quantity','0.99'), ('status','failed'), ('from_address','0xccc'), ('kind','balance_change'), ('direction','out'), ('review_eligible',False)]:
            with self.subTest(field=field):
                rows = [self.rows[0], {**self.rows[1], field: value}]
                self.assertEqual(feature.candidates(self.wallets, rows), [])
        self.assertEqual(feature.candidates(self.wallets[:1], self.rows), [])
    def test_unsafe_numbers(self):
        for value in ('NaN', 'Infinity', '-1', '0', '1e999', '1e-999'):
            self.assertIsNone(feature._amount(value))
    def test_duplicate_events_are_deduplicated(self):
        self.assertEqual(len(feature.candidates(self.wallets, self.rows * 2)), 1)
    def test_persist_review_and_account_isolation(self):
        for row in self.rows:
            self.c.execute('INSERT INTO chain_history VALUES (?,?)', (row['wallet_id'], json.dumps(row)))
        item = feature.read(self.c, 7, {})['items'][0]
        self.assertEqual(feature.read(self.c, 8, {})['items'], [])
        with self.assertRaises(ValueError):
            feature.action(self.c, 8, {'id': item['id'], 'status': 'confirmed'})
        feature.action(self.c, 7, {'id': item['id'], 'status': 'confirmed'})
        self.assertEqual(feature.read(self.c, 7, {})['items'][0]['status'], 'confirmed')
        feature.action(self.c, 7, {'id': item['id'], 'status': 'pending'})
        self.assertEqual(feature.read(self.c, 7, {})['items'][0]['status'], 'pending')
        with self.assertRaises(ValueError):
            feature.action(self.c, 7, {'id': item['id'], 'status': 'buy'})

if __name__ == '__main__':
    unittest.main()
