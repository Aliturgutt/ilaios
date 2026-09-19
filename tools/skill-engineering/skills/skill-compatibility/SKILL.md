# ILAIOS Skill Engineering — Compatibility

## Purpose

Determine whether an evaluated and regression-checked skill candidate can coexist with the current canonical contracts without silently breaking callers, runtime bindings, schemas, evidence semantics, or governance boundaries.

## Inputs

- immutable candidate digest;
- baseline skill/version identity;
- baseline and candidate input/output contract digests;
- evaluation and regression evidence identifiers;
- current runtime-binding evidence, when a runtime binding exists;
- declared migration requirements.

## Required checks

1. Candidate and baseline identities are comparable and evidence is bound to the exact candidate digest.
2. Required inputs are not removed or semantically narrowed without an explicit migration path.
3. Output fields and evidence semantics used by downstream consumers are not removed, renamed, or weakened without migration evidence.
4. Existing runtime authority is not broadened by package declarations, new capabilities, permissions, tools, provider credentials, or routing claims.
5. Canonical maturity and status semantics are preserved; `implemented`, `tested`, `verified`, `deployed`, and `production` are not conflated.
6. Required migrations are explicit, bounded, backward-compatible where possible, and remain external to this skill.

## Fail-closed behavior

Unknown consumer impact, missing baseline evidence, contract ambiguity, authority expansion, incompatible schema change, or missing migration evidence produces `BLOCKED`. This skill cannot execute migrations, alter runtime bindings, mutate production, approve incompatibility, or self-certify readiness.

## Output

Emit `COMPATIBLE` or `BLOCKED`, contract deltas, downstream impacts, required migrations, runtime-authority deltas, evidence identifiers, and unresolved blockers. Compatibility approval is a lifecycle input to promotion only and never a production claim.

## Governance boundary

Policy, Approval, runtime admission, migrations, Tool Gateway, routing, Validation, Audit, and Evidence remain authoritative and external.
