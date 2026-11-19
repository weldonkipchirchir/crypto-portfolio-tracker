import csv,io,unittest
from csv_safety import spreadsheet_text
import feature_exchange_imports as feature

class CSVTextSafetyTests(unittest.TestCase):
 def test_formula_and_control_prefixes_are_text(self):
  for value in ['=1',' +SUM(A1:A2)','\ufeff  @demo','-command','\tplain','\rplain','\nplain']:
   with self.subTest(value=repr(value)):self.assertEqual(spreadsheet_text(value),"'"+value)
 def test_plain_text_and_numbers_remain_unchanged(self):
  for value in ['Main exchange','  Savings','BTC','2026-01-01',0,-12,1.5]:self.assertEqual(spreadsheet_text(value),value)
 def test_activity_csv_preserves_numbers_and_original_data(self):
  event={key:'' for key in feature.ACTIVITY_FIELDS};event.update(datetime_utc='2026-01-01',asset='BTC',amount_native='-2',fee_native='0.01',status_code='1',reference='  =1',txid='\tplain',source='Demo "exchange"')
  original=event.copy();rows=list(csv.DictReader(io.StringIO(feature.activity_csv([event]))))
  self.assertEqual(event,original);self.assertEqual(rows[0]['amount_native'],'-2');self.assertEqual(rows[0]['reference'],"'  =1");self.assertEqual(rows[0]['txid'],"'\tplain");self.assertEqual(rows[0]['source'],'Demo "exchange"')
