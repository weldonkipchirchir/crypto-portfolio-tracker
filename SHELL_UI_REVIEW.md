# Workspace shell review

REA inspected the deployed pre-change `experience_ui.js`, retained as Evidence `ev_189a1a8105eb4ea0ea84c15474a8252ccc3f14b77cdf3898aadcf7e86b391f75`. One JavaScript file parsed, 2,292 AST nodes visited, no parse failures. Evidence is retained at `C:/Users/weldo/.codex/visualizations/2026/10/24/01a16f71-b4a0-7812-8cf8-c3590314d9b7/rea-navigation-shell-evidence.json`. The inert graph is not execution evidence or a security certification.

## Implementation

- Fixed-width floating desktop navigation with independent link scrolling and a stable account footer.
- Main sections share a centered 1,320px content limit inside the remaining workspace, with responsive gutters.
- Phone navigation becomes a labeled Menu button with expanded state and controlled navigation ID. Selection and Escape close it; focus returns to Menu. All existing routes remain available. Sign out is exposed in the expanded phone menu.
- Slate surfaces, mint accents and a blue active-navigation state distinguish actions from financial gain/loss colours. Tabular numerals improve numeric alignment.
- Liquid-glass styling is limited to navigation and floating controls; financial panels remain opaque. Unsupported backdrop filters retain solid surfaces. Reduced-transparency/high-contrast preferences disable the effect; forced-colour styles preserve outlines.

## Design references

[W3C contrast guidance](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum/) sets a 4.5:1 normal-text target. [MDN reduced transparency](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/%40media/prefers-reduced-transparency) documents preference-based opacity support. [MDN backdrop-filter](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/backdrop-filter) documents the enhancement used here.

Chosen opaque-token contrast measurements: dark text 14.14, dark muted 8.40, dark active text 9.45, dark primary 10.11; light text 14.90, light muted 6.06, light active text 12.54, light primary 7.02. This is a selected palette check, not a claim that every provider graphic or dynamic component meets WCAG.

## QA

All 54 frontend suites, four hosted-asset tests, static build and whitespace checks passed. The added navigation regression checks idempotent setup, expanded state, non-navigation clicks, selection closure and Escape/focus behavior. An isolated synthetic-data preview verified both themes, all 11 mobile destinations and centered wide-screen content: at 1,920px the 1,320px section had equal 120px inner margins. No production portfolio data was used in that preview.

Remaining limits: reduced-transparency and forced-colour preference branches were inspected in CSS rather than OS-emulated. These layout changes do not modify valuation or trading calculations.
