"""Explicit authenticated dispatcher for independent roadmap feature modules."""
import importlib,importlib.util
IDS=('exchange_imports', 'transfer_reconciliation', 'missing_cost', 'historical_portfolio', 'period_pnl', 'asset_performance', 'benchmark', 'fee_income', 'multiple_portfolios', 'time_machine', 'portfolio_heatmap', 'target_allocations', 'concentration', 'named_watchlists', 'coin_comparison', 'portfolio_alerts', 'relevant_news', 'token_unlocks', 'funding_history', 'price_oi', 'orderbook_history', 'cvd', 'multi_footprint', 'liquidation_dashboard', 'liquidation_heatmap')
def module(identity):
 if identity not in IDS:raise ValueError('Unknown feature')
 name='feature_'+identity
 if importlib.util.find_spec(name) is None:raise ValueError('This feature has no server-side operation')
 return importlib.import_module(name)
def init(c):
 for identity in IDS:
  name='feature_'+identity
  if importlib.util.find_spec(name) is not None:
   m=importlib.import_module(name)
   if hasattr(m,'init'):m.init(c)
def read(c,uid,raw):
 m=module(raw.get('feature'))
 if not hasattr(m,'read'):raise ValueError('This feature has no server-side read')
 return m.read(c,uid,raw)
def action(c,uid,raw):
 m=module(raw.get('feature'))
 if not hasattr(m,'action'):raise ValueError('This feature has no server-side action')
 return m.action(c,uid,raw)
