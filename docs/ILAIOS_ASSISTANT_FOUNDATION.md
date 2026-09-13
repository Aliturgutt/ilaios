# ILAIOS Assistant Foundation

## Status

Foundation contract only. This document does not claim production readiness.

## Product split

### Li — Founder Intelligence

Li is founder-only. Access MUST be derived from authenticated principal identity, never from prompt text.

Li may consume authorized founder context such as product architecture, factories, skills, roadmap, CI/deployment state, policy/cost state, and persistent founder memory when those sources are actually connected and current.

If authoritative evidence is unavailable, Li MUST answer with an explicit UNKNOWN or UNVERIFIED state instead of inferring completion.

Li MUST NOT expose founder memory, internal engineering knowledge, private roadmap, cross-tenant data, or privileged security detail to non-founder principals.

### ILAIOS Assistant — User Product Copilot

ILAIOS Assistant is the normal-user guidance layer. It is scoped to the authenticated user and current authorized tenant/project/workload context.

It may answer product-usage questions, explain real job/evidence state, recommend the correct factory/workflow, prepare a proposal, and hand off governed actions through existing canonical authorities.

It MUST NOT create a second router, approval service, policy service, budget authority, ToolGateway, or provider execution path.

## Canonical action path

Assistant responses are advisory until an existing governed execution path accepts a proposal.

Canonical mutation path:

`Assistant -> intent/proposal -> existing Policy/Approval/Budget authorities -> canonical ToolGateway -> existing factory/runtime`

Direct Assistant-to-provider or Assistant-to-factory mutation shortcuts are forbidden.

## Knowledge classes

Every retrievable knowledge record MUST have an authorization class. Minimum classes:

- `PUBLIC_PRODUCT`
- `USER_DOCUMENTATION`
- `TENANT_PROJECT`
- `INTERNAL_ENGINEERING`
- `FOUNDER_ONLY`

Authorization MUST be enforced before retrieval results are exposed to the model. Post-generation filtering is not an authorization control.

Recommended provenance metadata for retrievable records:

- `source_id`
- `source_type`
- `source_version` or source SHA where applicable
- `updated_at`
- `visibility`
- `tenant_id` when scoped
- `project_id` when scoped
- `owner_principal_id` when scoped

Cross-tenant, cross-project, cross-workload, and founder-to-user leakage MUST fail closed.

## Grounding contract

The language model is not the source of truth for ILAIOS state.

For repo, CI, deployment, runtime, job, policy, pricing, factory capability, and UI guidance claims, authoritative/current sources take precedence over model memory.

When a source is stale, missing, ambiguous, or inaccessible, the Assistant MUST communicate that state rather than fabricate a definitive answer.

## Bilingual requirement

ILAIOS Assistant v1 and Li MUST support Turkish and English.

There MUST be one authoritative knowledge model, not duplicated Turkish and English knowledge silos.

Language is a presentation preference:

- Turkish UI defaults to Turkish responses.
- English UI defaults to English responses.
- Users may switch language during a conversation.
- Explicit user language choice overrides UI default for the conversation/session policy selected by the product.
- Canonical product names and security/policy/cost semantics MUST remain consistent across languages.
- Authorization MUST be language-independent.

Critical states such as free/paid, approval required, unauthorized, failed, blocked, unknown, and unverified MUST be derived from the same semantic state before localization.

## Context contract

Normal-user Assistant context may include only authorized values such as:

- authenticated `user_id`
- `tenant_id`
- `project_id`
- `workload_id`
- current product surface/screen identifier
- current plan/entitlements
- authorized job/evidence identifiers
- language preference

Context supplied by browser/client input MUST NOT be trusted as proof of authorization. Server-side authenticated context remains authoritative.

## Cost and paid execution

The Assistant MUST NOT invent prices or label an operation free based on model knowledge.

Paid/external actions must use the existing canonical quote/budget/entitlement path. If the system requires approval before spending, the Assistant may prepare the action but MUST NOT dispatch it before the canonical approval/budget gate allows it.

## Red-team acceptance requirements

The foundation is not DONE until implementation and tests prove at minimum:

- founder principal accepted for Li
- non-founder principal rejected from Li
- normal user cannot retrieve founder memory
- cross-tenant retrieval rejected
- cross-project retrieval rejected
- cross-workload evidence/result reuse rejected where workload binding is required
- prompt text cannot elevate user to founder
- client-forged screen/context cannot elevate authorization
- language switching cannot change authorization outcome
- stale or missing authoritative sources produce UNKNOWN/UNVERIFIED instead of fabricated certainty
- Assistant action proposals cannot bypass Policy/Approval/Budget/ToolGateway controls
- paid action cannot bypass quote/entitlement/approval controls
- source provenance survives retrieval and can be used for grounded answers

## Evidence required for closure

No production-complete claim without repository and runtime evidence appropriate to the changed surfaces.

Minimum engineering closure target:

- focused tests PASS
- full relevant Pytest PASS
- Ruff PASS
- strict Mypy PASS
- pre-commit PASS
- exact-head CI PASS
- runtime/E2E evidence for claims that depend on deployed behavior

UI claims additionally require current browser/screenshot evidence. Production claims additionally require deployment and live-flow evidence.
