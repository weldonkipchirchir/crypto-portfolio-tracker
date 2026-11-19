"""Neutralize spreadsheet control/formula prefixes in text cells, without changing stored data."""
import re

def spreadsheet_text(value):
 if not isinstance(value,str):return value
 if value.startswith(('\t','\r','\n')) or re.match(r'^[\s\ufeff]*[=+@-]',value):return "'"+value
 return value
