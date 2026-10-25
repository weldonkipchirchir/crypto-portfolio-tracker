import unittest
from unittest.mock import patch
import token_integrations as tokens

def encoded(text):
 body=text.encode();return '0x'+(32).to_bytes(32,'big').hex()+len(body).to_bytes(32,'big').hex()+body.hex()+('00'*((-len(body))%32))
class MetadataTests(unittest.TestCase):
 def test_dynamic_and_legacy(self):
  self.assertEqual(tokens.decode_metadata(encoded('PONS')),'PONS');self.assertEqual(tokens.decode_metadata('0x'+b'PONS'.ljust(32,b'\0').hex()),'PONS')
 def test_bounds_and_controls(self):
  for raw in ['0x','0x'+'f'*10000,encoded('bad\u202ename'),encoded('a'*257)]:
   with self.assertRaises(ValueError):tokens.decode_metadata(raw)
 def test_malformed_metadata_is_optional(self):
  with patch('providers.request_json',return_value=[]):self.assertEqual(tokens.token_metadata('Robinhood Chain','0x'+'1'*40),{})
 def test_metadata_remains_unverified(self):
  with patch('providers.request_json',side_effect=[{'result':'0x'+format(123,'064x')},{'result':'0x'+format(2,'064x')},{'result':encoded('PONS')},{'result':encoded('Pons')}]):
   result=tokens.token_balances('Robinhood Chain','0x'+'1'*40,['0x'+'2'*40],include_metadata=True)
   token=result['tokens'][0];self.assertEqual(token['symbol'],'PONS');self.assertEqual(token['quantity'],'1.23');self.assertFalse(token['identity_verified'])
if __name__=='__main__':unittest.main()
