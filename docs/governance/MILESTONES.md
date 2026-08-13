# ILAIOS — MILESTONES

**Document Type:** Canonical Mutable Milestone & Execution Status Register
**Format:** GitHub Markdown + ASCII dependency/status diagrams
**Status:** Canonical Baseline v1.0 — Mutable by Evidence
**Architecture Authority:** `SYSTEM_ARCHITECTURE.md`
**Product Authority:** `PRODUCT_REQUIREMENTS.md`
**Implementation Authority:** `IMPLEMENTATION_SPEC.md`
**Dependency Authority:** `DEPENDENCY_GRAPH.md`
**API Authority:** `API_CONTRACTS.md`
**Security Authority:** `SECURITY_ARCHITECTURE.md`
**Data Authority:** `DATA_ARCHITECTURE.md`
**Threat Model Companion:** `THREAT_MODEL.md`
**Testing Authority:** `TESTING_AND_EVALUATION.md`
**Deployment Authority:** `DEPLOYMENT_ARCHITECTURE.md`
**FinOps Authority:** `FINOPS.md`
**Engineering Authority:** `ENGINEERING_STANDARDS.md`
**Governance Authority:** `docs/governance/GOVERNANCE.md`
**Core Milestone Principle:** **STATUS IS MUTABLE; ARCHITECTURE IS NOT**

> This document is the canonical mutable execution register for ILAIOS. It records milestone sequencing, current workstream selection, milestone state, entry/exit criteria, evidence requirements, owner-controlled gates, and the next governed execution steps. Unlike architecture/specification documents, this file is intentionally updated as work progresses. A milestone state is valid only for the exact revision/evidence scope that supports it.

---

# 00. Purpose

The canonical architecture defines:

```text
WHAT ILAIOS MUST BE
```

The milestone register defines:

```text
WHAT IS BEING DONE
IN WHAT ORDER
WITH WHAT EVIDENCE
AND WHAT IS CURRENTLY TRUE
```

This distinction is mandatory.

`MILESTONES.md` may contain mutable states such as:

```text
PLANNED
READY
IN_PROGRESS
BLOCKED
NEEDS_OWNER
VERIFIED
DORMANT
DEFERRED
CANCELLED
```

Canonical architecture documents should not contain these as current execution truth.

---

# 01. Scope

This document owns:

- current milestone sequence;
- current primary workstream;
- milestone dependencies;
- milestone readiness;
- milestone state;
- entry criteria;
- exit criteria;
- evidence requirements;
- owner-controlled gates;
- dependency blockers;
- release/promotion checkpoints;
- current execution snapshot;
- next milestone selection;
- dormant/deferred workstreams;
- milestone completion records.

This document does **not** own:

```text
architecture
    → SYSTEM_ARCHITECTURE.md

product requirements
    → PRODUCT_REQUIREMENTS.md

implementation contracts
    → IMPLEMENTATION_SPEC.md

canonical dependency semantics
    → DEPENDENCY_GRAPH.md

security controls
    → SECURITY_ARCHITECTURE.md

testing semantics
    → TESTING_AND_EVALUATION.md

governance rules
    → docs/governance/GOVERNANCE.md
```

---

# 02. Status Truth Rule

Milestone status must follow current evidence.

Authority order for current state:

```text
CURRENT CODE
    │
    ▼
CURRENT TEST RESULTS
    │
    ▼
CURRENT CI
    │
    ▼
CURRENT RUNTIME EVIDENCE
    │
    ▼
CURRENT DEPLOYMENT EVIDENCE
    │
    ▼
MILESTONE STATUS
```

If this file conflicts with stronger evidence:

```text
STRONGER CURRENT EVIDENCE WINS
```

and this file must be updated.

---

# 03. Snapshot Rule

Every current-state section must identify:

```text
snapshot date
repository
branch
revision/commit
evidence source
```

A historical milestone snapshot must never be presented as current without revalidation.

---

# 04. Current Repository Evidence Snapshot

**Snapshot Date:** 2026-08-13
**Repository:** `Aliturgutt/ilaios`
**Default Branch:** `master`
**Verified Master HEAD:** `31b75faf71243b1534d46369286b3f51532e4ccb`
**HEAD Commit:** `Governance: select RAG/Knowledge as next primary workstream`

Primary evidence:

```text
docs/governance/post_v1_dependency_graph.yaml
PR #39
master commit 31b75faf71243b1534d46369286b3f51532e4ccb
```

This section is mutable.

It must be refreshed when master or the adopted execution graph changes.

---

# 05. Current Governed Post-v1 Snapshot

At the snapshot above, the adopted repository execution graph records:

```text
GOV_BASELINE
    = VERIFIED

CAPABILITY_REVALIDATION
    = VERIFIED

EXISTING_FACTORY_PROMOTION
    = VERIFIED

PRODUCT_SELECTION
    = SELECTED

selected workstream
    = RAG_KNOWLEDGE

MOBILE
    = DORMANT_NOT_SELECTED

COMMERCIAL_SAAS
    = DORMANT_NOT_SELECTED
```

These are **current execution-status claims**, not timeless architecture.

---

# 06. Current Factory Promotion Snapshot

The adopted repository evidence records the following promotion chain as `VERIFIED` at the snapshot revision:

```text
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

This is a mutable milestone-history statement tied to the repository snapshot.

---

# 07. Current Primary Workstream

```text
RAG_KNOWLEDGE
```

is the selected primary post-v1 workstream at the verified snapshot.

The adopted graph defines its dependency set as:

```text
FINAL_LINEAGE_REDTEAM
RESEARCH_DATA_FACTORY
ENTERPRISE_HARDENING
```

and requires these gates:

```text
tenant_isolation
authorization_aware_retrieval
source_provenance
privacy_dlp
deterministic_evidence
full_platform_ci
```

---

# 08. Excluded / Separate Workstreams

At the current adopted execution snapshot:

```text
Website
    = separate / excluded from RAG platform workstream

Desktop
    = separate / excluded from RAG platform workstream
```

This means:

```text
RAG work must not silently modify Website or Desktop scope
```

unless a future governed dependency change explicitly authorizes it.

---

# 09. Dormant Workstreams

Current adopted graph records:

```text
MOBILE
    = DORMANT_NOT_SELECTED

COMMERCIAL_SAAS
    = DORMANT_NOT_SELECTED
```

Dormant means:

```text
not the active primary workstream
```

It does **not** mean:

```text
abandoned
rejected forever
architecturally forbidden
```

---

# 10. External Owner Gates

The current adopted graph identifies external owner-controlled gates including:

```text
master branch protection policy
repository license decision
store/developer-account actions for client distribution
payment/provider/account actions for commercial billing
```

These gates cannot be falsely marked complete by repository code alone.

---

# 11. Milestone Status Vocabulary

Canonical milestone execution states:

```text
PLANNED
READY
IN_PROGRESS
BLOCKED
NEEDS_OWNER
VERIFIED
DORMANT
DEFERRED
CANCELLED
```

---

# 12. PLANNED

Definition:

```text
milestone exists
scope defined
not yet ready for execution or not yet started
```

---

# 13. READY

Definition:

```text
dependencies satisfied
entry criteria satisfied
required authority available
execution may begin
```

---

# 14. IN_PROGRESS

Definition:

```text
governed implementation/testing is actively occurring
```

---

# 15. BLOCKED

Definition:

```text
cannot proceed due to technical, evidence, dependency, or external blocker
```

Every blocker should identify:

```text
blocking condition
owner
required resolution
```

---

# 16. NEEDS_OWNER

Definition:

```text
next step requires explicit human/product/owner decision or external account action
```

---

# 17. VERIFIED

Definition:

```text
milestone exit criteria satisfied
required tests PASS
required evidence complete
scope independently verified as required
```

This is a milestone state.

Capability maturity uses the canonical maturity model separately.

---

# 18. DORMANT

Definition:

```text
known workstream intentionally inactive and not selected
```

---

# 19. DEFERRED

Definition:

```text
previously considered work intentionally postponed
```

---

# 20. CANCELLED

Definition:

```text
workstream/milestone explicitly terminated by governance decision
```

Historical evidence remains.

---

# 21. Milestone vs Capability Maturity

Do not confuse milestone status with capability maturity.

Capability maturity:

```text
DESIGNED
→ SPECIFIED
→ IMPLEMENTED
→ TESTED
→ VERIFIED
→ DEPLOYED / PRODUCTION
```

Milestone status:

```text
PLANNED
READY
IN_PROGRESS
BLOCKED
NEEDS_OWNER
VERIFIED
DORMANT
DEFERRED
CANCELLED
```

Example:

```text
Milestone RAG.05 = IN_PROGRESS

Capability knowledge = IMPLEMENTED
```

can both be true.

---

# 22. Milestone Record Contract

Every milestone should define:

```yaml
milestone_id: "RAG.01"
title: "Source and Data Contract"
status: "PLANNED"
dependencies: []
objective: "..."
entry_criteria: []
deliverables: []
required_tests: []
required_evidence: []
exit_criteria: []
forbidden_scope: []
owner_gates: []
```

---

# 23. Milestone Identity

IDs must be stable.

Never reuse an old milestone ID for a different objective.

---

# 24. Milestone Versioning

If milestone meaning changes materially:

```text
record revision
or
supersede with new milestone
```

Do not silently rewrite historical completion meaning.

---

# 25. Milestone Dependency Rule

A milestone may start only when:

```text
all hard dependencies satisfied
```

unless governance explicitly changes the dependency graph.

---

# 26. No Dependency Bypass

Forbidden:

```text
dependency is difficult
→ skip it
```

Correct:

```text
dependency blocked
→ milestone BLOCKED
→ resolve blocker
or
governed dependency change
```

---

# 27. Entry Criteria

Entry criteria answer:

```text
What must be true before work begins?
```

Examples:

```text
upstream capability verified
contract approved
test environment available
owner decision made
```

---

# 28. Exit Criteria

Exit criteria answer:

```text
What must be proven before milestone is VERIFIED?
```

Exit criteria must be:

```text
specific
testable
evidence-bearing
```

---

# 29. Milestone Evidence

Evidence may include:

```text
commit/revision
PR
test run
CI run
artifact hash
validation report
security report
deployment record
owner approval
```

---

# 30. Status Change Rule

A milestone state change requires evidence.

Examples:

```text
PLANNED → READY
    dependency evidence

READY → IN_PROGRESS
    execution started

IN_PROGRESS → VERIFIED
    acceptance evidence

IN_PROGRESS → BLOCKED
    blocker evidence
```

---

# 31. No Status by Assertion

Forbidden:

```text
"looks done"
"probably works"
"code exists"
```

as milestone completion proof.

---

# 32. Revalidation Rule

A previously VERIFIED milestone may require revalidation when:

```text
critical dependency changes
security invariant changes
provider behavior changes
data migration occurs
major architecture changes
```

Historical verification remains historical.

---

# 33. Current High-Level Program Map

```text
V1 BASELINE
    │
    ▼
GOVERNANCE BASELINE
    │
    ▼
CAPABILITY REVALIDATION
    │
    ▼
EXISTING FACTORY PROMOTION
    │
    ▼
FINAL LINEAGE RED-TEAM
    │
    ▼
RAG / KNOWLEDGE
    │
    ▼
RAG ENTERPRISE HARDENING
    │
    ▼
RAG RELEASE / PRODUCTION GATE
    │
    ▼
NEXT WORKSTREAM SELECTION
```

---

# 34. Historical Baseline: RELEASE.R03

The adopted post-v1 dependency graph references:

```text
RELEASE.R03
```

as the prerequisite to governance baseline.

`RELEASE.R03` is treated here as the historical baseline boundary recorded by repository governance evidence.

This document does not independently reconstruct or re-prove that release.

---

# 35. GOV_BASELINE

**Status at Snapshot:** `VERIFIED`

Objective:

```text
synchronize repository truth and governance after v1 baseline
```

Dependency:

```text
RELEASE.R03
```

Current evidence reference:

```text
docs/governance/post_v1_dependency_graph.yaml
```

---

# 36. GOV_BASELINE Exit Criteria

Historical/adopted exit intent:

```text
repository truth synchronized
governance/security baseline present
CI/workflow inventory established
capability maturity view available
owner-controlled gates identified
```

---

# 37. CAPABILITY_REVALIDATION

**Status at Snapshot:** `VERIFIED`

Dependency:

```text
GOV_BASELINE
```

Purpose:

```text
revalidate existing implementation before rewrite or expansion
```

---

# 38. Capability Revalidation Targets

The adopted graph records targets including:

```text
code_intelligence
knowledge_graph
project_manager
web_factory_foundation
software_factory_foundation
privacy_boundary
cryptography_boundary
security_factory_foundation
```

---

# 39. PRODUCT_SELECTION

**Status at Snapshot:** `SELECTED`

Selected:

```text
RAG_KNOWLEDGE
```

The mutable state vocabulary in this document uses `READY/IN_PROGRESS/...`; `SELECTED` is retained here only as the exact historical/current value from the adopted repository graph.

For forward milestone management:

```text
RAG_KNOWLEDGE = current primary workstream
```

---

# 40. EXISTING_FACTORY_PROMOTION

**Status at Snapshot:** `VERIFIED`

Dependency:

```text
CAPABILITY_REVALIDATION
```

Purpose:

```text
promote existing/planned factory capabilities using bounded implementation and fresh E2E evidence
```

---

# 41. FACTORY.01 — Agent Executor E2E

**Repository Snapshot State:** `VERIFIED`

Purpose:

```text
prove named ILAIOS agents can execute bounded governed work
through stable machine IDs and independent verification
```

---

# 42. FACTORY.02 — Research / Data Factory

**Repository Snapshot State:** `VERIFIED`

Dependency:

```text
FACTORY.01
```

Purpose:

```text
bounded Research/Data Factory over existing Knowledge,
Privacy, and Evidence foundations
```

---

# 43. FACTORY.03 — Creative / Document Factory

**Repository Snapshot State:** `VERIFIED`

Dependency:

```text
FACTORY.02
```

---

# 44. FACTORY.04 — Commerce / Growth Factory

**Repository Snapshot State:** `VERIFIED`

Dependency:

```text
FACTORY.03
```

Historical scope constraint:

```text
no billing or paid-provider mutation in the bounded promotion package
```

---

# 45. FACTORY.05 — Personal Operations Factory

**Repository Snapshot State:** `VERIFIED`

Dependency:

```text
FACTORY.04
```

---

# 46. FACTORY.06 — App Factory Platform Boundary

**Repository Snapshot State:** `VERIFIED`

Dependency:

```text
FACTORY.05
```

Historical boundary:

```text
platform-side App Factory boundary
without modifying Desktop, Website, or mobile client implementation
```

---

# 47. FACTORY.07 — Enterprise Hardening

**Repository Snapshot State:** `VERIFIED`

Dependency:

```text
FACTORY.06
```

Purpose:

```text
cross-cutting recovery
isolation
provenance
observability
security
cost gates
```

---

# 48. FACTORY.08 — Final Lineage Red-Team

**Repository Snapshot State:** `VERIFIED`

Dependency:

```text
FACTORY.07
```

Purpose:

```text
final capability/identity/security/regression lineage audit
```

Historical names may appear in provenance, but active canonical identity remains ILAIOS.

---

# 49. RAG_KNOWLEDGE — Primary Program

**Current Workstream:** `RAG_KNOWLEDGE`

**Current Repository Graph State:** `SELECTED`

Dependencies:

```text
FINAL_LINEAGE_REDTEAM
RESEARCH_DATA_FACTORY
ENTERPRISE_HARDENING
```

Required adopted gates:

```text
tenant_isolation
authorization_aware_retrieval
source_provenance
privacy_dlp
deterministic_evidence
full_platform_ci
```

---

# 50. RAG Program Objective

Build a bounded, tenant-isolated, authorization-aware Knowledge/RAG capability over existing ILAIOS platform foundations.

Target product path:

```text
Authorized Source
      │
      ▼
Ingestion
      │
      ▼
Classification / Provenance
      │
      ▼
Knowledge Unit / Chunk / Index
      │
      ▼
Authorization-Aware Retrieval
      │
      ▼
Reranking
      │
      ▼
AuthorizedContext
      │
      ▼
Task / Agent / Factory
      │
      ▼
Grounded Output + Evidence
```

---

# 51. RAG Program Non-Goals

RAG milestones must not:

```text
create a second Control Plane
create a RAG-specific identity authority
create a private router
create factory-owned retrieval authorization
move tenant filtering to client
store secrets in vectors
treat similarity as permission
modify Website/Desktop scope without authorization
```

---

# 52. RAG Milestone Sequence

Recommended governed sequence:

```text
RAG.00  Baseline & Gap Confirmation
RAG.01  Source / Data Contract
RAG.02  Tenant Isolation & Authorization Model
RAG.03  Ingestion & Provenance
RAG.04  Knowledge Unit / Chunk / Index Lifecycle
RAG.05  Embedding / Index Provider Adapter
RAG.06  Retrieval & Reranking
RAG.07  Authorization-Aware Query Path
RAG.08  AuthorizedContext Integration
RAG.09  Privacy / DLP / Injection Hardening
RAG.10  Evaluation & Leakage Red-Team
RAG.11  Full Platform Integration / CI
RAG.12  Recovery / Observability / FinOps
RAG.13  Final RAG Lineage Red-Team
RAG.14  Production Promotion Decision
```

---

# 53. RAG.00 — Baseline & Gap Confirmation

**Status:** `READY`

Reason:

```text
RAG_KNOWLEDGE is selected and its adopted upstream dependencies
are recorded VERIFIED at the current repository snapshot.
```

Objective:

```text
revalidate the exact current RAG/Knowledge implementation surface
before adding new code
```

---

# 54. RAG.00 Entry Criteria

```text
RAG selected as primary workstream
upstream factory promotion chain verified in adopted graph
repository master resolved
current Knowledge implementation inspected
```

---

# 55. RAG.00 Deliverables

```text
current implementation inventory
current tests inventory
current schemas/stores inventory
current provider/index adapters
current security/privacy boundaries
gap list against canonical architecture
exact change ownership map
```

---

# 56. RAG.00 Required Tests

No new capability implementation is required merely to complete baseline.

Required verification:

```text
existing Knowledge-related tests
current platform CI relevant scope
architecture drift scan
```

---

# 57. RAG.00 Exit Criteria

```text
current implemented surface known
gaps classified
no duplicate Knowledge authority planned
RAG.01 exact scope accepted
```

---

# 58. RAG.01 — Source / Data Contract

**Status:** `PLANNED`

Dependency:

```text
RAG.00
```

Objective:

```text
define canonical source/source-version/knowledge-unit contract
```

---

# 59. RAG.01 Deliverables

```text
Source
SourceVersion
KnowledgeUnit
Chunk
classification
tenant/project ownership
retention metadata
provenance
content hash
```

---

# 60. RAG.01 Exit Criteria

```text
contracts specified
schema validation tests
source version immutable semantics
tenant/project fields mandatory
API/data architecture alignment
```

---

# 61. RAG.02 — Tenant Isolation & Authorization Model

**Status:** `PLANNED`

Dependency:

```text
RAG.01
```

Objective:

```text
prove tenant/project/Principal authorization is enforced before retrieval release
```

---

# 62. RAG.02 Deliverables

```text
authorization context
server-side tenant filter
project filter
purpose/classification policy
cross-tenant negative fixtures
```

---

# 63. RAG.02 Required Negative Tests

```text
Tenant A cannot retrieve Tenant B
Project A cannot retrieve protected Project B
client-forged tenant ignored/denied
stale membership denied
```

---

# 64. RAG.02 Exit Criteria

```text
tenant isolation tests PASS
authorization failure is fail-closed
retrieval cannot run without required scope
evidence produced
```

This satisfies part of:

```text
tenant_isolation
authorization_aware_retrieval
```

adopted gates.

---

# 65. RAG.03 — Ingestion & Provenance

**Status:** `PLANNED`

Dependency:

```text
RAG.02
```

Objective:

```text
ingest authorized sources while preserving provenance and classification
```

---

# 66. RAG.03 Pipeline

```text
Authorized Source
      │
      ▼
Source Identity
      │
      ▼
Safety / Parsing
      │
      ▼
Classification
      │
      ▼
Version / Hash
      │
      ▼
Knowledge Unit
      │
      ▼
Provenance
```

---

# 67. RAG.03 Exit Criteria

```text
source identity preserved
source version preserved
classification preserved
content hash stored
provenance trace complete
malformed input safe
```

This addresses:

```text
source_provenance
```

---

# 68. RAG.04 — Knowledge Unit / Chunk / Index Lifecycle

**Status:** `PLANNED`

Dependency:

```text
RAG.03
```

Objective:

```text
define deterministic derived-data lifecycle
```

---

# 69. RAG.04 Deliverables

```text
chunk identity
source-version linkage
index metadata
embedding linkage
delete/update propagation
re-index semantics
```

---

# 70. RAG.04 Exit Criteria

```text
derived units cannot lose tenant/project scope
source update invalidates/rebuilds correct derived data
source deletion propagates
index consistency tests PASS
```

---

# 71. RAG.05 — Embedding / Index Provider Adapter

**Status:** `PLANNED`

Dependency:

```text
RAG.04
```

Objective:

```text
support replaceable embedding/index resources behind ILAIOS-owned contracts
```

---

# 72. RAG.05 Rules

```text
provider != authority
embedding provider cannot decide tenant scope
vector DB cannot be public client authority
provider credentials remain scoped
pricing/usage recorded
```

---

# 73. RAG.05 Exit Criteria

```text
provider adapter normalized
failure behavior defined
usage evidence
provider replaceability
no direct factory/provider bypass
```

---

# 74. RAG.06 — Retrieval & Reranking

**Status:** `PLANNED`

Dependency:

```text
RAG.05
```

Objective:

```text
retrieve and rank eligible knowledge without changing authorization semantics
```

---

# 75. RAG.06 Retrieval Order

```text
Authorization Scope
      │
      ▼
Eligible Knowledge Set
      │
      ▼
Similarity / Search
      │
      ▼
Rerank
      │
      ▼
Authorized Results
```

Not:

```text
search everything
→ filter after model sees it
```

---

# 76. RAG.06 Exit Criteria

```text
retrieval quality tests
stable result contracts
bounded limits
failure handling
provenance retained
```

---

# 77. RAG.07 — Authorization-Aware Query Path

**Status:** `PLANNED`

Dependency:

```text
RAG.06
```

Objective:

```text
make the governed retrieval request path canonical
```

---

# 78. RAG.07 Contract Path

```text
RetrievalRequest
      │
      ▼
PrincipalContext
TenantContext
ProjectContext
Purpose
Classification
      │
      ▼
Policy / Authorization
      │
      ▼
Retrieve
      │
      ▼
RetrievalResult
      │
      ▼
Evidence
```

---

# 79. RAG.07 Exit Criteria

```text
all runtime retrieval uses canonical path
no direct vector DB bypass
all protected retrieval evidence-bearing
negative bypass tests PASS
```

This completes core:

```text
authorization_aware_retrieval
```

gate.

---

# 80. RAG.08 — AuthorizedContext Integration

**Status:** `PLANNED`

Dependency:

```text
RAG.07
```

Objective:

```text
integrate retrieved knowledge into two-phase task-scoped context
```

---

# 81. RAG.08 Context Model

```text
Minimal Authorized Pre-Plan Context
        +
Task-Scoped Authorized Context
```

---

# 82. RAG.08 Exit Criteria

```text
no entire-tenant context dump
task context bounded
artifact/knowledge refs traceable
context hash/reference recorded
expired/stale context handling tested
```

---

# 83. RAG.09 — Privacy / DLP / Injection Hardening

**Status:** `PLANNED`

Dependency:

```text
RAG.08
```

Objective:

```text
make retrieval safe against sensitive-data leakage and indirect prompt injection
```

---

# 84. RAG.09 Controls

```text
classification
DLP
secret detection
data minimization
instruction/data separation
content cannot grant authority
provider eligibility
residency
```

---

# 85. RAG.09 Red-Team Cases

```text
malicious webpage
malicious PDF
malicious repository text
prompt-injected Knowledge Unit
secret-containing source
restricted data sent to ineligible provider
```

---

# 86. RAG.09 Exit Criteria

```text
privacy tests PASS
DLP tests PASS
injection cannot expand authority
provider privacy eligibility enforced
```

This satisfies:

```text
privacy_dlp
```

gate.

---

# 87. RAG.10 — Evaluation & Leakage Red-Team

**Status:** `PLANNED`

Dependency:

```text
RAG.09
```

Objective:

```text
prove retrieval quality and prove forbidden leakage does not occur
```

---

# 88. RAG.10 Quality Metrics

Evaluate:

```text
retrieval precision
retrieval recall
groundedness
citation correctness
source diversity where required
answer completeness
hallucination
```

---

# 89. RAG.10 Security Metrics

Evaluate:

```text
cross-tenant leakage
cross-project leakage
unauthorized existence hints
classification violations
citation/provenance mismatch
poisoned source behavior
```

---

# 90. RAG.10 Exit Criteria

```text
golden dataset PASS
cross-tenant golden isolation PASS
indirect injection tests PASS
independent evaluation PASS
security evidence complete
```

---

# 91. RAG.11 — Full Platform Integration / CI

**Status:** `PLANNED`

Dependency:

```text
RAG.10
```

Objective:

```text
prove RAG integrates through existing ILAIOS Control Plane/runtime
```

---

# 92. RAG.11 Required Integration

```text
Identity/Tenant
Policy
Goal/Job
Knowledge
Routing
Worker
Provider Adapter
Evidence
Artifact/Evaluation
```

---

# 93. RAG.11 Required Gates

Repository-defined applicable gates plus:

```text
unit
contract
integration
tenant negative tests
RAG E2E
architecture no-bypass
```

---

# 94. RAG.11 Exit Criteria

```text
full relevant platform CI PASS
no test weakening
no architecture bypass
E2E evidence complete
```

This addresses:

```text
full_platform_ci
```

---

# 95. RAG.12 — Recovery / Observability / FinOps

**Status:** `PLANNED`

Dependency:

```text
RAG.11
```

Objective:

```text
harden RAG for durable bounded operation
```

---

# 96. RAG.12 Recovery Scope

```text
provider timeout
embedding failure
index unavailable
retrieval timeout
worker crash
checkpoint/resume
source update during job
```

---

# 97. RAG.12 Observability Scope

```text
ingestion latency
retrieval latency
rerank latency
provider failure
authorization denial
DLP trigger
tenant isolation violation
```

---

# 98. RAG.12 FinOps Scope

```text
ingestion cost
embedding cost
storage/index cost
retrieval cost
reranking cost
generation cost
evaluation cost
```

---

# 99. RAG.12 Exit Criteria

```text
bounded retry
bounded cost
recovery tested
observability available
usage attributable
no evidence loss
```

---

# 100. RAG.13 — Final RAG Lineage Red-Team

**Status:** `PLANNED`

Dependency:

```text
RAG.12
```

Objective:

```text
prove end-to-end RAG lineage and no hidden parallel authority
```

---

# 101. RAG.13 Full Lineage

```text
Principal
  │
  ▼
Tenant / Project
  │
  ▼
Source
  │
  ▼
SourceVersion
  │
  ▼
KnowledgeUnit
  │
  ▼
RetrievalRequest
  │
  ▼
Policy
  │
  ▼
RetrievalResult
  │
  ▼
AuthorizedContext
  │
  ▼
Task / Route / Worker
  │
  ▼
Output
  │
  ▼
Validation
  │
  ▼
Evidence
```

---

# 102. RAG.13 Red-Team Questions

```text
Can vector DB be called directly?
Can tenant scope be omitted?
Can poisoned content grant authority?
Can provider bypass routing?
Can deleted source still leak?
Can evidence omit source provenance?
Can retry reset budget?
```

Expected:

```text
NO
```

---

# 103. RAG.13 Exit Criteria

All adopted RAG gates proven:

```text
tenant_isolation
authorization_aware_retrieval
source_provenance
privacy_dlp
deterministic_evidence
full_platform_ci
```

---

# 104. RAG.14 — Production Promotion Decision

**Status:** `PLANNED`

Dependency:

```text
RAG.13
```

Objective:

```text
decide whether the verified RAG scope may be deployed/promoted
```

---

# 105. RAG.14 Entry Criteria

```text
RAG.13 VERIFIED
release artifact/revision fixed
required tests PASS
security review complete
deployment plan
rollback/recovery
FinOps limits
```

---

# 106. RAG.14 Decision Outcomes

```text
APPROVE_FOR_STAGING
APPROVE_FOR_LIMITED_PRODUCTION
APPROVE_FOR_PRODUCTION
REQUIRES_CHANGES
BLOCKED
```

These are release decisions.

They are not current state until recorded with evidence.

---

# 107. RAG.14 Production Evidence

If production promotion occurs, evidence must include:

```text
release revision
artifact/version
deployment target
approval
deployment result
health verification
rollback status
```

---

# 108. RAG Program Completion

RAG program is complete only when:

```text
required scope VERIFIED
and
the selected release/promotion decision is satisfied
```

If production is not authorized, the capability may still be `VERIFIED` without being `DEPLOYED / PRODUCTION`.

---

# 109. Deterministic Evidence Gate

The adopted graph requires:

```text
deterministic_evidence
```

Minimum RAG evidence lineage:

```text
source/version
tenant/project
retrieval request
policy decision
retrieved units
route/provider
output
validation
cost
```

---

# 110. Tenant Isolation Gate

Must prove:

```text
database isolation
Knowledge index isolation
vector retrieval isolation
artifact isolation
evidence isolation
cache isolation
```

for the RAG scope.

---

# 111. Authorization-Aware Retrieval Gate

Required:

```text
server-side authorization
before content release
```

No post-hoc model-only filtering.

---

# 112. Source Provenance Gate

Every retrieved unit must identify:

```text
source_id
source_version_id
content hash
provenance
classification
```

---

# 113. Privacy / DLP Gate

Must prove:

```text
sensitive source handling
provider eligibility
secret/PII minimization
DLP
residency
```

as applicable.

---

# 114. Full Platform CI Gate

Must prove RAG changes do not regress:

```text
Core
Identity
Policy
Routing
Factories
Evidence
Security
```

for impacted scope.

---

# 115. RAG Blocker Classes

Potential blocker types:

```text
ARCHITECTURE
SECURITY
DATA
TEST
PROVIDER
COST
EXTERNAL_OWNER
CI
DEPLOYMENT
```

---

# 116. RAG Stop Conditions

Stop/mark BLOCKED if:

```text
tenant isolation fails
authorization bypass discovered
required evidence cannot be generated
architecture would require second authority
hard budget cannot be enforced
required CI fails
```

---

# 117. RAG Repair Rule

Repair failing implementation within the same milestone.

Do not skip forward.

---

# 118. RAG Dependency Change Rule

If new hard prerequisite discovered:

```text
update canonical dependency graph
through governance
then update milestone sequence
```

Do not silently add hidden prerequisite.

---

# 119. Post-RAG Workstream Selection

After RAG reaches its governed completion point:

```text
revalidate capability matrix
review dormant alternatives
select exactly one next primary workstream
```

unless independent parallel execution is explicitly proven/governed.

---

# 120. Candidate: Mobile Enablement

**Current Status:** `DORMANT`

Not selected in current adopted graph.

If later selected, likely milestone family:

```text
MOBILE.00  Shared Client Architecture Audit
MOBILE.01  Android Project Enablement
MOBILE.02  Auth / Control Plane Connectivity
MOBILE.03  Read-Only Operational Projection
MOBILE.04  Governed Interaction
MOBILE.05  Android Build / Signing Readiness
MOBILE.06  Play Store Owner Gate
MOBILE.07  iOS Enablement
MOBILE.08  TestFlight / App Store Readiness
```

This is future planning, not current execution authority.

---

# 121. Mobile Constitutional Rule

Mobile client remains projection.

It must not move:

```text
Policy
Routing
scheduler
provider secrets
authoritative state
```

into the client.

---

# 122. Candidate: Commercial SaaS

**Current Status:** `DORMANT`

Not selected in current adopted graph.

Possible future milestone family:

```text
SAAS.00 Entitlement Model
SAAS.01 Usage / Quota Metering
SAAS.02 Rate-Limit Integration
SAAS.03 Billing Adapter
SAAS.04 Webhook Reconciliation
SAAS.05 Invoice / Payment Projection
SAAS.06 Failure / Refund / Cancellation
SAAS.07 Security / Privacy / FinOps Verification
SAAS.08 Limited Rollout
```

---

# 123. Commercial SaaS Constitutional Rule

Billing provider is replaceable.

Commercial provider does not become:

```text
identity authority
tenant authority
Policy authority
entitlement truth without ILAIOS-owned contract
```

---

# 124. Candidate: Website Workstream

Website is a separate workstream from current RAG platform scope.

Any current website work must be tracked independently.

It must not be used to claim platform/RAG milestone completion.

---

# 125. Candidate: Desktop Workstream

Desktop is a separate workstream.

Desktop packaging/store readiness is not equivalent to platform RAG progress.

---

# 126. Cross-Workstream Independence Rule

Two workstreams may run concurrently only when:

```text
dependencies independent
file/module ownership bounded
CI isolation understood
no shared authority conflict
governance explicitly permits
```

---

# 127. Workstream Collision

If two workstreams touch:

```text
Core
Policy
Routing
Identity
Evidence
```

treat them as potentially dependent until proven otherwise.

---

# 128. Owner-Controlled Gate: Branch Protection

Milestone status:

```text
NEEDS_OWNER
```

when a required branch-protection change cannot be executed by bounded repository code/tool authority.

Current actual branch-protection state must be verified separately before claiming completion.

---

# 129. Owner-Controlled Gate: Repository License

License selection is an owner/legal governance decision.

Do not infer license from code content.

---

# 130. Owner-Controlled Gate: Store Accounts

External store account tasks may include:

```text
Microsoft Store
Apple Developer / App Store
Google Play
```

Completion requires external platform evidence.

---

# 131. Owner-Controlled Gate: Billing / Payment Accounts

Commercial billing may require:

```text
payment provider account
KYC/business verification
merchant configuration
```

These are external gates.

---

# 132. External Gate Status Rule

Use:

```text
NEEDS_OWNER
BLOCKED
VERIFIED
```

based on real external evidence.

Never guess.

---

# 133. Milestone Evidence Package

A milestone verification package should include:

```text
milestone ID
scope
base revision
head revision
changed files
tests
CI
security checks
artifacts
evidence
known residual risks
exit decision
```

---

# 134. Milestone Completion Record

Conceptual:

```yaml
milestone_id: "RAG.02"
state: "VERIFIED"
scope: "tenant-aware retrieval authorization"
revision: "..."
verified_at: "..."
tests:
  - "..."
ci:
  - "..."
evidence:
  - "..."
residual_risks: []
```

---

# 135. Current-State Update Template

When updating this file:

```markdown
## Repository Evidence Snapshot

Date:
Repository:
Branch:
HEAD:

Evidence:
- ...

Current primary workstream:
- ...

Changed milestone states:
- ...
```

---

# 136. Milestone Status History

Do not erase important historical state transitions.

Optionally maintain:

```text
state history
date
revision
reason
```

for major milestones.

---

# 137. Status Regression

If regression invalidates a milestone:

```text
VERIFIED
→ BLOCKED
```

may be appropriate for current execution state.

Historical verification remains recorded.

---

# 138. Reopened Milestone

A reopened milestone must identify:

```text
reason
triggering revision/incident
required revalidation
```

---

# 139. Milestone Failure

A failed implementation attempt does not automatically cancel milestone.

Use:

```text
IN_PROGRESS
BLOCKED
```

until governance decides otherwise.

---

# 140. Milestone Cancellation

Cancellation requires explicit governance decision.

---

# 141. Milestone Deferment

Deferred work remains known but inactive.

---

# 142. Milestone Parallelism

Parallel tasks inside one milestone are allowed when the DAG proves independence.

---

# 143. Milestone Task DAG

Milestone may contain:

```text
task A
task B
task C
```

with explicit dependencies.

Milestone status is aggregated from governed evidence, not arbitrary percentage.

---

# 144. Progress Percentage

Percentages are optional projections.

They must not replace milestone state.

Avoid false precision such as:

```text
93.7% complete
```

without defined measurement.

---

# 145. Readiness Gate

Before marking READY, confirm:

```text
dependencies
scope
authority
environment
tests
budget where relevant
```

---

# 146. Execution Gate

Before IN_PROGRESS:

```text
task package exists
allowed paths known
forbidden paths known
stop conditions defined
```

---

# 147. Verification Gate

Before VERIFIED:

```text
exit criteria satisfied
required tests PASS
CI PASS where required
evidence complete
no known blocking red-team issue
```

---

# 148. Production Gate

Before `DEPLOYED / PRODUCTION` capability maturity claim:

```text
VERIFIED
deployment action
health verification
deployment evidence
```

---

# 149. Milestone Security Gate

Security-critical milestones require:

```text
threat mapping
negative tests
tenant tests
secret/tool tests as applicable
```

---

# 150. Milestone Data Gate

Data-changing milestones require:

```text
schema
migration
tenant scope
retention/deletion
lineage
```

---

# 151. Milestone API Gate

API-changing milestones require:

```text
contract version
compatibility
consumer tests
```

---

# 152. Milestone FinOps Gate

Paid-resource milestones require:

```text
budget
usage attribution
cost limit
retry/repair economics
```

---

# 153. Milestone Deployment Gate

Deployment-changing milestones require:

```text
target
identity
config
rollback
verification
```

---

# 154. Milestone Documentation Gate

Update affected canonical docs where normative behavior changes.

Do not update architecture to legitimize accidental code drift.

---

# 155. Milestone Review Gate

Final review asks:

```text
Did scope remain bounded?
Did any new authority appear?
Were tests weakened?
Did status claim exceed evidence?
```

---

# 156. Evidence Freshness

Evidence that depends on mutable external state must be refreshed.

Examples:

```text
provider health
branch protection
deployment health
store status
pricing
```

---

# 157. Immutable Evidence

Evidence tied to immutable artifact/revision may remain valid historically.

---

# 158. Current Health

Current health is not a milestone by itself.

It is operational status.

Use runtime evidence.

---

# 159. Current Deployment

Current deployment version must be read from deployment/runtime evidence.

Do not assume master HEAD is deployed.

---

# 160. Current CI

A prior CI PASS applies only to the tested revision/run.

---

# 161. Current Branch

Snapshot branch matters.

Status from feature branch must not be represented as master reality before merge.

---

# 162. PR Status

PR:

```text
open
merged
closed
```

is repository workflow state.

It can support milestone evidence but is not the milestone state itself.

---

# 163. Merge State

Merged code may still be:

```text
not deployed
not live
not verified in production
```

---

# 164. Release State

Released artifact may still be:

```text
not deployed
```

---

# 165. Deployment State

Deployed artifact may still be:

```text
UNHEALTHY
DEGRADED
UNKNOWN
```

---

# 166. No “Complete” Without Scope

Use:

```text
RAG.02 VERIFIED for tenant-aware retrieval authorization
```

not:

```text
RAG complete
```

until all program exit criteria pass.

---

# 167. No Factory Completion by File Presence

A factory directory existing does not prove the factory milestone.

---

# 168. No RAG Completion by Vector Search

Embedding + similarity search is not RAG completion.

Need:

```text
authorization
provenance
DLP
evaluation
evidence
```

---

# 169. No Deployment Completion by Config

Deployment config is not deployment evidence.

---

# 170. No Release Completion by Tag Alone

A tag is source/release metadata, not runtime health.

---

# 171. No Security Completion by Documentation

Security architecture does not prove controls are implemented.

---

# 172. No FinOps Completion by Budget Class

Budget structures must be enforced and tested.

---

# 173. Milestone Blocking Principle

When a hard gate fails:

```text
STOP
```

Do not move milestone downstream.

---

# 174. Minimal Fix Principle

When milestone fails:

```text
root cause
→ smallest correct fix
→ rerun relevant gates
```

---

# 175. No Test Weakening

Never modify acceptance tests merely to turn FAIL into PASS unless the canonical requirement itself changes through governance.

---

# 176. No Architecture Redefinition

Milestone implementation cannot redefine architecture.

If architecture must change:

```text
architecture proposal
→ governance
→ canonical doc update
→ implementation
```

---

# 177. No Autonomous Production Promotion

Passing milestones do not automatically authorize production promotion.

Deployment governance still applies.

---

# 178. No Hidden Workstream Switch

Changing primary workstream requires explicit product/governance decision.

Update this file and adopted execution graph/evidence accordingly.

---

# 179. Next-Workstream Selection Gate

After current workstream completes:

```text
1. refresh capability matrix
2. inspect current evidence
3. identify remaining high-value gaps
4. rank candidates
5. select exactly one primary workstream
6. record selection
```

---

# 180. Selection Criteria

Candidate ranking may consider:

```text
product value
architecture readiness
existing implementation
security risk
dependency readiness
external owner gates
cost
delivery effort
```

---

# 181. Selection Does Not Equal Implementation

`SELECTED` means:

```text
primary workstream chosen
```

not:

```text
implemented
tested
verified
```

---

# 182. Workstream Candidate Record

Conceptual:

```yaml
workstream_id: "MOBILE"
state: "DORMANT"
dependencies: []
product_value: "..."
architecture_fit: "..."
external_gates: []
selection_evidence: null
```

---

# 183. Dormant Candidate Review

Dormant candidates should be reconsidered when:

```text
current primary workstream complete
dependency materially changes
owner priority changes
external blocker clears
```

---

# 184. Milestone Report Format

Recommended status report:

```text
Snapshot:
Primary workstream:
Current milestone:
State:
Dependencies:
Evidence:
Blockers:
Owner gates:
Next action:
```

---

# 185. Red-Team Milestone Review

Before marking major milestone VERIFIED:

```text
run red-team
attempt bypass
attempt tenant leak
attempt stale-state abuse
attempt evidence omission
attempt budget/retry abuse
```

as relevant.

---

# 186. Final Lineage Review

Final program review verifies:

```text
requirement
→ architecture
→ implementation
→ tests
→ evidence
→ milestone status
```

---

# 187. Two-Pass Completeness Scan

For large programs, use:

## Pass 1 — Forward

```text
planned milestone
→ implementation/evidence
```

## Pass 2 — Reverse

```text
actual code/capability
→ owning milestone/requirement
```

This detects orphan implementation and missing work.

---

# 188. Orphan Work

If code exists with no milestone/requirement:

```text
classify
adopt through governance
or remove
```

---

# 189. Orphan Milestone

If milestone exists but architecture no longer requires it:

```text
defer/cancel/supersede through governance
```

---

# 190. Duplicate Milestone

Two milestones must not own the same authoritative outcome.

Consolidate or clarify scope.

---

# 191. Milestone Ownership

Every milestone needs logical owner.

In solo-founder operation, owner may be one person across multiple roles.

---

# 192. Milestone Approval

Only milestones requiring governance/privileged decision need approval.

Ordinary bounded engineering milestones may proceed under standing engineering authority.

---

# 193. Milestone Budgets

Large milestones may define:

```text
engineering time budget
provider test budget
deployment budget
```

where useful.

---

# 194. Milestone Stop Conditions

Examples:

```text
hard security failure
architecture contradiction
external account unavailable
budget exhausted
tool limit
required dependency missing
```

---

# 195. Hard Tool Limit

Execution tools may stop due to environment/tool limits.

Record:

```text
checkpoint
completed work
remaining work
exact next action
```

Do not mark milestone VERIFIED.

---

# 196. Continuation Checkpoint

A valid continuation block includes:

```text
active milestone
branch/PR if applicable
revision
completed evidence
pending tests
exact next action
```

---

# 197. Checkpoint Is Not Completion

`CONTINUATION_REQUIRED` or checkpoint state means work remains.

---

# 198. Milestone Completion Claim

Use:

```text
VERIFIED
```

only after all hard exit criteria pass.

---

# 199. External Evidence Claim

For store/account/platform steps, attach external evidence such as:

```text
platform status
verification result
submission record
```

---

# 200. Website Milestone Separation

Website deployment/SEO/social updates must not advance RAG milestones unless directly required and governed.

---

# 201. Desktop Milestone Separation

Desktop Store status must not advance core platform milestone unless milestone explicitly depends on it.

---

# 202. Marketing Milestone Separation

LinkedIn/X/visibility work is commercial/visibility execution, not proof of platform capability maturity.

---

# 203. Certification Separation

Founder training/certifications do not directly prove ILAIOS implementation status.

---

# 204. Repository Governance Work vs Product Work

Branch protection/license decisions are governance gates.

They must not be conflated with factory/RAG implementation.

---

# 205. Milestone Evidence Naming

Evidence artifacts should use stable descriptive names.

Example:

```text
RAG.02-tenant-isolation-test-report
```

---

# 206. Milestone Evidence Retention

Retain enough evidence to audit critical VERIFIED transitions.

---

# 207. Evidence Privacy

Do not include raw secrets in milestone evidence.

---

# 208. Evidence Integrity

Critical evidence should be integrity-verifiable where appropriate.

---

# 209. Milestone Dashboard

A future dashboard may project this register.

The dashboard does not become authority.

---

# 210. Machine-Readable Milestones

A machine-readable companion may exist if governed.

It must not diverge from this document.

---

# 211. Milestone Automation

Automation may:

```text
check dependencies
run tests
collect evidence
update proposed status
```

Human/governance approval remains required where specified.

---

# 212. Automated Status Proposal

Agent may propose:

```text
RAG.02 appears VERIFIED based on evidence
```

but canonical state update should follow governance rules.

---

# 213. Evidence-Based Status Automation

For deterministic cases, status may be machine-computed if:

```text
all required evidence sources are authoritative
logic is versioned/tested
```

---

# 214. Current Snapshot Refresh Procedure

To refresh:

```text
1. resolve canonical repo
2. resolve default branch
3. resolve current HEAD
4. read adopted execution graph
5. read relevant current tests/CI/runtime
6. update current status only
7. preserve architecture sections
```

---

# 215. Snapshot Staleness

If master changes after snapshot:

```text
this snapshot may be stale
```

Revalidate before making current-status decisions.

---

# 216. Current Snapshot Evidence Table

| Item | Snapshot Value |
|---|---|
| Repository | `Aliturgutt/ilaios` |
| Branch | `master` |
| HEAD | `31b75faf71243b1534d46369286b3f51532e4ccb` |
| Primary Post-v1 Workstream | `RAG_KNOWLEDGE` |
| Existing Factory Promotion | `VERIFIED` in adopted graph |
| RAG_KNOWLEDGE | `SELECTED` in adopted graph |
| Mobile | `DORMANT_NOT_SELECTED` in adopted graph |
| Commercial SaaS | `DORMANT_NOT_SELECTED` in adopted graph |

This table is mutable current-state data.

---

# 217. Current RAG Gate Table

| Gate | Required by Adopted Graph | Milestone Owner |
|---|---:|---|
| Tenant isolation | Yes | `RAG.02` / `RAG.10` |
| Authorization-aware retrieval | Yes | `RAG.02` / `RAG.07` |
| Source provenance | Yes | `RAG.03` |
| Privacy / DLP | Yes | `RAG.09` |
| Deterministic evidence | Yes | all, finalized in `RAG.13` |
| Full Platform CI | Yes | `RAG.11` |

---

# 218. Current Next Action

Based on the verified repository snapshot and this canonical milestone decomposition:

```text
NEXT PRIMARY MILESTONE
    = RAG.00 — Baseline & Gap Confirmation
```

This is a planning conclusion derived from:

```text
RAG_KNOWLEDGE selected
+
upstream dependencies recorded VERIFIED
+
implementation must be revalidated before net-new changes
```

---

# 219. RAG.00 Execution Rule

RAG.00 must be read-only first.

Before writing code:

```text
inspect
map
compare
classify
```

Then implement only verified gaps.

---

# 220. RAG.00 No-Rewrite Rule

If existing implementation already satisfies a requirement:

```text
preserve it
```

Do not rewrite merely because a new milestone document exists.

---

# 221. RAG.00 Evidence Order

Preferred:

```text
code
tests
CI
runtime/deployment where relevant
```

Status documents are secondary.

---

# 222. Milestone State at Authoring

This newly authored `MILESTONES.md` defines the following forward states:

```text
RAG.00 = READY
RAG.01 = PLANNED
RAG.02 = PLANNED
RAG.03 = PLANNED
RAG.04 = PLANNED
RAG.05 = PLANNED
RAG.06 = PLANNED
RAG.07 = PLANNED
RAG.08 = PLANNED
RAG.09 = PLANNED
RAG.10 = PLANNED
RAG.11 = PLANNED
RAG.12 = PLANNED
RAG.13 = PLANNED
RAG.14 = PLANNED
```

These are planning states, not claims of implementation.

---

# 223. Why RAG.00 Is READY

The adopted graph provides the prerequisite state:

```text
RAG selected
upstream dependencies VERIFIED
```

RAG.00 is a read-only revalidation milestone.

Therefore it can be `READY` without claiming RAG implementation progress.

---

# 224. Why RAG.01+ Are PLANNED

RAG.01 and later milestones depend on findings from RAG.00.

Until baseline/gaps are refreshed:

```text
exact implementation delta is unknown
```

Therefore they remain `PLANNED`.

---

# 225. Status Reconciliation Rule

If RAG.00 discovers that a later requirement is already implemented and verified:

```text
do not reimplement
```

Instead:

```text
map existing evidence
run fresh required tests
promote milestone state accordingly
```

---

# 226. No False Sequential Work

Milestone numbering defines dependency/order.

It does not force redundant implementation.

Existing evidence may satisfy multiple milestones after revalidation.

---

# 227. Existing Evidence Reuse

Existing evidence may be reused only if:

```text
same relevant revision/behavior
evidence remains valid
required scope matches
```

Fresh tests may still be required.

---

# 228. Fresh Evidence Rule

Security/tenant/RAG boundaries should prefer fresh evidence during active promotion.

---

# 229. RAG Completion Decision Matrix

```text
If all RAG.01–RAG.13 gates verified
    → RAG capability may be VERIFIED for defined scope

If RAG.14 production deployment also succeeds
    → may claim DEPLOYED / PRODUCTION for that scope

If live health is currently observed
    → may separately claim LIVE_HEALTHY operational status
```

---

# 230. Production Claim Scope

Example:

```text
RAG/Knowledge retrieval VERIFIED
for tenant-isolated project retrieval
at revision X
```

not:

```text
ILAIOS RAG fully complete forever
```

---

# 231. Future Workstream Rule

After RAG:

```text
do not automatically activate Mobile
do not automatically activate Commercial SaaS
```

Re-run selection gate.

---

# 232. Product Selection Evidence

Selection must record:

```text
candidate set
dependency readiness
product priority
owner decision
selected workstream
```

---

# 233. Workstream Selection Update

When changed:

```text
update adopted execution graph
update MILESTONES.md snapshot
record governance decision
```

---

# 234. Current External Gates Snapshot

At the adopted graph snapshot, external owner gates include:

```text
master branch protection policy
repository license decision
store/developer account actions
payment/provider/account actions
```

Their actual current completion states must be checked separately.

This document does not assume them complete.

---

# 235. Branch Protection Milestone

Possible future governance milestone:

```text
GOV.EXT.01
Master Branch Protection
```

Status must be based on actual GitHub configuration.

---

# 236. License Milestone

Possible future governance milestone:

```text
GOV.EXT.02
Repository License Decision
```

Requires explicit owner/legal decision.

---

# 237. Store Account Milestones

Possible:

```text
DIST.MSSTORE
DIST.PLAY
DIST.APPSTORE
```

These remain separate from platform core unless a selected workstream depends on them.

---

# 238. Commercial Provider Milestone

Possible:

```text
SAAS.EXT.PAYMENT
```

Requires provider/account evidence.

---

# 239. Cross-Document Milestone Traceability

Every milestone should map to:

```text
PRODUCT_REQUIREMENTS
IMPLEMENTATION_SPEC
DEPENDENCY_GRAPH
SECURITY
TESTING
```

as applicable.

---

# 240. Milestone Requirement Matrix

Conceptual:

| Milestone | Primary Requirements | Primary Verification |
|---|---|---|
| RAG.01 | Data/source contracts | schema/contract tests |
| RAG.02 | tenant/auth | isolation negative tests |
| RAG.03 | provenance | lineage/integrity tests |
| RAG.04 | lifecycle | update/delete/index tests |
| RAG.05 | provider independence | adapter tests |
| RAG.06 | retrieval quality | retrieval evaluation |
| RAG.07 | auth-aware path | bypass negative tests |
| RAG.08 | bounded context | context scope tests |
| RAG.09 | privacy/DLP | adversarial/security tests |
| RAG.10 | quality/leakage | golden/red-team |
| RAG.11 | platform integration | full CI/E2E |
| RAG.12 | operations/cost | recovery/FinOps |
| RAG.13 | final lineage | red-team/evidence |
| RAG.14 | promotion | deployment/health evidence |

---

# 241. Milestone Dependency Diagram

```text
RAG.00
  │
  ▼
RAG.01
  │
  ▼
RAG.02
  │
  ▼
RAG.03
  │
  ▼
RAG.04
  │
  ▼
RAG.05
  │
  ▼
RAG.06
  │
  ▼
RAG.07
  │
  ▼
RAG.08
  │
  ▼
RAG.09
  │
  ▼
RAG.10
  │
  ▼
RAG.11
  │
  ▼
RAG.12
  │
  ▼
RAG.13
  │
  ▼
RAG.14
```

---

# 242. Dependency Parallelization

Within a milestone, independent sub-tasks may run concurrently.

Across milestone boundaries, hard dependencies remain.

---

# 243. Milestone Checkpoint Format

```text
CHECKPOINT
Milestone:
Revision:
State:
Completed:
Tests:
Evidence:
Blocker:
Exact Next Action:
```

---

# 244. Milestone PASS Report

```text
MILESTONE VERIFIED

ID:
Scope:
Revision:
Tests:
CI:
Security:
Evidence:
Residual Risks:
Next Milestone:
```

---

# 245. Milestone FAIL Report

```text
MILESTONE BLOCKED / FAIL

ID:
Failed Gate:
Root Cause:
Evidence:
Required Fix:
Next Allowed Action:
```

---

# 246. No Ambiguous “Done”

Do not use:

```text
done
finished
completed
```

without mapping to a milestone state and scope.

---

# 247. Owner Decision Checkpoint

For `NEEDS_OWNER`:

```text
Decision Required:
Options:
Tradeoffs:
Evidence:
Default Safe State:
```

---

# 248. Default Safe State

When owner decision absent:

```text
do not perform privileged/external action
```

---

# 249. Milestone Priority

Priority may be:

```text
P0
P1
P2
```

but priority does not override dependency or security.

---

# 250. Critical Gate Priority

Tenant isolation, authorization, evidence, and production permission are always hard gates when applicable.

---

# 251. Milestone Risk Classification

Suggested:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

based on:

```text
data
privilege
blast radius
external side effect
cost
```

---

# 252. RAG Risk Classification

Tenant-isolated RAG is at least security/data-sensitive.

Tenant isolation failures are critical blockers.

---

# 253. Production Risk

Production deployment milestones are privileged/high-risk.

---

# 254. External Account Risk

Payment/store/DNS milestones require human/external platform authority.

---

# 255. Milestone Governance Change

Changing milestone exit criteria to make current implementation pass is forbidden unless the underlying requirement legitimately changes through governance.

---

# 256. Milestone Decomposition Change

You may split a milestone when:

```text
scope too large
dependencies become clearer
verification can be isolated
```

Preserve traceability.

---

# 257. Milestone Merge

Two milestones may be merged if:

```text
same owner
same dependencies
same verification
```

and governance updates history clearly.

---

# 258. Superseded Milestone

Use explicit:

```text
SUPERSEDED BY <ID>
```

in history if replaced.

---

# 259. Milestone Archive

Old completed milestones may move to archive/history only if current top-level traceability remains.

---

# 260. Historical Status Integrity

Do not rewrite a prior VERIFIED milestone to pretend it was never verified.

Record later regression separately.

---

# 261. Current Status Integrity

Do not leave stale VERIFIED state if current evidence clearly invalidates it.

---

# 262. Snapshot Update Trigger

Update the repository snapshot when:

```text
master HEAD changes materially
adopted execution graph changes
workstream selection changes
major milestone transitions
```

---

# 263. Automated Snapshot Caution

Automated update must not infer production health solely from repository merge.

---

# 264. CI Evidence Linkage

A milestone requiring CI should record:

```text
run ID
revision
result
```

---

# 265. Deployment Evidence Linkage

A deployment milestone should record:

```text
deployment ID
artifact hash
target
result
health check
```

---

# 266. External Evidence Linkage

External store/account milestone should record platform-specific evidence.

---

# 267. Final Program Lineage

```text
V1 BASELINE
    │
    ▼
GOV BASELINE
    │
    ▼
CAPABILITY REVALIDATION
    │
    ▼
FACTORY PROMOTION
    │
    ▼
FINAL LINEAGE RED-TEAM
    │
    ▼
RAG / KNOWLEDGE
    │
    ▼
RAG FINAL VERIFICATION
    │
    ▼
PRODUCTION DECISION
    │
    ▼
NEXT WORKSTREAM SELECTION
```

---

# 268. Current Program Position

At the snapshot date/revision:

```text
V1 / Post-v1 governance baseline
    recorded complete

Existing Factory Promotion
    recorded VERIFIED

RAG_KNOWLEDGE
    selected

Next governed execution step
    RAG.00 — Baseline & Gap Confirmation
```

This is the current milestone interpretation of repository evidence.

---

# 269. Final Milestone Formula

```text
DEPENDENCIES SATISFIED
+
SCOPE DEFINED
+
IMPLEMENTATION / ACTION
+
REQUIRED TESTS
+
NEGATIVE TESTS
+
EVIDENCE
+
REVIEW
+
EXIT CRITERIA
=
VERIFIED MILESTONE
```

---

# 270. Final Milestone Invariant

The defining rule is:

> **`MILESTONES.md` may change frequently; the canonical architecture may not be rewritten merely to make the milestone register look complete.**

Therefore:

```text
STATUS
    follows evidence

MILESTONE ORDER
    follows dependencies

VERIFIED
    follows tests + evidence

PRODUCTION
    follows deployment authority + runtime evidence

WORKSTREAM SELECTION
    follows explicit governance
```

And:

```text
MILESTONES.md
    = mutable execution truth

SYSTEM_ARCHITECTURE.md
    = target architecture truth

CODE / TEST / CI / RUNTIME / DEPLOYMENT
    = current reality evidence
```

**ILAIOS milestones exist to convert architecture into governed, evidence-backed progress without turning planning prose into false implementation truth.**
