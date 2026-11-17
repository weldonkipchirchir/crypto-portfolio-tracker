# Workspace usability review — 17 November 2026

## Improvements

- All eleven workspace destinations share concise guidance and a section jump menu. Jumping opens a containing disclosure and focuses the heading. Reduced-motion preferences are respected.
- The last workspace destination is restored within the browser tab, scoped to the signed-in account and checked against a fixed allowlist. Page titles identify the current section. Storage failures fall back to Overview.
- Profile, Learn, Markets, Data and Targets omit unrelated global trade actions. Table regions support keyboard scrolling and explicit column scopes; financial tables retain their own geometry.
- Forms show saving feedback and restore each button's previous disabled state after success or failure. Notes show readable local save dates. Authentication shows submission progress.
- Insights' screen-reader labels no longer create horizontal overflow. Insights and Targets use readable light surfaces.
- Phone Data navigation uses a visible category grid instead of clipped horizontal buttons. Missing breadth observations show a clear retry message.
- Phone Studio starts with compact controls: candle sizes, zoom, studies and chart. Show tools exposes drawing and advanced controls; setup saving and the desktop toolbox remain available.
- Missing market ranks and wholly missing sample totals stay unavailable. Known zero prices remain zero.
- Public guides share the saved light/dark preference and gain contents lists. Their content remains in HTML, independent of the application bundle. Public CSS is 7,456 raw / 2,461 gzip bytes.

## Verification

- All 56 JavaScript test files passed, including new page restoration, button-state recovery, readable timestamps, compact Studio and missing-provider rendering checks.
- SEO and public-registration checks: 14 Python tests passed. Static build and git diff whitespace checks passed.
- Isolated temporary SQLite database, synthetic wallets, trades, exchange snapshot, chart series and headlines. Real production credentials and portfolio data were not used or changed.
- All 11 workspace destinations checked at desktop and phone widths. Final 390px phone sweep covered light and dark themes with no document overflow.
- All 25 analytics tools opened on desktop and phone, including empty and unavailable-provider states. Rapid navigation hit the normal request budget; affected tools presented retry states and opened after the window reset. No application rate limits were weakened.
- All 12 Data views checked. The mobile category transition failure was reproduced, corrected with the grid and retested: each category selected the intended view without page overflow.
- All six public page files checked at desktop and 390px, including theme switching and guide contents. The legacy tracker URL redirects to the landing page on production.
- Synthetic registration mismatch, successful registration, new-account guidance, sign-in/session refresh, account-scoped page restoration, note/profile saves, Studio tool expansion and account setup saving checked in the browser. No final browser console errors.

## Limits

This is UI/workflow QA, not a security certification, an exhaustive accessibility audit or a load test. Provider-dependent views were checked for rendering and recovery, but live feed availability, email delivery and real exchange-key authorization were not validated. Calculations were not changed in this pass. Screenshots and the disposable demo fixture are saved outside the repository under the ui-review artifact folder.
