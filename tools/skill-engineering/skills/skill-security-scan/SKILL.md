# ILAIOS Skill Engineering — Security Scan

## Purpose

Gate a skill candidate on security evidence after semantic validation and before evaluation. This lifecycle stage does not create a new security engine. It requires and evaluates evidence produced by the canonical Assurance and governance boundaries that apply to the candidate's risk and dependency surface.

## Inputs

- immutable candidate package digest;
- validated candidate evidence;
- declared capabilities, tools, permissions, dependencies, and risk class;
- applicable Assurance evidence identifiers;
- unresolved security findings and accepted-exception evidence, if any.

## Required checks

1. Validation evidence belongs to the exact candidate digest.
2. Required security-review evidence exists and is current for the candidate.
3. Threat-model, supply-chain, dependency, or differential-review evidence is required when the candidate surface makes that control applicable.
4. No evidence indicates governance bypass, secret retrieval, unrestricted network, direct production mutation, uncontrolled tool access, tenant escape, approval bypass, routing takeover, or evidence-chain bypass.
5. High/critical findings remain blocking unless the canonical governance system records an explicit, scoped, current exception; this skill cannot create that exception.
6. Security conclusions are bound to candidate digest and evidence IDs.

## Fail-closed behavior

Missing, stale, mismatched, contradictory, or insufficient Assurance evidence produces `BLOCKED`. Cost, speed, benchmark gain, or user convenience cannot waive a protected-boundary finding. This skill cannot run an unrestricted scanner, retrieve secrets, mutate policy, approve itself, invoke production tools, or self-certify security.

## Output

Emit `PASS` or `BLOCKED`, the exact candidate digest, required Assurance controls, evidence consumed, blocking findings, accepted-exception evidence identifiers, and unresolved blockers. `PASS` means the security evidence gate is satisfied for the candidate revision only; it is not production verification.

## Governance boundary

Assurance implementations, Policy, Approval, tenant controls, Tool Gateway, Validation, Audit, Evidence, and runtime admission remain authoritative. This package only composes their evidence into the Skill Engineering lifecycle.
