# skill-regression

Identity: `skill-engineering/regression`, first-party ILAIOS Skill Engineering package.

Purpose: compare compatible candidate evidence against an approved baseline and block downstream promotion when quality, safety, governance, compatibility, cost, or reliability regresses beyond policy.

## Required behavior

- Compare only evidence with compatible candidate/baseline contracts and scenario semantics.
- Bind every delta to exact baseline/candidate identities and evidence IDs.
- Treat security, governance, tenant isolation, evidence integrity, policy/approval, Tool Gateway, validation, and secret-handling regressions as blocking regardless of aggregate quality gains.
- Do not waive regression because a candidate is newer, cheaper, faster, or produced by a stronger model.
- Distinguish missing evidence from neutral delta; missing evidence is BLOCKED.
- Emit a regression decision and blockers only. Do not promote, register, deploy, mutate production, or self-certify.

## Governance boundary

Regression is one gate in the lifecycle, not the promotion authority. Compatibility, policy/approval, runtime provisioning, deployment, and production verification remain separate evidence-gated stages.

## Evidence

Emit exact baseline/candidate identities, per-dimension deltas, blocking regressions, evidence IDs, and unresolved blockers.
