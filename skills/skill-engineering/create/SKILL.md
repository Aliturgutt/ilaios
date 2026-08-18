# ilaios-skill-create

Create a new ILAIOS-native skill as a bounded capability package without copying external skill implementations or weakening canonical governance.

## Purpose

Use this skill when a new repeatable execution pattern should become a reusable ILAIOS skill. External repositories may be studied for methodology, packaging ideas, evaluation strategy, or interoperability conventions, but their implementation text must not be copied into the resulting ILAIOS skill.

## Required inputs

- a clearly bounded task or capability goal;
- authorized trace or evidence inputs when learning from prior execution;
- intended capability dependencies;
- required permissions and tool classes;
- acceptance criteria and test scenarios;
- target version identifier.

## Required output

Produce a candidate skill package with:

- a stable `ilaios.skill.*` machine identity;
- `SKILL.md` as the primary instruction contract;
- optional `references/`, `scripts/`, and `assets/` only when needed;
- explicit capability and permission requirements;
- source-trace digest or equivalent provenance identifier;
- evaluation scenarios;
- evidence references;
- no promotion claim.

## Governance invariants

A skill is never execution authority. It must not bypass or replace:

- Identity / tenant boundaries;
- Policy Engine;
- Approval Engine;
- Tool Gateway;
- Validation Pipeline;
- Audit / Evidence Chain;
- canonical routing;
- bounded retry and repair controls.

Tool or provider use must continue through the governed execution path. A skill may describe what capability is required; it may not grant itself permission to use that capability.

## Candidate workflow

1. Define the bounded task and acceptance criteria.
2. Normalize authorized trace/evidence into reusable observations.
3. Separate durable method from one-off execution details.
4. Write original ILAIOS-native instructions.
5. Declare dependencies and permissions explicitly.
6. Generate or attach deterministic test scenarios.
7. Evaluate candidate behavior against a baseline.
8. Run regression comparison.
9. Record evidence.
10. Submit to canonical policy/approval promotion gates.

## Promotion rule

A candidate remains a candidate until all required scenarios pass, configured quality thresholds are met, regression is non-negative, canonical governance authorizes promotion, and promotion evidence is durably recorded.

`PLAN != IMPLEMENTATION`

`IMPLEMENTED != TESTED != VERIFIED`

`NO EVIDENCE -> NO PROMOTION`

## Interoperability

The package layout intentionally remains compatible with the common open Agent Skills convention of a primary `SKILL.md` plus optional supporting directories. Compatibility is an adapter concern; ILAIOS identity, governance, evidence, and promotion semantics remain authoritative.

## External-reference rule

Reference implementations may inform design decisions only. Do not paste, translate, mechanically rewrite, or lightly rename third-party skill text or source code into ILAIOS. Re-derive the capability from ILAIOS requirements and write the implementation independently.
