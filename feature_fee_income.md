# Fees and income feature

`feature_fee_income.js` registers `fee_income` in the feature workspace. It reads fresh authenticated `state` on each load and writes nothing. Load the script before opening the workspace feature.

Recorded trade fees use the existing ledger USD fee field. Missing fees make the complete total unavailable, while a clearly labeled known subtotal remains visible. Values are summed as decimal strings without floating point quantity rounding.

Network fees use verified native history records belonging to a wallet present in that same state and with the same chain. Only confirmed and failed transactions are eligible; failed transactions may still pay gas. Repeated observations for the same wallet/network/transaction are counted once. Networks have an explicit native symbol allowlist; unsupported units are excluded. Native fees remain separate by chain and are never converted using today's quote. Coverage, pagination and provider errors remain visible.

Reward and funding income are unavailable because no supported actual payment ledger is exposed here. Earn principal, balances, transfers and ambiguous balance changes never count as income. There is no combined USD expense/income total and no manual record persistence.

Run `node feature_fee_income.test.cjs` for exact decimal arithmetic, missing versus zero, native identity and status checks, duplicate suppression, wallet scope, HTML escaping and fresh account state regression checks.

Integration extension: account-scoped manually entered payment evidence now supports staking/Earn rewards, funding received/paid, network and withdrawal fees. Date, exact asset identity, quantity and statement reference are mandatory. Historical USD is optional; missing USD prevents a complete net total. Records are explicitly manual and do not alter trade P&L or balances. Delete requires confirmation and owner scope.
