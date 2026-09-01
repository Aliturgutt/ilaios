# ILAIOS — PRODUCT REQUIREMENTS

**Document Type:** Canonical Product Requirements Document  
**Format:** GitHub Markdown  
**Status:** Canonical Baseline v1.0 — Pending Repository Publication  
**Architecture Authority:** `SYSTEM_ARCHITECTURE.md`  
**Autonomous Execution View:** `AUTONOMOUS_NODE_ARCHITECTURE.md`  
**Repository Orientation:** `README.md`  
**Core Product Principle:** **SIGN IN → ONE PROMPT → VERIFIED FINISHED PRODUCT**

> This document defines **what the ILAIOS product must do and what experience it must provide**. It does not define implementation details, repository paths, deployment topology, or current implementation status. Those belong to downstream canonical documents.

---

# 00. Purpose

ILAIOS is a governed AI operating system whose product promise is:

```text
SIGN IN
   │
   ▼
ONE PROMPT
   │
   ▼
GOVERNED AUTONOMOUS EXECUTION
   │
   ▼
VERIFIED FINISHED PRODUCT
```

The purpose of ILAIOS is not to expose a collection of AI tools.

The purpose is to let a user express an outcome and have ILAIOS own the governed path from intent to verified result.

Example:

```text
"Build a premium website for my furniture company."
```

The expected product experience is not:

```text
Choose model
Choose agent
Choose skill
Choose provider
Choose browser
Choose coding tool
Choose deployment workflow
Manually combine outputs
```

The expected product experience is:

```text
Authenticate
Describe the desired outcome
Provide indispensable context when needed
Review approvals when required
Receive a verified finished product
```

---

# 01. Product Definition

## 1.1 Product Category

ILAIOS is a:

> **Governed Capability Operating System with native finished-product factories.**

Its product identity includes:

```text
Authoritative Control Plane
Governed Capability Fabric
Native Factories
Authorized Context / Knowledge
Single Routing Truth
Governed Workers
Permissioned Tools
Replaceable Providers
Human Approval Where Required
Independent Evaluation
Bounded Repair
Evidence / Provenance
Verified Final Artifacts and Actions
```

## 1.2 What ILAIOS Is Not

ILAIOS is not:

- a thin wrapper around one LLM;
- an OpenAI wrapper;
- a Claude wrapper;
- a Gemini wrapper;
- an agent chat demo;
- an uncontrolled multi-agent swarm;
- a marketplace of random skills;
- a permanent dependency on a routing proxy;
- a fork of a third-party editor;
- a UI that merely visualizes external tools;
- a product where the user must understand provider infrastructure to complete work.

## 1.3 Product Brain

The product brain remains ILAIOS.

External models, providers, tools, editors, skill repositories, and development actuators are replaceable or reference resources.

The user outcome must remain an ILAIOS product outcome.

---

# 02. Product Vision

ILAIOS should allow an individual, team, or enterprise to move from intent to completed digital work without manually operating the underlying AI/tool stack.

The long-term product experience is:

```text
I need something done
        │
        ▼
I tell ILAIOS the outcome
        │
        ▼
ILAIOS understands the goal
        │
        ▼
ILAIOS plans bounded work
        │
        ▼
ILAIOS obtains authorized context
        │
        ▼
ILAIOS selects capabilities
        │
        ▼
ILAIOS executes under policy
        │
        ▼
ILAIOS validates and repairs
        │
        ▼
ILAIOS proves what happened
        │
        ▼
I receive the finished result
```

The product should feel like one coherent operating system, even when many providers or workers participate internally.

---

# 03. Product Principles

The following are product-level invariants.

## PRIN-001 — One Product Brain

ILAIOS must present one coherent system.

The product must not expose competing planners, routers, runtimes, or provider-specific product identities as separate brains.

## PRIN-002 — Outcome First

Users describe desired outcomes.

The default product flow must not require model/provider/tool selection.

## PRIN-003 — Governed Autonomy

Autonomy must always operate within:

```text
identity
tenant/project scope
permissions
privacy policy
risk policy
budget
approval rules
runtime limits
repair limits
evidence requirements
```

## PRIN-004 — Verified, Not Merely Generated

A generated artifact is not automatically a completed product.

Required validation and acceptance must pass before ILAIOS represents an output as verified/final.

## PRIN-005 — Provider Independence

Providers are replaceable.

The critical product contract must not depend on the continued existence of one named model or external project.

## PRIN-006 — Evidence Is Part of the Product

ILAIOS must be able to explain the governed lineage of material outputs/actions.

## PRIN-007 — Minimal Necessary User Interruption

ILAIOS should infer and proceed where safe and reasonable.

It should ask the user only when:

- essential information is missing;
- policy requires explicit approval;
- the requested outcome is materially ambiguous;
- a risk/cost decision cannot safely be inferred;
- execution reaches a genuine user-dependent blocker.

## PRIN-008 — Fail Closed on Authority

Missing mandatory identity, tenant, permission, privacy, or security context must not be treated as permission to continue.

## PRIN-009 — No Infinite Autonomy

Retry and repair must be bounded.

## PRIN-010 — Core Is Frozen by Default

Product expansion should happen through governed capabilities/factories.

Core evolution requires proof of a platform-wide invariant need.

---

# 04. Target Users

ILAIOS must support multiple product contexts without changing its core operating model.

## 4.1 Individual / Founder

Needs:

- finished websites;
- product assets;
- research;
- code changes;
- documents;
- business automation;
- personal operations.

Primary value:

> One interface replaces multiple manual AI/tool workflows.

## 4.2 Small Team

Needs:

- shared projects;
- controlled access;
- collaborative approvals;
- repeatable workflows;
- reusable knowledge;
- project history.

Primary value:

> Shared execution without losing ownership, policy, or traceability.

## 4.3 Enterprise Team

Needs:

- organizational identity;
- tenant isolation;
- role/permission control;
- SSO;
- policy enforcement;
- approval workflows;
- audit/evidence;
- privacy/data controls;
- cost governance.

Primary value:

> AI execution that can operate under enterprise governance.

## 4.4 Developer / Technical Operator

Needs:

- repository context;
- software changes;
- testing;
- CI-aware execution;
- artifacts;
- reproducibility;
- evidence;
- clear failure states.

Primary value:

> Governed autonomous software work rather than unbounded code generation.

## 4.5 Approver / Administrator

Needs:

- clear action scope;
- risk context;
- approval/rejection;
- auditability;
- tenant/project controls;
- policy visibility.

Primary value:

> Human authority remains explicit where required.

---

# 05. Primary User Promise

The product must make this user journey possible:

```text
USER
  │
  ▼
SIGN IN
  │
  ▼
SELECT / RESOLVE TENANT + PROJECT
  │
  ▼
ENTER ONE NATURAL-LANGUAGE GOAL
  │
  ▼
ILAIOS UNDERSTANDS INTENT
  │
  ▼
GOAL + ACCEPTANCE ARE ESTABLISHED
  │
  ▼
AUTHORIZED CONTEXT IS ACQUIRED
  │
  ▼
BOUNDED PLAN IS CREATED
  │
  ▼
CAPABILITIES / FACTORY ARE RESOLVED
  │
  ▼
EXECUTION IS ADMITTED
  │
  ▼
APPROVAL IS REQUESTED ONLY IF REQUIRED
  │
  ▼
WORK EXECUTES AUTONOMOUSLY
  │
  ▼
OUTPUTS ARE VALIDATED
  │
  ▼
FAILURES ARE REPAIRED WITHIN BOUNDS
  │
  ▼
FINAL RESULT IS INDEPENDENTLY EVALUATED
  │
  ▼
EVIDENCE IS ASSEMBLED
  │
  ▼
RESULT IS DELIVERED / DEPLOYED / PUBLISHED
  │
  ▼
VERIFIED FINISHED PRODUCT
```

---

# 06. Authentication and Identity Requirements

## AUTH-001 — Sign-In Options

The target product must support provider-neutral identity integration for:

- Google;
- Microsoft;
- Outlook/Hotmail via Microsoft identity;
- GitHub;
- Apple;
- email-based account access;
- Microsoft Entra ID;
- Google Workspace;
- generic SAML/OIDC enterprise identity.

Support may be released incrementally, but all methods must normalize into the same ILAIOS identity model.

## AUTH-002 — Canonical Principal

Every authenticated person must resolve to an ILAIOS Principal independent of the external login provider.

## AUTH-003 — Tenant Resolution

Every governed execution must resolve the tenant/organization context when applicable.

## AUTH-004 — Project Resolution

Project-scoped work must execute under explicit project context.

## AUTH-005 — Cross-Tenant Denial

A user authenticated to one tenant must not gain access to another tenant's protected resources without explicit authorized membership/role.

## AUTH-006 — Stronger Authentication

Privileged operations must be able to require stronger assurance/MFA according to policy.

## AUTH-007 — Session Security

Expired or revoked sessions must not remain usable for future privileged execution.

---

# 07. Account, Tenant, and Project Requirements

## ORG-001 — Personal Workspace

A user must be able to operate in an individual workspace.

## ORG-002 — Organization / Tenant

The product must support organization/tenant boundaries.

## ORG-003 — Membership

Tenants must support member identity and role/permission association.

## ORG-004 — Project

Users must be able to organize work by project.

## ORG-005 — Project Context

Project context should bind:

- goals;
- jobs;
- artifacts;
- knowledge;
- evidence;
- approvals;
- relevant configuration.

## ORG-006 — Tenant Isolation

Tenant isolation must persist across:

- operational data;
- knowledge;
- artifacts;
- queues;
- workers;
- logs/evidence;
- provider context.

---

# 08. Prompt and Goal Requirements

## GOAL-001 — Natural-Language Goal

A user must be able to initiate work using a natural-language outcome.

## GOAL-002 — Intent Preservation

ILAIOS must preserve the user's intended outcome when converting the prompt into a structured goal.

## GOAL-003 — Requirements Extraction

ILAIOS should extract:

- objective;
- deliverable;
- constraints;
- preferences;
- risk/data hints;
- required acceptance criteria.

## GOAL-004 — Acceptance Before Finality

The system must establish acceptance criteria before claiming final completion.

## GOAL-005 — Clarification Only When Necessary

When essential information cannot safely be inferred, the system must be able to enter a state equivalent to:

```text
NEEDS_USER_INPUT
```

The product should avoid unnecessary clarification loops.

## GOAL-006 — Material Scope Change

A material user goal change during execution must trigger controlled re-planning.

## GOAL-007 — Outcome Visibility

The user should be able to understand what ILAIOS believes it is producing.

---

# 09. Planning Requirements

## PLAN-001 — Bounded Plan

Every autonomous execution must be backed by a bounded execution plan/DAG.

## PLAN-002 — No Infinite Task Graph

Planning must enforce bounded task count/depth according to product/runtime policy.

## PLAN-003 — Dependency Awareness

Tasks must represent dependencies explicitly.

## PLAN-004 — Inspectability

The product must be able to expose an understandable representation of the active plan when appropriate.

## PLAN-005 — Planning Is Not Permission

A plan alone must not authorize privileged actions.

## PLAN-006 — Cross-Factory Planning

A single goal may compose multiple factories/capabilities under one governed plan.

---

# 10. Context, Memory, and Knowledge Requirements

## KNOW-001 — Authorized Context

Only authorized context may be injected into execution.

## KNOW-002 — Project Memory

ILAIOS should be able to use project-scoped memory/context to improve continuity.

## KNOW-003 — Source Ingestion

Users and authorized systems must be able to add governed knowledge sources.

## KNOW-004 — Source Provenance

Retrieved information must retain source provenance.

## KNOW-005 — Authorization-Aware Retrieval

Retrieval must enforce tenant/principal/project/purpose authorization before content is returned.

## KNOW-006 — No Cross-Tenant Leakage

Knowledge from another tenant must never be returned merely because it is semantically relevant.

## KNOW-007 — Classification

Knowledge units must support data classification metadata.

## KNOW-008 — Grounded Synthesis

Where source-grounded output is required, ILAIOS must preserve linkage between claims and supporting sources.

## KNOW-009 — Knowledge Is More Than Vector Search

RAG product readiness requires authorization, provenance, privacy, evidence, and tenant isolation—not merely embeddings.

---

# 11. Capability Requirements

## CAP-001 — Canonical Capability Identity

ILAIOS must maintain one canonical capability identity system.

## CAP-002 — Capability Discovery

The system must determine which capabilities are required to satisfy a goal.

## CAP-003 — Capability Composition

Multiple capabilities may be composed into a bounded workflow.

## CAP-004 — No Capability Duplication

New product functionality must not create a parallel capability identity for existing authority.

## CAP-005 — Capability Status

The product/engineering system must be able to distinguish the canonical capability maturity stages:

```text
DESIGNED
→ SPECIFIED
→ IMPLEMENTED
→ TESTED
→ VERIFIED
→ DEPLOYED / PRODUCTION
```

`DEPRECATED` is a lifecycle exit state and is not part of the forward maturity sequence.

A capability's registration does not itself prove production readiness.

## CAP-006 — Fine-Grained Capability Growth

Product growth should prefer bounded capabilities/sub-capabilities rather than unnecessary agent proliferation.

---

# 12. Skill Requirements

## SKILL-001 — Approved Skills

Production execution must use approved skills/behavior contracts.

## SKILL-002 — Bounded Authority

A skill cannot request more authority than permitted.

## SKILL-003 — Integrity

Skills should be immutable/content-addressed where applicable.

## SKILL-004 — Traceability

The system must be able to identify which skill/version influenced material execution.

## SKILL-005 — External Skill Safety

Third-party skill definitions cannot become production behavior solely by installation/import.

## SKILL-006 — Skill ≠ Agent

Adding a new skill must not automatically require a new agent.

---

# 13. Agent Requirements

## AGENT-001 — Governed Roles

Agents represent governed roles, not unrestricted autonomous identities.

## AGENT-002 — Authority Boundaries

Agents cannot grant themselves new permissions.

## AGENT-003 — Role Reuse

The product should prefer a controlled set of reusable roles over one agent per micro-task.

## AGENT-004 — Producer / Verifier Separation

Where feasible, final verification should be independent of the producing role.

## AGENT-005 — Agent Visibility

The UI may show agent roles/activity, but agent visualization must not become execution authority.

---

# 14. Factory Requirements

Factories convert goals into finished domain outcomes.

Required factory families include:

- Web Factory;
- Video / Media Factory;
- Software Factory;
- App Factory;
- Research / Data;
- Security Factory;
- Creative / Document;
- Commerce / Growth;
- Personal Operations.

Knowledge/RAG is a governed knowledge capability/plane and may participate across factories.

## FACT-001 — Shared Governance

Every factory must use the shared ILAIOS governance path.

## FACT-002 — Shared Routing

Every factory must use the canonical routing truth.

## FACT-003 — Shared Evidence

Every factory must use the canonical evidence/provenance system.

## FACT-004 — No Mini-Platform

A factory must not create:

- its own Core;
- its own planner authority;
- its own provider router;
- its own policy authority;
- its own hidden execution runtime.

## FACT-005 — Finished Outcome

A factory should produce a usable finished product/action, not merely an intermediate generation.

## FACT-006 — Cross-Factory Composition

Factories must be composable through the shared bounded plan.

---

# 15. Web Factory Product Requirements

## WEB-001 — One-Prompt Website Goal

A user must be able to request a complete website as an outcome.

## WEB-002 — Research

The Web Factory should be able to perform relevant business/product/context research under authorization.

## WEB-003 — Information Architecture

The Web Factory must be able to create coherent site structure.

## WEB-004 — Copy

The Web Factory must be able to produce/organize website copy.

## WEB-005 — Design System

The Web Factory should produce a consistent design system appropriate to the goal.

## WEB-006 — Visual Design

The system must evaluate hierarchy, typography, spacing, composition, interaction, and visual coherence.

## WEB-007 — Implementation

The product must be able to produce deployable website artifacts, not only screenshots/mockups.

## WEB-008 — Browser Validation

Rendered behavior must be tested in a browser-capable validation path.

## WEB-009 — Security Validation

Web artifacts must pass required security checks.

## WEB-010 — Accessibility

Required accessibility criteria must be evaluated.

## WEB-011 — Performance

Required performance criteria must be evaluated.

## WEB-012 — SEO

Where relevant to the goal, technical/content SEO requirements must be evaluated.

## WEB-013 — Visual QA

Visual quality must be independently evaluated before final acceptance.

## WEB-014 — Bounded Repair

Failed web acceptance must enter bounded repair rather than infinite regeneration.

## WEB-015 — Deployment

Production deployment is a governed action and may require approval.

---

# 16. Video / Media Factory Product Requirements

## VIDEO-001 — One-Prompt Video Goal

A user must be able to request a finished video as an outcome.

## VIDEO-002 — Research / Concept

The product must support research and creative concept development.

## VIDEO-003 — Script

The product must support script generation/validation.

## VIDEO-004 — Storyboard / Shot Plan

The system must support structured scene/shot planning.

## VIDEO-005 — Asset Acquisition / Generation

Video execution may use replaceable image/video/audio providers behind governed routing.

## VIDEO-006 — Asset Management

Generated/acquired assets must be tracked as product artifacts.

## VIDEO-007 — Voice / Music / SFX

The system should support governed voice, music, and sound-effect workflows.

## VIDEO-008 — Captions

Caption generation/validation must be supported where applicable.

## VIDEO-009 — Canonical Timeline

The product must maintain one authoritative video composition/timeline lineage.

## VIDEO-010 — Editing

Native editing capabilities must support domain needs without creating a second video engine.

## VIDEO-011 — Render

The product must produce a final rendered artifact.

## VIDEO-012 — Video QA

Visual/video validation must run before acceptance.

## VIDEO-013 — Audio QA

Audio quality/synchronization validation must run where applicable.

## VIDEO-014 — Repair

Failed validation must enter bounded repair.

## VIDEO-015 — Evidence

The final video must retain relevant artifact/provenance/evaluation evidence.

---

# 17. Software Factory Product Requirements

## SW-001 — Repository Understanding

ILAIOS must be able to inspect an authorized code repository and understand relevant stack/architecture context.

## SW-002 — Proposal Before Mutation

Repository intelligence should produce a bounded proposal before governed write actions.

## SW-003 — Scoped Repository Writes

Code mutations require explicit repository/tool authority.

## SW-004 — Test-Aware Changes

Behavioral changes must include or preserve relevant tests.

## SW-005 — Quality Gates

The system must respect repository quality gates.

## SW-006 — Diff Integrity

Changes must be reviewable and bounded to intended scope.

## SW-007 — PR Workflow

Where Git hosting supports it, the product should support branch/PR-based governed delivery.

## SW-008 — No CI Bypass

ILAIOS must not weaken required checks merely to achieve PASS.

## SW-009 — Build ≠ Deployment

Successful build/CI does not automatically mean production deployment.

---

# 18. App Factory Product Requirements

## APP-001 — Application Outcomes

The App Factory must support application-level goals using shared Software Factory capabilities.

## APP-002 — Shared Software Primitives

App Factory must not duplicate core software development primitives.

## APP-003 — Platform-Specific Delivery

App-specific build/package/release requirements may extend the shared workflow.

## APP-004 — Store / Distribution Governance

External store/distribution actions must be treated as governed side effects.

---

# 19. Research / Data Product Requirements

## RD-001 — Authorized Research

Research must occur under project/tenant policy.

## RD-002 — Source Traceability

Research outputs must retain source attribution/provenance.

## RD-003 — Claim Status

The system should distinguish verified claims from unverified material when product behavior depends on factual grounding.

## RD-004 — Reusable Knowledge

Research outputs should be capable of entering the governed Knowledge layer without losing authorization/provenance metadata.

## RD-005 — No Hidden External Brain

External research products may be references but must not become authoritative ILAIOS knowledge runtime by convenience.

---

# 20. Security Factory Product Requirements

## SECFACT-001 — Security Analysis

The product should support bounded security analysis of authorized targets.

## SECFACT-002 — Remediation Proposal

Security findings may produce governed remediation proposals.

## SECFACT-003 — No Independent Security Authority

Security Factory does not replace Policy Gateway.

## SECFACT-004 — Security Mutation Governance

Security-sensitive changes use the same permission/approval/evidence path as other privileged actions.

---

# 21. Personal Operations Product Requirements

## PERS-001 — Personal Workflow Goals

Users should be able to request bounded personal operational outcomes.

## PERS-002 — Connected Service Safety

Connected accounts/services must use scoped permissions.

## PERS-003 — Side-Effect Awareness

Sending messages, changing calendar state, making purchases, or other external actions may require explicit policy/approval.

## PERS-004 — No Credential Exposure

Connected-service credentials must not be exposed to arbitrary agents/workers.

---

# 22. Execution Admission Requirements

## EXEC-001 — Every Privileged Task Is Admitted

Every privileged executable task must pass a policy/admission decision.

## EXEC-002 — Admission Inputs

Admission must account for:

```text
identity
tenant
project
permission
privacy
data classification
residency
tool scope
secret scope
risk
blast radius
budget
quota
approval policy
```

## EXEC-003 — Outcomes

Admission must support:

```text
ALLOW
DENY
REQUIRE_APPROVAL
```

## EXEC-004 — Scoped Grants

Allowed execution must use scoped authorization.

## EXEC-005 — Expiry

Execution authorization must be time/scope bounded where appropriate.

---

# 23. Human Approval Requirements

## HITL-001 — Policy-Driven Approval

Human approval must be triggered by policy/risk, not by arbitrary agent preference.

## HITL-002 — Exact Scope

Approval must identify the exact proposed action.

## HITL-003 — Approve / Reject

Authorized humans must be able to approve or reject.

## HITL-004 — Expiration / Revocation

Approval may expire or be revoked.

## HITL-005 — No Self-Approval

Agents/workers cannot approve their own privileged action.

## HITL-006 — Approval State Visibility

The user must be able to see when work is blocked waiting for approval.

## HITL-007 — Typical Approval Candidates

Policy must be able to require approval for actions such as:

- production deployment;
- DNS changes;
- external spend/payment;
- destructive data changes;
- privileged identity/security changes;
- external communications;
- publishing/release.

---

# 24. Routing and Provider Requirements

## ROUTE-001 — One Routing Truth

All provider/model/resource selection must converge on one canonical `RoutingDecision` truth.

## ROUTE-002 — Policy Before Optimization

Security, authority, privacy, and residency eligibility must be satisfied before optimizing quality/cost/latency.

## ROUTE-003 — Routing Inputs

Routing must be capable of considering:

```text
capability match
authority
privacy / residency
context/modalities
tool requirements
quality floor
provider health
quota
availability
budget/cost
latency
historical reliability
historical quality
deterministic tie-break
```

## ROUTE-004 — Replaceable Providers

The user outcome must not require one permanent provider identity unless the user explicitly requests that provider.

## ROUTE-005 — Local Execution

ILAIOS should support local execution resources where capability/policy allows.

## ROUTE-006 — External Router Boundary

An external routing service may be used as a bounded adapter/resource, but not as the authoritative ILAIOS routing brain.

## ROUTE-007 — Fallback

Provider failure may trigger governed fallback.

Fallback must not bypass security/privacy/budget rules.

## ROUTE-008 — User Abstraction

Provider selection should normally remain invisible to the end user.

---

# 25. Worker Requirements

## WORK-001 — Bounded Task Execution

Workers execute bounded tasks.

## WORK-002 — Worker ≠ Authority

Workers must not own policy, approval, or final job-state authority.

## WORK-003 — Isolation

Worker execution must support isolation appropriate to task risk.

## WORK-004 — Lease / Ownership

The platform must prevent stale/duplicate workers from corrupting authoritative state.

## WORK-005 — Resource Limits

Workers must respect execution/time/resource limits.

## WORK-006 — Cancellation

Authorized job cancellation must prevent new work and reject/fence invalid late results.

---

# 26. Tool Requirements

## TOOL-001 — Permissioned Tools

Tool execution must require explicit allowed scope.

## TOOL-002 — Tool Families

The product may expose governed capabilities backed by:

- browser;
- shell/code;
- files;
- Git/repository;
- external API;
- cloud;
- search;
- media;
- deployment;
- communication.

## TOOL-003 — No Raw Unrestricted Access

Production agents/workers must not receive unrestricted tool access by default.

## TOOL-004 — Secret Scoping

Only required credentials may be made available to the relevant execution.

## TOOL-005 — Untrusted Results

Tool results and external content remain untrusted until validated.

## TOOL-006 — Destructive Operations

Destructive operations may require explicit approval.

---

# 27. Artifact Requirements

## ART-001 — Artifact Identity

Material outputs must have stable artifact identity.

## ART-002 — Versioning

Repairs/changes should create traceable artifact versions.

## ART-003 — Integrity

Artifacts should be integrity-verifiable.

## ART-004 — Ownership

Artifacts must retain tenant/project ownership context.

## ART-005 — Exact Validation Binding

Validation results must refer to the exact artifact version evaluated.

## ART-006 — Artifact Types

Artifacts may include:

- websites;
- code/packages;
- documents;
- images;
- videos;
- audio;
- research reports;
- data outputs;
- configuration;
- deployment packages;
- externally executed action results.

---

# 28. Evidence and Provenance Requirements

## EVID-001 — Continuous Evidence

Material decisions/actions must emit evidence throughout the job, not only at the end.

## EVID-002 — Evidence Coverage

The system should record sufficient evidence for:

```text
goal
plan
policy decision
approval
routing decision
worker execution
tool call
provider call
artifact
validation
repair
cost/usage
checkpoint
delivery
```

## EVID-003 — Acceptance Manifest

A completed product must be able to produce an acceptance/evidence summary showing why it was accepted.

## EVID-004 — Integrity

Evidence must be tamper-evident or integrity-verifiable according to its criticality.

## EVID-005 — Privacy

Evidence must preserve privacy/classification rules.

## EVID-006 — Evidence ≠ Logs

Debug logs are not a substitute for canonical evidence.

---

# 29. State and Progress Requirements

## STATE-001 — Authoritative State

Execution state must be owned by the platform, not client UI.

## STATE-002 — User-Visible Progress

The UI should expose understandable states such as:

```text
Planning
Queued
Running
Waiting for Approval
Validating
Checkpointed
Repairing
Retrying
Final Validation
Done
Failed
Cancelled
```

## STATE-003 — Live Projection

Clients should receive current progress without becoming execution authority.

## STATE-004 — Resume

Long-running work should resume from durable checkpoints where supported.

## STATE-005 — Reconnect

A client reconnect should reconstruct state from authoritative platform data.

---

# 30. Checkpoint / Resume Requirements

## CKPT-001 — Durable Progress

Meaningful completed work should be checkpointable.

## CKPT-002 — Resume Safety

Resume must revalidate relevant current authority/policy.

## CKPT-003 — Grant Expiry

Expired authorization must not be silently reused after resume.

## CKPT-004 — Budget State

Retry/spend state must survive resume.

## CKPT-005 — Artifact Preservation

Already completed immutable artifact/evidence references must survive interruption.

---

# 31. Evaluation Requirements

## EVAL-001 — Step Validation

Individual DAG outputs must be validated before downstream use when required.

## EVAL-002 — Final Evaluation

The final product must undergo independent acceptance evaluation.

## EVAL-003 — Applicable Dimensions

Evaluation may include:

- functional correctness;
- security;
- privacy;
- visual quality;
- audio quality;
- accessibility;
- performance;
- provenance/source grounding;
- policy compliance;
- user acceptance criteria.

## EVAL-004 — Producer Independence

Where feasible, producer and verifier should not be the same decision authority.

## EVAL-005 — Explainable Failure

Evaluation failure should identify actionable failure categories suitable for bounded repair.

---

# 32. Repair Requirements

## REPAIR-001 — Bounded Repair

Repair must enforce hard limits.

At minimum:

```text
max_attempts
max_cost
max_elapsed_time
```

## REPAIR-002 — Failure Classification

Repair begins with failure classification.

## REPAIR-003 — Re-Admission

Repair execution must remain governed.

## REPAIR-004 — No Policy Workaround

Security/policy denial cannot be “repaired” by bypassing the control.

## REPAIR-005 — Exhaustion

When repair limits are exhausted, the product must:

```text
fail safely
or
request user input/approval where appropriate
```

It must not loop indefinitely.

---

# 33. Failure Requirements

The product must explicitly handle:

```text
provider unavailable
provider degraded
quota exhausted
budget exhausted
network failure
tool failure
worker failure
validation failure
policy denial
security violation
privacy violation
tenant-scope violation
approval rejection
approval expiration
artifact integrity failure
timeout
cancelled work
unrecoverable internal failure
```

## FAIL-001 — No Silent Success

A terminal failure must not be presented as completed success.

## FAIL-002 — Actionable User State

User-facing failure should distinguish:

- retrying automatically;
- waiting for user;
- waiting for approval;
- safely failed;
- partially completed;
- externally blocked.

## FAIL-003 — Preserve Evidence

Failure evidence must be preserved.

---

# 34. Delivery / Deployment / Publish Requirements

## DELIV-001 — Artifact vs Side Effect

The product must distinguish:

```text
artifact creation
≠
external publication/deployment/action
```

## DELIV-002 — Governed Side Effects

Production deploy/publish actions pass through the same governance model as other privileged actions.

## DELIV-003 — Approval

Delivery may require human approval.

## DELIV-004 — Verification

Delivery success must be verified where technically possible.

## DELIV-005 — No False Live Claim

Architecture or deployment configuration alone must never cause ILAIOS to claim a service is currently live/healthy.

---

# 35. Client Surface Requirements

Target surfaces may include:

- Web;
- Desktop;
- Mobile;
- API;
- CLI;
- Enterprise Console.

## UI-001 — Consistent Job Model

All surfaces should represent the same canonical jobs/state.

## UI-002 — One-Prompt Entry

Primary surfaces must support a simple natural-language goal entry.

## UI-003 — Progress

Users must be able to see meaningful execution progress.

## UI-004 — Approval

Approvers must be able to inspect and act on approval requests.

## UI-005 — Artifacts

Users must be able to access final and relevant intermediate artifacts according to permission.

## UI-006 — Evidence

Users/administrators must be able to inspect appropriate evidence/provenance.

## UI-007 — Projection Only

No client surface becomes authoritative execution state.

---

# 36. Notifications Requirements

ILAIOS should be able to notify users about meaningful execution states such as:

```text
approval required
user input required
job failed
job completed
delivery completed
policy denied
budget blocked
```

Notifications should avoid unnecessary noise.

Sensitive details must respect permission/privacy constraints.

---

# 37. Security Product Requirements

## SECURITY-001 — Authentication

Protected execution requires authenticated identity.

## SECURITY-002 — Authorization

Every protected action must be authorization-checked.

## SECURITY-003 — Tenant Isolation

Tenant boundary must survive all execution/data layers.

## SECURITY-004 — Prompt / Content Injection Defense

External/untrusted content must not automatically become trusted instruction.

## SECURITY-005 — Tool Permission Firewall

Tool permissions must be bounded.

## SECURITY-006 — Secret Protection

Credentials/secrets must not be exposed broadly.

## SECURITY-007 — DLP / PII

The platform must support data loss prevention and sensitive-data handling.

## SECURITY-008 — Sandbox

Risk-appropriate execution isolation is required.

## SECURITY-009 — Network/Egress Controls

Workers/tools must support bounded network access according to policy.

## SECURITY-010 — Audit Evidence

Material security decisions/actions must produce evidence.

## SECURITY-011 — Fail Closed

Missing critical security context prevents privileged execution.

Detailed controls belong in `SECURITY_ARCHITECTURE.md`.

---

# 38. Privacy Product Requirements

## PRIV-001 — Data Classification

User/project data must support classification.

## PRIV-002 — Purpose Limitation

Protected data usage must be consistent with authorized purpose.

## PRIV-003 — Provider Eligibility

Provider selection must consider privacy/residency constraints.

## PRIV-004 — Data Minimization

Only required context should be shared with tools/providers.

## PRIV-005 — Retention

Data/evidence/artifact retention must support governed lifecycle policies.

## PRIV-006 — Tenant Data Separation

Tenant data must not be commingled in a way that relies solely on UI filtering for protection.

---

# 39. Cost / FinOps Product Requirements

## COST-001 — Budget Awareness

Jobs must be able to operate under budget constraints.

## COST-002 — Cost-Aware Routing

Cost may influence routing after eligibility requirements are satisfied.

## COST-003 — Repair Spend

Repair/retry consumes the same governed budget envelope.

## COST-004 — Spend Approval

External spend may require explicit approval.

## COST-005 — Usage Evidence

Material usage/cost should be attributable to job/project/tenant where applicable.

## COST-006 — No Free-Capacity Assumption

Product reliability must not depend on an assumption that free model/provider capacity will always exist.

---

# 40. Performance and Reliability Requirements

Specific SLO values belong in operational documents and release decisions.

Product-level requirements:

## NFR-REL-001 — Durable Jobs

Long-running jobs must survive client disconnect.

## NFR-REL-002 — Controlled Retry

Transient failures may be retried within bounds.

## NFR-REL-003 — Provider Failure Isolation

A single provider outage should not collapse the ILAIOS product when an eligible alternative exists.

## NFR-REL-004 — State Integrity

Authoritative state must resist stale/duplicate worker updates.

## NFR-REL-005 — Recoverability

Checkpoint-capable work should resume without repeating unnecessary completed work.

## NFR-REL-006 — Graceful Failure

When no eligible route exists, the product must fail clearly rather than fabricate completion.

---

# 41. Quality Requirements

## NFR-QUAL-001 — Acceptance Driven

Quality is measured against explicit acceptance criteria.

## NFR-QUAL-002 — Domain Quality Gates

Factories must define domain-appropriate quality gates.

## NFR-QUAL-003 — Verification Before Final

Required quality evaluation must pass before `VERIFIED FINISHED PRODUCT`.

## NFR-QUAL-004 — Evidence Binding

Quality results must bind to exact artifact versions.

---

# 42. Accessibility Requirements

## A11Y-001 — Product UI

ILAIOS user interfaces should follow recognized accessibility practices appropriate to the target platform.

## A11Y-002 — Generated Products

Factories that produce user-facing interfaces/content must support accessibility evaluation where applicable.

## A11Y-003 — Approval Accessibility

Critical approval workflows must be usable without requiring visual-only interpretation.

---

# 43. Observability Product Requirements

## OBS-001 — Operational Visibility

Administrators/operators must be able to understand:

- current job status;
- failure class;
- provider/worker health signals;
- queue/runtime state;
- latency;
- major cost/usage signals.

## OBS-002 — Privacy

Operational telemetry must not broadly expose protected content/secrets.

## OBS-003 — Evidence Separation

Observability does not replace evidence.

## OBS-004 — No Control Authority

Observability cannot alter execution authority by itself.

Detailed requirements belong in `OBSERVABILITY.md`.

---

# 44. External Reference Product Requirements

ILAIOS may learn from external projects.

Required principle:

```text
REFERENCE
   │
   ▼
REQUIREMENT EXTRACTION
   │
   ▼
ILAIOS SPECIFICATION
   │
   ▼
ILAIOS-NATIVE IMPLEMENTATION
```

## EXT-001 — License Review

Relevant external references must be license-reviewed before code/assets are incorporated.

## EXT-002 — Supply-Chain Review

Third-party runtime dependencies require security/supply-chain review.

## EXT-003 — Independence

Critical product behavior must not depend on a reference project unless explicitly approved as a replaceable dependency.

## EXT-004 — No Second Brain

External routers, agent frameworks, editors, skills, or research apps cannot become alternative execution authority.

## EXT-005 — Provenance

Material adapted ideas/code/assets must retain appropriate provenance.

---

# 45. Provider Independence Acceptance

ILAIOS should pass the conceptual independence test:

```text
Provider/reference disappears
          │
          ▼
Can ILAIOS still preserve:
  - identity?
  - policy?
  - planning?
  - capability definitions?
  - evidence?
  - artifact history?
  - alternative routing where available?
```

A product capability should not be falsely marketed as provider-independent when its only implementation path depends on one unavailable provider.

Provider independence means **architecture and product authority are ILAIOS-owned**, not that every capability always has an equivalent fallback.

---

# 46. Data Model Product Entities

The product requires stable conceptual entities:

```text
User
Account
Principal
Tenant / Organization
Membership
Project
Goal
Job
Task
Agent Run
Tool Call
Provider Call
Approval
Artifact
Artifact Version
Validation
Evidence
Checkpoint
Notification
```

Detailed schemas belong in `DATA_ARCHITECTURE.md`.

---

# 47. API Product Requirements

## API-001 — Programmatic Access

ILAIOS should expose governed APIs for appropriate product capabilities.

## API-002 — Same Authority Model

API clients must use the same identity/policy model as UI clients.

## API-003 — Asynchronous Jobs

Long-running operations must support stable job identity and status retrieval.

## API-004 — Idempotency

Replay-sensitive mutations should support idempotency.

## API-005 — No API Bypass

API access must not create a shortcut around Control Plane governance.

Detailed contracts belong in `API_CONTRACTS.md`.

---

# 48. Cancellation Requirements

## CANCEL-001 — User Cancellation

Authorized users must be able to request cancellation of cancellable jobs.

## CANCEL-002 — Stop New Work

Cancellation must stop future scheduling where possible.

## CANCEL-003 — Late Result Protection

Late worker/provider results must not silently reactivate a cancelled job.

## CANCEL-004 — Evidence

Cancellation and already-incurred usage must remain recorded.

---

# 49. History and Reproducibility Requirements

## HIST-001 — Job History

Users must be able to access permitted historical jobs.

## HIST-002 — Artifact History

Artifact versions must remain traceable according to retention policy.

## HIST-003 — Decision Trace

Material policy/routing/approval/evaluation decisions must be attributable.

## HIST-004 — Reproducibility

Where deterministic reproduction is possible, sufficient configuration/evidence should be retained.

For nondeterministic AI generation, reproducibility means preserving inputs, route/model/provider identifiers, parameters where permitted, outputs, and evidence—not guaranteeing identical regenerated content.

---

# 50. Search and Discovery Requirements

Users should be able to discover authorized:

- projects;
- jobs;
- artifacts;
- evidence;
- knowledge sources;
- completed outputs.

Search must enforce the same tenant/project/permission boundaries as direct access.

---

# 51. Administrative Requirements

Enterprise/administrative capability should support:

- identity/membership management;
- roles/permissions;
- tenant policy;
- provider eligibility policy;
- budget policy;
- approval policy;
- privacy/data controls;
- audit/evidence access;
- operational status appropriate to role.

Administration must not expose secrets unnecessarily.

---

# 52. User Experience Requirements

## UX-001 — Simple Default

The default experience should hide infrastructure complexity.

## UX-002 — Progressive Disclosure

Technical details such as route/provider/worker/evidence should be available when useful without overwhelming normal users.

## UX-003 — State Clarity

The user must be able to distinguish:

```text
working
waiting for approval
waiting for user input
repairing
failed
done
```

## UX-004 — No Fake Progress

Progress indicators must be grounded in authoritative state, not decorative timers.

## UX-005 — Explainable Blocking

When work cannot proceed, the product should explain the actionable reason.

## UX-006 — Finished Product Focus

The primary UX should emphasize outcomes/artifacts, not agent chatter.

---

# 53. Developer Experience Requirements

## DX-001 — Canonical Docs

Developers must be able to identify the canonical architecture and product requirements.

## DX-002 — Stable Contracts

Cross-boundary interfaces should be typed/versioned.

## DX-003 — Bounded Changes

Changes should be reviewable and limited in scope.

## DX-004 — Evidence-Based Claims

Developer tooling/documentation must not claim PASS/deployed/production without current evidence.

## DX-005 — Testability

Capabilities/factories must expose testable contracts.

## DX-006 — No Hidden Architecture

Major authority boundaries must not depend on undocumented implicit behavior.

---

# 54. Product Status Semantics

ILAIOS must use precise status language.

Recommended meanings:

```text
PLANNED
    requirement/design exists

PARTIAL
    some implementation exists, acceptance incomplete

IMPLEMENTED
    code exists for defined scope

VERIFIED
    required tests/evidence for defined scope pass

DEPLOYED
    a deployment action has been evidenced

LIVE_HEALTHY
    current live state has been directly verified
```

These states must not be used interchangeably.

---

# 55. Product Metrics Framework

Exact KPI targets will be defined separately.

The product should be measurable across:

## Outcome

- goal completion rate;
- acceptance pass rate;
- finished-product delivery rate.

## Autonomy

- percentage of jobs completed without avoidable user intervention;
- average required approval count;
- clarification rate.

## Quality

- first-pass validation rate;
- repair success rate;
- regression/failure rate.

## Reliability

- provider fallback success;
- resume/recovery success;
- terminal failure rate.

## Governance

- unauthorized-action denial correctness;
- cross-tenant isolation violations;
- approval enforcement;
- evidence completeness.

## Cost

- cost per completed goal;
- repair/retry cost share;
- provider-routing cost efficiency.

## User Experience

- time from goal to usable result;
- abandoned jobs;
- user acceptance/rejection.

Metrics must not incentivize bypassing safety or quality.

---

# 56. MVP / Baseline Product Definition

The canonical architecture is broader than one release.

A baseline ILAIOS product is considered meaningfully usable when a user can:

```text
authenticate
create/select a project
submit a natural-language goal
receive a bounded plan
execute through governed capabilities
use at least one real finished-product factory
see job state
approve privileged action when required
receive a validated artifact
observe bounded repair on failure
receive evidence/provenance
resume or fail safely
```

The MVP does not need every factory or every provider.

It does require the **single governed operating model**.

---

# 57. Enterprise Readiness Requirements

Enterprise readiness requires more than SSO.

At minimum, the product must support or prove:

```text
tenant isolation
enterprise identity integration
RBAC/ABAC or equivalent governed authorization
MFA/strong-auth policy for privileged action
approval workflows
privacy/DLP controls
secret/key management
provider/privacy policy
evidence/audit
budget governance
failure/recovery
observability
secure deployment architecture
```

Enterprise readiness must be evidence-backed, not marketing-only.

---

# 58. Product Non-Goals

The following are explicitly not product requirements:

- expose every underlying provider to all users;
- let end users manually orchestrate every worker;
- maximize number of agents;
- support unlimited repair;
- guarantee every provider is always available;
- guarantee every task can run for free;
- make UI state authoritative;
- copy third-party products wholesale;
- maintain multiple equivalent Cores/runtimes;
- support arbitrary unreviewed skills;
- bypass approval to make automation “more autonomous”;
- claim live deployment based solely on infrastructure code;
- redesign architecture independently per factory.

---

# 59. Red Lines

The following product behavior is unacceptable:

```text
Factory → Provider bypass
Factory → hidden router
Agent → self-granted permission
Agent → self-approval
Worker → authoritative job-state ownership
UI → execution authority
Cross-tenant retrieval
Unbounded retry / repair
Secret exposure to broad context
Unvalidated final artifact labeled verified
Provider-specific dependency presented as ILAIOS authority
Parallel planner/router/capability registry
Security denial silently worked around
```

---

# 60. End-to-End Product Acceptance Scenario — Website

User request:

```text
"Build a premium website for my furniture company."
```

Expected product behavior:

```text
1. Authenticate user.
2. Resolve tenant/project.
3. Capture the goal.
4. Derive explicit acceptance criteria.
5. Retrieve only authorized business/brand context.
6. Build a bounded plan.
7. Resolve Web Factory capabilities.
8. Apply execution admission/policy.
9. Request approval only if a privileged side effect requires it.
10. Route models/tools/providers internally.
11. Research and create IA/copy/design/build output.
12. Run browser/security/accessibility/performance/SEO/visual checks as applicable.
13. Record evidence and checkpoints.
14. Repair bounded failures.
15. Run final independent evaluation.
16. Produce a deployable website artifact.
17. If production deployment is requested, govern that as a privileged action.
18. Deliver final artifact + evidence.
```

Acceptance fails if:

- the user must manually orchestrate providers to complete the normal flow;
- the site is marked verified without required QA;
- production deployment bypasses policy;
- evidence cannot identify the accepted artifact version.

---

# 61. End-to-End Product Acceptance Scenario — Video

User request:

```text
"Create a 60-second launch video for my new product."
```

Expected product behavior:

```text
1. Authenticate and resolve project.
2. Establish goal/duration/style constraints.
3. Establish acceptance criteria.
4. Research authorized context.
5. Plan concept/script/storyboard/shots.
6. Select Video Factory capabilities.
7. Admit execution.
8. Route media/model resources.
9. Generate/acquire assets.
10. Produce voice/music/SFX/captions when required.
11. Compose canonical timeline.
12. Edit/mix/render.
13. Perform video/audio QA.
14. Record evidence.
15. Repair bounded failures.
16. Independently evaluate final result.
17. Deliver final rendered video + evidence.
```

Acceptance fails if:

- a second video runtime becomes authority;
- render success alone is treated as quality PASS;
- final evidence does not identify the output/artifact lineage.

---

# 62. End-to-End Product Acceptance Scenario — Software Change

User request:

```text
"Add this feature to my repository and prepare it for review."
```

Expected product behavior:

```text
1. Authenticate.
2. Resolve repository/project authority.
3. Inspect repository safely.
4. Create bounded change proposal.
5. Resolve Software Factory capabilities.
6. Admit write authority.
7. Create governed code change.
8. Run tests/static checks.
9. Inspect diff.
10. Record evidence.
11. Repair bounded failures.
12. Produce reviewable branch/PR artifact where applicable.
```

Acceptance fails if:

- read-only repository intelligence silently mutates source;
- required checks are weakened;
- write scope exceeds grant;
- unrelated changes are hidden in the same operation.

---

# 63. Product Requirement Priority Model

Requirements may be prioritized:

```text
P0 — constitutional / security / product identity
P1 — required for reliable finished-product workflows
P2 — major product expansion
P3 — optional enhancement
```

## P0 Categories

- single Control Plane;
- single routing truth;
- identity/tenant boundary;
- policy/admission;
- bounded execution;
- evidence;
- provider replaceability;
- no bypass;
- verified finality;
- bounded repair.

## P1 Categories

- durable state;
- checkpoint/resume;
- approvals;
- real provider adapters;
- Knowledge/RAG authorization;
- factory quality gates;
- observability;
- cost governance.

Specific milestone sequencing belongs in `MILESTONES.md` and `DEPENDENCY_GRAPH.md`.

---

# 64. Requirement Traceability

Every implementation milestone should trace to product requirements.

Recommended traceability form:

```text
Requirement ID
      │
      ▼
Architecture Component
      │
      ▼
Implementation Contract
      │
      ▼
Tests
      │
      ▼
Evidence
      │
      ▼
Milestone Acceptance
```

Example:

```text
ROUTE-001
→ Routing architecture
→ RoutingDecision contract
→ routing consolidation tests
→ route evidence
→ provider-routing milestone PASS
```

---

# 65. Documentation Boundaries

This PRD intentionally does not duplicate downstream detail.

Use:

```text
PRODUCT_REQUIREMENTS.md
    → what the product must do

IMPLEMENTATION_SPEC.md
    → how architecture/product requirements become implementation rules

DEPENDENCY_GRAPH.md
    → dependency and sequencing truth

API_CONTRACTS.md
    → API schemas/contracts

SECURITY_ARCHITECTURE.md
    → security control architecture

DATA_ARCHITECTURE.md
    → data entities/stores/lifecycle

THREAT_MODEL.md
    → adversaries/threats/mitigations

TESTING_AND_EVALUATION.md
    → verification/evaluation strategy

DEPLOYMENT_ARCHITECTURE.md
    → runtime/deployment topology

FINOPS.md
    → budgets/cost governance

ENGINEERING_STANDARDS.md
    → engineering rules

GOVERNANCE.md
    → change/authority governance

MILESTONES.md
    → delivery milestones

ADR/
    → significant architecture decisions

OBSERVABILITY.md
    → logs/metrics/traces/SLO/alerts

FAILURE_RECOVERY.md
    → failure/recovery/rollback/continuity
```

---

# 66. Final Product Formula

```text
USER INTENT
     │
     ▼
GOAL + ACCEPTANCE
     │
     ▼
AUTHORIZED CONTEXT
     │
     ▼
BOUNDED PLAN
     │
     ▼
CAPABILITY RESOLUTION
     │
     ▼
NATIVE FACTORY ORCHESTRATION
     │
     ▼
GOVERNED EXECUTION ADMISSION
     │
     ▼
APPROVAL IF REQUIRED
     │
     ▼
ONE ROUTING TRUTH
     │
     ▼
REPLACEABLE WORKERS / TOOLS / PROVIDERS
     │
     ▼
STEP VALIDATION
     │
     ▼
EVIDENCE + STATE + CHECKPOINT
     │
     ▼
INDEPENDENT FINAL EVALUATION
     │
     ├──── FAIL ───► BOUNDED REPAIR ───► RE-EVALUATION
     │
     ▼ PASS
DELIVERY / DEPLOY / PUBLISH
     │
     ▼
VERIFIED FINISHED PRODUCT
```

---

# 67. Final Product Requirement

The defining ILAIOS requirement is:

> **The user asks for an outcome. ILAIOS owns the governed path from authenticated intent to a verified finished result.**

Supporting product identity:

```text
Providers execute.
Tools actuate.
Workers run.
Agents coordinate.
Skills constrain expertise.
Factories organize domain work.
Knowledge supplies authorized context.
The Control Plane owns authority.
Policy controls risk.
Evidence proves what happened.
Independent evaluation decides whether the result is acceptable.
```

**ILAIOS is the product. The underlying providers are replaceable parts.**
