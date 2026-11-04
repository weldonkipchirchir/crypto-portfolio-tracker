# Analytics verification — 2026-11-04

All 25 features register load, render and bind contracts. This verifies integration, not every possible live-provider response.

## Confirmed improvements

- Fixed daily Period P&L reading a nonexistent field, which generated NaN chart coordinates.
- Date spacing now reflects actual UTC calendar gaps, including selected period boundaries.
- Daily results use signed green/red bars; cumulative results use a blue line. Native SVG titles expose exact dates and values; the daily table remains available.
- Scope labels distinguish saved history, manually sourced unlocks/income, manual in-app alert checks, bounded market observations and hypothetical liquidation scenarios.
- Keyboard focus is visible on Analytics controls.

## Verification boundaries

The preceding deployment passed 30 production page/asset MIME, navigation and security-policy checks and both unauthenticated feature endpoints returned 401. Account isolation and provider failures have fixture-based regression coverage. Actual private exchange credentials were not exercised. Optional PostgreSQL integration tests require their external fixture configuration. Browser automation was unavailable, so visual phone/desktop acceptance and live OKX stream operation are not claimed.

See ROADMAP_IMPLEMENTATION.md for all 25 tool scopes, research sources and architecture diagrams. Missing historical valuations are not invented; sampled execution data is not a full exchange archive. Email delivery is not promised by the manual Analytics portfolio-alert tool.

## Delegated review follow-up

Three agents reviewed portfolio chart/date behavior, market chart rendering, and shared Analytics discovery/lifecycle behavior. Fixes reject unknown history values instead of charting zero, sort observations, use complete UTC calendar-day filters, reject impossible sale dates, and enable custom dates only for custom periods. Charts now distinguish value/cost colors, center constant observations, label comparison indices and distinguish overlapping venue markers without altering their timestamps. Watchlists format USD and signed percentages while retaining unknown values. Tool search, category counts, remembered category selection, accessible loading placeholders, mobile controls and retry-cache recovery improve navigation.

Verification: all 53 frontend suites plus the explicit exchange activity UI check passed; 14 affected backend/authentication/static-asset tests passed. The final loading placeholder change passed the workspace suite separately. No backend/provider calculations changed. Existing visual-browser and live-credential limitations above still apply.
