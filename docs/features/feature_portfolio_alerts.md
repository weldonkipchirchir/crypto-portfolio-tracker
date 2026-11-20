Portfolio-aware alerts

This feature checks the account's recorded-trades portfolio only, using saved USD quotes and their account-owned price_metadata timestamps. It makes no network calls. Manual evaluation requires every open ledger holding to have a positive quote at most 900 seconds old. Missing, future or stale quote timestamps suppress the entire evaluation, preserve crossing state, and show the reason on each rule.

Supported metrics: total ledger USD value, allocation percent of an exact ledger symbol, and unrealized return percent from recorded remaining weighted-average cost. Connected holdings and ledger holdings are not combined. Allocation symbols are exact recorded ledger identifiers; wallet tokens are not inferred from tickers. Closed ledger symbols have zero allocation in an otherwise complete portfolio. Zero remaining cost suppresses unrealized return evaluation.

Rules and events are private to the authenticated account. Maximum 50 rules and newest 200 events. Equality meets a threshold. The first observed matching condition records an event; repeated checks while true do not. A subsequent event requires a valid false observation first. Rule deletion retains bounded historical events. Checks are manual and in-app only. The existing price email template cannot accurately describe these metrics, so these events are not queued as misleading price emails.

Drawdown is explicitly unavailable: existing connected daily totals lack sufficient historical quote freshness provenance for fail-closed alerts. Observed daily changes also include transfers and balance membership changes and must not be presented as investment return drawdown.

Validation: python -m unittest feature_portfolio_alerts_test; node --check feature_portfolio_alerts.js.
