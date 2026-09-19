# skill-evaluate

Identity: `skill-engineering/evaluate`, first-party ILAIOS Skill Engineering package.

Purpose: evaluate an exact validated candidate against explicit scenarios and assertions and produce evidence without granting execution authority or promotion.

## Required behavior

- Bind every result to candidate digest, scenario-set identity, evaluator/model identity, execution context, and evidence IDs.
- Measure scenario pass/fail and assertion-level outcomes. Missing execution evidence is BLOCKED, never PASS.
- Where a compatible baseline exists, report baseline and candidate metrics separately; do not fabricate unavailable token, latency, cost, or quality telemetry.
- Keep test generation distinct from test execution. Generated cases are not evidence that they passed.
- Prevent evaluator self-certification from satisfying independent review where policy requires another verifier.
- Do not route providers, grant tools, mutate production, register skills, or promote candidates.

## Governance boundary

Evaluation consumes only candidates that have crossed required validation/security gates. Provider/model execution, when used, remains subject to canonical routing, policy, tenant, budget, Approval, Tool Gateway, and evidence controls.

## Evidence

Emit exact candidate/scenario/evaluator identities, pass rate, assertion totals, available measurements, evidence IDs, and unresolved blockers.
