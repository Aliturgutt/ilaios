# ILAIOS — DEPENDENCY GRAPH

**Document Type:** Canonical Dependency Graph  
**Format:** GitHub Markdown + ASCII dependency diagrams  
**Status:** Canonical Baseline v1.0 — Pending Repository Publication  
**Architecture Authority:** `SYSTEM_ARCHITECTURE.md`  
**Autonomous Execution View:** `AUTONOMOUS_NODE_ARCHITECTURE.md`  
**Product Authority:** `PRODUCT_REQUIREMENTS.md`  
**Implementation Authority:** `IMPLEMENTATION_SPEC.md`  
**Core Principle:** **NO DEPENDENCY BYPASS — NO PARALLEL AUTHORITY**

> This document defines **what depends on what** across ILAIOS documents, platform capabilities, factories, runtime execution, data/evidence planes, maturity gates, and the currently adopted post-v1 workstream graph. It does not replace architecture, implementation specification, milestones, or runtime evidence.

---

# 00. Purpose

ILAIOS must remain one coherent system.

A dependency graph is required so that:

- no capability bypasses a required platform authority;
- no factory creates hidden infrastructure;
- no provider becomes a product authority;
- no implementation begins before its prerequisite contract exists;
- no maturity state is claimed without its prior gates;
- no post-v1 workstream starts by skipping adopted dependencies;
- no document redefines a concern owned elsewhere.

The canonical dependency rule is:

```text
DEPENDENCY
    =
a prerequisite contract,
authority,
capability,
state,
evidence gate,
or implementation condition
that must exist before the dependent node can be valid.
```

A dependency is **not** merely a suggested sequence.

---

# 01. Dependency Semantics

This document uses the following dependency classes.

## 01.1 Constitutional Dependency

A node cannot exist correctly without the upstream platform invariant.

Example:

```text
Provider Routing
    depends on
Policy / Governance
```

because routing may choose only among permitted resources.

## 01.2 Contract Dependency

A component consumes a canonical contract produced upstream.

Example:

```text
Worker
    depends on
ExecutionGrant
```

## 01.3 Runtime Dependency

A task cannot execute until an upstream runtime state or resource exists.

Example:

```text
Worker Execution
    depends on
WorkerLease
```

## 01.4 Data Dependency

A component requires an authoritative data plane or scoped record.

Example:

```text
Authorized Retrieval
    depends on
Principal + Tenant + Project context
```

## 01.5 Governance Dependency

A privileged action requires policy or approval.

Example:

```text
Production Deployment
    depends on
Execution Admission
    + optional Approval
```

## 01.6 Evidence Dependency

A maturity/release claim requires evidence from prior stages.

Example:

```text
VERIFIED
    depends on
TESTED
    + independent acceptance evidence
```

## 01.7 External Owner Gate

A dependency cannot be autonomously satisfied by runtime code and requires an authorized owner/account action.

Example:

```text
Store Publication
    depends on
Developer Account / Store Approval
```

---

# 02. Global Dependency Invariants

The following are hard rules:

```text
NO second Core
NO second Control Plane
NO second Planner authority
NO second Capability Registry
NO second Agent Runtime authority
NO second Policy authority
NO second RoutingDecision truth
NO second Evidence / Provenance truth
NO factory-specific hidden runtime
NO direct factory → provider bypass
NO direct worker → unrestricted tool bypass
NO client → authoritative state bypass
NO cross-tenant context shortcut
NO production side effect without required admission
NO VERIFIED without TESTED + acceptance evidence
NO DEPLOYED / PRODUCTION without VERIFIED
```

---

# 03. Canonical Document Dependency Graph

The canonical documentation set is dependency-ordered.

```text
SYSTEM_ARCHITECTURE.md
        │
        ├──────────────► AUTONOMOUS_NODE_ARCHITECTURE.md
        │
        ├──────────────► README.md
        │
        ▼
PRODUCT_REQUIREMENTS.md
        │
        ▼
IMPLEMENTATION_SPEC.md
        │
        ▼
DEPENDENCY_GRAPH.md
        │
        ├──────────────► API_CONTRACTS.md
        ├──────────────► SECURITY_ARCHITECTURE.md
        ├──────────────► DATA_ARCHITECTURE.md
        ├──────────────► THREAT_MODEL.md
        ├──────────────► TESTING_AND_EVALUATION.md
        ├──────────────► DEPLOYMENT_ARCHITECTURE.md
        ├──────────────► FINOPS.md
        ├──────────────► ENGINEERING_STANDARDS.md
        ├──────────────► GOVERNANCE.md
        ├──────────────► MILESTONES.md
        ├──────────────► ADR/
        ├──────────────► OBSERVABILITY.md
        └──────────────► FAILURE_RECOVERY.md
```

## 03.1 Document Responsibilities

```text
SYSTEM_ARCHITECTURE.md
    defines system authority and boundaries

AUTONOMOUS_NODE_ARCHITECTURE.md
    visualizes authoritative node connections

README.md
    orients repository users

PRODUCT_REQUIREMENTS.md
    defines product behavior/outcomes

IMPLEMENTATION_SPEC.md
    translates architecture/product into implementation rules

DEPENDENCY_GRAPH.md
    defines prerequisite relationships

API_CONTRACTS.md
    defines interface schemas

SECURITY_ARCHITECTURE.md
    defines control architecture

DATA_ARCHITECTURE.md
    defines entities/stores/lifecycle

THREAT_MODEL.md
    defines threats and mitigations

TESTING_AND_EVALUATION.md
    defines validation/evaluation obligations

DEPLOYMENT_ARCHITECTURE.md
    defines runtime deployment topology

FINOPS.md
    defines cost/budget governance

ENGINEERING_STANDARDS.md
    defines engineering discipline

docs/governance/GOVERNANCE.md
    defines change/authority governance

MILESTONES.md
    defines delivery units and acceptance

ADR/
    records significant architecture decisions

OBSERVABILITY.md
    defines logs/metrics/traces/SLO/alerts

FAILURE_RECOVERY.md
    defines recovery/rollback/continuity
```

No downstream document may silently redefine an upstream authority.

---

# 04. Target Truth vs Current Reality

Dependency truth has two distinct dimensions.

```text
TARGET TRUTH
    = canonical architecture + specifications + dependency rules

CURRENT REALITY
    = current code + tests + CI + runtime + deployment evidence
```

Therefore:

```text
Architecture says "A must depend on B"
        │
        ▼
Implementation must prove A actually depends on B
        │
        ▼
Tests/evidence prove bypass is impossible
```

Status or roadmap prose cannot prove this relationship by itself.

---

# 05. Constitutional Platform Dependency Graph

At the highest level:

```text
                    ILAIOS CONSTITUTIONAL CORE
                              │
                              ▼
                    Authoritative Control Plane
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
 Identity/Tenant         Goal / State        Evidence Primitives
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
                  Governed Platform Capabilities
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
       Policy              Runtime             Knowledge
          │                   │                   │
          ├───────────────┐   │   ┌───────────────┤
          │               │   │   │               │
          ▼               ▼   ▼   ▼               ▼
       Routing          Agents Scheduler       Research
          │               │     │
          └───────────────┼─────┘
                          ▼
                       Factories
                          │
                          ▼
                 Governed Execution
                          │
                          ▼
                  Replaceable Resources
```

Core is not a dumping ground for every dependency.

---

# 06. Canonical Capability Registry Graph

The active capability namespace is:

```text
ilaios.capability.*
```

The current registry defines these canonical capability identities and dependencies.

---

# 07. Platform Capability Dependencies

```text
ilaios.capability.core
    │
    ├──► ilaios.capability.identity-tenant
    │        │
    │        ├──► ilaios.capability.policy-governance
    │        │        │
    │        │        ├──► ilaios.capability.agent-governance
    │        │        └──► ilaios.capability.provider-routing
    │        │
    │        ├──► ilaios.capability.privacy-dlp
    │        └──► ilaios.capability.secrets-crypto
    │
    ├──► ilaios.capability.workflow-runtime
    │        │
    │        └──► ilaios.capability.observability-operations
    │
    ├──► ilaios.capability.evidence-audit
    │
    ├──► ilaios.capability.code-intelligence
    │
    └──► ilaios.capability.knowledge
```

## 07.1 Core

```text
ilaios.capability.core
dependencies: none
```

Owns platform-wide invariants only.

## 07.2 Identity / Tenant

```text
ilaios.capability.identity-tenant
depends on:
    ilaios.capability.core
```

## 07.3 Workflow Runtime

```text
ilaios.capability.workflow-runtime
depends on:
    ilaios.capability.core
```

## 07.4 Policy / Governance

```text
ilaios.capability.policy-governance
depends on:
    ilaios.capability.identity-tenant
```

Policy cannot correctly evaluate a request without identity/tenant scope.

## 07.5 Evidence / Audit

```text
ilaios.capability.evidence-audit
depends on:
    ilaios.capability.core
```

## 07.6 Privacy / DLP

```text
ilaios.capability.privacy-dlp
depends on:
    ilaios.capability.identity-tenant
```

## 07.7 Secrets / Cryptography

```text
ilaios.capability.secrets-crypto
depends on:
    ilaios.capability.identity-tenant
```

## 07.8 Observability / Operations

```text
ilaios.capability.observability-operations
depends on:
    ilaios.capability.workflow-runtime
```

## 07.9 Agent Governance

```text
ilaios.capability.agent-governance
depends on:
    ilaios.capability.policy-governance
```

## 07.10 Provider Routing

```text
ilaios.capability.provider-routing
depends on:
    ilaios.capability.policy-governance
```

## 07.11 Code Intelligence

```text
ilaios.capability.code-intelligence
depends on:
    ilaios.capability.core
```

## 07.12 Knowledge

```text
ilaios.capability.knowledge
depends on:
    ilaios.capability.core
```

The registry dependency is minimal. Production-ready RAG has additional security/runtime dependencies defined later in this document.

---

# 08. Factory Capability Dependency Graph

Current canonical factory identities form this dependency graph:

```text
workflow-runtime ───────────────┬──────────────┬──────────────┐
                               │              │              │
                               ▼              ▼              ▼
                        Web Factory      Software Factory   Creative Document
                               │              │              │
                               │              ▼              │
                               │          App Factory        │
                               │                             │
                               ├─────────────────────────────┤
                               │                             │
                               ▼                             ▼
                        Personal Operations           Commerce / Growth

provider-routing ───────► Video / Media Factory
evidence-audit ─────────► Video / Media Factory

policy-governance ──────► Web Factory
policy-governance ──────► Software Factory

agent-governance ───────► Security Factory
evidence-audit ─────────► Security Factory

knowledge ──────────────► Research / Data Factory
```

---

# 09. Exact Factory Dependencies

## 09.1 Video / Media Factory

```text
ilaios.capability.video-media-factory
depends on:
    ilaios.capability.workflow-runtime
    ilaios.capability.evidence-audit
    ilaios.capability.provider-routing
```

## 09.2 Web Factory

```text
ilaios.capability.web-factory
depends on:
    ilaios.capability.workflow-runtime
    ilaios.capability.policy-governance
```

## 09.3 Software Factory

```text
ilaios.capability.software-factory
depends on:
    ilaios.capability.workflow-runtime
    ilaios.capability.policy-governance
```

## 09.4 Security Factory

```text
ilaios.capability.security-factory
depends on:
    ilaios.capability.agent-governance
    ilaios.capability.evidence-audit
```

## 09.5 App Factory

```text
ilaios.capability.app-factory
depends on:
    ilaios.capability.software-factory
```

App Factory must reuse shared software primitives.

## 09.6 Research / Data

```text
ilaios.capability.research-data
depends on:
    ilaios.capability.knowledge
```

## 09.7 Creative / Document

```text
ilaios.capability.creative-document
depends on:
    ilaios.capability.workflow-runtime
```

## 09.8 Commerce / Growth

```text
ilaios.capability.commerce-growth
depends on:
    ilaios.capability.workflow-runtime
```

## 09.9 Personal Operations

```text
ilaios.capability.personal-operations
depends on:
    ilaios.capability.workflow-runtime
```

---

# 10. Registry Dependency vs Runtime Dependency

A capability registry dependency is not always the complete runtime dependency.

Example:

```text
Registry:
Research / Data
    → Knowledge

Runtime:
Research / Data
    → Knowledge
    → Identity/Tenant authorization
    → Privacy/DLP
    → Policy
    → Evidence
    → Governed Runtime
```

The registry expresses canonical capability lineage.

Runtime execution must also satisfy all applicable cross-cutting authorities.

---

# 11. Cross-Cutting Dependency Planes

Every privileged execution can depend on several cross-cutting planes simultaneously.

```text
                         EXECUTABLE TASK
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
 Identity/Tenant          Policy/Security          Budget/FinOps
        │                      │                      │
        ├──────────────┬───────┴──────────┬───────────┤
        │              │                  │           │
        ▼              ▼                  ▼           ▼
 Privacy/DLP       Secrets/Crypto      Evidence   Observability
        │              │                  │           │
        └──────────────┴──────────┬───────┴───────────┘
                                  ▼
                         GOVERNED EXECUTION
```

These are not optional serial decorations.

They are cross-cutting dependencies.

---

# 12. Canonical Request Dependency Chain

The target execution dependency order is:

```text
AUTHENTICATED USER
      │
      ▼
PRINCIPAL + TENANT + PROJECT
      │
      ▼
PROMPT / REQUEST
      │
      ▼
MINIMAL AUTHORIZED PRE-PLAN CONTEXT
      │
      ▼
GOAL + ACCEPTANCE CRITERIA
      │
      ▼
BOUNDED EXECUTION PROPOSAL
      │
      ▼
CAPABILITY / FACTORY RESOLUTION
      │
      ▼
FACTORY / DOMAIN DAG
      │
      ▼
CONTROL PLANE VALIDATION
      │
      ▼
TASK EXECUTION LOOP
```

No downstream node can assume an upstream contract that was never produced.

---

# 13. Task Execution Dependency Chain

Every task depends on:

```text
TaskEnvelope
    │
    ▼
Execution Admission
    │
    ▼
Approval Decision if Required
    │
    ▼
Task-Scoped Authorized Context
    │
    ▼
RoutingDecision
    │
    ▼
Queue / Scheduler
    │
    ▼
WorkerLease + Fencing
    │
    ▼
Worker
    │
    ▼
Skill / Tool Gateway / Provider Adapter
    │
    ▼
Step Output
    │
    ▼
Validation
    │
    ▼
Evidence + State Update
    │
    ▼
Checkpoint
```

---

# 14. Execution Admission Dependencies

Execution Admission depends on:

```text
PrincipalContext
TenantContext
ProjectContext
TaskEnvelope
CapabilityRequirement
Data Classification
Risk Classification
Budget Context
Tool/Resource Request
```

It may also depend on:

```text
privacy/residency policy
DLP policy
secret policy
organization policy
project policy
provider policy
approval policy
```

Output:

```text
Allow
Deny
RequireApproval
```

or a scoped `ExecutionGrant`.

---

# 15. Human Approval Dependencies

Approval is only meaningful after the exact proposed action exists.

```text
Task / Proposed Action
        │
        ▼
Policy Decision
        │
        ▼
RequireApproval
        │
        ▼
ApprovalRequest
        │
        ▼
Authorized Human
        │
        ▼
ApprovalDecision
        │
        ▼
Scoped ExecutionGrant
```

Therefore:

```text
Approval
does NOT precede
the definition of the exact action being approved.
```

A materially changed action invalidates/requires reevaluation of prior approval.

---

# 16. Routing Dependencies

Canonical routing depends on all eligibility constraints before optimization.

```text
Capability Requirement
        │
        ▼
Authority / Permissions
        │
        ▼
Security / Privacy / Residency
        │
        ▼
Context / Modality Requirement
        │
        ▼
Tool Requirement
        │
        ▼
Quality Floor
        │
        ▼
Provider / Model Health
        │
        ▼
Quota / Availability
        │
        ▼
Budget / Cost
        │
        ▼
Latency
        │
        ▼
Historical Reliability / Quality
        │
        ▼
Deterministic Tie-Break
        │
        ▼
ONE RoutingDecision
```

Cost is not permitted to move ahead of security/privacy eligibility.

---

# 17. Routing Consolidation Dependency

Current routing foundations exist in more than one implementation module.

The target relationship is:

```text
services/runtime/routing.py
            │
            ├──────────────┐
            │              │
            ▼              ▼
   Skill/Authority      Provider
   eligibility          capability
            │              │
            └──────┬───────┘
                   │
                   ▼
             Routing Core
                   ▲
                   │
            ┌──────┴───────┐
            │              │
            ▼              ▼
 services/ai_governance.py
 provider/model registry
 policy/budget/quota/health
            │
            ▼
      ONE RoutingDecision
```

Hard rule:

```text
No third router.
No competing final RouteDecision.
```

---

# 18. Provider Dependency Boundary

Provider calls depend on:

```text
RoutingDecision
    │
    ▼
Approved Adapter
    │
    ▼
Provider Request
    │
    ▼
Provider
```

Providers do not sit above:

- identity;
- policy;
- budget;
- approval;
- artifact acceptance;
- evidence truth.

A provider outage may invalidate one route but not ILAIOS authority.

---

# 19. External Router Boundary

If an external routing system is ever used:

```text
ILAIOS Policy
    │
    ▼
ILAIOS Routing Authority
    │
    ▼
Approved External Routing Adapter
    │
    ▼
External Router
```

Never:

```text
Factory
    │
    ▼
External Router
    │
    ▼
Provider
```

without ILAIOS governance.

---

# 20. Tool Gateway Dependencies

Tool execution depends on:

```text
Worker
  │
  ▼
ToolRequest
  │
  ▼
ExecutionGrant
  │
  ▼
Permission Firewall
  │
  ▼
Scoped Secret Resolution
  │
  ▼
Network / Filesystem Policy
  │
  ▼
Sandbox / Isolation
  │
  ▼
Tool Adapter
  │
  ▼
Tool
```

No worker should receive unrestricted raw tool authority by default.

---

# 21. Repository / Git Dependencies

Repository mutation depends on:

```text
Authorized Repository
        │
        ▼
Repository Analysis
        │
        ▼
Bounded Change Proposal
        │
        ▼
Software Factory
        │
        ▼
Write Admission
        │
        ▼
Scoped Repository Grant
        │
        ▼
Branch / Change
        │
        ▼
Tests / Quality Gates
        │
        ▼
Diff Review
        │
        ▼
PR / Merge Policy
```

Read access does not imply write authority.

---

# 22. Worker Execution Dependencies

Worker execution requires:

```text
Admitted Task
+ RoutingDecision
+ WorkerLease
+ Fencing Token
+ ExecutionGrant
+ Task Inputs
```

Worker result commitment additionally depends on:

```text
lease still valid
job not cancelled
fencing token current
output contract valid
```

A stale worker result cannot become authoritative.

---

# 23. State Dependency Graph

Runtime state must follow validated transitions.

```text
PLANNING
   │
   ▼
QUEUED
   │
   ▼
RUNNING
   │
   ├──────────────► WAITING_FOR_APPROVAL
   │                       │
   │                       ▼
   │                     RUNNING
   │
   ├──────────────► NEEDS_USER_INPUT
   │                       │
   │                       ▼
   │                     RUNNING
   │
   ▼
VALIDATING
   │
   ├──── FAIL ───► REPAIRING ───► RETRYING ───► RUNNING
   │
   ▼ PASS
CHECKPOINTED
   │
   ├──── MORE WORK ───► QUEUED
   │
   ▼
FINAL_VALIDATION
   │
   ├──── FAIL ───► REPAIRING
   │
   ▼ PASS
DONE
```

Cancellation path:

```text
ANY CANCELLABLE ACTIVE STATE
        │
        ▼
CANCEL_REQUESTED
        │
        ▼
CANCELLED
```

---

# 24. Checkpoint Dependencies

Checkpoint creation depends on:

```text
validated durable boundary
+ authoritative state
+ artifact references if any
+ evidence cursor
+ budget/retry state
+ route references
```

Resume depends on:

```text
valid checkpoint
+ integrity verification
+ current identity/policy
+ current budget/retry state
+ valid/reissued grants
+ provider/routing reevaluation when needed
```

Checkpoint does not freeze security policy forever.

---

# 25. Artifact Dependency Graph

```text
Task Inputs
    │
    ▼
Producer
    │
    ▼
Artifact Version
    │
    ▼
Validation
    │
    ├──── FAIL ───► Repair ───► New Artifact Version
    │
    ▼ PASS
Accepted Artifact Version
    │
    ▼
AcceptanceManifest
```

A repaired artifact never silently replaces prior history.

---

# 26. Evidence Dependency Graph

```text
Goal ──────────────────┐
Plan ──────────────────┤
Policy Decision ───────┤
Approval ───────────────┤
RoutingDecision ────────┤
Worker Lease ───────────┤
Tool / Provider Call ───┤
Artifact Version ────────┼────► Evidence Chain
Validation ──────────────┤
Repair ──────────────────┤
Checkpoint ──────────────┤
Cost / Usage ────────────┤
Delivery Decision ───────┘
                              │
                              ▼
                     AcceptanceManifest
```

Final evidence depends on the entire material decision chain.

---

# 27. Final Evaluation Dependencies

Final evaluation requires:

```text
Final Artifact Version
+ GoalSpec
+ AcceptanceCriteria
+ Required Domain Evaluators
+ Security/Privacy gates
+ Evidence references
```

Output:

```text
PASS
or
FAIL + actionable failure classification
```

No final artifact may be labeled verified before this dependency is satisfied.

---

# 28. Bounded Repair Dependencies

Repair depends on:

```text
Evaluation / Validation FAIL
        │
        ▼
Failure Classification
        │
        ▼
Remaining Attempt Budget
        │
        ▼
Remaining Cost Budget
        │
        ▼
Remaining Elapsed-Time Budget
        │
        ▼
RepairProposal
        │
        ▼
Re-Admission
        │
        ▼
Repair Execution
        │
        ▼
Re-Evaluation
```

If any hard repair budget is exhausted:

```text
FAILED
or
NEEDS_USER_INPUT
```

according to policy.

---

# 29. Delivery / Deploy / Publish Dependencies

External side effects are governed DAG nodes.

```text
Accepted Artifact
      │
      ▼
Delivery Action Proposal
      │
      ▼
Admission
      │
      ▼
Approval if Required
      │
      ▼
Tool / Deployment Route
      │
      ▼
External Side Effect
      │
      ▼
Verification
      │
      ▼
Evidence
```

Artifact acceptance does not automatically authorize publication.

---

# 30. Data Plane Dependency Graph

```text
                    Principal / Tenant / Project
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
 Operational Store      Knowledge Store        Artifact Store
        │                     │                     │
        ├──────────────┐      │      ┌──────────────┤
        │              │      │      │              │
        ▼              ▼      ▼      ▼              ▼
 Workflow State      Queue  Retrieval  Evidence Store
        │                                            │
        ▼                                            ▼
 Checkpoints                                    Acceptance
        │                                        Manifests
        │
        ▼
 Runtime Recovery

Secrets / Key Store
        │
        └────► scoped runtime injection only

Observability Stores
        │
        └────► logs / metrics / traces only
```

No one store should silently become all authorities.

---

# 31. Knowledge / RAG Production Dependencies

A production-grade RAG capability depends on more than `knowledge`.

```text
Knowledge / Project Context
        │
        ├────► Identity / Tenant
        ├────► Authorization-Aware Retrieval
        ├────► Privacy / DLP
        ├────► Source Provenance
        ├────► Evidence
        ├────► Governed Runtime
        ├────► Prompt-Injection Defense
        └────► Full Integration / CI
```

Therefore:

```text
Embeddings
+ Vector Store
≠
Production RAG
```

---

# 32. Web Factory Runtime Dependencies

Web Factory runtime depends on:

```text
Goal + Acceptance
        │
        ▼
Authorized Context / Research
        │
        ▼
Web Factory
        │
        ├────► Workflow Runtime
        ├────► Policy / Governance
        ├────► Routing when AI/provider needed
        ├────► Tool Gateway
        ├────► Artifact Store
        ├────► Evidence
        └────► Evaluation
```

Domain chain:

```text
Research
→ Information Architecture
→ Copy
→ Design System
→ Visual Design
→ Build
→ Browser QA
→ Security QA
→ Accessibility
→ Performance
→ SEO
→ Visual QA
→ Acceptance
→ Deployment Validation
```

---

# 33. Video / Media Factory Runtime Dependencies

```text
Video Factory
    ├────► Workflow Runtime
    ├────► Provider Routing
    ├────► Evidence
    ├────► Artifact Store
    ├────► Media Tools
    └────► Independent Evaluation
```

Domain chain:

```text
Research
→ Concept
→ Script
→ Storyboard
→ Shot Plan
→ Generation / Acquisition
→ Assets
→ Voice / Music / SFX / Captions
→ Canonical Timeline
→ Editing
→ Mix
→ Render
→ Video QA
→ Audio QA
→ Acceptance
```

No second video runtime is permitted.

---

# 34. Software Factory Runtime Dependencies

```text
Software Factory
    ├────► Workflow Runtime
    ├────► Policy / Governance
    ├────► Code Intelligence
    ├────► Repository Tool Gateway
    ├────► Test / CI Gates
    ├────► Evidence
    └────► Independent Review
```

Domain chain:

```text
Repository Analysis
→ Change Proposal
→ Write Admission
→ Scoped Change
→ Tests
→ Static/Security Checks
→ Build
→ Diff Review
→ PR / Review Artifact
```

---

# 35. App Factory Dependencies

```text
App Factory
    │
    ▼
Software Factory
    │
    ├────► platform packaging
    ├────► signing when applicable
    ├────► store metadata
    └────► distribution/release gates
```

App Factory may add platform delivery requirements but cannot duplicate Software Factory authority.

---

# 36. Research / Data Dependencies

```text
Research / Data
    │
    ▼
Knowledge
    │
    ├────► authorized sources
    ├────► provenance
    ├────► privacy
    └────► evidence
```

Research outputs may feed Knowledge only if authorization/provenance metadata survives.

---

# 37. Security Factory Dependencies

```text
Security Factory
    ├────► Agent Governance
    ├────► Evidence / Audit
    ├────► Policy Gateway for mutation
    └────► Approval when action is privileged
```

Security analysis authority is not permission authority.

---

# 38. Personal Operations Dependencies

```text
Personal Operations
    ├────► Workflow Runtime
    ├────► Identity / Connected Account
    ├────► Tool Gateway
    ├────► Policy / Approval
    └────► Evidence
```

External side effects such as communication/calendar/payment depend on appropriate scoped authorization.

---

# 39. Capability Maturity Dependency Graph

Canonical maturity progression:

```text
DESIGNED
   │
   ▼
SPECIFIED
   │
   ▼
IMPLEMENTED
   │
   ▼
TESTED
   │
   ▼
VERIFIED
   │
   ▼
DEPLOYED / PRODUCTION
```

`DEPRECATED` is a lifecycle exit state, not the next maturity stage.

---

# 40. DESIGNED Dependencies

`DESIGNED` depends on:

```text
responsibility defined
architecture boundary defined
upstream/downstream dependencies identified
authority duplication check
```

---

# 41. SPECIFIED Dependencies

`SPECIFIED` depends on `DESIGNED` plus:

```text
input/output contracts
policy requirements
data requirements
evidence requirements
failure behavior
acceptance criteria
```

---

# 42. IMPLEMENTED Dependencies

`IMPLEMENTED` depends on `SPECIFIED` plus:

```text
code exists
canonical capability identity maps to implementation
no hidden parallel authority
basic behavior demonstrable
```

---

# 43. TESTED Dependencies

`TESTED` depends on `IMPLEMENTED` plus required:

```text
unit tests
contract tests
integration tests
negative-path tests
security/isolation tests where applicable
```

---

# 44. VERIFIED Dependencies

`VERIFIED` depends on `TESTED` plus:

```text
independent acceptance
required security/governance gates
complete evidence
traceability to canonical requirements
```

---

# 45. DEPLOYED / PRODUCTION Dependencies

`DEPLOYED / PRODUCTION` depends on `VERIFIED` plus:

```text
release/deployment execution
valid production configuration
runtime health verification
release/deployment evidence
rollback/recovery knowledge
```

A production definition file alone does not satisfy this dependency.

---

# 46. Product / Implementation Status Semantics

Separate from capability maturity, repository status may use:

```text
PLANNED
PARTIAL
IMPLEMENTED
VERIFIED
DEPLOYED
LIVE_HEALTHY
```

These terms answer a different question.

They must not replace the capability maturity model.

---

# 47. Test Dependency Graph

```text
Implementation
    │
    ▼
Unit Tests
    │
    ▼
Contract Tests
    │
    ▼
Integration Tests
    │
    ▼
Negative / Deny-Path Tests
    │
    ▼
Security / Isolation Tests
    │
    ▼
End-to-End Acceptance
    │
    ▼
Independent Verification
```

Not every component requires every test category, but every omitted category must be justified by scope.

---

# 48. Negative Dependency Proofs

Critical dependencies must be proven both positively and negatively.

Examples:

```text
Tenant B retrieval
    must NOT succeed using Tenant A context

Expired ExecutionGrant
    must NOT execute

Factory direct provider call
    must NOT bypass routing

Skill with excess authority
    must NOT execute

Self-approval
    must NOT produce valid grant

Stale worker lease
    must NOT commit

Cancelled job
    must NOT be revived by late result

Budget exhausted
    must NOT silently route to paid fallback
```

---

# 49. Post-v1 Execution Overlay Boundary

The repository may maintain a post-v1 execution dependency overlay, but this canonical dependency document records **dependency relationships only**.

Mutable workstream states such as:

```text
VERIFIED
SELECTED
DORMANT
ACTIVE
BLOCKED
COMPLETE
```

do not belong to this canonical dependency authority.

Those states belong in:

```text
MILESTONES.md
execution-status records
runtime / CI / deployment evidence
```

This file may define that one workstream depends on another, but it must not claim the current maturity or execution state of that workstream.

---

# 50. Post-v1 Baseline Dependencies

The post-v1 execution overlay may include dependency relationships such as:

```text
RELEASE.R03
    │
    ▼
GOV_BASELINE
    │
    ▼
CAPABILITY_REVALIDATION
    │
    ├──────────────► PRODUCT_SELECTION
    │
    ▼
EXISTING_FACTORY_PROMOTION
```

This section defines only the dependency edges.

Current state assertions belong in `MILESTONES.md` and evidence.

---

# 51. Existing Factory Promotion Dependencies

The bounded promotion chain is:

```text
EXISTING_FACTORY_PROMOTION
        │
        ▼
AGENT_EXECUTOR_E2E
        │
        ▼
RESEARCH_DATA_FACTORY
        │
        ▼
CREATIVE_DOCUMENT_FACTORY
        │
        ▼
COMMERCE_GROWTH_FACTORY
        │
        ▼
PERSONAL_OPERATIONS_FACTORY
        │
        ▼
APP_FACTORY_PLATFORM_BOUNDARY
        │
        ▼
ENTERPRISE_HARDENING
        │
        ▼
FINAL_LINEAGE_REDTEAM
```

This graph defines execution prerequisites only.

Whether any node is currently `DESIGNED`, `IMPLEMENTED`, `VERIFIED`, or otherwise is not owned by this document.

---

# 52. RAG / Knowledge Workstream Dependencies

The RAG / Knowledge workstream depends on:

```text
RESEARCH_DATA_FACTORY ───────────┐
                                │
ENTERPRISE_HARDENING ────────────┼────► RAG_KNOWLEDGE
                                │
FINAL_LINEAGE_REDTEAM ───────────┘
```

Required gates include:

```text
tenant_isolation
authorization_aware_retrieval
source_provenance
privacy_dlp
deterministic_evidence
full_platform_ci
```

These are dependency / acceptance prerequisites.

Whether `RAG_KNOWLEDGE` is currently selected, active, implemented, verified, or deployed belongs to `MILESTONES.md` and current evidence.

---

# 53. Alternative Workstream Dependency Boundary

Alternative workstreams such as:

```text
MOBILE
COMMERCIAL_SAAS
```

may exist in the execution planning model.

This document does not assign mutable states such as:

```text
DORMANT
SELECTED
ACTIVE
BLOCKED
```

to them.

Their current status belongs to milestone/execution-status authority.

---

# 54. External Owner Gates

Some dependency edges terminate at external owner-controlled gates.

Examples:

```text
master branch protection policy
repository license decision
store/developer-account actions for client distribution
payment/provider/account actions for commercial billing
```

These remain valid dependency classes even though their current completion state is external and mutable.

Current completion status must be proven by evidence or tracked in `MILESTONES.md`.

---

# 55. Post-v1 Safety Dependencies

The post-v1 execution model requires these safety dependencies:

```text
repository evidence is truth
deterministic-first
no dependency bypass
no test weakening
no architecture redefinition
no autonomous production promotion
production mutation requires explicit human authorization
```

Scope exclusions or active-workstream choices are mutable execution decisions and therefore do not belong as current-state assertions in this canonical dependency graph.

---

# 56. Dependency Graph Ownership

This file owns:

```text
canonical prerequisite relationships
capability dependency topology
factory prerequisite topology
runtime prerequisite topology
maturity prerequisite topology
current adopted post-v1 dependency overlay
```

It does **not** own:

```text
architecture responsibility definitions
product requirements
implementation details
API field definitions
security controls
data schemas
test implementation details
deployment topology
cost formulas
milestone dates
```

Those belong to their respective canonical documents.

---

# 57. Dependency Change Rules

A dependency may change only through governed review when one of these is true:

```text
canonical architecture changes
contract ownership changes
capability boundary changes
security/privacy requirement changes
runtime/evidence invariant changes
a dependency is proven obsolete
a new hard prerequisite is proven necessary
```

A dependency must not be removed merely because:

- implementation is inconvenient;
- a test is failing;
- a provider is easier to call directly;
- a factory wants faster execution;
- a UI wants immediate control;
- an external project already solves the problem.

---

# 58. Dependency Addition Test

Before adding a dependency, answer:

```text
1. Is it truly required for correctness?
2. Is it constitutional, contract, runtime, data, governance, evidence, or external?
3. Is the dependency already represented elsewhere?
4. Does it create unwanted coupling?
5. Does it make a replaceable provider permanent?
6. Does it create a cycle?
7. Does it create a second authority?
8. Can the same requirement be satisfied through an existing canonical contract?
```

---

# 59. Cycle Rules

Canonical capability and execution dependencies should be acyclic at authority level.

Forbidden cycle:

```text
Policy
  → Router
  → Provider
  → Policy authority
```

Correct:

```text
Policy
  → Router eligibility
  → Provider execution
  → result/health evidence
  → future policy/routing input
```

Feedback data may exist.

Authority cycles may not.

---

# 60. Dependency Cycle Detection

Machine-readable dependency definitions should be validated for:

```text
unique node IDs
known dependencies
acyclic graph
no self-dependency
no orphan required authority
no duplicate canonical identity
```

A cycle is a blocking architecture defect unless explicitly modeled as a non-authoritative feedback loop.

---

# 61. Cross-Factory Dependency Rule

Factories should not hard-depend directly on one another unless the relationship is a canonical product composition.

Prefer:

```text
Factory A
   │
   ▼
Typed Artifact / Capability Contract
   │
   ▼
Control Plane DAG
   │
   ▼
Factory B
```

over:

```text
Factory A
   ─────────► hidden internal call ─────────► Factory B
```

---

# 62. Provider Independence Dependency Rule

A capability may use one provider initially.

But architecture must distinguish:

```text
CAPABILITY
    = ILAIOS-owned behavior contract

PROVIDER
    = one replaceable implementation resource
```

If the only provider disappears, the capability may become temporarily unavailable.

That does not transfer capability ownership to the provider.

---

# 63. Open-Source Reference Dependency Rule

External references are not hard dependencies by default.

Canonical path:

```text
Reference
   │
   ▼
Requirement Extraction
   │
   ▼
ILAIOS Specification
   │
   ▼
ILAIOS-Native Behavior
```

A permanent third-party runtime dependency requires explicit architectural approval, licensing/security review, and a bounded adapter contract.

---

# 64. Dependency Traceability

Every implemented dependency should be traceable:

```text
Product Requirement
      │
      ▼
Architecture Node
      │
      ▼
Dependency Edge
      │
      ▼
Implementation Contract
      │
      ▼
Code
      │
      ▼
Tests
      │
      ▼
Evidence
```

Example:

```text
ROUTE-001
→ Provider Routing architecture
→ Policy Governance → Provider Routing edge
→ RoutingDecision contract
→ routing implementation
→ no-bypass/consolidation tests
→ routing evidence
```

---

# 65. Dependency Evidence Requirements

A dependency edge is strongest when proven by:

```text
typed contract
+ code-level call/ownership boundary
+ test
+ negative bypass test
+ runtime/evidence event
```

Documentation-only edges remain target requirements until implementation evidence exists.

---

# 66. Dependency Review Checklist

For each new capability/factory:

```text
[ ] canonical capability ID exists
[ ] upstream dependencies are declared
[ ] no duplicate authority exists
[ ] input contracts exist
[ ] output contracts exist
[ ] identity/tenant boundary identified
[ ] policy/admission dependency identified
[ ] privacy/DLP dependency identified if applicable
[ ] routing dependency identified if provider/resource selection occurs
[ ] tool gateway dependency identified if side effects occur
[ ] evidence dependency identified
[ ] state/checkpoint dependency identified for long-running work
[ ] evaluation dependency identified
[ ] repair bounds identified
[ ] deployment/approval dependency identified if external side effects occur
[ ] tests prove required edges
[ ] negative tests prove forbidden bypasses
```

---

# 67. Full Canonical Dependency Map

```text
                              SYSTEM_ARCHITECTURE
                                      │
                                      ▼
                            PRODUCT_REQUIREMENTS
                                      │
                                      ▼
                            IMPLEMENTATION_SPEC
                                      │
                                      ▼
                              DEPENDENCY_GRAPH
                                      │
                                      ▼
                           CONSTITUTIONAL CORE
                                      │
                                      ▼
                           AUTHORITATIVE CONTROL
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ▼                       ▼                       ▼
        IDENTITY/TENANT          GOAL / STATE          EVIDENCE PRIMITIVES
              │                       │                       │
              └───────────────┬───────┴───────────────┬──────┘
                              │                       │
                              ▼                       ▼
                       POLICY / GOVERNANCE       WORKFLOW RUNTIME
                              │                       │
              ┌───────────────┼───────────────┐       │
              │               │               │       │
              ▼               ▼               ▼       ▼
      AGENT GOVERNANCE   PROVIDER ROUTING   PRIVACY  SCHEDULER
              │               │               │       │
              └───────────────┼───────────────┴───┬───┘
                              │                   │
                              ▼                   ▼
                      CAPABILITY RESOLUTION   KNOWLEDGE
                              │                   │
                              └──────────┬────────┘
                                         ▼
                                      FACTORIES
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
                   WEB                 VIDEO              SOFTWARE
                                                             │
                                                             ▼
                                                            APP
                    │                    │                    │
                    ├──────────┬─────────┴───────┬────────────┤
                    │          │                 │            │
                    ▼          ▼                 ▼            ▼
                RESEARCH    SECURITY         CREATIVE      PERSONAL /
                  DATA                        DOCUMENT     COMMERCE
                    │
                    └────────────────────┬────────────────────┘
                                         ▼
                              EXECUTION ADMISSION
                                         │
                                         ▼
                              APPROVAL IF REQUIRED
                                         │
                                         ▼
                               ONE RoutingDecision
                                         │
                                         ▼
                              QUEUE / SCHEDULER
                                         │
                                         ▼
                               LEASE / FENCING
                                         │
                                         ▼
                                      WORKER
                                         │
                              ┌──────────┼──────────┐
                              │          │          │
                              ▼          ▼          ▼
                            SKILL    TOOL GATEWAY  PROVIDER
                              │          │          │
                              └──────────┼──────────┘
                                         ▼
                                    STEP OUTPUT
                                         │
                                         ▼
                                     VALIDATION
                                         │
                           ┌─────────────┴─────────────┐
                           │                           │
                           ▼                           ▼
                         FAIL                         PASS
                           │                           │
                           ▼                           ▼
                  FAILURE CLASSIFIER               EVIDENCE
                           │                           │
                           ▼                           ▼
                    BOUNDED REPAIR                STATE UPDATE
                           │                           │
                           └─────────────┬─────────────┘
                                         ▼
                                     CHECKPOINT
                                         │
                                         ▼
                                  NEXT DAG NODE
                                         │
                                         ▼
                                   FINAL ARTIFACT
                                         │
                                         ▼
                             INDEPENDENT EVALUATION
                                         │
                            ┌────────────┴────────────┐
                            │                         │
                            ▼                         ▼
                          FAIL                       PASS
                            │                         │
                            ▼                         ▼
                    BOUNDED REPAIR          ACCEPTANCE MANIFEST
                                                      │
                                                      ▼
                                         GOVERNED DELIVERY /
                                          DEPLOY / PUBLISH
                                                      │
                                                      ▼
                                         VERIFIED FINISHED
                                              PRODUCT
```

---

# 68. Final Dependency Formula

```text
NO AUTHORITY WITHOUT IDENTITY
NO EXECUTION WITHOUT ADMISSION
NO PRIVILEGED ACTION WITHOUT REQUIRED APPROVAL
NO PROVIDER WITHOUT ROUTING
NO TOOL WITHOUT GATEWAY / GRANT
NO WORKER COMMIT WITHOUT VALID LEASE / FENCING
NO FINAL ARTIFACT WITHOUT VALIDATION
NO VERIFIED STATUS WITHOUT INDEPENDENT EVIDENCE
NO DEPLOYED / PRODUCTION WITHOUT VERIFIED
NO FACTORY WITHOUT SHARED PLATFORM AUTHORITIES
NO EXTERNAL REFERENCE AS A SECOND BRAIN
NO DEPENDENCY BYPASS
```

---

# 69. Canonical Dependency Identity

ILAIOS dependency architecture is:

```text
Constitutional Core
        ↓
Governed Platform Capabilities
        ↓
Native Factory Composition
        ↓
Admitted Execution
        ↓
Single Routing Truth
        ↓
Bounded Workers / Tools / Providers
        ↓
Validation / Evidence / State
        ↓
Independent Evaluation
        ↓
Verified Finished Product
```

**A dependency is valid only when it preserves one ILAIOS brain and strengthens explicit authority, isolation, recoverability, and evidence.**
