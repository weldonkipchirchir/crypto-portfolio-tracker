# Target allocations

The Portfolio workspace module stores account-scoped user targets under `feature-target-allocations-v1` using the existing chart setup load/save API. Version 1 is `{version:1, targets:{connected:[[positionKey,percent]],ledger:[[positionKey,percent]]}}`. It does not alter the older portfolio allocation plan.

Connected and recorded holdings have separate denominators and target totals. Targets use exact `OrbitPerformance.positions` keys, never symbol aggregation. Blank targets are unset; zero is explicit. Absent saved positions retain their targets and count toward 100% until explicitly removed from the draft. Unpriced positions remain visible but are excluded from priced exposure. Stale or incomplete positions are counted and labeled. Target values require positive priced exposure.

Use Preview draft drift for edited targets and Export draft CSV for a reviewable report. The table initially shows saved targets. Positive drift means weight above target. Saving submits a snapshot; edits during a save remain intact and are not represented as saved. Changing source or refreshing discards unsaved edits. Failed saved-plan reads disable saving until refreshed successfully, avoiding accidental replacement. Fees, slippage and taxes are excluded; no advice or execution is provided.

Validation: `node --test feature_target_allocations.test.cjs`.
