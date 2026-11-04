# Multiple portfolios

Groups reference existing source IDs; they never copy trades or assign holdings. Each group uses either connected wallets/exchange connections or ledger accounts. Combined is the unique union of memberships across saved groups, with connected and ledger values displayed separately because they can describe the same holdings. Connected exchange snapshots additionally deduplicate a shared account key; wallet identity follows canonical chain/address/asset identity through portfolio_daily.observation.

Values use saved snapshots and USD quotes only. Unpriced assets and absent observations are disclosed; zero is not substituted for unavailable valuation. These are current saved values, not cost basis, P&L or inferred linkage. Deleting a group only deletes its definition. Account ownership is checked when saving membership and when editing/deleting groups. Maximum 20 groups, 80 characters per name.

Integration: call feature_multiple_portfolios.init(c) at database initialization; dispatch read(c,uid,raw) and action(c,uid,raw) for feature `multiple_portfolios`; load feature_multiple_portfolios.js in the feature workspace. Action performs no provider requests. Run `python -m unittest feature_multiple_portfolios_test`.
