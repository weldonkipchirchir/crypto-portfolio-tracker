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
