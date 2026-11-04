# Historical time machine

Register `feature_time_machine.init(c)` during DB setup and route `read(c, uid, raw)` / `action(c, uid, raw)` under feature `time_machine`. Load `feature_time_machine.js` in the workspace. The host commits successful feature actions.

Read inputs: `source` (`connected`, `wallets`, `detailed`) and ISO UTC `date`. Chooses the latest saved observation timestamp on or before that UTC day, with actual timestamp and calendar-day offset. No interpolation, price fetch or historical balance reconstruction. Existing daily/checkpoint observations have totals only; holdings and cost remain explicitly unavailable.

Action: `operation: capture`. Copies saved wallet native/token observations and saved quotes through owner-filtered SQL, no HTTP. Detailed captures are wallet-only and are kept separate from exchange-inclusive daily totals. Each holding keeps balance/quote source timestamps; capture time describes when this copy was stored. Wallet costs cannot safely be attributed from symbol-based trades and remain null. Unknown quantities/prices remain null. Bounds: 2000 holdings, 365 captures/account, 60 seconds between captures. No automatic capture hook is required.

Tests: `python -m unittest feature_time_machine_test`; syntax: `node --check feature_time_machine.js`.
