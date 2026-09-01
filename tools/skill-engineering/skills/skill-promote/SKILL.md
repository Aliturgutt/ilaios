# ILAIOS Skill Engineering — Promote

## Purpose

Assemble the final evidence package required to request canonical skill promotion after all preceding lifecycle gates have passed. This skill does not own promotion authority and cannot write a promoted record by itself.

## Inputs

- immutable candidate package digest and version;
- lint, validation, security-scan, evaluation, benchmark, regression, and compatibility evidence identifiers;
- independent-review evidence;
- candidate capability/permission declarations;
- canonical governance and promotion-evidence references when authorization is granted.

## Required checks

1. Every required lifecycle evidence item belongs to the exact candidate digest/version and is current.
2. No preceding gate is `BLOCKED`, regressed, incompatible, or unresolved.
3. Independent review is present where required by risk class.
4. Evaluation and benchmark evidence cannot substitute for security, compatibility, policy, approval, or evidence requirements.
5. Requested runtime authority does not exceed an explicitly reviewed runtime binding; package declarations alone never grant execution.
6. Promotion must be delegated to the canonical `services.skill_factory.SkillPromotionGate`, which requires canonical governance authorization and durable promotion evidence before registration.

## Fail-closed behavior

Missing/mismatched evidence, unresolved blockers, failed regression, incompatible contracts, absent independent review, absent governance authorization, or absent durable promotion evidence produces `BLOCKED`. This skill cannot mutate the promotion registry directly, alter Policy/Approval decisions, modify master/production, provision runtime authority, deploy, or self-certify maturity.

## Output

Emit `ELIGIBLE_FOR_GOVERNED_PROMOTION` or `BLOCKED`, the candidate digest/version, evidence matrix, unresolved blockers, requested runtime-binding identity if one exists, and governance/evidence requirements still outstanding. Eligibility is not promotion; promotion is not runtime admission; runtime admission is not deployment; deployment is not production verification.

## Governance boundary

`SkillPromotionGate`, canonical Policy/Approval, durable Evidence, runtime admission, Tool Gateway, routing, Validation, Audit, tenant controls, and deployment remain authoritative and external.
