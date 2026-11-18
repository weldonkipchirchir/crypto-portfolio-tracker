# Light and dark theme review — 18 November 2026

## Confirmed problems and fixes

- Monthly calendar gain/loss cells became white in light mode because generic button rules outranked the state classes. Dark mode put white dates on bright green cells (measured 1.59:1 in the fixture). Calendar cells and legend now use scoped theme variables with contrasting date labels at all eight gain/loss intensities. Up/down/flat markers provide direction without colour alone; missing observations and baseline days remain distinct. Phone days have a 40px minimum height.
- Added a final shared theme layer with text, muted, financial, warning, surface, chart-series and histogram tokens. Financial text keeps its sign and meaning. Dense portfolio tables and explanatory notes have clearer type sizing and line spacing.
- Faded valuation notes, warnings, chart legends, market tile identities and disabled exchange setup explanations are readable in both themes. Disabled credential controls remain disabled; their explanatory text is no longer dimmed with the entire fieldset.
- Coin comparison and benchmark series use theme-aware colours for both labels and plotted marks. Populated order-book bids/asks share readable colours with their chart marks. RSI/MACD lines and histogram bars have stronger light-mode contrast.
- Studio quotes without a usable timestamp show Observation time unavailable. Invalid, empty, boolean and out-of-range timestamps are covered by regressions; a valid received time can be used when the provider observation time is absent or invalid.
- Saved theme is applied before the workspace stylesheet paints. Theme choices synchronize across tabs and follow system preference until a manual choice is saved. Native controls, scrollbars and browser theme colour update too. Blocked storage remains usable.
- Login/create-account fields and selected access tabs are consistent in both themes, inputs are 16px on phones, and only the auth layer scrolls while the underlying workspace is inert. Public light-mode calls to action and breadcrumb colours were corrected.

## Verification

- 57 JavaScript test files passed, including ten dedicated theme/contrast cases and timestamp/calendar regressions. All 18 hosted-asset, SEO and public-registration Python checks passed. Static build and diff whitespace checks passed.
- Selected shared text/semantic/series token pairs and every calendar date/background intensity meet the test target of at least 4.5:1. Four MACD histogram states meet at least 3:1 against each plot surface.
- Browser review covered all 11 workspace destinations in both themes at desktop and 390px phone width; the final phone sweep had no horizontal document overflow.
- Checked 25 analytics tools in both themes, then rechecked the comparison fix. Checked all 12 Data views in both themes using populated synthetic sentiment, RSI, order-book, execution, ratio, funding and venue fixtures. Unavailable coverage, including footprint feeds, remained explicit.
- The approximate computed-style text scan reported no remaining flagged text samples on the final 22 workspace views, 12 public desktop views and 24 populated Data views. This scan excludes SVG text, decorative preview content, hidden elements and disabled buttons; it does not establish full accessibility conformance. SVG oscillator/series colours received separate visual and palette checks.
- All six public page files checked in both themes on desktop and phone. Sign-in and create-account layouts checked in both themes; calendar day details, native colour-scheme changes and cross-tab preference synchronization were verified.
- Temporary SQLite database and synthetic wallets, trades, balances, charts and headlines were used. No production account records or production credentials were accessed. No valuation or P&L calculations changed.

## Artifacts and limits

Screenshots and disposable fixtures are outside the repository in the theme-review artifact directory. This pass is UI and readability QA, not a full accessibility certification, provider coverage validation or load/security test. Complex blended backgrounds, forced-colour behaviour and system preference changes were covered by selected CSS/unit checks rather than exhaustive OS/browser combinations.

Shared theme stylesheet: 12,649 raw bytes / 3,164 gzip bytes. It is explicitly allowlisted for static hosting and loaded after component styles.
