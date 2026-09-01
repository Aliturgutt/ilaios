# ILAIOS — IMPLEMENTATION SPECIFICATION

**Document Type:** Canonical Implementation Specification  
**Format:** GitHub Markdown  
**Status:** Canonical Baseline v1.0 — Pending Repository Publication  
**Architecture Authority:** `SYSTEM_ARCHITECTURE.md`  
**Autonomous Execution View:** `AUTONOMOUS_NODE_ARCHITECTURE.md`  
**Product Authority:** `PRODUCT_REQUIREMENTS.md`  
**Repository Orientation:** `README.md`  
**Core Product Principle:** **SIGN IN → ONE PROMPT → GOVERNED AUTONOMOUS EXECUTION → VERIFIED FINISHED PRODUCT**

> This document defines **how ILAIOS must be implemented**. It translates the canonical architecture and product requirements into code ownership, contracts, state transitions, execution boundaries, persistence rules, testing obligations, evidence obligations, and Definition of Done criteria. It must not create a second architecture.

---

# 00. Purpose

The canonical documents answer different questions:

```text
SYSTEM_ARCHITECTURE.md
    → What must the system be?

AUTONOMOUS_NODE_ARCHITECTURE.md
    → How do the authoritative nodes connect and execute?

PRODUCT_REQUIREMENTS.md
    → What must the product do?

IMPLEMENTATION_SPEC.md
    → How must those decisions become implementation?
```

This document is binding on implementation choices unless superseded by an explicitly governed architecture decision.

---

# 01. Authority Order

Authority depends on the question being answered.

For **what ILAIOS must be**, canonical architecture and specifications govern:

```text
01  SYSTEM_ARCHITECTURE.md
02  PRODUCT_REQUIREMENTS.md
03  IMPLEMENTATION_SPEC.md
04  DEPENDENCY_GRAPH.md
05  API_CONTRACTS.md
06  SECURITY_ARCHITECTURE.md
07  DATA_ARCHITECTURE.md
08  TESTING_AND_EVALUATION.md
09  DEPLOYMENT_ARCHITECTURE.md
10  FINOPS.md
11  ENGINEERING_STANDARDS.md
12  GOVERNANCE.md
13  MILESTONES.md
14  ADR/
```

For **what ILAIOS actually is today**, current implementation evidence is authoritative:

```text
Current code
→ Tests
→ CI
→ Runtime evidence
→ Deployment evidence
```

Planning, roadmap, status, milestone prose, comments, and historical claims must never override current implementation evidence.

Therefore:

```text
TARGET TRUTH
    = canonical architecture + governed specifications

CURRENT REALITY
    = current code + tests + CI + runtime + deployment evidence

STATUS / ROADMAP PROSE
    = descriptive only; lowest authority when it conflicts with evidence
```

`AUTONOMOUS_NODE_ARCHITECTURE.md` is a companion execution view of `SYSTEM_ARCHITECTURE.md`; it must remain aligned with the canonical architecture and must not become a competing authority.

---

# 02. Implementation Constitutional Invariants

Every implementation must preserve:

```text
ONE Authoritative Control Plane
ONE Governed Execution Runtime
ONE Canonical Capability / Skill / Agent Identity System
ONE RoutingDecision Truth
ONE Evidence / Provenance Truth
ONE Authoritative Job / Task State
Frozen-by-Default Constitutional Core
Governed Platform Capabilities
Native Factories
Replaceable Providers
Permissioned Tools
Bounded Autonomous DAG Execution
Human Approval Where Required
Continuous Evidence
Durable State / Checkpoint / Resume
Independent Evaluation
Bounded Repair
Verified Finished Product
```

Forbidden:

```text
second Core
second Control Plane
second Planner authority
second Capability Registry
second Agent Runtime authority
parallel Policy Engine
parallel Routing authority
factory-specific hidden runtime
provider-owned product authority
UI-owned execution authority
unbounded repair loop
self-approval
cross-tenant context leakage
```

---

# 03. Core Evolution Rule

## 3.1 Canonical Rule

> **CORE = FROZEN BY DEFAULT, EVOLVABLE BY PROOF**

Core changes are exceptional.

A new provider, model, factory, skill, agent role, UI, connector, RAG algorithm, browser implementation, editor, or open-source reference does **not** justify a Core change.

## 3.2 Core Change Proof Gate

A Core change proposal must prove all of the following:

```text
1. A platform-wide invariant or canonical contract is missing.
2. The requirement cannot be correctly owned by an existing governed capability.
3. The change does not create a second authority.
4. The change does not promote replaceable provider/domain/UI logic into Core.
5. Existing contracts cannot solve the requirement without violating architecture.
6. Compatibility impact is understood.
7. Migration strategy exists.
8. Rollback strategy exists.
9. Tests prove the new invariant.
10. Evidence demonstrates why the change is necessary.
```

If the proof is incomplete, Core remains unchanged.

---

# 04. As-Built Integration Anchors

The implementation must extend the existing ILAIOS system instead of replacing it with a parallel architecture.

Current authoritative integration anchors include:

```text
services/capability_registry.py
    Canonical ilaios.capability.* identity registry

src/core/
services/control_plane/
    Existing Core / Control Plane roots

services/control_plane/proposals.py
    GoalSpec / BudgetEnvelope / bounded DAG proposal foundation

services/runtime/
    Governed runtime foundation

services/runtime/routing.py
services/ai_governance.py
    Existing provider/model routing and cost-governance foundations

services/identity.py
    Identity / tenant boundary

services/agent_governance.py
services/agent_registry.py
    Agent governance

src/code_intelligence/
services/software_factory.py
    Code intelligence / software execution

src/knowledge_graph/
src/project_manager/
services/research_data_factory.py
    Knowledge / project / research foundations

services/integrations/web_factory.py
    Web Factory anchor

src/video_automation/
    Video / Media Factory anchor
```

These paths are **integration anchors**, not permanent folder-location requirements. A governed refactor may move them, but it must preserve singular authority and migration/evidence lineage.

---

# 05. Capability Maturity Model

All canonical capabilities use this maturity progression:

```text
DESIGNED
   ↓
SPECIFIED
   ↓
IMPLEMENTED
   ↓
TESTED
   ↓
VERIFIED
   ↓
DEPLOYED / PRODUCTION
```

`DEPRECATED` is a separate lifecycle exit state.

```text
DEPRECATED = lifecycle exit state
```

## 5.1 Meaning

### DESIGNED
Architectural responsibility and boundary are defined.

### SPECIFIED
Contracts, inputs/outputs, policy requirements, evidence requirements, and acceptance criteria are explicit.

### IMPLEMENTED
Code exists for the specified scope.

### TESTED
Required unit/contract/integration/security tests for the specified scope pass.

### VERIFIED
Independent acceptance/evidence proves the capability meets its canonical requirements.

### DEPLOYED / PRODUCTION
The verified capability is deployed in the intended production environment and required release/deployment evidence exists.

### DEPRECATED
The capability is being removed or no longer accepted for new use under an explicit migration/retirement plan.

## 5.2 Rule

A capability must never skip maturity states by documentation claim alone.

---

# 06. Implementation Layer Boundaries

```text
CLIENT / PROJECTION PLANE
        │
        ▼
AUTHORITATIVE CONTROL PLANE
        │
        ▼
GOVERNED PLATFORM CAPABILITIES
        │
        ▼
NATIVE FACTORIES
        │
        ▼
GOVERNED EXECUTION PLANE
        │
        ▼
TOOLS / ADAPTERS / PROVIDERS
```

Authority flows downward only through explicit contracts.

A lower layer cannot grant itself authority owned above it.

Examples:

```text
Provider cannot grant permission.
Worker cannot approve itself.
Factory cannot create routing truth.
Skill cannot expand agent authority.
Tool cannot broaden ExecutionGrant.
Client cannot mutate authoritative job state directly.
```

---

# 07. Canonical Contract Families

Every cross-boundary operation must use a typed/versioned contract.

Minimum contract families:

## Identity

```text
PrincipalContext
TenantContext
ProjectContext
SessionContext
```

## Goal / Planning

```text
GoalSpec
AcceptanceCriteria
BudgetEnvelope
ExecutionProposal
ExecutionPlan
TaskEnvelope
```

## Capability / Agent / Skill / Factory

```text
CapabilityDescriptor
CapabilityRequirement
SkillContract
AgentManifest
FactoryDescriptor
```

## Governance

```text
ExecutionRequest
PolicyDecision
ApprovalRequest
ApprovalDecision
ExecutionGrant
```

## Routing

```text
RoutingRequest
RoutingDecision
ProviderDescriptor
ModelDescriptor
WorkerDescriptor
```

## Tools / Providers

```text
ToolRequest
ToolResult
ProviderRequest
ProviderResult
```

## Knowledge

```text
RetrievalRequest
AuthorizedContext
KnowledgeUnit
SourceProvenance
```

## Runtime

```text
WorkerLease
StateTransition
ExecutionEvent
CheckpointRecord
FailureRecord
RepairProposal
```

## Artifact / Evaluation / Evidence

```text
ArtifactRecord
ArtifactVersion
ValidationResult
EvaluationResult
EvidenceRecord
AcceptanceManifest
```

---

# 08. Contract Requirements

Every durable or cross-process contract must define:

```text
contract_id
schema_version
required fields
optional fields
validation rules
security classification
tenant/project scope
serialization form
compatibility policy
evidence obligations
failure semantics
```

Breaking changes require:

```text
new version
+ migration
+ compatibility decision
+ tests
+ consumer impact review
+ evidence
```

Silent schema drift is forbidden.

---

# 09. Identity Implementation

All authentication methods normalize into ILAIOS-owned identity.

```text
Google
Microsoft / Outlook / Hotmail
GitHub
Apple
Email
Microsoft Entra
Google Workspace
SAML / OIDC
        │
        ▼
Identity Provider Adapter
        │
        ▼
ILAIOS Principal
        │
        ▼
Tenant
        │
        ▼
Project
```

## 9.1 Required Identity Types

```text
PrincipalId
TenantId
ProjectId
SessionId
AuthProviderId
AuthMethod
AssuranceLevel
RoleBinding
PermissionSet
```

## 9.2 PrincipalContext

Conceptual contract:

```yaml
principal_id: "principal-..."
tenant_id: "tenant-..."
project_id: "project-..."
session_id: "session-..."
auth_provider: "microsoft"
auth_method: "oidc"
assurance_level: "strong"
roles: []
permissions: []
issued_at: "timestamp"
expires_at: "timestamp"
```

## 9.3 Rules

- External provider user IDs are not canonical Principal IDs.
- Tenant is validated server-side.
- Project context is explicit for project-scoped work.
- Cross-tenant access fails closed.
- Privileged actions may require stronger authentication/MFA.
- Revoked/expired sessions cannot authorize future privileged action.
- Identity decisions generate evidence.

---

# 10. Prompt Intake and Intent

Authenticated input becomes structured intent.

```text
Authenticated Request
      │
      ▼
Prompt Intake
      │
      ▼
Intent Analysis
      │
      ▼
GoalSpec Candidate
```

Prompt intake must:

- preserve original user text;
- attach identity/tenant/project;
- record source surface;
- classify relevant data/risk hints;
- enforce input limits;
- reject malformed privileged requests.

Intent analysis may infer structure but does **not** grant execution authority.

---

# 11. GoalSpec Implementation

Existing `GoalSpec` semantics are retained and extended only through governed versioning.

Minimum fields:

```text
objective
acceptance_criteria
risk_class
data_class
budget
```

Minimum budget dimensions:

```text
max_attempts
max_runtime_seconds
max_external_spend
```

Rules:

- objective is non-empty;
- acceptance criteria are mandatory;
- criteria are evaluable;
- scope expansion triggers re-planning;
- goal mutation is evidence-bearing;
- an agent cannot silently redefine the user goal.

---

# 12. Planning and Bounded DAG

There is one planning truth.

```text
GoalSpec
   │
   ▼
Planner
   │
   ▼
ExecutionProposal
   │
   ▼
Bounded DAG
```

The existing proposal layer is planning-only; planning does not itself authorize privileged execution.

## 12.1 Task Requirements

Each task must define:

```text
task_id
responsibility
dependencies
required_capabilities
input_refs
expected_output
validation_contract
risk_class
budget allocation
retry/repair policy
evidence requirements
```

## 12.2 DAG Validation

Before admission:

- task IDs are unique;
- dependencies exist;
- graph is acyclic;
- graph is bounded;
- required capabilities resolve;
- acceptance mapping exists;
- privileged actions are identified;
- no task self-grants authority;
- no task contains a direct Core/provider/tool bypass.

---

# 13. Context Strategy — Two Phase

Authorized context is intentionally two-phase.

## Phase A — Minimal Pre-Plan Context

Used only to understand the request correctly.

May include:

```text
project identity
basic project state
allowed user preferences
minimal relevant artifacts
tenant policy
essential business/product context
```

## Phase B — Task-Scoped Context

Retrieved for each DAG node based on:

```text
principal
tenant
project
task
purpose
capability
classification
ExecutionGrant
```

## Rule

Do not inject the entire project knowledge base into every task.

Data minimization is a product and security requirement.

---

# 14. Knowledge / RAG Implementation

Retrieval is a governed action.

```text
RetrievalRequest
      │
      ▼
Authorization Filter
      │
      ▼
Retrieve
      │
      ▼
Rerank
      │
      ▼
Context Assembly
      │
      ▼
AuthorizedContext + Provenance
```

Every retrievable knowledge unit must retain enough metadata to enforce:

```text
source_id
tenant_id
project_id
classification
purpose restrictions
region/residency
retention
authorization attributes
content hash
ingestion version
provenance
```

Rules:

- cross-tenant retrieval fails closed;
- client-side filtering is not a security boundary;
- vector filtering alone is not sufficient authorization;
- returned content retains source provenance;
- external content remains untrusted;
- grounding/evidence survives synthesis.

---

# 15. Capability Registry

There is exactly one canonical capability registry.

Active IDs use:

```text
ilaios.capability.*
```

Legacy names may remain provenance metadata but cannot become active parallel identity.

## 15.1 CapabilityDescriptor

Conceptual schema:

```yaml
capability_id: "ilaios.capability.web-factory"
schema_version: "1"
display_name: "Web Factory"
domain: "factory"
dependencies: []
implementation_roots: []
input_contracts: []
output_contracts: []
required_permissions: []
validation_requirements: []
evidence_requirements: []
maturity: "SPECIFIED"
```

## 15.2 Rules

- IDs are globally unique.
- All dependencies resolve.
- Registration does not imply maturity.
- One capability cannot duplicate another's authority.
- Factory capabilities depend on shared runtime/governance.
- New sub-capabilities extend the canonical registry.

---

# 16. Skill Contract

The skill model must remain bounded, integrity-verifiable, and permission-scoped.

Target fields:

```text
skill_id
version
capability_id
purpose
input_schema
output_schema
requested_permissions
network_policy
filesystem_policy
secret_policy
risk_class
privacy_class
cost_class
worker_requirements
provider_requirements
validation_requirements
fallback_behavior
repair_behavior
license/provenance
immutable_digest
tests
maturity
```

Rules:

- production skills are approved;
- skill contents are immutable/content-addressed where applicable;
- skill permissions cannot exceed caller/agent grant;
- external skills are not trusted by installation alone;
- one skill does not require one agent;
- skill behavior generates traceable evidence.

---

# 17. Agent Manifest

Agent = governed coordinating role.

Target fields:

```text
agent_id
version
purpose
allowed_capabilities
allowed_callers
allowed_targets
permissions
input_contracts
output_contracts
dependencies
risk ceiling
required verifier
evidence requirements
maturity
```

Rules:

- Agent ≠ Worker.
- Agent ≠ Skill.
- Agent ≠ Provider.
- Agent cannot mint unrestricted grants.
- Agent cannot self-approve.
- Agent cannot bypass canonical routing.
- Agent cannot become a second Control Plane.
- Prefer few reusable roles over agent-per-function explosion.

---

# 18. Factory Framework

Factory = bounded domain workflow/DAG.

Every factory must implement the same high-level contract:

```text
GoalSpec
+ AcceptanceCriteria
+ AuthorizedContext
        │
        ▼
Factory
        │
        ▼
Bounded Domain DAG
        │
        ▼
Shared Admission
        │
        ▼
Shared Routing
        │
        ▼
Shared Runtime
        │
        ▼
Artifact + Evidence
```

FactoryDescriptor must define:

```text
factory_id
version
supported_goal_types
required_capabilities
input_schema
artifact_schema
default_dag_template
policy requirements
validation requirements
repair policy
evidence requirements
delivery contract
maturity
```

Forbidden:

```text
factory-owned Core
factory-owned router
factory-owned Policy Engine
factory-owned hidden scheduler
factory-owned evidence truth
factory-owned provider secrets
factory self-approval
```

---

# 19. Execution Admission

Every executable privileged task is admitted before execution.

```text
TaskEnvelope
      │
      ▼
Policy / Admission
      │
      ├─ Identity
      ├─ Tenant / Project
      ├─ Permission
      ├─ Privacy / Residency
      ├─ DLP / Secrets
      ├─ Tool Scope
      ├─ Risk / Blast Radius
      ├─ Budget / Quota
      └─ Approval Requirement
      │
      ▼
Allow | Deny | RequireApproval
```

## 19.1 ExecutionRequest

Must include:

```text
request_id
principal_id
tenant_id
project_id
job_id
task_id
capability_id
requested_action
requested_tools
requested_resources
data_class
risk_class
budget_ref
context_ref
```

## 19.2 ExecutionGrant

Must bind:

```text
grant_id
principal_id
tenant_id
project_id
job_id
task_id
capability_id
allowed_actions
allowed_tools
allowed_resources
network_scope
filesystem_scope
secret_scope
spend_ceiling
attempt_ceiling
issued_at
expires_at
policy_decision_ref
approval_ref if applicable
```

Rules:

- missing mandatory context fails closed;
- expired grant is invalid;
- a worker cannot broaden a grant;
- a provider cannot broaden a grant;
- retries remain inside grant/policy or must be re-admitted.

---

# 20. Human Approval / HITL

Approval is a first-class runtime state and policy outcome.

```text
Proposed Privileged Action
      │
      ▼
Policy
      │
      ▼
RequireApproval
      │
      ▼
WAITING_FOR_APPROVAL
      │
      ▼
Human Decision
   │          │
Approve    Reject
   │          │
   ▼          ▼
Scoped      Deny
Grant
```

ApprovalRecord must include:

```text
approval_id
approver_principal_id
tenant_id
project_id
job_id
task_id
exact_action
scope
decision
reason
issued_at
expires_at
revoked_at
evidence_ref
```

Approval can apply before:

- production deploy;
- DNS changes;
- payment/spend;
- destructive data action;
- security/identity changes;
- external communication;
- publication/release.

Agents and workers cannot self-approve.

---

# 21. ONE RoutingDecision

The current routing foundations must converge into **one canonical routing decision contract**.

No third router may be created.

## 21.1 Eligibility Order

```text
Capability Requirement
        │
        ▼
Authority Eligibility
        │
        ▼
Security / Privacy / Residency
        │
        ▼
Context / Modality
        │
        ▼
Tool Requirements
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

## 21.2 RoutingDecision

Target:

```yaml
route_id: "route-..."
tenant_id: "tenant-..."
project_id: "project-..."
job_id: "job-..."
task_id: "task-..."
capability_id: "ilaios.capability..."
worker_class: "..."
provider_id: "..."
model_or_resource_id: "..."
adapter_id: "..."
quality_floor: "..."
privacy_class: "..."
residency: "..."
estimated_cost: 0
reason_codes: []
fallback_candidates: []
evidence_refs: []
created_at: "timestamp"
```

## 21.3 Consolidation Rule

`services/runtime/routing.py` and `services/ai_governance.py` may retain separated internal responsibilities, but externally:

```text
there must be one route request model
one eligibility pipeline
one canonical RoutingDecision
one evidence lineage
```

No independent module may make a competing final routing decision.

---

# 22. Provider Registry and Adapters

ProviderDescriptor must support:

```text
provider_id
adapter_id
provider_type
supported_capabilities
models/resources
modalities
context/input limits
output limits
regions
privacy metadata
cost metadata
health
quota
enabled state
```

Adapter owns only protocol translation:

```text
serialize request
call provider
normalize response
normalize errors
extract usage
emit health observations
support cancellation where available
```

Adapter does not own:

```text
authorization
tenant policy
budget authority
approval
final acceptance
canonical routing
```

Provider types may include:

```text
OpenAI
Anthropic
Gemini
other hosted models
image/video/audio providers
search providers
vLLM
Ollama
local deterministic runtimes
```

Provider catalog is runtime/configuration state, not Constitutional Core.

---

# 23. Worker and Scheduler

Worker = actual execution process.

Scheduler = governed work assignment.

WorkerDescriptor:

```text
worker_id
worker_class
supported_capabilities
runtime_environment
isolation_class
resource_limits
network_profile
health
version
```

WorkerLease:

```text
lease_id
worker_id
tenant_id
project_id
job_id
task_id
grant_id
attempt
issued_at
expires_at
fencing_token
```

Rules:

- lease is bounded;
- stale leases cannot commit authoritative results;
- duplicate execution must be idempotent or rejected;
- workers do not own job-state authority;
- worker crash is recoverable where checkpointing applies;
- cancelled jobs fence late results.

---

# 24. Tool Gateway

Workers must not directly receive unrestricted tool authority.

Canonical path:

```text
Worker
  │
  ▼
ToolRequest
  │
  ▼
Tool Gateway
  │
  ├─ ExecutionGrant check
  ├─ permission firewall
  ├─ scoped secret resolution
  ├─ network/filesystem policy
  └─ sandbox/isolation
  │
  ▼
Connector / Adapter
  │
  ▼
Tool / External Service
```

Tool families:

```text
Browser
Shell / Code
Files
Git / Repository
External APIs
Cloud
Search
Media
Deployment
Communication
```

ToolResult must be treated as untrusted content until validated.

---

# 25. GitHub / Repository Tool Boundary

GitHub identity and GitHub repository access are separate capabilities.

## Login role

```text
GitHub OAuth
→ ILAIOS Identity
```

## Repository tool role

```text
ILAIOS Tool Gateway
→ GitHub / Git Adapter
→ repository read/write operation
```

Repository mutation requires:

```text
authorized project/repository
scoped grant
bounded branch/change
tests
diff review
CI evidence
merge/release policy
```

Read-only repository intelligence does not automatically gain write authority.

---

# 26. Runtime State Machine

Authoritative state belongs to the platform.

Minimum states:

```text
PLANNING
QUEUED
RUNNING
WAITING_FOR_APPROVAL
NEEDS_USER_INPUT
VALIDATING
CHECKPOINTED
REPAIRING
RETRYING
FINAL_VALIDATION
DONE
FAILED
CANCEL_REQUESTED
CANCELLED
```

Representative transitions:

```text
PLANNING → QUEUED
QUEUED → RUNNING
RUNNING → WAITING_FOR_APPROVAL
WAITING_FOR_APPROVAL → RUNNING
RUNNING → NEEDS_USER_INPUT
NEEDS_USER_INPUT → RUNNING
RUNNING → VALIDATING
VALIDATING → CHECKPOINTED
VALIDATING → REPAIRING
REPAIRING → RETRYING
RETRYING → RUNNING
CHECKPOINTED → QUEUED
CHECKPOINTED → FINAL_VALIDATION
FINAL_VALIDATION → DONE
FINAL_VALIDATION → REPAIRING
* → FAILED when terminal
* → CANCEL_REQUESTED
CANCEL_REQUESTED → CANCELLED
```

Invalid transitions fail closed.

---

# 27. StateTransition Contract

```text
event_id
job_id
task_id
tenant_id
project_id
from_state
to_state
reason
actor
sequence
timestamp
evidence_ref
```

Rules:

- sequence is monotonic per authoritative stream;
- client cannot directly write transition state;
- state transition and evidence link are durable;
- late/stale worker commit is fenced;
- reconnect reconstructs from authoritative state.

---

# 28. Checkpoint / Resume

CheckpointRecord:

```text
checkpoint_id
tenant_id
project_id
job_id
task_id
state
completed_node_ids
pending_node_ids
artifact_refs
evidence_cursor
budget_state
retry_state
route_refs
context_refs
created_at
integrity_hash
```

Recommended checkpoint boundaries:

- task completion;
- expensive provider generation;
- artifact creation;
- approval wait;
- validation pass;
- factory phase completion;
- external side-effect pre/post boundary.

Resume sequence:

```text
Load checkpoint
→ verify integrity
→ reload current identity/policy
→ invalidate expired grants
→ reload budget/retry state
→ route again if required
→ resume next valid node
```

---

# 29. Continuous Evidence

Evidence is emitted during execution, not appended only at completion.

Required material events:

```text
goal accepted
plan proposed
plan validated
policy decision
approval decision
routing decision
worker lease
tool call
provider call
artifact created/versioned
validation
checkpoint
failure classification
repair proposal
cost/usage
delivery decision
```

EvidenceRecord:

```text
evidence_id
event_type
tenant_id
project_id
job_id
task_id
actor
timestamp
input_refs
output_refs
decision_refs
artifact_refs
content_hash
metadata
```

Evidence ≠ debug log.

---

# 30. Artifact and Version Model

ArtifactRecord:

```text
artifact_id
artifact_type
tenant_id
project_id
job_id
created_by_task
current_version
classification
storage_ref
created_at
```

ArtifactVersion:

```text
artifact_id
version_id
content_hash
size
mime_type
producer
route_ref
input_refs
storage_ref
validation_refs
created_at
```

Rules:

- repair creates new version;
- accepted validation refers to exact version;
- artifact ownership preserves tenant/project;
- content hash/integrity is available;
- object storage is not evidence authority.

---

# 31. Step-Level Execution Loop

Every executable DAG node follows:

```text
READY
  │
  ▼
ADMISSION
  │
  ▼
ROUTING
  │
  ▼
SCHEDULER / LEASE
  │
  ▼
WORKER
  │
  ▼
TOOL / SKILL / PROVIDER
  │
  ▼
STEP OUTPUT
  │
  ▼
VALIDATION
  │
  ├── FAIL → FAILURE CLASSIFIER → BOUNDED REPAIR
  │
  ▼ PASS
EVIDENCE
  │
  ▼
STATE UPDATE
  │
  ▼
CHECKPOINT
  │
  ▼
NEXT DAG NODE
```

This is the atomic autonomous execution pattern.

---

# 32. Validation

Step validation can include:

```text
schema validation
deterministic business rules
security checks
artifact existence/integrity
tool exit status
provider response normalization
domain-specific quality gate
policy invariants
```

No downstream task should consume a failed output unless the contract explicitly permits partial/error input.

---

# 33. Independent Final Evaluation

Final evaluation applies acceptance criteria to the complete artifact or action outcome.

Possible dimensions:

```text
functional
security
privacy
visual
audio
accessibility
performance
provenance/source grounding
policy compliance
user acceptance criteria
```

Where feasible:

```text
producer ≠ verifier
```

The producing model/worker must not be the sole authority accepting its own final result.

---

# 34. Bounded Repair

Canonical repair path:

```text
Validation FAIL
      │
      ▼
Failure Classification
      │
      ▼
RepairProposal
      │
      ▼
Budget / Attempt Check
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

Hard bounds:

```text
max_attempts
max_cost
max_elapsed_time
```

May additionally include:

```text
max_provider_failovers
max_tool_retries
max_artifact_versions
```

Security/policy denial cannot be repaired by bypassing policy.

---

# 35. Failure Classification

Minimum classes:

```text
validation_failure
transient_runtime_failure
provider_failure
provider_unavailable
quota_failure
budget_exhausted
timeout
tool_failure
dependency_failure
policy_denial
security_failure
privacy_violation
tenant_scope_violation
approval_rejection
approval_timeout
artifact_integrity_failure
internal_invariant_failure
cancelled
needs_user_input
```

Behavior:

```text
transient
    → bounded retry

provider
    → governed fallback / new route

validation
    → bounded repair

policy/security/privacy/tenant
    → fail closed

approval
    → wait/reject/expire

missing essential input
    → NEEDS_USER_INPUT
```

---

# 36. Cancellation and Compensation

Cancellation sequence:

```text
CancellationRequest
      │
      ▼
Authorize
      │
      ▼
CANCEL_REQUESTED
      │
      ▼
Stop new scheduling
      │
      ▼
Cancel safe active work
      │
      ▼
Fence late results
      │
      ▼
Compensate / rollback supported side effects
      │
      ▼
CANCELLED
```

Compensation is required where a reversible external side effect was partially committed and the underlying system supports rollback.

Irreversible actions require stronger pre-execution approval/risk handling.

---

# 37. Secrets

Secrets follow scoped runtime resolution.

```text
ExecutionGrant
      │
      ▼
Secret Policy
      │
      ▼
Secret Reference
      │
      ▼
Bounded Runtime Injection
      │
      ▼
Immediate Use
```

Forbidden:

- secret in source control;
- secret in documentation;
- entire vault injected into worker;
- secrets in ordinary evidence/log payload;
- client-embedded privileged backend secrets.

---

# 38. FinOps Enforcement

Cost controls apply before and during execution.

Cost context includes:

```text
tenant budget
project budget
goal budget
task budget
provider/model unit cost
external service spend
retry spend
repair spend
historical usage
```

Rules:

- security/privacy eligibility comes before cost;
- budget can be a hard admission constraint;
- retry/repair consumes same governed envelope;
- fallback cannot silently exceed budget;
- material usage is attributable to tenant/project/job;
- free provider capacity is never assumed as an architecture invariant.

---

# 39. Observability Hooks

Every major execution component emits structured operational telemetry with safe identifiers:

```text
tenant_id
project_id
job_id
task_id
capability_id
route_id
worker_id
tool_id when safe
provider_id when safe
latency
status
error_class
retry_count
cost/usage
```

Observability outputs:

```text
logs
metrics
traces
SLO signals
alerts
incident signals
```

Observability is not authoritative evidence and cannot grant execution authority.

---

# 40. Persistence Planes

Logical storage planes remain separated by responsibility.

```text
Operational Store
    principals / tenants / projects / jobs / tasks

Workflow State
    queues / leases / checkpoints / state

Knowledge Store
    source units / indexes / graph / retrieval metadata

Artifact Store
    files / images / video / packages

Evidence Store
    audit / provenance / manifests

Secret / Key Store
    credentials / keys / signing references

Observability Stores
    logs / metrics / traces
```

Tenant identity must persist across every boundary.

Detailed schemas belong in `DATA_ARCHITECTURE.md`.

---

# 41. Client / Projection Implementation

Supported surfaces may include:

```text
Web
Desktop
Mobile
API
CLI
Enterprise Console
```

Clients consume:

```text
authoritative state projections
approval requests
artifacts
evidence summaries
notifications
```

Clients must not contain:

```text
authoritative scheduler
canonical router
unrestricted provider secrets
hidden factory runtime
job-state authority
```

Reconnect reconstructs from authoritative backend state.

---

# 42. API Implementation Principles

Detailed API schemas belong in `API_CONTRACTS.md`.

Mandatory principles:

- contract-first;
- authenticated;
- server-side tenant validation;
- versioned;
- idempotency for replay-sensitive writes;
- async jobs return stable job IDs;
- privileged actions go through admission;
- errors do not leak secrets;
- API does not bypass Control Plane;
- API state is projection of authoritative state.

---

# 43. Web Factory Implementation

Target bounded phases:

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

Requirements:

- shared admission;
- shared routing;
- shared evidence;
- governed browser/tool usage;
- no external design project as runtime authority;
- deploy/publish is privileged side effect;
- code compile/build alone is not final acceptance.

---

# 44. Video / Media Factory Implementation

Target phases:

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

Rules:

- preserve existing canonical timeline lineage;
- extend existing FFmpeg/Remotion/render path rather than create second engine;
- editing capabilities may grow under native capability families;
- render success alone is not acceptance;
- external editors are references unless explicitly approved as replaceable tools.

---

# 45. Software Factory Implementation

Target flow:

```text
Repository Analysis
→ Change Proposal
→ Bounded Plan
→ Write Admission
→ Branch / Bounded Change
→ Tests
→ Static / Security Checks
→ Build
→ Diff Review
→ PR / Review Artifact
→ Merge / Release Policy
```

Rules:

- read-only intelligence does not imply write authority;
- repository write is scoped;
- tests cannot be weakened to obtain PASS;
- unrelated cleanup is not hidden in functional changes;
- merge respects required checks;
- build success ≠ deployment success.

---

# 46. App Factory Implementation

App Factory composes shared Software Factory primitives.

It may add platform-specific:

```text
application packaging
platform signing
store metadata
store validation
distribution
release channels
```

It must not duplicate:

```text
code change engine
test framework
policy
routing
evidence
software repository logic
```

Store publication is a governed external side effect.

---

# 47. Research / Data Implementation

Research outputs must retain:

```text
source
claim
verification state
provenance
classification
tenant/project
timestamp/version
```

Research may feed Knowledge/RAG without losing authorization/provenance metadata.

External research applications are references, not authoritative ILAIOS knowledge runtimes.

---

# 48. Security Factory Implementation

Security Factory may:

```text
analyze
detect
evaluate
classify
propose remediation
verify remediation
generate evidence
```

It cannot:

```text
replace Policy Gateway
grant permission
self-authorize remediation
bypass approval
```

Security-sensitive mutations use normal governed execution.

---

# 49. Cross-Factory Composition

Cross-factory work is one shared DAG.

```text
Compound Goal
    │
    ▼
Shared Execution Plan
    │
    ├─ Research
    ├─ Web
    ├─ Video
    ├─ Software/App
    ├─ Creative
    └─ Security
    │
    ▼
Artifact Composition
    │
    ▼
Cross-Factory Evaluation
```

Factories communicate through typed artifact/contracts, not hidden direct dependencies.

---

# 50. External Reference Assimilation

Required path:

```text
External Reference
      │
      ▼
Pin source / commit / tag
      │
      ▼
License Review
      │
      ▼
Security / Supply-Chain Review
      │
      ▼
Architecture / UX / Behavior Study
      │
      ▼
Requirement Extraction
      │
      ▼
ILAIOS Specification
      │
      ▼
ILAIOS-Native Implementation
      │
      ▼
Tests
      │
      ▼
Independent Evaluation
      │
      ▼
Evidence / Provenance
      │
      ▼
Capability Registration
```

Independence test:

```text
Disable/remove upstream reference
→ build ILAIOS
→ run relevant tests
→ run E2E acceptance
→ verify required native behavior still works
```

---

# 51. External Reference Boundaries

Examples:

```text
OmniRoute
    routing/fallback ideas
    NOT routing authority

NotebookLM-style systems
    research/RAG workflow reference
    NOT Core dependency

Taste / design skill repositories
    design heuristics
    NOT permanent skill authority

OpenCut
    editing/timeline semantics reference
    NOT second video engine

Delegation-style visualizers
    projection UX reference
    NOT runtime authority

Codex / Claude Code / Gemini CLI / OpenClaw
    development actuators
    NOT released-product brain
```

---

# 52. Determinism

Determinism is mandatory where authority and replay depend on it.

Use:

```text
stable IDs
canonical serialization
content hashes
bounded DAG ordering
deterministic route tie-break
validated state transitions
idempotency keys
fencing tokens
artifact versions
```

AI generation itself may be nondeterministic.

The governance/evidence path must still be able to prove what happened.

---

# 53. Concurrency and Idempotency

Required controls:

```text
stable task identity
lease/fencing
idempotent mutation where possible
sequenced state
artifact versioning
optimistic/transactional concurrency where necessary
```

No authoritative state mutation may rely on unsafe “last write wins”.

---

# 54. Configuration Hierarchy

Conceptual hierarchy:

```text
platform constitutional defaults
      ↓
environment config
      ↓
tenant policy
      ↓
project policy
      ↓
goal/task bounded overrides
```

Lower scopes may tighten rules.

They cannot weaken constitutional invariants.

---

# 55. Feature Flags

Feature flags may control:

```text
availability
tenant eligibility
rollout percentage
provider eligibility
experimental evaluator
factory phase
```

They cannot disable:

```text
tenant isolation
mandatory policy
mandatory evidence
critical approval
required acceptance
constitutional invariants
```

---

# 56. Migration and Backward Compatibility

Breaking changes require an explicit lifecycle:

```text
new contract/version
→ migration or compatibility adapter
→ consumer migration
→ evidence
→ old version retirement
```

Temporary dual paths must have a retirement condition.

Parallel authority may never become permanent “compatibility”.

---

# 57. Testing Layers

Every material component must map to tests.

Required categories:

```text
unit
contract
integration
state-transition
policy/deny-path
tenant-isolation
routing
tool permission
artifact/evidence
failure/recovery
end-to-end
security/adversarial where applicable
```

Detailed strategy belongs in `TESTING_AND_EVALUATION.md`.

---

# 58. Mandatory Negative Tests

Critical denial paths must be tested.

Examples:

```text
cross-tenant retrieval denied
expired grant denied
unauthorized tool denied
skill authority expansion denied
unknown capability denied
disabled provider rejected
budget exhaustion enforced
invalid state transition denied
factory bypass denied
self-approval denied
repair limit enforced
stale worker commit fenced
cancelled job late commit denied
missing policy context fails closed
```

Positive-only testing is insufficient for governed boundaries.

---

# 59. Repository Quality Gates

Python/platform changes preserve the established gates where applicable:

```text
python -m pytest -q
ruff check .
mypy --strict src tests
pre-commit run --all-files
git diff --check
```

Component-specific gates may be stricter.

A documented command is not evidence that it passed for a specific commit.

---

# 60. Capability Definition of Done

A capability reaches each maturity state only when these gates are met.

## DESIGNED

```text
responsibility defined
architecture boundary defined
dependencies identified
no authority duplication
```

## SPECIFIED

```text
input/output contracts defined
policy requirements defined
evidence requirements defined
failure behavior defined
acceptance criteria defined
```

## IMPLEMENTED

```text
code exists
canonical registry maps to implementation
no hidden parallel authority
basic local behavior demonstrable
```

## TESTED

```text
required unit tests pass
contract tests pass
integration tests pass
negative-path tests pass where required
```

## VERIFIED

```text
independent acceptance passes
security/governance gates pass
evidence is complete
canonical requirements are traceable
```

## DEPLOYED / PRODUCTION

```text
release/deployment completed
production configuration valid
required runtime health verified
release evidence exists
rollback/recovery path known
```

---

# 61. Factory Definition of Done

A factory is not complete because one happy-path generation works.

A factory requires:

```text
goal contract
bounded DAG
shared admission
shared routing
shared runtime
artifact model
step validation
failure classification
bounded repair
final independent evaluation
evidence
delivery contract
negative tests
end-to-end acceptance
```

---

# 62. Provider Integration Definition of Done

A provider adapter is complete when:

```text
provider is registered
capabilities are declared
adapter is bounded
credentials are scoped
requests normalize
responses normalize
errors normalize
usage is captured
health is observable
routing eligibility works
fallback semantics are tested
privacy/budget rules are enforced
evidence identifies provider/route
```

Provider integration alone does not make the related factory complete.

---

# 63. RAG Definition of Done

Knowledge/RAG is not production-ready until:

```text
tenant isolation
authorization-aware retrieval
source provenance
classification
privacy/DLP
retrieval evidence
prompt-injection handling
grounded output linkage
negative isolation tests
full integration tests
```

all pass for the defined production scope.

Embeddings/indexing alone = not complete.

---

# 64. Routing Consolidation Definition of Done

Provider routing is considered canonical when:

```text
one external RoutingRequest contract
one eligibility pipeline
one canonical RoutingDecision contract
one provider/model registry relationship
one evidence lineage
one deterministic tie-break policy
one governed fallback path
```

and tests prove there is no competing final route authority.

---

# 65. Human Approval Definition of Done

Approval subsystem must prove:

```text
policy can require approval
job enters WAITING_FOR_APPROVAL
exact action is shown
authorized approver can approve/reject
approval expires/revokes
self-approval is impossible
grant binds to approved scope
modified action requires reevaluation
evidence preserves decision
```

---

# 66. Checkpoint / Recovery Definition of Done

Checkpoint/resume must prove:

```text
durable state survives interruption
artifacts remain referenced
evidence cursor survives
budget/retry state survives
expired grants are rejected
resume continues from valid boundary
completed work is not unnecessarily duplicated
stale workers cannot overwrite resumed state
```

---

# 67. Evidence Definition of Done

Evidence subsystem must prove final acceptance can answer:

```text
Who requested the job?
Which tenant/project?
What goal?
What plan?
Which policy decisions?
Which approvals?
Which routes?
Which workers/tools/providers?
Which artifact version?
Which validations?
Which repair attempts?
Which cost/usage?
Why was the result accepted?
What was delivered?
```

---

# 68. Implementation Task Template

Every engineering task should be executable using a bounded template:

```text
TASK ID
Purpose
Canonical requirement IDs
Architecture component
Existing implementation anchor
Files expected to change
Files explicitly out of scope
Input contracts
Output contracts
Security/policy impact
Data impact
Evidence impact
Tests required
Negative tests required
Migration required?
Rollback
Acceptance criteria
Definition of Done
```

This prevents coding agents from broadening scope while implementing.

---

# 69. Change Workflow

Canonical engineering flow:

```text
Current repository evidence
      │
      ▼
Identify exact requirement
      │
      ▼
Identify existing authority / anchor
      │
      ▼
Design smallest compatible change
      │
      ▼
Implement
      │
      ▼
Targeted tests
      │
      ▼
Repository-wide required gates
      │
      ▼
Diff inspection
      │
      ▼
Evidence
      │
      ▼
PR / review
      │
      ▼
Required CI
      │
      ▼
Merge / release according to governance
```

No implementation task starts by creating a second system.

---

# 70. Architecture Drift Detection

Implementation review must reject:

```text
new router that bypasses canonical router
new planner with independent authority
new capability registry
factory direct provider calls
factory direct secret access
agent self-approval
new job-state store used as authority
UI-side authoritative workflow
duplicate evidence system
unbounded repair logic
cross-tenant context shortcut
```

These are architecture defects, not stylistic differences.

---

# 71. Status Claims

Implementation status must be evidence-based.

Keep separate:

```text
architecture defined
code implemented
tests passed
CI passed
artifact built
deployment executed
production health verified
```

Never infer:

```text
Terraform exists
⇒ service is currently live

workflow exists
⇒ workflow passed

capability registered
⇒ capability is verified

provider adapter exists
⇒ provider is production-ready
```

---

# 72. Documentation Traceability

Each implementation should trace:

```text
PRODUCT_REQUIREMENT
      │
      ▼
SYSTEM_ARCHITECTURE component
      │
      ▼
IMPLEMENTATION_SPEC contract
      │
      ▼
code
      │
      ▼
tests
      │
      ▼
evidence
      │
      ▼
maturity / milestone decision
```

---

# 73. Implementation Non-Goals

This specification does not authorize:

- repo-wide rewrite for aesthetic cleanup;
- new parallel platform;
- one agent per skill;
- one provider per capability as permanent coupling;
- hidden provider-specific business logic;
- unlimited autonomous retries;
- production mutation without policy/approval;
- third-party project adoption without assimilation review;
- architecture changes made solely inside implementation code.

---

# 74. Canonical End-to-End Implementation Formula

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
GOAL + ACCEPTANCE
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
TASK LOOP
      │
      ├─ Admission / Policy
      ├─ Approval if required
      ├─ Task-scoped Authorized Context
      ├─ ONE RoutingDecision
      ├─ Queue / Scheduler / Lease / Fencing
      ├─ Worker
      ├─ Skill / Tool Gateway / Provider Adapter
      ├─ Step Output
      ├─ Validation
      ├─ Evidence
      ├─ State Update
      └─ Checkpoint
      │
      ▼
FINAL ARTIFACT
      │
      ▼
INDEPENDENT FINAL EVALUATION
      │
      ├──── FAIL → BOUNDED REPAIR → RE-ADMISSION
      │
      ▼ PASS
ACCEPTANCE MANIFEST
      │
      ▼
GOVERNED DELIVERY / DEPLOY / PUBLISH
      │
      ▼
VERIFIED FINISHED PRODUCT
```

---

# 75. Final Implementation Rule

The implementation is correct only if the user can experience one coherent ILAIOS product while all internal execution remains governed, bounded, replaceable, recoverable, and provable.

```text
Providers execute.
Tools actuate.
Workers run.
Agents coordinate.
Skills constrain expertise.
Factories compose domain work.
Knowledge provides authorized context.
Routing selects eligible resources.
Policy controls authority.
The Control Plane owns execution truth.
Evidence proves what happened.
Evaluation proves whether the result is acceptable.
```

**No implementation convenience may create a second ILAIOS brain.**
