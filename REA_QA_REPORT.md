# REA and QA review — 2026-11-10

## Evidence and scope

REA CLI 6.7.0 analyzed eight JavaScript files downloaded from the public production app. SHA-256 hashes and captured artifacts are retained under the local `rea-orbit-qa` directory. REA Evidence ID: `ev_82cd10d5929b133356470d95a3a5e33e45dc88d918a3209214d935b97ff2652a`.

The complete local evidence is `C:/Users/weldo/.codex/visualizations/2026/10/24/01a16f71-b4a0-7812-8cf8-c3590314d9b7/rea-orbit-evidence.json`. REA parsed eight JavaScript files, visited 56,474 AST nodes and reported no parse failures. Its inert graph includes module, storage and endpoint observations. Dynamic paths remain incomplete; static observations do not establish execution or absence of defects. This evidence is a pre-fix deployment capture, not a scan of the Python backend. REA MCP registration was missing; the CLI fallback required no configuration changes.

## Confirmed defects and fixes

| Finding | Evidence type | Fix / regression |
| --- | --- | --- |
| RSI aggregate cache could cross a UTC completed-candle boundary | Source and deterministic fixture | Partition cache by interval UTC bucket; test hourly, 4-hour and daily rollover |
| Up to 100 queued workers could still attempt provider fallback after budget exhaustion | Source and deadline fixture | Stop before provider call; cap RSI budget at 25 seconds; exhausted budget makes zero chart calls |
| RSI accepted a zero closing price | Source and numeric fixture | Reject nonpositive closing prices before Wilder calculation |

These defects were reproduced by source-level QA, not discovered by executing the REA artifact graph.

## Observed browser QA

- Saved-account sign-in succeeded without reading/exporting credentials.
- Analytics category navigation and live Binance/Bybit funding histories loaded.
- At a 390-pixel viewport override, document scroll width equaled client width; responsive category/tool controls appeared.
- Live footprint loaded actual executed rows. Zoom out switched to history; repeated zoom in restored `History = recent` and Bar details. Expanded mode opened and closed successfully.
- Browser error log check returned no errors for this observed session.
- Screenshot retained locally: `C:/Users/weldo/.codex/visualizations/2026/10/24/01a16f71-b4a0-7812-8cf8-c3590314d9b7/orbit-footprint-qa.png`.

## Limits

This is bounded QA of sign-in, navigation, responsive Analytics, funding and footprint zoom. Account mutations, real credential exchange import, email delivery, every indicator and every provider failure were not exercised. No claim of full application correctness or security certification is made. Native Hopper/Ghidra engines were unnecessary for these web artifacts.

Final verification: all 53 frontend suites passed. The full Python run completed 572 tests with 21 optional tests skipped. Static build and whitespace checks passed. All eight captured deployment scripts were byte-identical to checkout source files before these backend fixes.

## Overview, Markets and Data follow-up

REA Evidence `ev_3169584c85670bfe2f1c9d2894684edc566cdd3d5678bc141b6a7b53110ec6e7` covers the public pre-fix `portfolio_overview.js` and `market_dashboard.js` captures plus their hash manifest. Two scripts parsed, 11,360 AST nodes visited, no parse failures. Retained evidence: `C:/Users/weldo/.codex/visualizations/2026/10/24/01a16f71-b4a0-7812-8cf8-c3590314d9b7/rea-valuation-charts-evidence.json`. The earlier Data artifact evidence is reused. Neither static result is evidence of runtime calculation correctness.

Source regressions reproduce invalid/future timestamp freshness, corrupt duplicate snapshot precedence, invalid priced counts, overflow totals, numeric coercion in Data/Markets, invalid chart dates, unsorted observations, hidden off-scale quotes and old quote requests delaying newly selected coin quotes. Fixes preserve separate connected and ledger totals, expose saved-value coverage near the total, reject malformed observations, and make off-scale prices explicit. Provider data can be stale, missing or wrong; a saved valuation is an estimate, not an execution guarantee.

Integrated follow-up regression: all 53 frontend suites, 13 affected persistence/auth/static-asset tests, static build and whitespace checks passed.

Production follow-up browser checks: new valuation status rendered explicit partial/stale counts; live BTC candle chart and Binance USDT quote loaded; keyboard date inspection reached the first observation of the selected 30-day range; browser error log was empty. Visual QA observed a chart occupying only about 610px of a 949px workspace beside a stretched valuation card. The follow-up CSS moves metrics below a full-width chart; no pricing calculation changes.

Browser follow-up identified stale stylesheet reuse across deployments: the URL without a query still exposed the pre-fix CSS rules in the active browser despite updated production content. Build now emits content-hashed URLs for allowlisted app JavaScript and CSS. Four hosted-asset tests, including exact hash URLs, passed. This fix is based on observed stylesheet content, not an inferred REA finding.

## Portfolio consistency review — 2026-11-15

REA CLI inspected the latest public pre-fix `portfolio_performance.js`. Evidence ID: `ev_59ca793f7637d6d3e30467d72cfe73ae9861451f1a8fb5b2e7cf60e3f1f3e3fe`. One script parsed; 9,447 AST nodes visited, no parse failures. Capture/hash manifest: `C:/Users/weldo/.codex/visualizations/2026/10/24/01a16f71-b4a0-7812-8cf8-c3590314d9b7/rea-portfolio-nov15`; retained evidence ends in `rea-portfolio-nov15-evidence.json`. Existing overview evidence is reused. These are inert shipped-artifact observations; the defects below were reproduced with source regression fixtures.

- Portfolio movement, period-dollar estimates and holdings colours reject stale market/history returns. Stale holdings cannot supply current-weight dollar-change estimates. Saved values remain visible with an explicit sync label.
- Exchange positions now select valid newest snapshots using ISO/seconds/milliseconds timestamps, consistent with overview totals. Missing quote timestamps require review.
- Wallet asset deduplication selects newest native/token observations independently. A newer zero balance suppresses an older duplicate positive balance instead of resurrecting it.
- Daily snapshots normalize timestamps, prefer valid newest wallet/exchange observations, use the real token `price_fetched_at` field, and fingerprint missing Flexible/Locked Earn coverage explicitly.

No missing historical values, cost bases or investment returns are inferred. The new rules can show unavailable changes where old code showed plausible but stale estimates. A balance sync and price refresh are separate operations.

Regression verification: all 53 frontend suites passed after the final wallet fix. Full Python regression ran 576 tests with 21 optional tests skipped. Static build and whitespace checks passed.

## Holdings colour and calendar navigation review

REA Evidence `ev_81d80676e4944923b338ae39cb7ab0e76da4582b5c07139956d374a16f57c65c` captures the public pre-fix portfolio renderer (one script, 9,768 AST nodes, no parse failures). Retained at `C:/Users/weldo/.codex/visualizations/2026/10/24/01a16f71-b4a0-7812-8cf8-c3590314d9b7/rea-overview-sections-evidence.json`. Static inspection is supplemented by source semantics review and regressions; REA did not establish runtime correctness.

Market-return colour is now independent of holding-balance freshness: a fresh exact-ID market percentage can colour an old saved holding, while its saved value remains marked for sync. Personal P&L colour and dollar-change estimates retain strict freshness requirements. Ledger positions propagate quote freshness from saved price metadata. Stale market percentages remain unavailable.

Calendar navigation adds saved-month/all-month/specific-month filtering, a full-year saved-date/comparison summary, and distinct baseline/zero/missing legend entries. The explicit source switch applies to holdings analysis, while the calendar still represents connected portfolio observations. Hidden-amount mode now covers holdings-card USD amounts and their total.

Validation: 53 frontend suites and 15 affected persistence/build tests passed. Saved history and cost basis are not reconstructed or inferred.


## Portfolio tracking and returns review — 2026-11-15

REA evidence `ev_e2d05453e358ce52fd07d5b0ac03210d291513bfbcfe21a389c10451f58f686e` analyzed captured production portfolio_performance.js and market_discovery.js as inert JavaScript. Static relationships do not establish runtime correctness; source review, regression tests and browser checks supply separate evidence. Capture manifest and evidence are saved in the local visualization workspace under rea-portfolio-tracking.

Findings and changes:
- A source-selector child invalidated positional grid rules, stretching the selector into a large empty card. Explicit full-width rules now keep it compact and make movement/P&L panels readable on desktop and phone.
- Daily observations previously depended on successful price refresh alone. Authenticated workspace reads and balance/token/exchange/manual-price updates now capture saved valuations. Identical routine reads are deduplicated, explicit observations are preserved, and stale workspace reads cannot invent daily returns. Day dialogs explain capture and comparison limitations. No background scheduler or historical backfill is implied.
- INJ and GRASS ledger quote mappings were absent. Exact CoinGecko IDs were verified against the public coin catalog and added with a mapping regression. Wallet token identities remain contract-based.
- Partial ledger P&L retains an unavailable full unrealized total but exposes an explicitly labeled known subtotal and missing symbols. Realized totals identify the number of recorded sales.
- Movement cards preserve strict weighted-value freshness and can separately display a labeled simple mean of fresh distinct-coin returns when saved weights are stale. These are market changes, not investment P&L.
- Crypto bubbles now offer a readable price/return table, stricter number/date/quote validation, stale-data notices and request ordering protection. Flat return charts remain centered.

Validation: 54 JavaScript suites passed; targeted calendar/backend tests and quote mapping tests passed. Full backend regression and post-deployment browser results are recorded below when complete.

Full backend regression: 582 tests passed with 21 optional skips. Static build and git diff --check passed.

Production QA (deployment dpl_4Gj3FBoJgQ7aQJJqNtbBn22zs4Av, READY and aliased): authenticated overview opened successfully; selector height 71px desktop / 96px phone; no document overflow at 390px; movement displayed fresh distinct-coin means; price refresh priced all 8 ledger assets including INJ/GRASS and displayed a complete unrealized total; today contained a saved connected valuation and correctly explained missing prior-day comparison. Coin table filtering and Bitcoin daily-history calculation loaded successfully. Browser error log was empty. Temporary theme/viewport/filter changes were restored. Connected balance timestamps remain stale and require an actual balance sync; this QA did not modify trades or credentials. Screenshot proofs: portfolio-tracking-desktop.png and portfolio-tracking-phone.png in the local visualization workspace.
