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

## Desktop UX contract

The existing Desktop home layout remains authoritative. Assistant/Li MUST NOT shift, resize, or reflow the nine factory cards when opened.

Desktop reference mockup discussed for this contract is 1536 x 1024 px. Measurements taken from that mockup are approximate visual-reference measurements only and MUST NOT become canonical implementation constants until verified against the current Desktop code and real viewport.

Reference measurements:

- closed left navigation: approximately 216 px wide
- expanded Assistant/Li history area: approximately 290 px wide
- lower conversation overlay begins at approximately x=289 px
- lower conversation overlay right edge: approximately x=1524 px
- lower conversation overlay width: approximately 1235 px
- lower conversation overlay top edge: approximately y=637 px
- lower conversation overlay bottom edge: approximately y=995 px
- lower conversation overlay height: approximately 358 px
- reference composer area: approximately 1200 x 120 px
- reference conversation-history area: approximately 290 x 510 px

Open behavior is an L-shaped overlay: the left Assistant/Li area expands below the Settings region and the conversation surface overlays the lower Agents area. The `Start work` surface and all nine factory cards remain visible and stationary. The Agents area may be covered while the Assistant/Li surface is open; it MUST NOT be pushed sideways or cause the factory grid to reflow.

Closed behavior restores the normal approximately 216 px navigation without destroying conversation state.

Founder and normal-user presentation MUST be distinct:

- authenticated founder sees `Li` and `Li — Founder Intelligence`
- normal users see `Asistan` when Desktop UI locale is Turkish and `Assistant` when Desktop UI locale is English
- normal users MUST NOT receive a rendered Li tab, Li mode, founder-memory control, or founder-only content
- hiding Li in the client is not an authorization control; founder access MUST also be enforced server-side

Conversation history MUST persist across closing the overlay, navigating to another Desktop surface, and restarting the Desktop application, subject to the applicable retention/deletion policy. Chat history and authorized memory/context are separate data concepts and MUST NOT be conflated.

## Desktop localization and attachment contract

Desktop UI locale is the single presentation-language source for Assistant/Li v1.

- Turkish Desktop UI -> Assistant/Li UI and responses are Turkish
- English Desktop UI -> Assistant/Li UI and responses are English
- changing the Desktop UI locale updates the Assistant/Li presentation language
- Assistant/Li MUST NOT render an independent `TR / EN` language selector
- authorization, policy, approval, budget, cost, UNKNOWN/UNVERIFIED, and other semantic states remain language-independent before localization

Assistant/Li MUST NOT add a separate file-upload/attachment control inside its composer. Existing canonical Desktop file-upload/input mechanisms MUST be reused when an authorized workflow needs files; a second upload authority or duplicate attachment path MUST NOT be introduced.

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

ILAIOS Assistant v1 and Li MUST support Turkish and English through the Desktop UI locale contract above.

There MUST be one authoritative knowledge model, not duplicated Turkish and English knowledge silos.

Canonical product names and security/policy/cost semantics MUST remain consistent across languages. Authorization MUST be language-independent.

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
- Desktop UI locale

Context supplied by browser/client input MUST NOT be trusted as proof of authorization. Server-side authenticated context remains authoritative.

## Cost and paid execution

The Assistant MUST NOT invent prices or label an operation free based on model knowledge.

Paid/external actions must use the existing canonical quote/budget/entitlement path. If the system requires approval before spending, the Assistant may prepare the action but MUST NOT dispatch it before the canonical approval/budget gate allows it.

## Red-team acceptance requirements

The foundation is not DONE until implementation and tests prove at minimum:

- founder principal accepted for Li
- non-founder principal rejected from Li
- normal user cannot retrieve founder memory
- normal-user UI does not render Li/founder controls
- cross-tenant retrieval rejected
- cross-project retrieval rejected
- cross-workload evidence/result reuse rejected where workload binding is required
- prompt text cannot elevate user to founder
- client-forged screen/context cannot elevate authorization
- Desktop locale changes presentation language without changing authorization outcome
- no independent Assistant/Li language selector exists in v1
- no duplicate Assistant/Li attachment/upload path exists
- opening Assistant/Li does not shift/reflow the nine factory cards
- Assistant/Li lower overlay may cover Agents but not the factory grid or Start-work surface
- closing/reopening and Desktop restart preserve authorized conversation history
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
