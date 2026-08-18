# ilaios-skill-regression

Compare a candidate skill against its approved baseline and block promotion when quality or governance behavior regresses.

## Purpose

Make skill changes evidence-driven and reversible by detecting behavior loss before promotion.

## Required inputs

- candidate evaluation record;
- baseline evaluation record for the same task/scenario class;
- configured regression tolerances;
- governance-critical invariants;
- evidence identifiers.

## Regression checks

1. Candidate and baseline refer to comparable scenario definitions.
2. Candidate pass rate does not fall below the configured threshold.
3. No governance-critical scenario changes from pass to fail.
4. No new permission, tool, provider, tenant, secret, or deployment authority appears without explicit review.
5. Measured cost or latency regressions outside configured bounds are surfaced, not hidden.
6. Missing evidence is treated as unknown and blocks promotion when evidence is mandatory.

## Output

Return explicit regression findings, metric deltas, governance findings, and evidence identifiers.

## Promotion rule

Regression PASS is necessary but not sufficient for promotion. Canonical policy/approval authorization and durable promotion evidence remain mandatory.
