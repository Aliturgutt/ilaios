# Skill: ILAIOS Security Review

## Purpose

Perform an adversarial review of a bounded ILAIOS change or release candidate and report evidence-backed security findings without taking over policy, approval, or runtime authority.

## Scope

Review may cover authorization, tenant isolation, secrets handling, data boundaries, policy/approval enforcement, Tool Gateway usage, evidence integrity, dependency/supply-chain exposure, unsafe defaults, and failure behavior.

## Procedure

1. Bind the review to an exact change, branch/commit, artifact, configuration, or deployment identity when available.
2. Identify trust boundaries, privileged operations, external inputs, persisted data, credentials, and execution capabilities touched by the change.
3. Look specifically for bypasses of Policy, Approval, authorization, tenant isolation, validation, Tool Gateway, audit, and Evidence Chain controls.
4. Check fail-open behavior, stale-state assumptions, identity confusion, path/input injection, secret leakage, over-broad permissions, and unsafe dependency changes.
5. Distinguish confirmed findings from hypotheses and unavailable evidence.
6. Require focused regression tests for corrected security invariants.
7. Preserve unresolved high-risk findings as blockers rather than downgrading them for delivery speed.

## Output

- reviewed identity/scope;
- confirmed findings with severity and evidence;
- unverified hypotheses clearly labeled;
- required remediation and regression coverage;
- residual risk and blockers.

## Forbidden

- silently weakening governance to make tests pass;
- declaring a finding resolved because code was changed without verification;
- creating an alternate security authority outside canonical ILAIOS governance.
