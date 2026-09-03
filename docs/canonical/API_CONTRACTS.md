# ILAIOS — API CONTRACTS

**Document Type:** Canonical API & Cross-Boundary Contract Specification  
**Format:** GitHub Markdown + YAML/JSON-style contract examples  
**Status:** Canonical Baseline v1.0 — Published in Repository  
**Architecture Authority:** `SYSTEM_ARCHITECTURE.md`  
**Product Authority:** `PRODUCT_REQUIREMENTS.md`  
**Implementation Authority:** `IMPLEMENTATION_SPEC.md`  
**Dependency Authority:** `DEPENDENCY_GRAPH.md`  
**Security Authority:** `SECURITY_ARCHITECTURE.md`  
**Data Authority:** `DATA_ARCHITECTURE.md`  
**Core API Principle:** **CLIENTS EXPRESS INTENT; THE CONTROL PLANE OWNS AUTHORITY**

> This document defines the **canonical public API boundaries and internal cross-boundary contracts** of ILAIOS. It defines schemas, invariants, compatibility rules, idempotency, errors, asynchronous job/event behavior, authorization context, and the contract surfaces between Control Plane, policy, routing, scheduler, workers, tools, providers, Knowledge/RAG, factories, artifacts, evaluation, and evidence. It does not claim that every endpoint described here is currently implemented or deployed.

---

# 00. Purpose

ILAIOS must expose one coherent product while preserving strict internal authority boundaries.

The public experience is:

```text
Authenticated Client
      │
      ▼
ILAIOS Control Plane API
      │
      ▼
Goal / Job
      │
      ▼
Governed Autonomous Execution
      │
      ▼
Artifact + Evidence
```

The public experience is **not**:

```text
Client
  ├─ directly selects privileged worker
  ├─ directly invokes provider with platform credentials
  ├─ directly mints ExecutionGrant
  ├─ directly mutates authoritative job state
  └─ directly bypasses policy/routing/tool gateway
```

This document therefore separates:

```text
PUBLIC CLIENT CONTRACTS
INTERNAL CONTROL CONTRACTS
RUNTIME CONTRACTS
TOOL CONTRACTS
PROVIDER ADAPTER CONTRACTS
KNOWLEDGE CONTRACTS
FACTORY CONTRACTS
ARTIFACT / EVIDENCE CONTRACTS
EVENT CONTRACTS
```

---

# 01. Contract Authority

For API behavior:

```text
SYSTEM_ARCHITECTURE.md
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
        ▼
API_CONTRACTS.md
```

This file may define the exact contract representation of an upstream architectural concept.

It must not change the meaning or authority of that concept.

Example:

```text
SYSTEM_ARCHITECTURE
    says Policy Gateway owns execution admission

API_CONTRACTS
    defines ExecutionRequest / PolicyDecision / ExecutionGrant schemas

API_CONTRACTS
    may NOT make the client the Policy Gateway
```

---

# 02. Target Truth vs Current Reality

This document is **target contract truth**.

Current API reality must be established from:

```text
current code
current schemas
current tests
current CI
current runtime
current deployment evidence
```

Therefore:

```text
contract documented
≠ endpoint implemented
≠ endpoint tested
≠ endpoint deployed
≠ endpoint currently healthy
```

Mutable implementation status belongs in evidence / milestones / operational status, not this canonical contract authority.

---

# 03. API Planes

ILAIOS uses several contract planes.

```text
┌──────────────────────────────────────────────────────────────┐
│ PUBLIC CLIENT API                                            │
│ Web / Desktop / Mobile / CLI / External API Client          │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ CONTROL PLANE CONTRACTS                                      │
│ Identity / Project / Goal / Job / Approval / Artifacts      │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ INTERNAL GOVERNANCE CONTRACTS                                │
│ Policy / ExecutionGrant / Routing / Capability Resolution   │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ RUNTIME CONTRACTS                                            │
│ Queue / Task / Lease / Worker / State / Checkpoint          │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ TOOL / PROVIDER CONTRACTS                                    │
│ Tool Gateway / Adapter / ProviderRequest / ProviderResult   │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ OUTPUT CONTRACTS                                             │
│ Artifact / Validation / Evidence / AcceptanceManifest       │
└──────────────────────────────────────────────────────────────┘
```

---

# 04. Public vs Internal Contract Rule

## Public contracts

May be used by authorized product clients:

```text
identity/session projection
tenant/project discovery
goal submission
job status
job event stream
user input continuation
approval decision
artifact retrieval
evidence summary/retrieval
knowledge-source management where permitted
cancellation
```

## Internal-only contracts

Must not be treated as arbitrary public APIs:

```text
ExecutionGrant
PolicyDecision internals
RoutingDecision mutation
WorkerLease
FencingToken
secret resolution
provider credential resolution
raw Tool Gateway execution
worker state commit
internal evidence append
```

A future enterprise SDK may expose abstractions for some internal capabilities, but it must still preserve the same authority model.

---

# 05. Transport Model

The canonical contracts are transport-neutral.

They may be represented using:

```text
HTTP/JSON
SSE
WebSocket
message queue
event bus
internal RPC
durable workflow payload
```

The transport may change without changing contract authority.

For public HTTP APIs, this document uses a target logical version prefix:

```text
/v1
```

Exact routing infrastructure belongs in deployment architecture.

---

# 06. Canonical Request Envelope

Every public request should be traceable using a canonical request envelope or equivalent transport metadata.

Conceptual fields:

```yaml
request_id: "req_..."
schema_version: "1"
timestamp: "..."
client:
  client_type: "web|desktop|mobile|cli|api"
  client_version: "..."
project_id: "project_..."   # when applicable
payload: {}
```

The following must **not** become client-authoritative merely because they appear in a request:

```text
tenant_id
principal_id
roles
permissions
risk clearance
ExecutionGrant
approval status
provider eligibility
```

The server derives or validates authoritative security context.

---

# 07. Canonical Response Envelope

Success:

```yaml
request_id: "req_..."
schema_version: "1"
data: {}
meta:
  generated_at: "..."
```

Failure:

```yaml
request_id: "req_..."
schema_version: "1"
error:
  code: "..."
  message: "safe human-readable message"
  retryable: false
  details: {}
```

Sensitive internal details are not returned in public errors.

---

# 08. Authentication Contract

Public API requests require authenticated identity unless an endpoint is explicitly public.

Typical public transport:

```text
Authorization: Bearer <session/access token>
```

Authentication token semantics are defined by the identity implementation.

The token must resolve to:

```text
Principal
Session
Tenant memberships
Assurance level
```

A token is not itself permission to every tenant/project/resource.

---

# 09. Request Security Context

The Control Plane resolves:

```yaml
principal_context:
  principal_id: "principal_..."
  session_id: "session_..."
  auth_method: "oidc"
  auth_provider: "microsoft"
  assurance_level: "strong"

tenant_context:
  tenant_id: "tenant_..."

project_context:
  project_id: "project_..."
```

The authoritative context is server-produced.

---

# 10. Tenant Selection Contract

A client may request a tenant context:

```http
POST /v1/session/context
```

Request:

```json
{
  "tenant_id": "tenant_123",
  "project_id": "project_456"
}
```

Server requirements:

```text
authenticate Principal
verify active Tenant membership
verify Project membership/access
apply assurance/security policy
return accepted context projection
```

Client submission alone is not authorization.

---

# 11. Current Principal Contract

```http
GET /v1/me
```

Response concept:

```yaml
principal:
  principal_id: "principal_..."
  display_name: "..."
  preferred_locale: "..."
session:
  session_id: "session_..."
  assurance_level: "..."
tenants:
  - tenant_id: "tenant_..."
    display_name: "..."
```

Do not return broad internal permissions or sensitive IdP assertions unnecessarily.

---

# 12. Tenant Contract

```http
GET /v1/tenants
GET /v1/tenants/{tenant_id}
```

Tenant projection may include:

```yaml
tenant_id: "tenant_..."
name: "..."
tenant_type: "personal|organization"
status: "..."
allowed_actions: []
```

Public projection must not leak secret/provider/security configuration.

---

# 13. Project Contract

```http
GET  /v1/projects
POST /v1/projects
GET  /v1/projects/{project_id}
```

Create request:

```yaml
name: "Furniture Company Website"
purpose: "..."
classification_default: "INTERNAL"
```

Response:

```yaml
project_id: "project_..."
tenant_id: "tenant_..."
name: "..."
created_at: "..."
status: "..."
```

`tenant_id` in response reflects authoritative scope.

---

# 14. Project Update Contract

```http
PATCH /v1/projects/{project_id}
```

Use optimistic concurrency for behaviorally important changes.

Example:

```http
If-Match: "project-version-7"
```

or equivalent explicit version field.

Lost updates must not silently win.

---

# 15. Goal Submission Contract

Primary one-prompt product API:

```http
POST /v1/projects/{project_id}/goals
```

Request:

```yaml
objective: "Build a premium website for my furniture company."
constraints:
  - "..."
preferences:
  - "..."
attachments:
  - artifact_or_upload_ref
requested_delivery:
  mode: "artifact"
```

The client does not submit provider/model/worker as mandatory default choices.

---

# 16. Goal Submission Response

Goal submission should normally create or start a durable Job.

Response:

```yaml
goal_id: "goal_..."
job_id: "job_..."
state: "PLANNING"
accepted_input:
  objective: "..."
next:
  status_uri: "/v1/jobs/job_..."
  events_uri: "/v1/jobs/job_.../events"
```

The API must not claim completion synchronously for long-running work unless the work actually completed.

---

# 17. GoalSpec Contract

Internal canonical `GoalSpec`:

```yaml
goal_id: "goal_..."
tenant_id: "tenant_..."
project_id: "project_..."
requested_by_principal_id: "principal_..."
objective: "..."
acceptance_criteria_ref: "criteria_..."
risk_class: "..."
data_class: "..."
budget:
  max_attempts: 3
  max_runtime_seconds: 3600
  max_external_spend:
    amount: 10.00
    currency: "USD"
version: 1
```

Exact numeric defaults are policy/configuration decisions, not hard-coded by this document.

---

# 18. AcceptanceCriteria Contract

```yaml
acceptance_criteria_id: "criteria_..."
goal_id: "goal_..."
version: 1
criteria:
  - criterion_id: "criterion_1"
    type: "functional"
    description: "..."
    required: true
  - criterion_id: "criterion_2"
    type: "security"
    description: "..."
    required: true
```

Final evaluation must reference the exact version.

---

# 19. Clarification / User Input Contract

If essential information cannot safely be inferred:

```text
Job State = NEEDS_USER_INPUT
```

Client retrieves the request:

```http
GET /v1/jobs/{job_id}
```

Projection:

```yaml
state: "NEEDS_USER_INPUT"
user_input_request:
  request_id: "inputreq_..."
  prompt: "..."
  fields:
    - field_id: "..."
      required: true
      type: "string"
```

Submission:

```http
POST /v1/jobs/{job_id}/user-input
```

Request:

```yaml
input_request_id: "inputreq_..."
answers:
  field_id: "value"
```

Input must be revalidated and may trigger re-planning/re-admission.

---

# 20. ExecutionProposal Contract

Internal planning output:

```yaml
proposal_id: "proposal_..."
goal_id: "goal_..."
plan_version: 1
tasks:
  - task_id: "task_..."
    responsibility: "..."
    dependencies: []
    required_capabilities:
      - "ilaios.capability.web-factory"
    expected_output_contract: "..."
    risk_class: "..."
    data_class: "..."
    validation_requirements: []
graph_hash: "sha256:..."
```

Planner produces a proposal.

Planner does not produce authorization.

---

# 21. CapabilityRequirement Contract

```yaml
capability_requirement_id: "capreq_..."
job_id: "job_..."
task_id: "task_..."
capability_id: "ilaios.capability.web-factory"
required_operations: []
input_contract_refs: []
output_contract_refs: []
quality_floor: {}
security_constraints: {}
```

---

# 22. CapabilityDescriptor Contract

Canonical registry projection:

```yaml
capability_id: "ilaios.capability.web-factory"
schema_version: "1"
display_name: "Web Factory"
domain: "factory"
dependencies:
  - "ilaios.capability.workflow-runtime"
  - "ilaios.capability.policy-governance"
input_contracts: []
output_contracts: []
required_permissions: []
maturity: "SPECIFIED"
```

Capability maturity values:

```text
DESIGNED
SPECIFIED
IMPLEMENTED
TESTED
VERIFIED
DEPLOYED / PRODUCTION
```

`DEPRECATED` is a lifecycle exit state.

---

# 23. FactoryDescriptor Contract

```yaml
factory_id: "ilaios.factory.web"
version: "1"
capability_id: "ilaios.capability.web-factory"
supported_goal_types: []
required_capabilities: []
input_contract: "..."
artifact_contract: "..."
policy_requirements: []
validation_requirements: []
repair_policy_ref: "..."
evidence_requirements: []
delivery_contract: "..."
```

Factory cannot declare a private router or private policy authority.

---

# 24. ExecutionRequest Contract

Internal execution admission request:

```yaml
request_id: "execreq_..."
principal_id: "principal_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
task_id: "task_..."
capability_id: "ilaios.capability..."
requested_action:
  operation: "..."
requested_tools: []
requested_resources: []
data_class: "CONFIDENTIAL"
risk_class: "..."
budget_ref: "budget_..."
context_ref: "context_..."
```

---

# 25. PolicyDecision Contract

```yaml
policy_decision_id: "policy_..."
request_id: "execreq_..."
decision: "ALLOW|DENY|REQUIRE_APPROVAL"
reason_codes:
  - "..."
policy_id: "..."
policy_version: "..."
evaluated_at: "..."
evidence_id: "evidence_..."
```

Missing mandatory security context must not become `ALLOW`.

---

# 26. ExecutionGrant Contract

Internal-only scoped authorization:

```yaml
grant_id: "grant_..."
principal_id: "principal_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
task_id: "task_..."
capability_id: "ilaios.capability..."
allowed_actions: []
allowed_tools: []
allowed_resources: []
network_scope: {}
filesystem_scope: {}
secret_scope: []
spend_ceiling: {}
attempt_ceiling: 1
issued_at: "..."
expires_at: "..."
policy_decision_id: "policy_..."
approval_id: null
```

Rules:

```text
not transferable across tenants
not implicitly reusable across tasks
not broadable by worker/provider
expires
revocable
```

---

# 27. ApprovalRequest Contract

Internal/public projection pair.

Canonical record:

```yaml
approval_id: "approval_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
task_id: "task_..."
requested_action:
  action_hash: "sha256:..."
  human_summary: "Deploy website to production"
scope: {}
risk:
  class: "HIGH"
  reason_codes: []
requested_by: "principal_or_system_ref"
created_at: "..."
expires_at: "..."
```

---

# 28. Approval Public API

Retrieve:

```http
GET /v1/approvals
GET /v1/approvals/{approval_id}
```

Decide:

```http
POST /v1/approvals/{approval_id}/decision
```

Request:

```yaml
decision: "APPROVE|REJECT"
reason: "..."
```

The server derives the approver Principal.

Client cannot supply an arbitrary `approver_principal_id` as authority.

---

# 29. ApprovalDecision Contract

```yaml
approval_id: "approval_..."
decision: "APPROVED|REJECTED|EXPIRED|REVOKED"
approver_principal_id: "principal_..."
decided_at: "..."
reason: "..."
action_hash: "sha256:..."
evidence_id: "evidence_..."
```

Approval is bound to exact action hash/scope.

---

# 30. RoutingRequest Contract

Internal:

```yaml
routing_request_id: "routereq_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
task_id: "task_..."
capability_requirement_ref: "capreq_..."
grant_id: "grant_..."
constraints:
  data_class: "..."
  privacy: {}
  residency: {}
  modality: []
  context: {}
  tool_requirements: []
  quality_floor: {}
  budget: {}
  latency: {}
```

---

# 31. RoutingDecision Contract

Canonical single route truth:

```yaml
route_id: "route_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
task_id: "task_..."
capability_id: "ilaios.capability..."
worker_class: "..."
provider_id: "provider_..."
model_or_resource_id: "..."
adapter_id: "adapter_..."
reason_codes: []
quality_floor: {}
privacy_class: "..."
residency: "..."
estimated_cost: {}
fallback_candidates: []
created_at: "..."
evidence_id: "evidence_..."
```

There must be no second final route contract.

---

# 32. Route Eligibility Contract

A route is eligible only after:

```text
authority
security
privacy
residency
capability
context/modality
tool requirements
quality floor
provider health
quota
budget
```

are satisfied.

Cost/latency ranking occurs only within eligible candidates.

---

# 33. ProviderDescriptor Contract

```yaml
provider_id: "provider_openai"
provider_type: "hosted-model"
adapter_id: "adapter_openai"
enabled: true
supported_capabilities: []
supported_modalities: []
regions: []
privacy:
  classifications_allowed: []
cost_model_ref: "..."
health_ref: "..."
quota_ref: "..."
schema_version: "1"
```

Provider metadata is replaceable runtime/configuration state.

---

# 34. ModelDescriptor Contract

```yaml
model_id: "..."
provider_id: "provider_..."
capabilities: []
modalities: []
context_limit: null
output_limit: null
regions: []
enabled: true
schema_version: "1"
```

Model ID is not a product-level permanent capability ID.

---

# 35. ProviderRequest Contract

Internal adapter input:

```yaml
provider_request_id: "provreq_..."
route_id: "route_..."
job_id: "job_..."
task_id: "task_..."
operation: "generate"
normalized_input_ref: "..."
parameters: {}
timeout_ms: 60000
```

Secret credentials are resolved by the adapter/runtime boundary, not embedded as ordinary contract fields.

---

# 36. ProviderResult Contract

```yaml
provider_request_id: "provreq_..."
status: "SUCCEEDED|FAILED|CANCELLED"
normalized_output_ref: "..."
usage:
  input_units: null
  output_units: null
  runtime_units: null
provider_request_ref: "external-id"
error:
  class: null
  code: null
  retryable: false
completed_at: "..."
evidence_id: "evidence_..."
```

Provider-native response shape must be normalized before leaving the adapter boundary.

---

# 37. WorkerDescriptor Contract

```yaml
worker_id: "worker_..."
worker_class: "web-build"
supported_capabilities: []
runtime_environment: "..."
isolation_class: "sandboxed"
resource_limits: {}
health: "..."
version: "..."
```

Worker availability is not execution authority.

---

# 38. WorkerLease Contract

Internal:

```yaml
lease_id: "lease_..."
worker_id: "worker_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
task_id: "task_..."
grant_id: "grant_..."
attempt: 1
fencing_token: 42
issued_at: "..."
expires_at: "..."
```

A worker commit must present valid lease/fencing identity.

---

# 39. TaskEnvelope Contract

```yaml
task_id: "task_..."
job_id: "job_..."
tenant_id: "tenant_..."
project_id: "project_..."
capability_id: "ilaios.capability..."
responsibility: "..."
input_refs: []
expected_output_contract: "..."
validation_contract: "..."
risk_class: "..."
data_class: "..."
grant_id: "grant_..."
route_id: "route_..."
```

---

# 40. ToolRequest Contract

Internal Tool Gateway input:

```yaml
tool_request_id: "toolreq_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
task_id: "task_..."
tool_id: "tool_browser"
operation: "navigate"
parameters: {}
input_refs: []
grant_id: "grant_..."
timeout_ms: 30000
expected_result_schema: "..."
```

---

# 41. ToolResult Contract

```yaml
tool_request_id: "toolreq_..."
status: "SUCCEEDED|FAILED|CANCELLED"
normalized_output_ref: "..."
artifact_refs: []
usage: {}
error:
  class: null
  code: null
  retryable: false
redaction:
  applied: false
evidence_id: "evidence_..."
```

Tool output remains untrusted until validated.

---

# 42. Secret Resolution Contract

Internal only.

Request uses a secret reference and grant:

```yaml
secret_access_request_id: "secretreq_..."
grant_id: "grant_..."
secret_ref: "vault://..."
purpose: "provider-authentication"
```

Result should normally be injected directly into the bounded runtime rather than returned as an ordinary serialized API payload.

Secret values must not enter evidence/log contracts.

---

# 43. RetrievalRequest Contract

```yaml
retrieval_id: "retrieval_..."
principal_id: "principal_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
task_id: "task_..."
purpose: "execution"
query_ref: "..."
data_class: "..."
authorization_context_ref: "..."
filters: {}
limit: 20
```

Retrieval is a governed action.

---

# 44. RetrievalResult Contract

```yaml
retrieval_id: "retrieval_..."
status: "SUCCEEDED|DENIED|FAILED"
units:
  - knowledge_unit_id: "ku_..."
    source_id: "source_..."
    source_version_id: "sourcev_..."
    classification: "..."
    relevance_score: 0.0
    rerank_score: null
    provenance_ref: "prov_..."
authorization_decision_ref: "policy_..."
evidence_id: "evidence_..."
```

Unauthorized units must not be returned with a flag saying “do not use”.

They must be excluded/denied.

---

# 45. AuthorizedContext Contract

```yaml
context_id: "context_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
task_id: "task_..."
purpose: "..."
knowledge_unit_refs: []
artifact_version_refs: []
policy_ref: "..."
created_at: "..."
expires_at: null
content_hash: "sha256:..."
```

Context is task-scoped where appropriate.

---

# 46. Knowledge Source Public API

Authorized source management may expose:

```http
POST   /v1/projects/{project_id}/sources
GET    /v1/projects/{project_id}/sources
GET    /v1/projects/{project_id}/sources/{source_id}
DELETE /v1/projects/{project_id}/sources/{source_id}
```

Source creation request:

```yaml
source_type: "upload|url|repository|connector|note"
locator_or_upload_ref: "..."
classification: "CONFIDENTIAL"
purpose: "project-knowledge"
```

Source ingestion success does not imply every source statement is verified truth.

---

# 47. Source Contract

```yaml
source_id: "source_..."
tenant_id: "tenant_..."
project_id: "project_..."
source_type: "..."
canonical_locator: "..."
classification: "..."
region: "..."
retention_policy_ref: "..."
authorization_policy_ref: "..."
created_at: "..."
status: "..."
current_version_id: "sourcev_..."
```

---

# 48. SourceVersion Contract

```yaml
source_version_id: "sourcev_..."
source_id: "source_..."
content_hash: "sha256:..."
content_ref: "..."
parser_version: "..."
classification_version: "..."
provenance_ref: "..."
created_at: "..."
```

Derived chunks must point to exact source versions.

---

# 49. KnowledgeUnit Contract

```yaml
knowledge_unit_id: "ku_..."
tenant_id: "tenant_..."
project_id: "project_..."
source_id: "source_..."
source_version_id: "sourcev_..."
unit_type: "..."
content_ref: "..."
content_hash: "sha256:..."
classification: "..."
purpose_constraints: []
region: "..."
retention_policy_ref: "..."
authorization_attributes: {}
provenance_ref: "..."
```

---

# 50. ArtifactRecord Contract

```yaml
artifact_id: "artifact_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
artifact_type: "website"
classification: "INTERNAL"
created_by_task_id: "task_..."
current_version_id: "artifactv_..."
created_at: "..."
status: "..."
```

---

# 51. ArtifactVersion Contract

```yaml
artifact_version_id: "artifactv_..."
artifact_id: "artifact_..."
version: 1
content_hash: "sha256:..."
size: 0
mime_type: "..."
storage_ref: "object://..."
producer:
  type: "worker|tool|provider|factory"
  ref: "..."
route_id: "route_..."
input_refs: []
created_at: "..."
supersedes_version_id: null
```

Version contents are immutable.

---

# 52. Artifact Public API

```http
GET /v1/projects/{project_id}/artifacts
GET /v1/artifacts/{artifact_id}
GET /v1/artifacts/{artifact_id}/versions
GET /v1/artifacts/{artifact_id}/versions/{version_id}
```

Binary download may use:

```text
short-lived authorized URL
or
streaming gateway
```

Object storage must not be publicly exposed merely because the client knows a storage key.

---

# 53. Artifact Upload Contract

When users upload inputs:

```http
POST /v1/projects/{project_id}/uploads
```

Create-upload request:

```yaml
filename: "brand-guide.pdf"
mime_type: "application/pdf"
size: 12345
classification: "CONFIDENTIAL"
purpose: "goal-input"
content_hash: "sha256:..."
```

The server may return a bounded upload target.

Finalization validates integrity and scope.

---

# 54. ValidationResult Contract

```yaml
validation_id: "validation_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
task_id: "task_..."
artifact_id: "artifact_..."
artifact_version_id: "artifactv_..."
validator_id: "validator_..."
validator_version: "..."
validation_type: "security"
result: "PASS|FAIL"
failure_codes: []
metrics: {}
created_at: "..."
evidence_id: "evidence_..."
```

---

# 55. EvaluationResult Contract

```yaml
evaluation_id: "evaluation_..."
goal_id: "goal_..."
job_id: "job_..."
artifact_version_refs: []
acceptance_criteria_id: "criteria_..."
acceptance_criteria_version: 1
evaluator_refs: []
result: "PASS|FAIL"
failure_classification: []
created_at: "..."
evidence_id: "evidence_..."
```

---

# 56. FailureRecord Contract

```yaml
failure_id: "failure_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
task_id: "task_..."
failure_class: "validation_failure"
error_code: "..."
safe_message: "..."
diagnostic_ref: "..."
retryable: true
repairable: true
created_at: "..."
evidence_id: "evidence_..."
```

---

# 57. RepairProposal Contract

```yaml
repair_proposal_id: "repair_..."
failure_id: "failure_..."
job_id: "job_..."
task_id: "task_..."
proposed_actions: []
estimated_cost: {}
estimated_attempts: 1
requires_re_admission: true
created_at: "..."
```

Repair is not authorization.

---

# 58. CheckpointRecord Contract

```yaml
checkpoint_id: "checkpoint_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
task_id: null
runtime_state: "CHECKPOINTED"
completed_task_ids: []
pending_task_ids: []
artifact_refs: []
evidence_cursor: "..."
budget_state_ref: "..."
retry_state: {}
route_refs: []
context_refs: []
created_at: "..."
integrity_hash: "sha256:..."
```

---

# 59. StateTransition Contract

```yaml
event_id: "event_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
task_id: null
sequence: 42
from_state: "RUNNING"
to_state: "VALIDATING"
reason_code: "task-output-ready"
actor_ref: "..."
timestamp: "..."
evidence_id: "evidence_..."
```

The client cannot fabricate a valid state transition merely by calling an endpoint.

---

# 60. Canonical Job States

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

Public projections may simplify wording but must map to canonical state.

---

# 61. Job Public API

```http
GET /v1/jobs/{job_id}
```

Response concept:

```yaml
job_id: "job_..."
goal_id: "goal_..."
project_id: "project_..."
state: "RUNNING"
progress:
  completed_tasks: 4
  total_tasks: 9
current_activity:
  category: "web.build"
waiting_reason: null
artifacts: []
created_at: "..."
updated_at: "..."
```

Do not expose secret/internal prompts/raw provider credentials.

---

# 62. Job List API

```http
GET /v1/projects/{project_id}/jobs
```

Supports pagination and filters such as:

```text
state
created_after
created_before
goal_id
```

Filters must never broaden tenant/project visibility.

---

# 63. Job Event Stream

Target logical endpoint:

```http
GET /v1/jobs/{job_id}/events
```

Transport may be SSE or WebSocket.

Events are projections of authoritative state.

---

# 64. EventEnvelope Contract

```yaml
event_id: "event_..."
sequence: 42
event_type: "task.started"
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
task_id: "task_..."
timestamp: "..."
payload: {}
evidence_ref: "evidence_..."
```

Public event payload must be safe for the authorized client.

---

# 65. Event Types

Canonical families may include:

```text
goal.created
goal.updated
plan.created
plan.admitted
job.queued
job.started
task.started
approval.required
approval.decided
user_input.required
route.selected
tool.started
tool.completed
provider.started
provider.completed
retrieval.completed
artifact.created
artifact.versioned
validation.completed
repair.started
checkpoint.created
job.final_validation
job.completed
job.failed
job.cancel_requested
job.cancelled
delivery.started
delivery.completed
```

New event types are additive if they do not alter authority.

---

# 66. Event Replay Contract

Clients reconnect using:

```text
last_event_id
or
last_sequence
```

The server may replay retained events then continue live.

Client-local event history is not authoritative.

---

# 67. Cancellation Public API

```http
POST /v1/jobs/{job_id}/cancel
```

Request:

```yaml
reason: "User requested cancellation"
```

Response:

```yaml
job_id: "job_..."
state: "CANCEL_REQUESTED"
```

Cancellation is asynchronous if workers/providers cannot stop instantly.

---

# 68. Cancellation Internal Contract

Canonical flow:

```text
CancellationRequest
→ Authorization
→ CANCEL_REQUESTED
→ Scheduler stops new work
→ active work cancellation attempt
→ stale result fencing
→ compensation if supported
→ CANCELLED
```

---

# 69. EvidenceRecord Contract

```yaml
evidence_id: "evidence_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
task_id: null
event_type: "route.selected"
actor_ref: "..."
timestamp: "..."
input_refs: []
output_refs: []
decision_refs: []
artifact_refs: []
content_hash: "sha256:..."
classification: "INTERNAL"
metadata: {}
```

Evidence schema is canonical historical proof, not debug logging.

---

# 70. AcceptanceManifest Contract

```yaml
acceptance_manifest_id: "acceptance_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
goal_id: "goal_..."
accepted_artifact_version_refs: []
acceptance_criteria:
  id: "criteria_..."
  version: 1
validation_refs: []
evaluation_refs: []
policy_refs: []
approval_refs: []
routing_refs: []
cost_refs: []
evidence_root_ref: "..."
created_at: "..."
manifest_hash: "sha256:..."
```

---

# 71. Evidence Public API

Authorized access:

```http
GET /v1/jobs/{job_id}/evidence
GET /v1/jobs/{job_id}/acceptance-manifest
GET /v1/evidence/{evidence_id}
```

Public projection may redact sensitive evidence content while preserving integrity/decision semantics.

---

# 72. UsageRecord Contract

```yaml
usage_id: "usage_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
task_id: "task_..."
route_id: "route_..."
provider_id: "provider_..."
model_or_resource_id: "..."
tool_id: null
input_units: null
output_units: null
runtime_units: null
external_cost:
  amount: 0
  currency: "USD"
retry_number: 0
created_at: "..."
evidence_id: "evidence_..."
```

Cost formulas and budgets belong in `FINOPS.md`.

---

# 73. Notification Contract

```yaml
notification_id: "notification_..."
principal_id: "principal_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
notification_type: "approval_required"
safe_payload: {}
created_at: "..."
delivered_at: null
read_at: null
status: "PENDING"
```

---

# 74. Notification Public API

Possible target family:

```http
GET  /v1/notifications
POST /v1/notifications/{notification_id}/read
```

Notifications never carry broader authority than the underlying resource.

---

# 75. Web Factory Contract

Canonical internal input:

```yaml
factory_id: "ilaios.factory.web"
goal_spec_ref: "goal_..."
acceptance_criteria_ref: "criteria_..."
authorized_context_ref: "context_..."
project_id: "project_..."
```

Output:

```yaml
artifact_refs:
  - "artifact_..."
validation_requirements: []
evidence_refs: []
factory_result: "READY_FOR_FINAL_EVALUATION|FAILED"
```

Factory does not return `DEPLOYED` merely because the artifact is buildable.

---

# 76. Video Factory Contract

Input:

```text
GoalSpec
AcceptanceCriteria
AuthorizedContext
```

Output includes refs to:

```text
script
storyboard
shot plan
media assets
canonical timeline
rendered artifact
video/audio validation
evidence
```

Final acceptance remains outside producer-only authority.

---

# 77. Software Factory Contract

Input includes:

```yaml
goal_spec_ref: "..."
repository_ref: "..."
base_revision: "..."
authorized_context_ref: "..."
```

Output may include:

```yaml
change_artifact_ref: "..."
branch_ref: "..."
test_result_refs: []
build_artifact_refs: []
diff_review_ref: "..."
evidence_refs: []
```

Repository mutation requires scoped tool authority.

---

# 78. App Factory Contract

App Factory consumes Software Factory outputs and may add:

```text
package artifact
signing request
store metadata
distribution request
release evidence
```

Signing/store publication contracts are privileged side effects.

---

# 79. Research / Data Factory Contract

Output should preserve:

```yaml
research_result_id: "..."
source_refs: []
claim_refs: []
artifact_refs: []
knowledge_promotion_candidates: []
provenance_refs: []
evidence_refs: []
```

Promotion to Knowledge is a distinct governed operation.

---

# 80. Security Factory Contract

Security Factory outputs findings/recommendations/evidence:

```yaml
security_result_id: "..."
findings:
  - finding_id: "..."
    severity: "..."
    category: "..."
    evidence_refs: []
remediation_proposals: []
```

It cannot return an authorization grant.

---

# 81. DeliveryRequest Contract

External delivery/deploy/publish is a governed action.

```yaml
delivery_request_id: "delivery_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
artifact_version_refs: []
delivery_type: "deploy|publish|send|release"
target_ref: "..."
requested_by: "..."
risk_class: "..."
```

---

# 82. DeliveryResult Contract

```yaml
delivery_request_id: "delivery_..."
status: "SUCCEEDED|FAILED|CANCELLED"
external_action_ref: "..."
verification_ref: "..."
completed_at: "..."
evidence_id: "evidence_..."
```

Successful artifact acceptance and successful external delivery are separate facts.

---

# 83. DeploymentRecord Contract

```yaml
deployment_id: "deployment_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
artifact_version_id: "artifactv_..."
environment: "production"
target_ref: "..."
approval_id: "approval_..."
status: "..."
verification_ref: "..."
started_at: "..."
completed_at: "..."
evidence_id: "evidence_..."
```

This is historical action data, not live-health truth.

---

# 84. Live Health Contract

Current health belongs to observability/runtime status.

Conceptually:

```yaml
resource_ref: "..."
observed_at: "..."
status: "HEALTHY|DEGRADED|UNHEALTHY|UNKNOWN"
checks: []
```

A stale health observation must not be treated as current.

---

# 85. Error Contract

Canonical public error:

```yaml
error:
  code: "ILAIOS_AUTHORIZATION_DENIED"
  message: "You are not allowed to perform this action."
  retryable: false
  details:
    field_errors: []
```

Internal error contracts may include protected diagnostic references.

---

# 86. Error Code Families

Use stable machine-readable families.

```text
ILAIOS_AUTHENTICATION_REQUIRED
ILAIOS_AUTHENTICATION_INSUFFICIENT
ILAIOS_AUTHORIZATION_DENIED
ILAIOS_TENANT_SCOPE_INVALID
ILAIOS_PROJECT_SCOPE_INVALID
ILAIOS_VALIDATION_FAILED
ILAIOS_CONFLICT
ILAIOS_IDEMPOTENCY_CONFLICT
ILAIOS_POLICY_DENIED
ILAIOS_APPROVAL_REQUIRED
ILAIOS_APPROVAL_EXPIRED
ILAIOS_BUDGET_EXHAUSTED
ILAIOS_QUOTA_EXHAUSTED
ILAIOS_ROUTE_UNAVAILABLE
ILAIOS_PROVIDER_UNAVAILABLE
ILAIOS_TOOL_DENIED
ILAIOS_TOOL_FAILED
ILAIOS_RETRIEVAL_DENIED
ILAIOS_ARTIFACT_NOT_FOUND
ILAIOS_JOB_NOT_FOUND
ILAIOS_JOB_TERMINAL
ILAIOS_REPAIR_EXHAUSTED
ILAIOS_CANCELLED
ILAIOS_INTERNAL_INVARIANT
```

Exact list may grow additively.

---

# 87. HTTP Status Mapping

Typical public mapping:

```text
200  success/read/update
201  created
202  accepted asynchronous operation
204  successful no-content mutation
400  malformed request
401  authentication required/invalid
403  authenticated but forbidden
404  not found or intentionally concealed resource
409  state/version/idempotency conflict
412  precondition/version failed
422  semantically invalid request
429  rate/quota constraint
500  internal failure
502  upstream provider/tool failure where appropriate
503  temporarily unavailable
```

Security policy may intentionally use `404` to avoid confirming protected resource existence.

---

# 88. Validation Errors

Field-level errors:

```yaml
error:
  code: "ILAIOS_VALIDATION_FAILED"
  message: "Request validation failed."
  retryable: false
  details:
    field_errors:
      - field: "objective"
        code: "required"
        message: "Objective is required."
```

Do not leak internal schema implementation details unnecessarily.

---

# 89. Idempotency Contract

Replay-sensitive public mutations accept:

```http
Idempotency-Key: <opaque-client-key>
```

or equivalent explicit field.

Server binds:

```text
idempotency key
+ authenticated principal
+ tenant/project scope
+ endpoint/operation
+ request hash
```

Same key + same request returns the original result where feasible.

Same key + materially different request returns conflict.

---

# 90. Required Idempotent Operations

Idempotency is strongly required for operations such as:

```text
goal/job creation
payment/spend
external communication
deployment/publish
store submission
repository mutation initiation
approval decision
artifact finalization
```

---

# 91. Optimistic Concurrency Contract

Mutable authoritative resources may expose:

```text
version
etag
sequence
```

Update requests must use a precondition where lost updates are dangerous.

Example:

```http
If-Match: "v17"
```

Conflict returns:

```text
409 or 412
```

according to endpoint semantics.

---

# 92. Pagination Contract

List APIs use stable cursor pagination.

Request:

```text
?limit=50&cursor=<opaque>
```

Response:

```yaml
data: []
meta:
  next_cursor: "..."
  has_more: true
```

Cursor must not encode trust decisions that bypass authorization on continuation.

---

# 93. Filtering Contract

Filters are request constraints, not authorization.

Example:

```text
GET /v1/projects/{project_id}/jobs?state=FAILED
```

Authorization is applied independently before/filtering results.

---

# 94. Sorting Contract

Sort fields must be allowlisted.

Examples:

```text
created_at
updated_at
name
```

Raw caller-provided SQL/order expressions are forbidden.

---

# 95. Timestamp Contract

Machine timestamps use an unambiguous standard representation.

Recommended:

```text
UTC ISO-8601
```

Example:

```text
2026-08-13T00:00:00Z
```

Presentation timezone is client/user preference.

---

# 96. Identifier Contract

API identifiers are opaque.

Clients must not infer permission, tenant, ordering, or type-specific secret information from IDs.

---

# 97. Schema Versioning

Every durable/cross-process contract must be versionable.

Version fields may appear as:

```text
API path version
Content-Type version
schema_version
event schema version
```

Exact transport choice may vary.

---

# 98. Compatibility Rules

Backward-compatible changes:

```text
add optional field
add enum only when consumers tolerate unknown values
add endpoint
add event type when subscribers are forward-compatible
```

Potentially breaking changes:

```text
remove field
rename field
change field meaning
make optional field required
change identity/scope semantics
change ordering/idempotency behavior
change enum without compatibility
```

Breaking changes require explicit new version/migration.

---

# 99. Unknown Field Rule

Public clients should generally tolerate unknown response fields.

Servers may reject unknown request fields for security-sensitive contracts where ambiguity is unsafe.

The choice must be contract-specific and documented.

---

# 100. Enum Evolution

Consumers must not assume the enum list never grows unless the contract explicitly marks it closed.

Security-sensitive state machines may use closed enums and versioning.

---

# 101. Null vs Missing

Contracts must distinguish where necessary:

```text
missing
    = caller did not provide / field not projected

null
    = explicitly no value
```

Do not overload empty strings as null.

---

# 102. Data Classification Field

When a contract carries protected content, classification metadata should be explicit or derivable.

Canonical values:

```text
PUBLIC
INTERNAL
CONFIDENTIAL
RESTRICTED
```

More restrictive tenant-specific classes may map through policy.

---

# 103. Redaction Contract

A response may state:

```yaml
redaction:
  applied: true
  fields:
    - "provider_payload"
  reason_codes:
    - "SECRET_PROTECTION"
```

Redaction must not falsify decision outcome.

---

# 104. Request Size Limits

Every endpoint/transport must define bounded sizes.

Large binaries should use artifact/upload flows instead of embedding unbounded base64 payloads in JSON.

---

# 105. Rate / Quota Contract

Rate/quota errors should return:

```yaml
error:
  code: "ILAIOS_QUOTA_EXHAUSTED"
  retryable: true
  details:
    retry_after_seconds: 60
```

Do not expose sensitive global capacity information.

---

# 106. Public API Security Rules

All protected public endpoints require:

```text
authentication
server-side tenant validation
server-side project/resource authorization
input validation
rate/abuse controls
safe errors
evidence for material privileged action
```

A client-provided tenant/project ID is only a locator candidate.

---

# 107. Internal API Security Rules

Internal service identity does not imply universal trust.

Internal calls must preserve:

```text
service identity
tenant/project context
job/task context
audience
bounded authorization
schema validation
```

---

# 108. Service-to-Service Authentication

Internal contracts may use:

```text
mTLS
short-lived service tokens
signed workload identity
platform service identity
```

Exact mechanism belongs in deployment/security implementation.

Long-lived shared master tokens should be avoided.

---

# 109. Queue / Event Authentication

A valid queue message must be produced through trusted workflow infrastructure and still contain scoped task identity.

A worker must not trust arbitrary payloads inserted into a queue without integrity/authority validation.

---

# 110. Public Provider Selection Rule

Default public Goal API does not require users to choose providers.

If an advanced enterprise contract later permits provider constraints, it must be expressed as **preference/allowed set**, not permission to bypass routing/security.

Example:

```yaml
execution_preferences:
  allowed_provider_ids:
    - "provider_..."
```

Policy may further restrict it.

---

# 111. Public Tool Selection Rule

Normal users specify desired outcomes.

They do not receive arbitrary raw tool execution endpoints by default.

If an enterprise developer API exposes bounded tool capability, it still goes through:

```text
Capability Requirement
→ Policy
→ ExecutionGrant
→ Tool Gateway
```

---

# 112. External Router Rule

No public/internal contract may define:

```text
OmniRouteDecision
```

as competing canonical route truth.

External routing adapters consume/participate under ILAIOS routing policy.

Canonical output remains:

```text
RoutingDecision
```

---

# 113. GitHub Identity vs Repository API

These are distinct.

```text
GitHub OAuth
    → authentication/account linkage

GitHub Repository Connector
    → permissioned tool capability
```

Repository endpoint contracts must never infer write authority from GitHub sign-in alone.

---

# 114. RepositoryRef Contract

```yaml
repository_ref:
  provider: "github"
  repository_id: "external-or-canonical-ref"
  canonical_url: "..."
  owner: "..."
  name: "..."
  base_ref: "..."
  base_commit: "..."
```

Credentials are not included.

---

# 115. RepositoryMutationRequest Contract

Internal:

```yaml
repository_mutation_id: "repomut_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
task_id: "task_..."
repository_ref: {}
operation_scope:
  branch: "..."
  paths: []
grant_id: "grant_..."
```

---

# 116. RepositoryMutationResult Contract

```yaml
repository_mutation_id: "repomut_..."
status: "SUCCEEDED|FAILED"
branch_ref: "..."
commit_refs: []
diff_artifact_ref: "artifact_..."
test_refs: []
ci_refs: []
evidence_id: "evidence_..."
```

Merge/release may be a separate privileged operation.

---

# 117. Search Contract

Search endpoint families return authorized canonical entity references.

Example:

```http
GET /v1/search?q=...
```

Result:

```yaml
items:
  - type: "artifact"
    id: "artifact_..."
    project_id: "project_..."
    title: "..."
    snippet: "safe authorized snippet"
```

Search authorization is applied before result release.

---

# 118. Export Contract

Tenant/project export is a privileged or policy-governed operation.

```http
POST /v1/projects/{project_id}/exports
```

Request:

```yaml
include:
  - "artifacts"
  - "knowledge"
  - "evidence"
format: "..."
```

Response:

```yaml
export_job_id: "job_..."
```

Never export unrelated tenants, secrets, or protected system configuration.

---

# 119. Import Contract

```http
POST /v1/projects/{project_id}/imports
```

Input uses artifact/upload refs.

Import must run:

```text
schema validation
classification
tenant binding
provenance
security/content checks
```

before becoming authoritative project data.

---

# 120. Audit Query Contract

Enterprise-authorized users may query evidence/audit projections.

The API must enforce:

```text
audit role/permission
tenant scope
data classification
redaction
pagination
```

Audit access itself may generate evidence.

---

# 121. Administrative API Boundary

Administrative endpoints are separated by privilege.

Possible areas:

```text
memberships
roles/policies
provider eligibility
security policy
budget policy
approval policy
retention policy
audit access
```

Admin API does not expose raw platform secrets.

---

# 122. Membership API

Possible target family:

```http
GET    /v1/tenants/{tenant_id}/memberships
POST   /v1/tenants/{tenant_id}/memberships
PATCH  /v1/tenants/{tenant_id}/memberships/{membership_id}
DELETE /v1/tenants/{tenant_id}/memberships/{membership_id}
```

Every mutation requires tenant administration authority.

---

# 123. Policy API Boundary

Tenant policy may be configurable through governed administrative contracts.

A policy update must include:

```text
policy version
change diff
requester
security impact
approval if required
evidence
```

The policy engine itself remains internal authority.

---

# 124. Feature Flag Contract Boundary

Feature flags may affect availability, not constitutional security.

Flag API must not permit disabling:

```text
tenant isolation
mandatory policy
mandatory evidence
critical approval
security validation
```

---

# 125. Webhook / Callback Contract

If ILAIOS supports outbound webhooks:

```yaml
event_id: "event_..."
event_type: "job.completed"
occurred_at: "..."
resource_ref:
  type: "job"
  id: "job_..."
payload: {}
signature:
  algorithm: "..."
  key_id: "..."
```

Webhooks must be signed/authenticated and replay-resistant.

No secret full payload should be sent unnecessarily.

---

# 126. Webhook Delivery Semantics

Webhook delivery should be:

```text
at-least-once
```

unless another explicit guarantee is implemented.

Receivers must use event IDs/idempotency.

ILAIOS records delivery attempts separately from source event truth.

---

# 127. Internal Event Delivery Semantics

Internal events may also be at-least-once.

Consumers must be idempotent.

Exactly-once processing must not be claimed without direct implementation proof.

---

# 128. Event Ordering Semantics

Ordering guarantee should be explicit.

Minimum canonical expectation:

```text
authoritative job state events are sequenceable per job
```

Global total ordering is not required.

---

# 129. Retry Semantics

Transport retries and business retries are distinct.

```text
HTTP retry
    may repeat same request under idempotency

Task retry
    creates/updates governed attempt state

Repair
    is a new governed execution path after failure classification
```

---

# 130. Timeout Semantics

Every cross-boundary call should define:

```text
connect timeout
execution timeout
job/task timeout
provider/tool timeout
```

Timeout does not imply successful cancellation of the external operation.

---

# 131. Partial Failure Semantics

A multi-step Goal can partially produce artifacts.

Public job status must distinguish:

```text
FAILED with recoverable artifacts
DONE
CANCELLED
NEEDS_USER_INPUT
```

Never label partial output as verified final product unless final acceptance passes.

---

# 132. Provider Failure Semantics

Provider failure produces normalized failure data.

It may lead to:

```text
retry
new RoutingDecision
fallback
safe failure
```

Provider error itself cannot authorize fallback to an otherwise ineligible provider.

---

# 133. Tool Failure Semantics

Tool failure returns:

```text
normalized error class
retryability hint
safe result metadata
evidence
```

Untrusted raw stderr/output must be handled carefully.

---

# 134. Knowledge Retrieval Denial Semantics

Unauthorized retrieval returns denial.

It must not return protected data.

Example:

```yaml
status: "DENIED"
units: []
authorization_decision_ref: "policy_..."
```

---

# 135. Artifact Access Denial Semantics

Protected artifact APIs may use:

```text
403
or
404
```

according to concealment policy.

They must not leak existence across tenants.

---

# 136. State Conflict Semantics

Invalid mutation against current state returns conflict.

Example:

```text
approve expired approval
cancel already terminal job
commit with stale fencing token
update project using stale version
```

These are not generic 500 errors.

---

# 137. State Projection Rule

Public state is a projection.

Canonical internal state remains authoritative.

UI/client may cache state but must reconcile from server.

---

# 138. Evidence Projection Rule

Public evidence responses may be:

```text
full authorized evidence
redacted evidence
summary evidence
```

but must maintain stable evidence IDs and truthful outcomes.

---

# 139. Contract Traceability

Every major contract should map:

```text
Product Requirement
      │
      ▼
Architecture Component
      │
      ▼
API / Internal Contract
      │
      ▼
Implementation
      │
      ▼
Tests
      │
      ▼
Evidence
```

---

# 140. Contract Definition of Done

A canonical contract reaches `SPECIFIED` only when:

```text
ownership is explicit
caller is explicit
consumer is explicit
required fields are defined
optional fields are defined
validation rules are defined
tenant/project scope is defined
security classification is defined
failure semantics are defined
versioning strategy is defined
evidence requirements are defined
```

---

# 141. Contract TESTED Gate

A contract reaches `TESTED` for a defined scope when required:

```text
serialization tests
schema validation tests
backward compatibility tests
authorization tests
tenant isolation tests
idempotency tests
error mapping tests
event ordering tests
negative malformed-input tests
```

pass.

---

# 142. Contract VERIFIED Gate

A contract reaches `VERIFIED` when:

```text
producer and consumer integration passes
required security gates pass
negative bypass tests pass
end-to-end workflow uses the contract
evidence proves expected behavior
```

---

# 143. Public API Negative Tests

Required examples:

```text
unauthenticated protected request denied
client-forged principal_id ignored/denied
client-forged tenant membership denied
cross-tenant project access denied
stale version update rejected
idempotency key request mismatch rejected
unauthorized approval denied
artifact from another tenant denied
event stream from another tenant denied
```

---

# 144. Internal Contract Negative Tests

Required examples:

```text
expired ExecutionGrant denied
task/grant mismatch denied
worker lease mismatch denied
stale fencing token denied
tool outside allowed_tools denied
secret outside secret_scope denied
provider outside route denied
RoutingDecision tenant mismatch denied
retrieval result tenant mismatch denied
state transition invalid sequence denied
```

---

# 145. Contract Red Lines

Reject any contract design that introduces:

```text
client-generated authoritative Principal
client-generated valid ExecutionGrant
client-generated PolicyDecision
client-generated RoutingDecision
factory-specific competing route schema
provider-specific product-level Goal schema
raw secrets in contract payload
tool result automatically trusted
artifact acceptance without version binding
evidence with no tenant/project/job context
state mutation with no sequence/concurrency rule
unversioned breaking durable event
```

---

# 146. Canonical Public API Map

```text
/v1/me

/v1/session/context

/v1/tenants
/v1/tenants/{tenant_id}

/v1/projects
/v1/projects/{project_id}

/v1/projects/{project_id}/goals
/v1/projects/{project_id}/jobs
/v1/jobs/{job_id}
/v1/jobs/{job_id}/events
/v1/jobs/{job_id}/user-input
/v1/jobs/{job_id}/cancel

/v1/approvals
/v1/approvals/{approval_id}
/v1/approvals/{approval_id}/decision

/v1/projects/{project_id}/sources
/v1/projects/{project_id}/sources/{source_id}

/v1/projects/{project_id}/uploads

/v1/projects/{project_id}/artifacts
/v1/artifacts/{artifact_id}
/v1/artifacts/{artifact_id}/versions
/v1/artifacts/{artifact_id}/versions/{version_id}

/v1/jobs/{job_id}/evidence
/v1/jobs/{job_id}/acceptance-manifest
/v1/evidence/{evidence_id}

/v1/notifications
/v1/notifications/{notification_id}/read

/v1/search

/v1/projects/{project_id}/imports
/v1/projects/{project_id}/exports
```

This is the canonical **target API family map**, not proof that all endpoints are currently deployed.

---

# 147. Canonical Internal Contract Map

```text
GoalSpec
    │
    ▼
ExecutionProposal
    │
    ▼
CapabilityRequirement
    │
    ▼
ExecutionRequest
    │
    ▼
PolicyDecision
    │
    ├────► ApprovalRequest / ApprovalDecision
    │
    ▼
ExecutionGrant
    │
    ▼
RoutingRequest
    │
    ▼
RoutingDecision
    │
    ▼
TaskEnvelope
    │
    ▼
WorkerLease
    │
    ├────► ToolRequest → ToolResult
    │
    ├────► ProviderRequest → ProviderResult
    │
    └────► RetrievalRequest → RetrievalResult
    │
    ▼
ArtifactVersion
    │
    ▼
ValidationResult
    │
    ▼
EvaluationResult
    │
    ▼
EvidenceRecord
    │
    ▼
AcceptanceManifest
```

---

# 148. Full End-to-End API Contract Flow

```text
CLIENT
  │
  │ POST /projects/{project}/goals
  ▼
GOAL SUBMISSION
  │
  ▼
GoalSpec
  │
  ▼
ExecutionProposal
  │
  ▼
CapabilityRequirement
  │
  ▼
ExecutionRequest
  │
  ▼
PolicyDecision
  │
  ├──── DENY
  │
  ├──── REQUIRE_APPROVAL
  │        │
  │        ▼
  │   ApprovalDecision
  │
  ▼
ExecutionGrant
  │
  ▼
RoutingRequest
  │
  ▼
ONE RoutingDecision
  │
  ▼
TaskEnvelope
  │
  ▼
Queue / WorkerLease / Fencing
  │
  ▼
Worker
  │
  ├──── ToolRequest ──────► Tool Gateway ──────► ToolResult
  │
  ├──── ProviderRequest ──► Adapter ───────────► ProviderResult
  │
  └──── RetrievalRequest ─► Knowledge Plane ───► RetrievalResult
  │
  ▼
ArtifactVersion
  │
  ▼
ValidationResult
  │
  ├──── FAIL ─► FailureRecord ─► RepairProposal ─► Re-admission
  │
  ▼ PASS
EvaluationResult
  │
  ▼
EvidenceRecord
  │
  ▼
AcceptanceManifest
  │
  ▼
CLIENT ARTIFACT / EVIDENCE PROJECTION
```

---

# 149. Canonical Contract Formula

```text
AUTHENTICATED INTENT
        +
SERVER-DERIVED PRINCIPAL / TENANT / PROJECT
        +
VERSIONED TYPED CONTRACTS
        +
FAIL-CLOSED POLICY
        +
SCOPED EXECUTIONGRANT
        +
ONE ROUTINGDECISION
        +
LEASED / FENCED EXECUTION
        +
PERMISSIONED TOOL / PROVIDER ADAPTERS
        +
AUTHORIZED RETRIEVAL
        +
VERSIONED ARTIFACTS
        +
VALIDATION / EVALUATION
        +
INTEGRITY-VERIFIABLE EVIDENCE
        =
ILAIOS API CONTRACT MODEL
```

---

# 150. Final API Invariant

The defining API rule is:

> **No API surface may give a caller more authority than the canonical ILAIOS architecture grants to that caller.**

Public clients express:

```text
intent
context selection
user input
approval decisions
cancellation requests
authorized reads
```

The platform owns:

```text
identity resolution
tenant validation
policy
ExecutionGrant
routing
scheduler state
worker authority
tool permissions
provider credentials
evidence truth
final acceptance
```

**ILAIOS APIs expose the product. They do not expose a bypass around the product’s governance.**
