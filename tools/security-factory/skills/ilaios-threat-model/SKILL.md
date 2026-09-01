---
name: ilaios-threat-model
description: Evidence-bounded ILAIOS trust-boundary inventory and threat-model completeness review.
---

# ILAIOS Threat Model

Use this skill to build a defensive repository-backed view of which critical trust boundaries have observable implementation evidence.

## Authority

Owner: `ilaios.agent.security.codesec.v1`

Capability: `security.sast`

The skill is an analytical specialization of CodeSec. It does not grant design authority, authorization authority, or exploit capability.

## Boundaries evaluated

The analyzer inventories repository evidence for:

- identity and authentication
- tenant isolation
- policy and governance
- approval controls
- tool gateway controls
- evidence and audit
- provider/routing boundaries
- CI workflows

The inventory is bounded to repository paths and intentionally limits evidence samples per boundary.

## Interpretation

A missing boundary is reported as a **threat-model evidence gap**, not automatically as a vulnerability. A present file path is evidence of implementation surface, not proof that the control is correct.

## Adversarial questions

When reviewing the inventory, reason about failure modes such as cross-tenant access, approval bypass, unauthorized tool invocation, evidence tampering, provider/data egress, and privileged CI input. Convert them into findings only when repository evidence supports the claim.

## Guardrails

- No exploitation.
- No arbitrary network access.
- No credential retrieval.
- No production mutation.
- No inference that a control is safe merely because a matching file exists.
- No self-verification.

## Status rule

The model remains evidence-bounded. Independent SecurityVerifier evidence is required for a verification decision.
