# ILAIOS — DATA ARCHITECTURE

**Document Type:** Canonical Data Architecture  
**Format:** GitHub Markdown + ASCII architecture diagrams  
**Status:** Canonical Baseline v1.0 — Pending Repository Publication  
**Architecture Authority:** `SYSTEM_ARCHITECTURE.md`  
**Product Authority:** `PRODUCT_REQUIREMENTS.md`  
**Implementation Authority:** `IMPLEMENTATION_SPEC.md`  
**Dependency Authority:** `DEPENDENCY_GRAPH.md`  
**Security Authority:** `SECURITY_ARCHITECTURE.md`  
**Core Data Principle:** **EVERY MATERIAL RECORD MUST RESOLVE TO OWNER, SCOPE, PURPOSE, LIFECYCLE, AND PROVENANCE**

> This document defines **the canonical logical data model, store boundaries, ownership rules, lifecycle rules, lineage, consistency model, tenant isolation, knowledge data architecture, artifact/evidence separation, and data movement contracts of ILAIOS**. It defines target data architecture, not current production deployment state.

---

# 00. Purpose

ILAIOS converts an authenticated user goal into governed autonomous execution and a verified finished product.

That process creates and consumes many kinds of data:

```text
identity
tenant membership
projects
goals
acceptance criteria
plans
jobs
tasks
state transitions
worker leases
tool calls
provider/model calls
knowledge
artifacts
artifact versions
validation
evidence
approvals
cost/usage
checkpoints
notifications
security events
```

Without a canonical data architecture, these records can fragment into parallel truths.

Therefore the data architecture must preserve:

```text
ONE canonical identity scope
ONE authoritative job/task state
ONE artifact lineage
ONE evidence/provenance truth
ONE tenant boundary
CLEAR separation of operational data, knowledge, artifacts, evidence, secrets, and observability
```

---

# 01. Data Architecture Scope

This document owns:

- canonical logical entities;
- identity and ownership fields;
- entity relationships;
- store responsibility boundaries;
- source-of-truth rules;
- data classification metadata;
- tenant/project isolation;
- job/task data model;
- execution event/state data;
- artifact/version model;
- evidence/provenance model;
- Knowledge/RAG data model;
- source-ingestion lineage;
- provider/tool call metadata;
- approvals;
- FinOps usage records;
- checkpoint state;
- notifications;
- retention/deletion concepts;
- backup/restore data invariants;
- integrity/versioning rules;
- cross-store reference rules;
- data migration principles;
- consistency/idempotency requirements.

This document does **not** own:

```text
API request/response wire contracts
    → API_CONTRACTS.md

security control architecture
    → SECURITY_ARCHITECTURE.md

threat scenarios
    → THREAT_MODEL.md

physical cloud topology
    → DEPLOYMENT_ARCHITECTURE.md

test methodology
    → TESTING_AND_EVALUATION.md

operational SLO/logging definitions
    → OBSERVABILITY.md

incident/recovery procedures
    → FAILURE_RECOVERY.md
```

---

# 02. Canonical Data Invariants

The following are hard invariants:

```text
NO protected record without owner/scope
NO tenant inferred solely from UI
NO cross-tenant join without explicit governed authority
NO artifact mutation without version lineage
NO validation detached from exact artifact version
NO evidence replaced by debug logs
NO secret values in ordinary application records
NO vector similarity treated as authorization
NO queue/workflow record without job/task identity
NO stale worker commit without lease/fencing validation
NO provider/model record as product authority
NO client-side filtering as tenant boundary
NO silent destructive overwrite of historical provenance
```

---

# 03. Canonical Logical Entity Chain

The primary entity lineage is:

```text
USER
  │
  ▼
ACCOUNT
  │
  ▼
PRINCIPAL
  │
  ▼
TENANT / ORGANIZATION
  │
  ▼
MEMBERSHIP / ROLE BINDING
  │
  ▼
PROJECT
  │
  ▼
GOAL
  │
  ▼
JOB / WORKFLOW
  │
  ▼
TASK
  │
  ├────────► AGENT RUN
  ├────────► TOOL CALL
  ├────────► PROVIDER / MODEL CALL
  ├────────► RETRIEVAL
  ├────────► APPROVAL
  └────────► WORKER LEASE
              │
              ▼
          ARTIFACT
              │
              ▼
       ARTIFACT VERSION
              │
              ▼
         VALIDATION
              │
              ▼
          EVIDENCE
              │
              ▼
     ACCEPTANCE MANIFEST
```

---

# 04. Canonical Store Architecture

```text
┌───────────────────────────────────────────────────────────────┐
│ OPERATIONAL STORE                                             │
│ Accounts / Principals / Tenants / Projects / Goals / Jobs    │
│ Tasks / Approvals / Config References                         │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│ WORKFLOW / DURABLE STATE                                      │
│ Queue / Task State / Events / Leases / Checkpoints           │
└──────────────────────────────┬────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
┌──────────────────┐ ┌──────────────────┐ ┌─────────────────────┐
│ KNOWLEDGE STORE  │ │ ARTIFACT STORE   │ │ EVIDENCE STORE      │
│ Sources          │ │ Files            │ │ Decisions           │
│ Units / Chunks   │ │ Images           │ │ Routes              │
│ Index / Graph    │ │ Video            │ │ Validations         │
│ Provenance       │ │ Packages         │ │ Provenance          │
└──────────────────┘ └──────────────────┘ └─────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│ SECRET / KEY STORE                                            │
│ Credentials / Encryption Keys / Signing References           │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│ OBSERVABILITY STORES                                          │
│ Logs / Metrics / Traces / Operational Diagnostics            │
└───────────────────────────────────────────────────────────────┘
```

These stores may map to one or several physical technologies.

Logical authority boundaries must remain distinct.

---

# 05. Store Responsibility Matrix

## Operational Store

Owns durable product entities:

```text
Account
Principal
Tenant
Membership
Project
Goal
Job
Task metadata
Approval metadata
Provider registry metadata
Capability registry references
configuration references
```

## Workflow / Durable State

Owns:

```text
queue state
task state
state transitions
worker leases
fencing tokens
checkpoint references
retry state
repair state
orchestration cursor
```

## Knowledge Store

Owns:

```text
sources
source versions
parsed units
chunks
embeddings/index references
knowledge graph relations
classification
authorization metadata
provenance
```

## Artifact Store

Owns:

```text
binary/text artifacts
artifact versions
large files
images
audio
video
build packages
generated websites
documents
```

## Evidence Store

Owns:

```text
material execution evidence
policy decisions
approval decisions
routing decisions
validation evidence
artifact integrity references
cost evidence
acceptance manifests
security events where canonical evidence is required
```

## Secret / Key Store

Owns secret values and cryptographic material.

## Observability Stores

Own operational telemetry.

---

# 06. Data Ownership Model

Every protected record must be classifiable as one of:

```text
SYSTEM
TENANT
PROJECT
PRINCIPAL
JOB
TASK
ARTIFACT
```

Most business/product data will include at least:

```text
tenant_id
```

Project-scoped data additionally includes:

```text
project_id
```

Execution-scoped data includes:

```text
job_id
task_id where applicable
```

---

# 07. Canonical Identifier Rules

Canonical IDs must be:

- stable;
- globally unique or unique within clearly defined scope;
- non-semantic where possible;
- immutable after creation;
- safe to reference across stores;
- independent of provider-specific IDs.

Recommended conceptual IDs:

```text
user_id
account_id
principal_id
tenant_id
membership_id
project_id
goal_id
job_id
task_id
agent_run_id
tool_call_id
provider_call_id
retrieval_id
approval_id
route_id
lease_id
checkpoint_id
artifact_id
artifact_version_id
validation_id
evidence_id
source_id
source_version_id
knowledge_unit_id
notification_id
```

---

# 08. External Identifier Mapping

External IDs may be retained as mappings:

```text
Google subject
Microsoft object ID
GitHub user ID
provider request ID
cloud resource ID
repository ID
external deployment ID
```

They must not replace canonical ILAIOS identity.

Example:

```text
ILAIOS principal_id
    │
    ├── Google subject
    ├── Microsoft subject
    └── GitHub user ID
```

---

# 09. User

`User` represents the product-level human identity concept.

Minimum conceptual attributes:

```text
user_id
display_name
preferred_locale
created_at
status
```

Sensitive identity details may live on account/identity records rather than User.

---

# 10. Account

`Account` represents an authentication/account relationship.

Conceptual attributes:

```text
account_id
user_id
provider_type
provider_subject
verified_email_ref
assurance metadata
linked_at
last_authenticated_at
status
```

Account linking must preserve evidence and security policy.

---

# 11. Principal

`Principal` is the canonical actor used by authorization.

Conceptual attributes:

```text
principal_id
principal_type
user_id or service identity ref
status
created_at
```

Principal types may include:

```text
human
service
system
```

Agent identities do not automatically equal authorization Principals unless architecture explicitly defines such a constrained service principal.

---

# 12. Tenant / Organization

`Tenant` is the primary isolation boundary.

Conceptual attributes:

```text
tenant_id
name
tenant_type
region/residency policy ref
security policy ref
data policy ref
billing/FinOps policy ref
status
created_at
```

No protected tenant data may be accessed using only a client-supplied tenant string.

---

# 13. Membership

Membership binds Principal to Tenant.

Conceptual fields:

```text
membership_id
tenant_id
principal_id
status
role_refs
attribute_refs
joined_at
expires_at optional
```

Authorization evaluates current membership state.

---

# 14. Role and Attribute Bindings

Authorization data may include:

```text
role_id
permission_id
principal_id
tenant_id
project_id optional
attribute key/value
policy reference
valid_from
valid_until
```

Role metadata must not become a substitute for policy evaluation.

---

# 15. Project

`Project` is the primary work-context boundary inside a Tenant.

Conceptual fields:

```text
project_id
tenant_id
name
purpose
classification_default
region/residency policy ref
knowledge scope ref
artifact namespace ref
created_by
created_at
status
```

---

# 16. Goal

A `Goal` records the user outcome request.

Conceptual fields:

```text
goal_id
tenant_id
project_id
requested_by_principal_id
original_prompt_ref
objective
risk_class
data_class
budget_ref
created_at
version
status
```

Goal mutation after execution begins must create a traceable version/change event.

---

# 17. Acceptance Criteria

Acceptance criteria belong to the Goal and are versioned.

Conceptual fields:

```text
acceptance_criteria_id
goal_id
version
criterion_type
criterion_text
required
evaluator_ref optional
created_at
```

Final acceptance must resolve the exact criteria version used.

---

# 18. Execution Proposal / Plan

Plan data is immutable or versioned after admission.

Conceptual fields:

```text
proposal_id
goal_id
plan_version
graph_hash
task_ids
topological_order
created_by
created_at
admission_state
```

If the plan materially changes:

```text
new plan version
+ evidence
+ re-admission
```

---

# 19. Job

`Job` is the authoritative execution instance for a Goal.

Conceptual fields:

```text
job_id
tenant_id
project_id
goal_id
plan_version
requested_by
state
state_sequence
budget_state_ref
created_at
started_at
ended_at
current_checkpoint_id
```

The client does not own Job state.

---

# 20. Task

`Task` is a bounded executable DAG node.

Conceptual fields:

```text
task_id
job_id
tenant_id
project_id
responsibility
dependency_task_ids
required_capabilities
risk_class
data_class
state
attempt
max_attempts
expected_output_contract
validation_contract
created_at
```

---

# 21. Task Dependency Data

Task dependencies must be persisted or deterministically reconstructable.

Rules:

- no self-dependency;
- all dependency IDs resolve;
- graph is acyclic;
- task completion state is version/sequence aware;
- downstream readiness is based on authoritative dependency completion.

---

# 22. Runtime State

Canonical runtime states include:

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

State is stored as authoritative platform state.

---

# 23. State Transition Event

Every meaningful transition creates a durable event.

Conceptual fields:

```text
event_id
tenant_id
project_id
job_id
task_id optional
sequence
from_state
to_state
reason_code
actor_ref
timestamp
evidence_ref
```

Sequence must prevent stale state from winning.

---

# 24. Event Ordering

At minimum:

```text
per-job state events
```

must be totally orderable.

Depending on implementation, ordering can use:

```text
monotonic sequence
database transaction version
event-stream offset
logical clock
```

Wall-clock timestamp alone is insufficient for authoritative ordering.

---

# 25. Worker Lease

`WorkerLease` owns temporary execution assignment.

Conceptual fields:

```text
lease_id
tenant_id
project_id
job_id
task_id
worker_id
grant_id
fencing_token
attempt
issued_at
expires_at
released_at
status
```

Lease is not permanent ownership.

---

# 26. Fencing Token

A fencing token protects state/artifacts from stale workers.

Required property:

```text
new valid lease
    must be distinguishable from
old expired lease
```

Commit attempts carrying stale fencing identity must fail.

---

# 27. ExecutionGrant Data

ExecutionGrant references belong in operational/workflow state; secret values do not.

Conceptual metadata:

```text
grant_id
tenant_id
project_id
job_id
task_id
principal_id
capability_id
scope summary
policy_decision_id
approval_id optional
issued_at
expires_at
revoked_at
```

Detailed permission contract belongs in implementation/API documents.

---

# 28. Policy Decision

Policy decisions are material evidence-bearing records.

Conceptual fields:

```text
policy_decision_id
tenant_id
project_id
job_id
task_id
principal_id
policy_version
decision
reason_codes
risk_class
data_class
issued_at
evidence_id
```

Decision values:

```text
ALLOW
DENY
REQUIRE_APPROVAL
```

---

# 29. Approval

Conceptual fields:

```text
approval_id
tenant_id
project_id
job_id
task_id
requested_action_hash
requested_scope
requested_by
approver_principal_id optional
decision
reason
created_at
decided_at
expires_at
revoked_at
evidence_id
```

A material action change requires a new approval decision.

---

# 30. Agent Run

Agent runs are orchestration records, not authority.

Conceptual fields:

```text
agent_run_id
tenant_id
project_id
job_id
task_id
agent_id
agent_version
input_refs
output_refs
started_at
ended_at
status
evidence_refs
```

---

# 31. Skill Invocation

Skill invocation metadata should retain:

```text
skill_id
skill_version
skill_digest
capability_id
agent_run_id or task_id
input_refs
output_refs
requested_permission summary
validation status
evidence_ref
```

The skill body itself may be versioned elsewhere.

---

# 32. RoutingDecision Data

One canonical `RoutingDecision` is persisted/evidenced.

Conceptual fields:

```text
route_id
tenant_id
project_id
job_id
task_id
capability_id
worker_class
provider_id
model_or_resource_id
adapter_id
reason_codes
quality_floor
privacy_class
residency
estimated_cost
fallback_refs
created_at
evidence_id
```

Routing metadata must not contain raw secret credentials.

---

# 33. Provider Registry Data

Provider metadata includes:

```text
provider_id
provider_type
adapter_id
enabled
supported_capabilities
supported_modalities
regions
privacy metadata
health reference
quota reference
cost model reference
version
```

Provider registry state is configuration/operational data.

It is not product authority.

---

# 34. Model / Resource Registry Data

Conceptual fields:

```text
model_or_resource_id
provider_id
capabilities
modalities
context limits
output limits
region support
cost metadata
enabled
version
```

Do not hard-code provider model IDs into product entities where a canonical route/reference suffices.

---

# 35. Provider Call

Provider calls are execution events.

Conceptual fields:

```text
provider_call_id
tenant_id
project_id
job_id
task_id
route_id
provider_id
model_or_resource_id
adapter_id
request_payload_ref
response_payload_ref
usage_ref
started_at
ended_at
status
provider_request_id optional
error_class optional
evidence_ref
```

Sensitive payloads may be stored separately, redacted, or not retained according to policy.

---

# 36. Tool Call

Conceptual fields:

```text
tool_call_id
tenant_id
project_id
job_id
task_id
tool_id
operation
grant_id
request_ref
result_ref
started_at
ended_at
status
error_class
evidence_ref
```

Raw tool output should not automatically enter evidence or prompt context without classification/validation.

---

# 37. Retrieval Request

Conceptual fields:

```text
retrieval_id
tenant_id
project_id
principal_id
job_id
task_id
purpose
query_ref
data_class
authorization_context_ref
created_at
status
evidence_ref
```

Retrieval itself is a governed action.

---

# 38. Source

A `Source` represents an authorized knowledge origin.

Conceptual fields:

```text
source_id
tenant_id
project_id
source_type
canonical_locator
owner_ref
classification
region
retention_policy_ref
authorization_policy_ref
created_at
status
```

Examples:

```text
uploaded document
web source
repository
database export
research record
manual note
connector source
```

---

# 39. Source Version

Source content must be versionable.

Conceptual fields:

```text
source_version_id
source_id
content_hash
content_ref
retrieved_or_uploaded_at
parser_version
classification_version
provenance
status
```

Derived knowledge must reference a specific source version.

---

# 40. Knowledge Unit

Knowledge unit is the retrievable canonical content unit.

Conceptual fields:

```text
knowledge_unit_id
tenant_id
project_id
source_id
source_version_id
unit_type
content_ref
content_hash
classification
purpose constraints
region
retention_policy_ref
authorization attributes
provenance
created_at
```

---

# 41. Chunk

A chunk is a retrieval/index representation of a Knowledge Unit.

Conceptual fields:

```text
chunk_id
knowledge_unit_id
source_version_id
chunk_index
content_ref
content_hash
token_count
embedding_ref optional
created_at
```

Chunk metadata must not lose tenant/project/source lineage.

---

# 42. Embedding Record

Embedding metadata:

```text
embedding_id
chunk_id
embedding_model_ref
dimension
vector_store_ref
created_at
content_hash
```

Embedding vectors do not contain authorization authority.

Authorization is evaluated from canonical metadata/policy.

---

# 43. Knowledge Graph Entity

Knowledge graph nodes/edges must retain source provenance.

Conceptual node:

```text
kg_entity_id
tenant_id
project_id
entity_type
canonical_label
attributes
provenance_refs
```

Conceptual edge:

```text
kg_edge_id
tenant_id
project_id
from_entity_id
to_entity_id
relation_type
confidence
provenance_refs
```

---

# 44. Retrieval Result

Every retrieved unit should carry:

```text
knowledge_unit_id
source_id
source_version_id
classification
authorization decision reference
relevance score
rerank score optional
provenance
```

The model should not receive a retrieval result detached from its security/provenance context.

---

# 45. AuthorizedContext

`AuthorizedContext` is an execution-time assembly, not a permanent universal memory dump.

Conceptual fields:

```text
context_id
tenant_id
project_id
job_id
task_id
purpose
knowledge_unit_refs
artifact_refs
policy_ref
created_at
expires_at optional
content_hash
```

Two-phase context architecture is preserved:

```text
minimal pre-plan context
+
task-scoped context
```

---

# 46. Memory Model

ILAIOS memory should distinguish:

```text
session memory
project memory
knowledge sources
artifact history
execution history
user preferences
organizational policy/context
```

These categories have different ownership, retention, and authorization rules.

They should not be collapsed into one opaque “memory” store.

---

# 47. Artifact

`Artifact` is a stable logical product/output identity.

Conceptual fields:

```text
artifact_id
tenant_id
project_id
job_id
artifact_type
classification
created_by_task_id
current_version_id
created_at
status
```

Artifact identity survives repairs/version changes.

---

# 48. Artifact Version

Conceptual fields:

```text
artifact_version_id
artifact_id
version_number or version token
content_hash
size
mime_type
storage_ref
producer_type
producer_ref
route_id optional
input_refs
created_at
supersedes_version_id optional
```

Artifact contents should be immutable for a version.

---

# 49. Artifact Types

Examples:

```text
website
source code
repository patch
application package
document
image
video
audio
research report
dataset
configuration
deployment package
render
generated archive
```

Artifact type controls validation/storage policy.

---

# 50. Artifact Storage Rule

Large content should use object/artifact storage.

Operational records should store:

```text
artifact_id
version_id
storage_ref
hash
metadata
```

rather than duplicating large binary payloads inside ordinary relational rows.

---

# 51. Content Addressing

Where useful, artifacts/evidence/source versions may use content hashes such as SHA-256.

Hash supports:

```text
integrity
deduplication
lineage
exact validation binding
tamper detection
```

Hash alone does not prove authorization or trustworthiness.

---

# 52. Validation Result

Conceptual fields:

```text
validation_id
tenant_id
project_id
job_id
task_id optional
artifact_id
artifact_version_id
validator_id
validator_version
validation_type
result
failure_codes
metrics
created_at
evidence_id
```

Validation must always identify the exact artifact version.

---

# 53. Evaluation Result

Final evaluation extends validation across the complete product.

Conceptual fields:

```text
evaluation_id
goal_id
job_id
artifact_version_refs
acceptance_criteria_version
evaluator_refs
result
failure_classification
created_at
evidence_ref
```

---

# 54. Evidence Record

Conceptual fields:

```text
evidence_id
tenant_id
project_id
job_id
task_id optional
event_type
actor_ref
timestamp
input_refs
output_refs
decision_refs
artifact_refs
content_hash
metadata
classification
```

Evidence is append-oriented and integrity-verifiable according to criticality.

---

# 55. Evidence Event Types

Examples:

```text
goal.accepted
plan.proposed
plan.admitted
policy.decision
approval.requested
approval.decided
route.selected
worker.leased
tool.called
provider.called
retrieval.performed
artifact.created
artifact.versioned
validation.completed
repair.started
checkpoint.created
cost.recorded
delivery.requested
delivery.completed
security.violation
```

---

# 56. Provenance Chain

```text
Goal + Acceptance
      │
      ▼
Plan Version
      │
      ▼
Policy / Approval
      │
      ▼
RoutingDecision
      │
      ▼
Tool / Provider / Retrieval Events
      │
      ▼
Artifact Version
      │
      ▼
Validation / Evaluation
      │
      ▼
Evidence Chain
      │
      ▼
AcceptanceManifest
```

---

# 57. AcceptanceManifest

Conceptual fields:

```text
acceptance_manifest_id
tenant_id
project_id
job_id
goal_id
accepted_artifact_version_refs
acceptance_criteria_version
validation_refs
evaluation_refs
policy_refs
approval_refs
routing_refs
cost_refs
evidence_root_ref
created_at
manifest_hash
```

It must answer why a product was accepted.

---

# 58. Checkpoint

Conceptual fields:

```text
checkpoint_id
tenant_id
project_id
job_id
task_id optional
runtime_state
completed_task_ids
pending_task_ids
artifact_refs
evidence_cursor
budget_state_ref
retry_state
route_refs
context_refs
created_at
integrity_hash
```

Checkpoint data is durable workflow state.

---

# 59. Retry / Repair State

Conceptual fields:

```text
job_id
task_id
attempt_count
repair_count
provider_failover_count
spent_cost
elapsed_time
last_failure_id
remaining_bounds
```

The persisted values must enforce:

```text
max_attempts
max_cost
max_elapsed_time
```

---

# 60. Failure Record

Conceptual fields:

```text
failure_id
tenant_id
project_id
job_id
task_id
failure_class
error_code
safe_message
diagnostic_ref
retryable
repairable
created_at
evidence_ref
```

Sensitive diagnostics belong in protected operational storage, not broad user-visible fields.

---

# 61. Cost / Usage Record

Conceptual fields:

```text
usage_id
tenant_id
project_id
job_id
task_id
route_id
provider_id optional
model_or_resource_id optional
tool_id optional
input_units
output_units
runtime_units
external_cost
currency
retry_number
created_at
evidence_ref
```

FinOps calculations belong in `FINOPS.md`.

---

# 62. Notification

Conceptual fields:

```text
notification_id
tenant_id
principal_id
project_id optional
job_id optional
notification_type
safe_payload_ref
created_at
delivered_at
read_at
status
```

Notification content must not expose protected data beyond recipient authorization.

---

# 63. Configuration Data

Configuration should distinguish:

```text
platform config
environment config
tenant config
project config
feature flag config
provider config
security policy refs
FinOps policy refs
```

Configuration records should be versioned where behavior/audit depends on them.

---

# 64. Policy Versioning

Material policy decisions should reference:

```text
policy_id
policy_version
```

so historical decisions can be interpreted accurately after policy updates.

---

# 65. Capability Registry Data

Canonical capability records include:

```text
capability_id
display_name
domain
dependencies
implementation roots
legacy provenance
maturity metadata if stored
schema/version
```

The canonical namespace remains:

```text
ilaios.capability.*
```

---

# 66. Capability Maturity Data

Canonical maturity values:

```text
DESIGNED
SPECIFIED
IMPLEMENTED
TESTED
VERIFIED
DEPLOYED / PRODUCTION
```

`DEPRECATED` is a lifecycle exit state.

A maturity record should reference evidence supporting the transition.

---

# 67. Agent Registry Data

Agent records should include:

```text
agent_id
version
purpose
allowed_capabilities
authority ceiling
allowed callers
allowed targets
risk ceiling
status/maturity
manifest hash
```

Agent registry data does not create authorization by itself.

---

# 68. Skill Registry Data

Skill registry records should include:

```text
skill_id
version
capability_id
content digest
approved authority set
network policy ref
filesystem policy ref
secret policy ref
provenance
status/maturity
```

---

# 69. Worker Registry / Runtime Data

Worker runtime metadata includes:

```text
worker_id
worker_class
runtime_environment
supported_capabilities
isolation_class
health
version
last_seen
current_lease_id optional
```

Worker health is operational data, not permanent evidence truth by itself.

---

# 70. Tool Registry Data

Tool metadata may include:

```text
tool_id
adapter_id
supported_operations
risk class
required permissions
network requirements
secret requirements
sandbox requirements
version
status
```

---

# 71. Store Boundary: Operational vs Evidence

Operational records may change:

```text
job.current_state
provider.health
membership.status
feature_flag
```

Evidence records represent historical facts:

```text
policy decision at time T
route selected at time T
artifact hash at time T
approval at time T
```

Do not overwrite evidence to match current operational state.

---

# 72. Store Boundary: Artifact vs Evidence

Artifact Store:

```text
what was produced
```

Evidence Store:

```text
how/why it was produced and accepted
```

A video file is not an evidence record.

A hash/validation proving the video version is accepted is evidence.

---

# 73. Store Boundary: Knowledge vs Artifact

A document may exist as:

```text
Artifact
    if produced/owned as project output

Source / Knowledge
    if ingested for retrieval

Both
    if an artifact is intentionally promoted into project knowledge
```

If promoted, the knowledge representation must reference the artifact version and preserve classification/provenance.

---

# 74. Store Boundary: Logs vs Evidence

Logs are mutable/operational telemetry.

Evidence is canonical proof.

Logs may expire sooner and may contain diagnostic detail.

Evidence retention follows governance/legal/security policy.

---

# 75. Store Boundary: Secrets vs Configuration

Configuration stores:

```text
secret_reference = "vault://..."
```

Secret store contains the actual credential.

Never:

```text
config.api_key = "real-secret"
```

for production secrets.

---

# 76. Tenant Isolation Across Stores

Tenant boundary must survive:

```text
Operational DB
Queue
Workflow state
Cache
Knowledge index
Knowledge graph
Object storage
Evidence store
Search index
Worker lease
Logs
Backup/restore
```

---

# 77. Tenant Query Rule

Protected read/write operations require server-side scope.

Conceptual query condition:

```text
requested_object.tenant_id
    must equal
authorized_context.tenant_id
```

plus project/resource authorization where applicable.

Client-side tenant filtering is never sufficient.

---

# 78. Global/System Records

Some records may be system-scoped:

```text
canonical capability definitions
global provider descriptors
platform policy templates
system migration metadata
```

System-scoped data must be explicitly marked.

A missing tenant_id must not automatically imply “global”.

---

# 79. Cross-Tenant Shared Resources

If a resource is intentionally shared:

```text
shared_resource_id
owner_scope
allowed_tenant_refs
policy
classification
```

must be explicit.

Cross-tenant sharing is not inferred.

---

# 80. Data Classification

Minimum classes:

```text
PUBLIC
INTERNAL
CONFIDENTIAL
RESTRICTED
```

Classification can inherit:

```text
tenant default
→ project default
→ source/artifact override
```

More restrictive classification wins unless governed policy explicitly permits otherwise.

---

# 81. Classification Propagation

Derived data should inherit or calculate classification conservatively.

Examples:

```text
RESTRICTED source
    → derived chunk is not PUBLIC

CONFIDENTIAL artifact
    → validation text containing artifact content is protected

secret-containing tool output
    → redacted derivative before broad telemetry
```

---

# 82. Purpose Metadata

Purpose is part of authorization for sensitive data.

Conceptual values may include:

```text
planning
execution
retrieval
evaluation
support
security
billing
operations
```

Purpose metadata must not be free-form authority.

Policy controls allowed purpose transitions.

---

# 83. Residency Metadata

Residency-related data may include:

```text
tenant_region_policy
source_region
storage_region
processing_region
provider_region
```

Routing and storage choices must obey effective residency policy.

---

# 84. Retention Metadata

Records requiring governed lifecycle should reference:

```text
retention_policy_id
retention_class
created_at
expires_at optional
legal_hold optional
deletion_state
```

Retention policy is not always “longest possible”.

---

# 85. Retention Categories

Different data classes may require different retention:

```text
session records
job state
task state
prompts
provider payloads
artifacts
knowledge
evidence
security evidence
billing records
observability
backups
secrets metadata
```

---

# 86. Deletion States

Deletion lifecycle may include:

```text
ACTIVE
DELETION_REQUESTED
LOGICALLY_DELETED
PURGED_ACTIVE_STORE
AWAITING_BACKUP_EXPIRY
RETAINED_BY_POLICY
PURGED
```

Exact status names may be refined later; the conceptual distinction must exist.

---

# 87. Legal / Security Hold

A deletion request may conflict with a legal/security retention requirement.

The system must distinguish:

```text
user-requested deletion
vs
authorized policy hold
```

and preserve evidence of the governing decision.

---

# 88. Derived Data Deletion

Deleting a source may require propagation to:

```text
parsed units
chunks
embeddings
knowledge graph edges
cached context
derived indexes
```

Deletion semantics must be explicit.

---

# 89. Provider-Side Data

External provider retention may not be fully controlled by ILAIOS.

The system should track, where relevant:

```text
provider_id
data handling policy ref
retention configuration
processing region
request identifiers
```

ILAIOS must not promise deletion guarantees it cannot enforce externally.

---

# 90. Caching

Caches are non-authoritative unless explicitly defined otherwise.

Cache rules:

```text
key includes tenant/project scope where required
TTL
classification-aware handling
safe invalidation
no secret values unless specialized secure cache
no cross-tenant key collision
```

Cache misses must reconstruct from authoritative stores.

---

# 91. Search Indexes

Search indexes are derived stores.

They must preserve:

```text
tenant/project scope
source object ID
classification
authorization attributes
source version
```

Index results require authorization before content release.

---

# 92. Vector Indexes

Vector index metadata must preserve:

```text
chunk_id
tenant_id
project_id
source_version_id
classification
authorization metadata
```

Similarity is relevance, not permission.

---

# 93. Knowledge Graph Consistency

Knowledge graph facts should maintain provenance and confidence.

Avoid turning model inference into an unqualified canonical fact.

Conceptual relation metadata:

```text
provenance
confidence
verification status
created_by
created_at
source_version
```

---

# 94. Claim Model

Research/knowledge may use a Claim entity:

```text
claim_id
tenant_id
project_id
claim_text_ref
verification_status
source_refs
confidence
created_at
```

Useful states:

```text
UNVERIFIED
SUPPORTED
CONFLICTED
REJECTED
```

These are knowledge-claim semantics, not capability maturity states.

---

# 95. Provenance Requirements

Provenance should answer:

```text
Where did this data come from?
Which version?
Who/what created it?
Under which tenant/project?
Which transformation produced it?
Which artifact/source inputs were used?
Which model/tool/provider participated?
```

---

# 96. Lineage Graph

```text
SOURCE VERSION
      │
      ▼
PARSED UNIT
      │
      ▼
KNOWLEDGE UNIT / CHUNK
      │
      ▼
AUTHORIZED RETRIEVAL
      │
      ▼
TASK INPUT
      │
      ▼
TOOL / MODEL / WORKER
      │
      ▼
ARTIFACT VERSION
      │
      ▼
VALIDATION
      │
      ▼
EVIDENCE
```

---

# 97. Artifact Lineage Example — Website

```text
Business Source
    │
    ▼
Authorized Context
    │
    ▼
Website Goal / Plan
    │
    ▼
Copy + Design + Code Artifacts
    │
    ▼
Build Artifact
    │
    ▼
Browser / Security / A11y / Performance Validation
    │
    ▼
Accepted Website Version
    │
    ▼
AcceptanceManifest
```

---

# 98. Artifact Lineage Example — Video

```text
Research Sources
    │
    ▼
Script
    │
    ▼
Storyboard / Shot Plan
    │
    ▼
Generated Media Assets
    │
    ▼
Canonical Timeline
    │
    ▼
Rendered Video Version
    │
    ▼
Video / Audio Validation
    │
    ▼
Accepted Video Version
```

---

# 99. Artifact Lineage Example — Software

```text
Repository Commit / Snapshot
    │
    ▼
Change Proposal
    │
    ▼
Patch / Code Changes
    │
    ▼
Test Results
    │
    ▼
Build Artifact
    │
    ▼
Diff / Review Evidence
    │
    ▼
PR / Release Candidate
```

---

# 100. Mutable vs Immutable Data

Prefer immutable/versioned records for:

```text
Goal versions
Plan versions
Artifact versions
Source versions
Policy decisions
Approvals
Routing decisions
Evidence
Validation
Acceptance manifests
```

Mutable operational state may include:

```text
current job state
current provider health
current membership status
current queue ownership
current feature flag
```

Historical transitions remain recorded.

---

# 101. Append-Only / Event-Oriented Records

Security/authority-sensitive events should be append-oriented.

Examples:

```text
state transition
policy decision
approval
route decision
secret access event
artifact version creation
validation
evidence
```

Corrections should usually create a new record referencing the old one rather than silently rewriting history.

---

# 102. Idempotency

Replay-sensitive mutations need idempotency.

Examples:

```text
job creation
payment
external send
deployment
artifact commit
provider submission where supported
approval action
```

Conceptual fields:

```text
idempotency_key
scope
request_hash
result_ref
created_at
expires_at
```

---

# 103. Optimistic Concurrency

Mutable records may use:

```text
version
etag
updated_at + version
transaction sequence
```

to reject lost updates.

Authoritative state should never rely on unguarded last-write-wins.

---

# 104. Transactions

Transactions should preserve invariants when multiple authoritative records change together.

Examples:

```text
job state + state transition
lease assignment + fencing increment
approval decision + grant issuance
artifact version + current version pointer
```

Distributed side effects may require outbox/saga/compensation patterns.

---

# 105. Outbox / Event Publication

If events are published to queues/buses, use a pattern that avoids:

```text
database says committed
but event was lost
```

Conceptually:

```text
authoritative transaction
    + durable outbox
    → event publication
```

Exact implementation belongs downstream.

---

# 106. Queue Message Data

Queue/task messages must carry references and scoped metadata, not broad sensitive payloads where avoidable.

Minimum:

```text
tenant_id
project_id
job_id
task_id
capability_id
grant_id
lease/fencing context
input refs
```

---

# 107. Queue Data Security

Queue systems must preserve:

- tenant scope;
- message integrity;
- retry/dead-letter semantics;
- visibility/lease semantics;
- no broad secret payloads;
- bounded retention.

---

# 108. Dead-Letter Data

Failed messages may enter DLQ/dead-letter storage.

They remain protected data.

DLQ must not become an ungoverned archive of sensitive payloads.

---

# 109. Checkpoint Data Integrity

Checkpoint integrity must verify:

```text
state
artifact refs
evidence cursor
budget/retry state
task completion set
```

Resume must not trust a corrupted checkpoint.

---

# 110. Cancellation Data

Cancellation requires records for:

```text
requested_by
requested_at
authorization result
state transition
worker cancellation attempts
late-result fencing
final cancellation state
side effects already committed
compensation result if applicable
```

---

# 111. Compensation Data

For reversible external side effects:

```text
original_action_id
compensation_action_id
reason
status
provider/tool refs
evidence refs
```

must maintain lineage.

---

# 112. Secrets Metadata

Secret values live in Secret/Key Store.

Ordinary stores may retain metadata:

```text
secret_ref
owner scope
purpose
provider
created_at
rotated_at
expires_at
status
```

Never persist raw secret values in evidence.

---

# 113. Key Metadata

Cryptographic key metadata may include:

```text
key_ref
key_purpose
algorithm
owner scope
created_at
rotation policy
status
```

Private key material remains in governed key service.

---

# 114. Observability Data Model

Operational telemetry may include:

```text
timestamp
tenant-safe identifiers
job_id
task_id
capability_id
route_id
worker_id
provider_id where safe
tool_id where safe
latency
status
error class
resource usage
```

Protected payload content should be minimized/redacted.

---

# 115. Audit/Evidence Data vs Telemetry

A log line may be sampled or expired.

A material evidence record must remain according to evidence policy.

Therefore:

```text
observability availability
≠
evidence correctness
```

---

# 116. Data Access Patterns

Primary access patterns include:

```text
Principal → memberships
Tenant → projects
Project → goals/jobs/artifacts/knowledge
Goal → plans/jobs
Job → tasks/state/events/evidence
Task → calls/artifacts/validation
Artifact → versions/validation/evidence
Source → versions/knowledge units
Knowledge unit → chunks/index/provenance
Evidence → referenced decisions/artifacts
```

Physical schema should optimize these without breaking boundaries.

---

# 117. Data Reference Pattern

Cross-store relationships should use canonical references:

```text
artifact_version_id
source_version_id
evidence_id
route_id
policy_decision_id
```

rather than copying mutable foreign payloads.

---

# 118. Referential Integrity

Where strong DB foreign keys are not possible across technologies, application/contract-level integrity must still be verifiable.

Broken critical references should fail validation rather than silently disappear.

---

# 119. Soft References

External resources may use soft references:

```text
external_repository_ref
cloud_resource_ref
provider_request_ref
deployment_ref
```

Soft references require clear failure behavior when external resource disappears.

---

# 120. Data Serialization

Canonical durable contracts should define:

```text
schema version
field names
timestamp format
ID format
enum values
nullability
normalization
```

Exact API encoding belongs in `API_CONTRACTS.md`.

---

# 121. Timestamp Rules

Use unambiguous machine timestamps.

Recommended:

```text
UTC
ISO-8601 compatible representation
```

Preserve user locale/timezone separately for presentation/business logic.

---

# 122. Clock Assumptions

Do not use wall clock alone for distributed ordering.

Use:

```text
sequence
transaction version
fencing token
event offset
```

for authoritative ordering.

---

# 123. Data Integrity Hashes

Hashes may protect:

```text
artifact versions
source versions
skill content
checkpoint content
acceptance manifest
evidence batch/root
```

Hash algorithm must be versionable.

---

# 124. Evidence Integrity

Evidence architecture should support tamper detection.

Possible approaches:

```text
content hashes
hash chains
signed records
append-only storage
Merkle roots
immutable object versions
```

Exact implementation may vary by deployment/risk.

---

# 125. Data Encryption

Data architecture assumes encryption:

```text
in transit
at rest
```

for protected data.

Sensitive fields may require additional encryption.

Encryption key ownership belongs to Security Architecture/Key Management.

---

# 126. PII Handling

PII records must carry or inherit classification.

PII may appear in:

```text
identity
user prompts
documents
knowledge
tool output
artifacts
evidence
logs
```

Broad replication must be minimized.

---

# 127. Secret Detection / Redaction

Before data enters broad telemetry or external provider context:

```text
secret detection
DLP
redaction/minimization
```

may apply according to policy.

---

# 128. Model Input Retention

Model/provider payload retention should be configurable according to:

```text
provider behavior
tenant policy
data classification
debugging need
legal/security requirements
```

Do not assume every raw prompt/response must be stored forever.

---

# 129. Prompt Record Strategy

Recommended conceptual separation:

```text
original user request
    durable product record

derived internal prompts
    execution data with policy-driven retention

provider wire payloads
    sensitive execution data, minimized retention
```

---

# 130. Context Snapshot Strategy

For reproducibility/evidence, store references to exact context units rather than always copying entire context blobs.

Conceptually:

```text
AuthorizedContext
    → knowledge_unit_ids
    → artifact_version_ids
    → policy version
    → hash
```

---

# 131. Provider Response Strategy

Store:

```text
normalized result
usage
provider request ID
route ref
artifact/result ref
```

Raw response retention is policy-dependent.

---

# 132. File Upload Data

Uploaded files require:

```text
artifact/source identity
tenant/project
original filename
normalized MIME type
size
content hash
classification
malware/safety status
storage ref
created_by
created_at
```

Do not use filename alone as canonical identity.

---

# 133. File Naming

User-visible filenames may change.

Canonical references use immutable IDs.

This avoids broken lineage after rename.

---

# 134. Large Media Data

Video/audio/image data belong in object storage.

Operational DB stores metadata/references.

Temporary processing files should use ephemeral scoped storage with cleanup policy.

---

# 135. Build / Package Data

Build artifacts should retain:

```text
source commit/ref
build configuration ref
dependency lock hash
CI/test refs
artifact hash
created_at
```

where relevant.

---

# 136. Repository Snapshot Data

Software Factory may record:

```text
repository_id
owner
canonical URL/ref
base branch
base commit SHA
working branch
target commit
```

Repository content itself may remain external rather than copied wholesale.

---

# 137. Deployment Record

A deployment action is separate from artifact creation.

Conceptual fields:

```text
deployment_id
tenant_id
project_id
job_id
artifact_version_id
environment
target_ref
requested_by
approval_ref
started_at
completed_at
status
verification_ref
evidence_ref
```

This is a historical action record.

---

# 138. Live Health Data

Current live health is mutable operational telemetry.

It belongs in observability/runtime status.

Do not encode `LIVE_HEALTHY` as permanent artifact metadata.

---

# 139. Release Record

Release metadata may include:

```text
release_id
artifact_version_refs
version/tag
environment/channel
approval_ref
deployment_refs
created_at
evidence_ref
```

Release policy belongs to Governance.

---

# 140. Multi-Region Data

If multi-region deployment is used, data architecture must explicitly define:

```text
authoritative region
replication rules
write ownership
read replicas
residency constraints
failover
conflict handling
```

Do not assume active-active multi-writer semantics.

---

# 141. Replication

Replicated data must preserve:

- tenant isolation;
- encryption;
- version/order;
- deletion propagation;
- retention;
- evidence integrity.

---

# 142. Backup Data Model

Backup metadata should include:

```text
backup_id
store
scope
created_at
encryption key ref
retention
region
integrity status
restore test ref
```

Backup state is operational data.

---

# 143. Restore Invariants

Restore must preserve:

```text
canonical IDs
tenant ownership
artifact hashes
evidence lineage
policy references
fencing/version state where needed
```

Restore must not resurrect revoked secrets as valid credentials.

---

# 144. Data Migration

Every breaking data migration needs:

```text
migration_id
from_schema
to_schema
affected entities
tenant impact
backfill strategy
validation
rollback
evidence
```

Migration must not create two indefinite sources of truth.

---

# 145. Schema Versioning

Schema versions may apply to:

```text
API contracts
durable events
artifacts metadata
evidence
knowledge units
checkpoints
configuration
```

Consumers must reject unsupported breaking versions safely.

---

# 146. Dual-Read / Dual-Write Migration

Temporary compatibility may require dual behavior.

Rules:

```text
time-bounded
explicit owner
explicit retirement condition
consistency checks
no permanent parallel authority
```

---

# 147. Data Quality

Data quality controls may include:

```text
required fields
enum validation
referential integrity
hash validation
deduplication
normalization
classification validation
provenance completeness
```

---

# 148. Deduplication

Deduplication may use content hashes but must preserve logical ownership.

Same bytes across two tenants do not automatically imply shared authorization.

Physical dedupe must never weaken logical isolation.

---

# 149. Data Lineage Definition of Done

A material artifact lineage is complete when it can resolve:

```text
tenant/project
goal
plan
task
inputs
authorized context
route
provider/tool/worker
artifact version
validation
evidence
acceptance
delivery
```

---

# 150. Tenant Isolation Definition of Done

Data isolation is `VERIFIED` for a defined scope only when negative tests prove:

```text
Tenant A cannot read Tenant B operational records
Tenant A cannot retrieve Tenant B knowledge
Tenant A cannot access Tenant B artifacts
Tenant A cannot inspect Tenant B evidence
Tenant A cannot receive Tenant B queue/task state
Tenant A cannot use Tenant B secret refs
search/index paths also deny cross-tenant access
```

---

# 151. Knowledge Data Definition of Done

Knowledge/RAG data architecture requires:

```text
source identity
source versioning
classification
tenant/project ownership
provenance
knowledge units
chunks/index references
authorization metadata
retrieval evidence
source-grounded output linkage
deletion propagation
negative isolation tests
```

---

# 152. Artifact Data Definition of Done

Artifact system requires:

```text
stable artifact_id
immutable/versioned content
content hash
tenant/project scope
storage reference
exact validation binding
provenance
repair version lineage
retention/deletion policy
```

---

# 153. Evidence Data Definition of Done

Evidence system requires:

```text
stable evidence IDs
tenant/project scope
material event taxonomy
integrity verification
artifact/version references
decision references
append-oriented history
privacy-aware metadata
acceptance manifest support
```

---

# 154. Workflow State Definition of Done

Durable workflow state requires:

```text
job/task IDs
valid state machine
sequenced transitions
leases
fencing
checkpoint
retry/repair state
cancel state
recovery tests
stale commit rejection
```

---

# 155. Data Security Definition of Done

Data architecture is not production-ready until:

```text
encryption controls
server-side tenant enforcement
classification
DLP/minimization
secret-store separation
backup protection
restore validation
retention/deletion policy
cross-tenant negative tests
```

exist for the defined scope.

---

# 156. Data Access Governance

Every data access is evaluated through:

```text
Principal
+ Tenant
+ Project
+ Resource
+ Action
+ Purpose
+ Classification
+ Policy
```

No storage technology may bypass the canonical authorization model.

---

# 157. Administrative Data Access

Administrative access must be explicitly scoped.

Operational support should not imply unrestricted access to tenant content.

High-risk support/security access may require:

```text
strong auth
break-glass
reason
approval
evidence
time limit
```

---

# 158. Analytics Data

Product analytics should use minimized/pseudonymized data where feasible.

Analytics pipelines must not become an uncontrolled copy of all tenant content.

Analytics datasets require:

```text
purpose
classification
retention
owner
access policy
```

---

# 159. Training / Model Improvement Data

Tenant/user data must not automatically become training data for ILAIOS or external providers.

Any future training/improvement use requires explicit governed policy, legal/privacy basis, data classification handling, and user/tenant controls as applicable.

---

# 160. Export Data

Tenant/project data export must be governed.

Export may include:

```text
operational metadata
artifacts
knowledge sources
evidence
```

depending on policy.

Export must not include:

- other tenants;
- internal secrets;
- protected system configuration;
- unrelated provider credentials.

---

# 161. Import Data

Imports require:

```text
source verification
schema validation
classification
tenant assignment
provenance
malware/content safety checks where relevant
```

Imported records cannot overwrite canonical IDs without controlled migration rules.

---

# 162. Data Portability

Where product policy supports portability, export formats should preserve enough metadata for:

```text
ownership
version
timestamps
provenance
artifact relationships
```

without exposing internal secrets.

---

# 163. Search Data

Search results should return references to authorized canonical entities.

Search does not create alternate object truth.

---

# 164. Notification Data Minimization

Notifications should use:

```text
safe summary
stable entity reference
deep link/reference
```

instead of embedding full sensitive task/artifact content.

---

# 165. Data Auditability

Material data lifecycle events may require evidence:

```text
created
classified
shared
exported
deleted
restored
migrated
retention hold applied
```

depending on risk/policy.

---

# 166. Current Reality vs Target Data Architecture

This document defines the target data architecture.

Current reality is determined from:

```text
current schemas
current code
current tests
current CI
runtime data behavior
deployment/storage evidence
```

Therefore:

```text
DATA_ARCHITECTURE.md says a store/entity must exist
≠
proof it is currently production-deployed
```

Mutable implementation status belongs in milestones/evidence, not this canonical data architecture.

---

# 167. Data Red Lines

Reject implementations that create:

```text
tenant inferred from frontend state
vector retrieval without authorization
artifact overwrite without version
validation without artifact version ref
evidence stored only as log text
secrets inside ordinary application rows
provider IDs as canonical user identity
two authoritative job state stores
two evidence truths
two capability identity stores
cross-store records with no owner/scope
unbounded cache as source of truth
silent data migration without evidence
```

---

# 168. Canonical Data Flow

```text
AUTHENTICATED PRINCIPAL
        │
        ▼
TENANT / PROJECT
        │
        ▼
GOAL
        │
        ▼
PLAN / JOB / TASK
        │
        ├──────────────► WORKFLOW STATE
        │
        ├──────────────► AUTHORIZED CONTEXT
        │                    │
        │                    ▼
        │              KNOWLEDGE STORE
        │
        ├──────────────► ROUTING / PROVIDER / TOOL EVENTS
        │
        ▼
EXECUTION
        │
        ▼
ARTIFACT VERSION
        │
        ├──────────────► ARTIFACT STORE
        │
        ▼
VALIDATION / EVALUATION
        │
        ▼
EVIDENCE
        │
        ▼
ACCEPTANCE MANIFEST
        │
        ▼
DELIVERY / DEPLOYMENT RECORD
```

---

# 169. Canonical Store Formula

```text
OPERATIONAL STORE
    = who / what / current durable product state

WORKFLOW STATE
    = where execution currently is and how it resumes

KNOWLEDGE STORE
    = authorized source-derived context

ARTIFACT STORE
    = what ILAIOS produced or owns as file/object output

EVIDENCE STORE
    = why/how material actions/results occurred and were accepted

SECRET / KEY STORE
    = protected credentials and cryptographic material

OBSERVABILITY STORES
    = operational diagnostics and performance signals
```

---

# 170. Final Data Invariant

The defining ILAIOS data rule is:

> **Every material record must be attributable, scoped, versioned where necessary, lifecycle-governed, and traceable to its authoritative context.**

The data architecture must always allow ILAIOS to answer:

```text
Who owns this?
Which tenant?
Which project?
Why does it exist?
Which version is this?
Where did it come from?
Who/what produced it?
Which policy applied?
Which artifact/source does it reference?
How long should it exist?
Can this principal access it?
What evidence proves its history?
```

If the system cannot answer those questions for security- or product-critical data, the data model is incomplete.

**ILAIOS data is not a pile of prompts and files. It is a governed graph of identity, execution, artifacts, knowledge, and evidence.**
