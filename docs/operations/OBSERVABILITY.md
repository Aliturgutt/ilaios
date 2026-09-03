# ILAIOS — OBSERVABILITY

**Document Type:** Canonical Observability Architecture & Operations Standard  
**Format:** GitHub Markdown + ASCII observability diagrams  
**Status:** Canonical Baseline v1.0 — Published in Repository  
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
**Milestone Companion:** `MILESTONES.md`  
**Core Observability Principle:** **OBSERVE THE SYSTEM WITHOUT CREATING A SECOND SOURCE OF TRUTH**

> This document defines the canonical observability model for ILAIOS: telemetry boundaries, logs, metrics, traces, correlation, health, SLOs, alerting, dashboards, provider/tool/worker/RAG visibility, security observability, privacy/redaction, cost observability, incident linkage, production health evidence, and observability Definition of Done. Observability explains what the platform is doing; it does not replace authoritative runtime state, Evidence Records, Policy Decisions, or deployment evidence.

---

# 00. Purpose

ILAIOS is an autonomous execution platform.

It must be possible to answer, with bounded and privacy-safe telemetry:

```text
What is running?
Why is it running?
For which tenant/project/job/task?
Which provider/tool/worker path is involved?
What is slow?
What failed?
What retried?
What was denied?
What is consuming cost?
What is currently healthy?
What changed after a release?
```

Observability exists to make autonomous execution understandable and operable.

It must not become:

```text
a second job-state database
a second evidence system
a second audit authority
a place to store raw secrets
a place to store full customer content by default
```

---

# 01. Scope

This document owns:

- telemetry architecture;
- logging standards;
- metrics standards;
- tracing standards;
- correlation/causality identifiers;
- runtime health observations;
- liveness/readiness semantics;
- SLI/SLO concepts;
- alerting;
- dashboarding;
- provider observability;
- routing observability;
- worker observability;
- queue/scheduler observability;
- Tool Gateway observability;
- RAG/Knowledge observability;
- artifact/evaluation observability;
- deployment observability;
- FinOps observability;
- security observability;
- privacy/redaction requirements;
- telemetry retention;
- sampling;
- cardinality governance;
- incident linkage;
- observability testing;
- observability Definition of Done.

This document does **not** own:

```text
authoritative job state
    → IMPLEMENTATION_SPEC.md / DATA_ARCHITECTURE.md

canonical EvidenceRecord semantics
    → API_CONTRACTS.md / DATA_ARCHITECTURE.md

security controls
    → SECURITY_ARCHITECTURE.md

incident/recovery procedures
    → FAILURE_RECOVERY.md

deployment topology
    → DEPLOYMENT_ARCHITECTURE.md

cost authority
    → FINOPS.md
```

---

# 02. Observability vs Evidence

This distinction is constitutional.

```text
OBSERVABILITY
    = operational visibility

EVIDENCE
    = canonical proof of material decisions/actions
```

Examples:

```text
log line:
"provider request completed"
    ≠
canonical ProviderResult evidence

metric:
job_success_total += 1
    ≠
AcceptanceManifest

trace:
tool call span
    ≠
authoritative ToolResult record
```

Observability may reference evidence.

It must not replace evidence.

---

# 03. Observability vs State

Authoritative runtime state lives in canonical state stores.

Telemetry may project or report state.

Correct:

```text
JobStore
    → authoritative state

Metric
    → count of jobs by state
```

Incorrect:

```text
metric says RUNNING
therefore JobStore is ignored
```

---

# 04. Observability vs Current Health

Current health is an observation.

It is mutable.

```text
HEALTHY
DEGRADED
UNHEALTHY
UNKNOWN
```

A historical health observation does not prove present health.

---

# 05. Target Observability vs Current Reality

This document defines the target observability architecture.

Current observability reality must be proven from:

```text
current instrumentation
current telemetry pipeline
current dashboards
current alerts
current health endpoints
current runtime observations
```

Therefore:

```text
metric specified
≠
metric implemented

dashboard specified
≠
dashboard deployed

alert specified
≠
alert currently active

historical health PASS
≠
current service health
```

---

# 06. Observability Constitutional Invariants

Mandatory:

```text
NO raw secret logging
NO observability-based authorization
NO log-only evidence truth
NO client-controlled authoritative telemetry labels
NO cross-tenant telemetry leakage
NO unbounded metric cardinality
NO raw prompt/artifact content in metrics
NO hidden provider/tool path without correlation
NO current-live-health claim without recent observation
NO critical alert without owner/routing
```

---

# 07. Canonical Observability Planes

```text
APPLICATION TELEMETRY
    │
    ├─ logs
    ├─ metrics
    └─ traces
    │
    ▼
TELEMETRY PIPELINE
    │
    ├─ collect
    ├─ redact
    ├─ sample
    ├─ enrich
    └─ export
    │
    ▼
OBSERVABILITY BACKEND
    │
    ├─ search
    ├─ dashboards
    ├─ SLO
    └─ alerts
```

Separate:

```text
EVIDENCE STORE
    = canonical proof plane
```

---

# 08. Observability Architecture Map

```text
CLIENT / API
    │
    ▼
CONTROL PLANE
    │
    ├──── logs
    ├──── metrics
    └──── traces
    │
    ▼
WORKFLOW / SCHEDULER
    │
    ▼
QUEUE
    │
    ▼
WORKER
    │
    ├──── TOOL GATEWAY
    │       │
    │       └──── external services
    │
    ├──── PROVIDER ADAPTER
    │       │
    │       └──── AI/media providers
    │
    └──── KNOWLEDGE PLANE
            │
            └──── retrieval/index
```

All major boundaries should emit correlation-safe telemetry.

---

# 09. Three Pillars

Canonical pillars:

```text
LOGS
METRICS
TRACES
```

They complement each other.

---

# 10. Logs

Logs answer:

```text
What happened?
With what context?
What error occurred?
```

Logs should be:

```text
structured
bounded
redacted
queryable
correlated
```

---

# 11. Metrics

Metrics answer:

```text
How often?
How much?
How slow?
How healthy?
```

Metrics are optimized for aggregation.

---

# 12. Traces

Traces answer:

```text
Where did time go?
Which service/path contributed?
What was the causal chain?
```

---

# 13. Correlation Identity

Recommended correlation identifiers:

```text
request_id
principal_id or safe actor ref
tenant_id
project_id
job_id
task_id
node_id
route_id
worker_id
lease_id
tool_call_id
provider_call_id
artifact_id
evaluation_id
deployment_id
```

Only include identifiers that are safe for the telemetry destination.

---

# 14. Correlation Rule

Every material execution path should allow reconstruction:

```text
request
→ job
→ task
→ route
→ worker
→ tool/provider
→ artifact
→ validation/evaluation
```

without storing raw content.

---

# 15. Correlation Propagation

Identifiers should propagate through:

```text
API headers/context
queue envelopes
worker context
tool requests
provider requests
trace context
```

---

# 16. Correlation Trust

Client-supplied correlation IDs may be accepted for diagnostics.

They are not authorization.

Canonical tenant/project/job identities are server-derived.

---

# 17. Request ID

`request_id` identifies one inbound request.

It must not be used as job identity.

---

# 18. Job ID

`job_id` identifies canonical autonomous job.

It should appear in telemetry for job-related operations.

---

# 19. Task ID

`task_id` identifies bounded executable task.

Useful for:

```text
worker logs
provider calls
tool calls
retry
cost
```

---

# 20. Route ID

`route_id` links provider execution to canonical `RoutingDecision`.

Provider telemetry without route correlation is incomplete for governed execution.

---

# 21. Evidence Reference

Telemetry may include:

```text
evidence_id
```

when material.

Do not duplicate the entire evidence payload into logs.

---

# 22. Logging Standard

Logs should use structured key/value fields.

Example:

```json
{
  "event": "routing.decision.applied",
  "job_id": "job_...",
  "task_id": "task_...",
  "route_id": "route_...",
  "provider_id": "provider_...",
  "result": "accepted"
}
```

No secret/raw protected content.

---

# 23. Log Event Naming

Recommended:

```text
<domain>.<entity>.<action>
```

Examples:

```text
auth.session.created
policy.decision.denied
routing.decision.created
worker.lease.acquired
tool.call.completed
provider.call.failed
rag.retrieval.completed
artifact.validation.failed
deployment.health.degraded
```

---

# 24. Log Severity

Canonical levels:

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

Use consistently.

---

# 25. DEBUG

For development diagnostics.

Production DEBUG may be:

```text
disabled
sampled
temporarily enabled
```

according to policy.

Must still obey secret/privacy rules.

---

# 26. INFO

Normal meaningful state/event observations.

Avoid logging every trivial loop iteration.

---

# 27. WARNING

Unexpected but recoverable condition.

Examples:

```text
provider degraded
retry triggered
budget near threshold
stale cache detected
```

---

# 28. ERROR

Operation failed and requires handling.

---

# 29. CRITICAL

System/security condition with severe impact.

Examples:

```text
tenant isolation violation
evidence integrity failure
secret compromise
production deployment corruption
```

---

# 30. Log Volume Governance

Logging must not create:

```text
cost explosion
storage exhaustion
performance regression
```

Use:

```text
sampling
aggregation
rate limiting
deduplication
```

for repetitive non-critical events.

---

# 31. Raw Prompt Logging

Default:

```text
DO NOT log raw prompts
```

If temporary debugging requires content:

```text
explicit environment
authorization
redaction
retention
access control
```

---

# 32. Raw Provider Response Logging

Default:

```text
DO NOT log full raw provider output
```

Prefer:

```text
response size
status
model/resource ID
usage
hash/reference
```

---

# 33. Secret Redaction

Telemetry must redact:

```text
API keys
OAuth tokens
cookies
Authorization headers
private keys
passwords
connection strings
signed URLs where sensitive
```

---

# 34. PII Redaction

Where possible, avoid directly logging:

```text
email
phone
address
full names
user-generated content
```

Use opaque IDs.

---

# 35. Redaction Pipeline

Defense in depth:

```text
application-level suppression
      │
      ▼
telemetry processor redaction
      │
      ▼
backend access controls
```

---

# 36. Redaction Failure

If telemetry redaction fails:

```text
drop unsafe field
or
drop event
```

for high-risk data.

Do not prefer observability completeness over secret exposure.

---

# 37. Metrics Standard

Metrics should have:

```text
stable name
unit
description
type
labels
owner
```

---

# 38. Metric Types

Common types:

```text
counter
gauge
histogram
summary where justified
```

---

# 39. Naming

Examples:

```text
ilaios_api_requests_total
ilaios_job_duration_seconds
ilaios_queue_depth
ilaios_provider_calls_total
ilaios_tool_calls_total
ilaios_rag_retrieval_duration_seconds
ilaios_artifact_validation_failures_total
```

---

# 40. Metric Units

Use explicit base units:

```text
seconds
bytes
requests
tokens
currency minor units
```

---

# 41. Metric Cardinality Rule

Avoid labels with unbounded values.

Bad:

```text
prompt
URL
artifact text
email
exception message
full file path
```

Good:

```text
service
environment
status
capability
provider
model class
error class
```

---

# 42. Tenant Labels

Tenant labels can create high cardinality/privacy risk.

Use tenant-level metrics only where business/operations need justifies and backend policy supports it.

Do not expose tenant labels publicly.

---

# 43. Project Labels

Same caution as tenant labels.

Prefer aggregation unless per-project observability is required.

---

# 44. Job-Level Metrics

Do not encode each `job_id` as metric label.

Use logs/traces/evidence for job-level inspection.

---

# 45. Error Labels

Use bounded error classes:

```text
AUTHZ_DENIED
PROVIDER_TIMEOUT
BUDGET_EXHAUSTED
VALIDATION_FAILED
```

not raw exception text.

---

# 46. Histograms

Use histograms for:

```text
latency
payload size
queue age
provider duration
retrieval duration
artifact size
```

---

# 47. API Metrics

Recommended:

```text
request count
latency
error rate
auth failure rate
rate-limit events
```

---

# 48. Authentication Metrics

Monitor:

```text
login success/failure
MFA challenge
session revocation
OIDC/SAML errors
```

Avoid logging sensitive tokens.

---

# 49. Authorization Metrics

Monitor:

```text
allow
deny
require-approval
missing-context fail-closed
```

---

# 50. Tenant Isolation Metrics

Security-sensitive indicators:

```text
tenant scope validation failures
cross-tenant access denial
unexpected tenant mismatch
```

Any successful cross-tenant violation is a critical incident, not a normal metric.

---

# 51. Control Plane Metrics

Recommended:

```text
job creations
state transition rate
state transition failures
policy decision latency
routing decision latency
approval wait count
```

---

# 52. Scheduler Metrics

Monitor:

```text
ready tasks
scheduled tasks
scheduler latency
unschedulable tasks
dependency wait
```

---

# 53. Queue Metrics

Monitor:

```text
depth
oldest message age
enqueue rate
dequeue rate
redelivery rate
dead-letter rate
```

---

# 54. Worker Metrics

Monitor:

```text
active workers
worker startup time
task duration
task success/failure
lease expiry
heartbeat failures
resource utilization
```

---

# 55. Lease Metrics

Important:

```text
lease acquisitions
lease renewals
lease expiries
stale commits rejected
fencing mismatches
```

---

# 56. Retry Metrics

Monitor:

```text
retry count
retry reason
retry cost
retry latency
```

---

# 57. Repair Metrics

Monitor:

```text
repair attempts
repair success
repair failure
repair cost
repair duration
```

---

# 58. Bounded Repair Alert

Alert when:

```text
repair rate spikes
attempt exhaustion increases
repair cost ratio exceeds expected range
```

---

# 59. Routing Metrics

Monitor:

```text
route decisions
provider selection distribution
route failures
fallback rate
no-eligible-provider
deterministic tie-break use
```

---

# 60. Provider Metrics

Per provider/resource:

```text
request count
success rate
latency
timeout
rate limit
quota failure
usage units
cost
```

---

# 61. Provider Health

Provider health may be derived from:

```text
recent failures
latency
quota
explicit provider status
```

Health signal influences routing but does not replace policy.

---

# 62. Provider Fallback Metrics

Track:

```text
fallback count
fallback reason
fallback provider
fallback success
fallback cost delta
```

---

# 63. Tool Gateway Metrics

Monitor:

```text
tool requests
allowed/denied
tool latency
tool failures
secret resolution failures
network denials
filesystem denials
```

---

# 64. High-Risk Tool Metrics

Examples:

```text
repo mutation
deployment
DNS
payment
email send
cloud mutation
```

High-risk operations should be visible by bounded category.

---

# 65. Tool Denial Metrics

Tool denial is expected under policy.

Monitor unusual spikes to detect:

```text
attack
misconfiguration
agent drift
```

---

# 66. Knowledge/RAG Metrics

Monitor:

```text
ingestion rate
ingestion failures
source count
source-version count
chunk/index count
retrieval count
retrieval latency
reranking latency
empty-result rate
citation rate
groundedness evaluation
```

---

# 67. RAG Authorization Metrics

Monitor:

```text
authorization denials
tenant mismatch
project mismatch
classification denial
stale-context rejection
```

---

# 68. RAG Security Metrics

Monitor:

```text
DLP triggers
prompt-injection detections/signals
provenance mismatch
deleted-source retrieval attempts
cross-tenant negative-test failures
```

---

# 69. RAG Quality Metrics

May include:

```text
retrieval precision
retrieval recall
citation correctness
groundedness
answer completeness
```

These are evaluation metrics, not necessarily low-latency runtime metrics.

---

# 70. Artifact Metrics

Monitor:

```text
artifact creations
artifact size
artifact version count
validation pass/fail
integrity mismatch
delivery success/failure
```

---

# 71. Evaluation Metrics

Monitor:

```text
evaluation count
PASS
FAIL
NEEDS_REVIEW
evaluator latency
repair trigger rate
```

---

# 72. Acceptance Metrics

Useful:

```text
accepted outcome rate
first-pass acceptance rate
repair-to-acceptance rate
```

---

# 73. Evidence Metrics

Monitor:

```text
evidence write success
evidence write failure
evidence completeness failure
integrity verification failure
```

Evidence contents remain in Evidence Store, not metric labels.

---

# 74. FinOps Metrics

Monitor:

```text
cost per job
cost per accepted outcome
provider spend
retry cost
repair cost
budget utilization
budget denial
forecast variance
```

---

# 75. Deployment Metrics

Monitor:

```text
deployment count
deployment success/failure
deployment duration
rollback count
post-deploy health failure
```

---

# 76. Release Metrics

May include:

```text
release frequency
change failure rate
rollback rate
time to recovery
```

when definitions are formally adopted.

---

# 77. Trace Standard

Traces should follow meaningful service boundaries.

Avoid one giant unstructured trace.

---

# 78. Root Span

Possible root spans:

```text
HTTP request
job execution
deployment
scheduled background operation
```

---

# 79. Job Trace

A job trace may include:

```text
plan
policy
routing
scheduler
worker
provider
tool
validation
evaluation
```

---

# 80. Trace Context Propagation

Use standard trace propagation where infrastructure supports it.

Queue boundaries must propagate trace context safely.

---

# 81. Trace and Job Identity

Trace ID is not job ID.

A job may span:

```text
multiple traces
long durations
restarts
checkpoints
```

Use `job_id` for durable correlation.

---

# 82. Span Attributes

Recommended bounded attributes:

```text
service
operation
environment
capability
job_state
provider
tool_class
result
error_class
```

---

# 83. Span Events

Useful:

```text
retry
fallback
approval wait
checkpoint
fencing rejection
```

---

# 84. Trace Sampling

Sampling may be:

```text
head-based
tail-based
adaptive
```

Critical security/failure traces may be retained at higher rate.

---

# 85. Unsampled Evidence

Evidence must not depend on trace sampling.

---

# 86. Trace Privacy

Never attach:

```text
raw prompt
full document
secret
token
```

as span attribute.

---

# 87. Trace Size

Avoid huge span payloads.

Store references/hashes.

---

# 88. Long-Running Jobs

For long autonomous jobs:

```text
durable job ID
multiple trace segments
checkpoint correlation
```

is preferred over one indefinite trace.

---

# 89. Health Model

Canonical health levels:

```text
PROCESS HEALTH
SERVICE READINESS
DEPENDENCY HEALTH
WORKFLOW HEALTH
BUSINESS/PRODUCT HEALTH
```

---

# 90. Liveness

Liveness answers:

```text
Is the process alive enough to continue/restart?
```

It should be simple.

---

# 91. Readiness

Readiness answers:

```text
Can this instance safely receive workload?
```

May depend on:

```text
config
DB
queue
policy readiness
```

---

# 92. Dependency Health

Dependencies include:

```text
database
queue
evidence store
provider
vector store
secret manager
```

Dependency health does not automatically equal service health.

---

# 93. Workflow Health

Examples:

```text
queue age
job stuck rate
repair exhaustion
checkpoint failures
```

---

# 94. Business/Product Health

Examples:

```text
accepted outcome rate
artifact delivery rate
RAG groundedness trend
```

---

# 95. Health Observation Contract

Conceptual:

```yaml
health_observation_id: "health_..."
resource_ref: "..."
observed_at: "..."
status: "HEALTHY|DEGRADED|UNHEALTHY|UNKNOWN"
checks: []
evidence_ref: null
```

---

# 96. Health Freshness

Health has a time horizon.

A health observation should be considered stale after a service-specific interval.

Exact intervals belong to operational policy.

---

# 97. Health Claim Rule

To claim:

```text
LIVE_HEALTHY
```

require recent direct runtime observation.

---

# 98. Health vs Deployment

```text
deployment succeeded
≠
service healthy
```

Post-deployment checks are required.

---

# 99. SLI

Service Level Indicator is measured behavior.

Examples:

```text
availability
latency
successful job completion
queue delay
artifact delivery success
```

---

# 100. SLO

Service Level Objective defines target for an SLI.

Numeric targets should be formally adopted.

This document does not invent universal numbers.

---

# 101. SLO Scope

SLOs may differ by:

```text
API
Control Plane
Knowledge
worker class
factory
enterprise tier
```

---

# 102. Error Budget

Error budget translates SLO into allowable failure.

Error budget is operational governance, not user financial budget.

---

# 103. Error Budget vs FinOps Budget

```text
SLO error budget
    = reliability tolerance

FinOps budget
    = economic ceiling
```

Do not conflate.

---

# 104. Burn Rate

Error-budget burn rate can guide alerting.

---

# 105. SLO Alerting

Alert on meaningful threat to SLO, not every tiny fluctuation.

---

# 106. Alerting Principle

Alerts should be:

```text
actionable
owned
bounded
deduplicated
severity-classified
```

---

# 107. Alert Severity

Suggested:

```text
INFO
WARNING
HIGH
CRITICAL
```

Exact paging policy belongs to operations.

---

# 108. Critical Alerts

Examples:

```text
tenant isolation violation
secret compromise
evidence integrity failure
production-wide outage
unauthorized production mutation
```

---

# 109. High Alerts

Examples:

```text
Control Plane severe error rate
queue backlog threatens SLO
provider outage with limited fallback
RAG authorization failures spike
```

---

# 110. Warning Alerts

Examples:

```text
budget nearing threshold
provider latency degraded
storage growth abnormal
```

---

# 111. Alert Ownership

Each alert should have:

```text
owner
severity
runbook
notification target
deduplication behavior
```

---

# 112. Alert Without Owner

An alert without an owner is incomplete.

---

# 113. Alert Fatigue

Avoid:

```text
low-value noisy alerts
duplicate alerts
alert per individual retry
```

Prefer aggregation and symptoms.

---

# 114. Symptom vs Cause

Page on user-impacting symptom.

Use lower-severity telemetry for root-cause clues.

---

# 115. Alert Deduplication

Deduplicate repeated events by:

```text
service
failure class
resource
time window
```

---

# 116. Alert Suppression

Suppression may be used during known maintenance.

Must be:

```text
bounded
documented
time-limited
```

Never suppress security-critical signals silently.

---

# 117. Alert Escalation

Unacknowledged critical alerts may escalate according to operations policy.

---

# 118. Alert Evidence

Critical alerts may link to:

```text
trace
logs
metrics
deployment ID
evidence ID
```

---

# 119. Dashboard Principle

Dashboards are projections.

They are not authoritative state stores.

---

# 120. Executive Dashboard

May show:

```text
system availability
accepted outcomes
active incidents
cost
major provider health
deployment health
```

---

# 121. Platform Dashboard

May show:

```text
API
Control Plane
queue
workers
DB
evidence
artifact store
```

---

# 122. Routing Dashboard

May show:

```text
provider selection
fallback
latency
failure
cost
quality
```

---

# 123. RAG Dashboard

May show:

```text
ingestion
retrieval
authorization denial
latency
quality
DLP
```

---

# 124. Security Dashboard

May show:

```text
auth anomalies
tenant violations
grant denials
high-risk tool denials
secret events
```

---

# 125. FinOps Dashboard

May show:

```text
spend
budget
forecast
provider mix
retry/repair cost
```

---

# 126. Deployment Dashboard

May show:

```text
current release
deployment status
health
rollback
change failure
```

Current release must come from deployment/runtime truth.

---

# 127. Dashboard Access Control

Dashboards may expose sensitive operational metadata.

Apply:

```text
authentication
role-based access
tenant scope where applicable
```

---

# 128. Tenant Dashboard

Enterprise tenants may see their own:

```text
jobs
usage
cost
quality
availability
```

but never other tenant metadata.

---

# 129. Public Status Page

A public status page may expose:

```text
high-level service health
incidents
maintenance
```

without sensitive internals.

---

# 130. Status Page Is Not Internal Truth

Public status is a projection.

Internal health/evidence remains authoritative.

---

# 131. Security Observability

Security-relevant telemetry includes:

```text
auth failures
MFA events
authorization denials
tenant mismatches
grant validation failures
approval failures
secret access anomalies
network policy denials
```

---

# 132. Authentication Anomaly Signals

Examples:

```text
unusual login volume
repeated failed MFA
session replay signal
unexpected provider issuer
```

---

# 133. Authorization Anomaly Signals

Examples:

```text
same actor repeatedly requests forbidden tenant
unexpected high-risk tool request
grant mismatch
```

---

# 134. Tenant Isolation Signal

A detected successful cross-tenant access is CRITICAL.

A denied attempt is security telemetry and may indicate attack/misconfiguration.

---

# 135. Approval Abuse Signals

Monitor:

```text
approval replay attempts
expired approval use
scope mismatch
self-approval attempt
```

---

# 136. Grant Abuse Signals

Monitor:

```text
expired grant
wrong task
wrong tenant
tool outside scope
```

---

# 137. Tool Security Signals

Monitor:

```text
SSRF denial
path traversal denial
secret path denial
external egress denial
```

---

# 138. Provider Security Signals

Monitor:

```text
malformed response
unexpected model/resource
policy-ineligible provider attempt
```

---

# 139. RAG Security Signals

Monitor:

```text
cross-tenant retrieval attempt
classification denial
DLP event
poisoned source indicator
provenance mismatch
```

---

# 140. Secret Access Observability

Record:

```text
secret reference
service/worker identity
task/job scope
result
```

Never secret value.

---

# 141. Key Management Observability

Monitor:

```text
key rotation
signature verification failure
revoked key usage
```

---

# 142. Deployment Security Signals

Monitor:

```text
wrong environment attempt
unauthorized deploy
artifact digest mismatch
expired approval
```

---

# 143. Supply-Chain Signals

Monitor:

```text
dependency vulnerability
image digest drift
unexpected package
CI action change
```

---

# 144. Privacy Observability

Privacy telemetry should report:

```text
classification decisions
DLP triggers
provider residency denials
data minimization events
```

without exposing protected content.

---

# 145. DLP Telemetry

Record category, not raw data.

Example:

```text
dlp.category = "secret"
```

not:

```text
dlp.value = "sk-..."
```

---

# 146. Data Residency Telemetry

Record:

```text
requested region
allowed/denied
selected provider region
```

where safe.

---

# 147. Retention Telemetry

Monitor failures of:

```text
retention job
deletion propagation
archive lifecycle
```

---

# 148. Artifact Security Observability

Monitor:

```text
integrity mismatch
unauthorized download attempt
unexpected public access
```

---

# 149. Evidence Security Observability

Monitor:

```text
evidence write failure
integrity verification failure
unauthorized evidence access
```

---

# 150. FinOps Observability

FinOps telemetry must support operational cost visibility without replacing ledger/accounting truth.

---

# 151. Cost Attribution Signals

Useful bounded labels:

```text
capability
provider
resource class
environment
result
```

Tenant/job detail belongs in logs/ledger when needed.

---

# 152. Cost Anomaly Alert

Alert on:

```text
unexpected cost spike
retry storm
repair storm
provider price anomaly
storage growth
```

---

# 153. Budget Denial Observability

Track:

```text
budget exhausted
approval threshold
quota exhausted
unknown price
```

---

# 154. Provider Price Drift

Pricing metadata changes may trigger operational signal and forecast refresh.

---

# 155. Reliability Observability

Monitor:

```text
MTTR-related signals
failure frequency
retry success
checkpoint recovery
rollback
```

---

# 156. Recovery Observability

Monitor:

```text
checkpoint created
resume attempted
resume succeeded/failed
stale worker rejected
```

---

# 157. Cancellation Observability

Monitor:

```text
cancel requested
cancel acknowledged
late result rejected
final cancelled
```

---

# 158. Compensation Observability

Monitor:

```text
compensation requested
approved
executed
failed
```

---

# 159. Incident Correlation

Incident should link:

```text
service
environment
time window
deployments
alerts
traces
logs
evidence IDs
```

---

# 160. Incident Timeline

Telemetry should help construct:

```text
first signal
impact start
detection
containment
recovery
verification
```

---

# 161. Failure Recovery Boundary

`FAILURE_RECOVERY.md` owns operational recovery procedures.

This document provides the signals needed to detect/understand failures.

---

# 162. Deployment Correlation

Every deployment should emit/record:

```text
deployment_id
release_id
artifact hash
environment
```

into telemetry context.

---

# 163. Post-Deploy Comparison

Compare before/after:

```text
error rate
latency
accepted outcome rate
provider failure
cost
```

---

# 164. Canary Observability

Canary requires segmented metrics by:

```text
release/version
canary cohort
```

without exposing tenant data.

---

# 165. Rollback Observability

Monitor:

```text
rollback started
rollback completed
post-rollback health
```

---

# 166. Feature Flag Observability

Record bounded:

```text
flag version
variant
```

where useful.

Do not use flag telemetry as authorization.

---

# 167. Version Attribution

Telemetry should identify:

```text
service version
artifact version
commit/revision
```

where practical.

---

# 168. Configuration Attribution

Material behavior may require:

```text
config version
policy version
```

for debugging/reproducibility.

---

# 169. Provider Version Attribution

When provider/model versions are material:

```text
provider_id
model/resource_id
adapter_version
```

---

# 170. Schema Version Attribution

Cross-process errors should include schema/contract version where useful.

---

# 171. Environment Attribution

Every telemetry event must identify environment.

Examples:

```text
local
ci
staging
production
```

---

# 172. Region Attribution

Include region where needed for:

```text
residency
latency
failover
```

---

# 173. Service Attribution

Every telemetry record must identify service/component.

---

# 174. Capability Attribution

Where useful, include canonical capability ID.

---

# 175. Factory Attribution

Factory metrics should not create a parallel capability identity system.

Use canonical factory/capability IDs.

---

# 176. Provider Attribution

Provider labels must use stable ILAIOS provider IDs, not free-form display names.

---

# 177. Tool Attribution

Tool labels should use stable tool class/ID.

---

# 178. Error Taxonomy

Errors should map to bounded classes.

Recommended families:

```text
AUTH
AUTHZ
POLICY
TENANT
VALIDATION
PROVIDER
TOOL
QUEUE
WORKER
STATE
ARTIFACT
EVIDENCE
RAG
SECURITY
FINOPS
DEPLOYMENT
```

---

# 179. Retryability Attribute

Errors may include:

```text
retryable = true|false
```

derived from failure classification.

---

# 180. User-Actionable Attribute

Some errors may indicate:

```text
needs_user_input
needs_owner
```

for UX/operations.

---

# 181. Logging Exceptions

Capture:

```text
error_class
safe message
stack trace in protected backend
```

Do not leak secrets.

---

# 182. Stack Trace Retention

Stack traces may contain paths/values.

Protect access and retention.

---

# 183. Sampling Logs

High-volume INFO logs may be sampled.

Never sample away all visibility of critical security events.

---

# 184. Tail Sampling Traces

Tail sampling can retain:

```text
errors
slow traces
security-relevant traces
```

at higher rate.

---

# 185. Telemetry Retention

Retention depends on:

```text
diagnostic value
security
privacy
cost
compliance
```

Do not retain all telemetry forever by default.

---

# 186. Logs vs Evidence Retention

Evidence may need longer retention than logs.

Do not delete required evidence because log retention expired.

---

# 187. Metric Retention

Aggregated metrics may retain longer than raw logs.

---

# 188. Trace Retention

Detailed traces may be shorter-lived due to volume/privacy.

---

# 189. Security Telemetry Retention

Security telemetry may require longer retention according to risk/compliance.

---

# 190. Telemetry Data Classification

Classify telemetry itself.

Possible:

```text
PUBLIC
INTERNAL
CONFIDENTIAL
RESTRICTED
```

depending on fields.

---

# 191. Telemetry Access

Apply least privilege.

Examples:

```text
developer
operator
security
billing
tenant admin
```

may need different views.

---

# 192. Observability Backend Credentials

Telemetry exporters use scoped credentials.

They must not have application mutation authority.

---

# 193. Telemetry Pipeline Isolation

Compromise of telemetry backend must not grant:

```text
Control Plane authority
provider secrets
tenant DB write
```

---

# 194. Telemetry Ingestion Authentication

Services should authenticate to telemetry pipeline where practical.

---

# 195. Log Injection

Untrusted user/tool/provider data must be escaped/structured.

Never parse raw log text as trusted commands.

---

# 196. Metric Poisoning

Do not trust client-supplied metric labels that can alter operational decisions without validation.

---

# 197. Trace Poisoning

Trace context from external clients may be accepted but sanitized/bounded.

---

# 198. Observability Availability

Telemetry pipeline failure should not necessarily stop all product execution.

But critical evidence is separate and may be mandatory.

---

# 199. Telemetry Backpressure

Telemetry exporters should use:

```text
bounded buffers
batching
drop policy for non-critical telemetry
```

to avoid cascading application failure.

---

# 200. Critical Telemetry Loss

If critical security observability fails:

```text
alert through alternate path
or
degrade safely
```

according to risk.

---

# 201. Evidence Write Failure

Evidence write failure is not merely observability loss.

If evidence is mandatory:

```text
verified completion may be blocked
```

---

# 202. Logging Performance

Logging should not dominate critical request latency.

---

# 203. Async Export

Prefer async/batched telemetry export when safe.

---

# 204. Local Development Observability

Local environment should support:

```text
console structured logs
local metrics
trace debugging
```

without production secrets.

---

# 205. CI Observability

CI may emit:

```text
test timing
failure class
artifact size
coverage
```

CI logs remain separate from runtime logs.

---

# 206. Staging Observability

Staging should approximate production instrumentation.

---

# 207. Production Observability

Production requires:

```text
service health
critical metrics
structured logs
trace correlation
alerts
```

for defined service scope.

---

# 208. Provider External Status

External provider status pages may supplement internal telemetry.

Internal observed behavior remains important.

---

# 209. Synthetic Monitoring

Safe synthetic tests may verify:

```text
API
authentication
job creation
RAG query
artifact retrieval
```

without customer side effects.

---

# 210. Synthetic Tenant

Use dedicated test tenant/project.

Never mix synthetic monitoring with customer data.

---

# 211. Synthetic Side Effects

Avoid real:

```text
payments
emails
production mutations
```

unless explicitly designed.

---

# 212. Black-Box Monitoring

Monitor externally observable behavior:

```text
DNS
TLS
HTTP
API response
```

---

# 213. White-Box Monitoring

Monitor internal metrics:

```text
queue
DB
worker
provider
```

---

# 214. Both Are Required

Black-box may detect user impact before internal metrics.

White-box helps root cause.

---

# 215. API SLI Candidates

Examples:

```text
availability
p95/p99 latency
error rate
```

Exact percentiles/targets require operational policy.

---

# 216. Job SLI Candidates

Examples:

```text
time to accepted outcome
success rate
stuck-job rate
```

---

# 217. RAG SLI Candidates

Examples:

```text
retrieval latency
authorization correctness
groundedness trend
```

Security correctness is a hard gate, not a normal error-budget tolerance.

---

# 218. Provider SLI Candidates

Examples:

```text
success rate
latency
rate-limit rate
```

---

# 219. Tool SLI Candidates

Examples:

```text
success rate
latency
permission-denial anomalies
```

---

# 220. Artifact SLI Candidates

Examples:

```text
artifact creation success
validation success
delivery success
```

---

# 221. Evidence SLI Candidates

Examples:

```text
evidence write success
completeness success
```

---

# 222. SLO Governance

SLOs must be:

```text
owned
versioned
measurable
reviewed
```

---

# 223. SLO Change

Changing target may require:

```text
product
engineering
operations
FinOps
```

review depending on impact.

---

# 224. SLO Anti-Pattern

Do not define vanity SLOs disconnected from user outcomes.

---

# 225. Alert Runbook

Every high/critical alert should link to a runbook or recovery guidance.

---

# 226. Runbook Boundary

Runbook may instruct:

```text
inspect
contain
restart
rollback
```

Detailed recovery belongs in `FAILURE_RECOVERY.md`.

---

# 227. Alert Testing

Alerts must be tested.

Examples:

```text
synthetic metric threshold
simulated provider outage
queue backlog
```

---

# 228. Alert Delivery Testing

Verify notification channel works.

---

# 229. Alert Silence Testing

Verify maintenance silence expires.

---

# 230. Dashboard Testing

Dashboards should be validated for:

```text
correct query
correct units
correct environment
no tenant leakage
```

---

# 231. Telemetry Contract Testing

Instrumentation fields should be tested for critical events.

---

# 232. Redaction Tests

Mandatory:

```text
API key absent
OAuth token absent
password absent
Authorization header absent
private key absent
```

---

# 233. Cardinality Tests

Check bounded label dimensions.

---

# 234. Correlation Tests

E2E should verify:

```text
request_id
job_id
task_id
route_id
```

propagate across major boundaries.

---

# 235. Trace Continuity Tests

Queue/worker boundary should preserve trace/correlation context.

---

# 236. Health Endpoint Tests

Test:

```text
healthy
dependency down
misconfigured
not ready
```

---

# 237. Liveness Safety Test

Liveness endpoint must not trigger side effects.

---

# 238. Readiness Fail-Closed Test

Missing critical configuration should produce not-ready.

---

# 239. Provider Observability Tests

Mock:

```text
success
timeout
rate limit
malformed response
```

and verify telemetry.

---

# 240. Worker Observability Tests

Test:

```text
lease acquire
heartbeat
expiry
stale commit rejection
```

telemetry.

---

# 241. Queue Observability Tests

Test backlog/redelivery/DLQ signals.

---

# 242. RAG Observability Tests

Test:

```text
authorized retrieval
denied retrieval
empty retrieval
injection/DLP event
```

telemetry without content leak.

---

# 243. Tool Observability Tests

Test allowed/denied tool call telemetry.

---

# 244. Artifact Observability Tests

Test validation PASS/FAIL events.

---

# 245. Evidence Observability Tests

Test evidence write/completeness failures produce operational signal.

---

# 246. FinOps Observability Tests

Test budget denial and spend spike alerts.

---

# 247. Deployment Observability Tests

Test deployment success/failure/rollback signals.

---

# 248. Security Observability Tests

Inject benign security test events to verify alert path.

---

# 249. Observability Negative Tests

Mandatory examples:

```text
secret does not appear in logs
prompt does not become metric label
Tenant A cannot access Tenant B telemetry
client cannot spoof authoritative tenant label
trace sampling does not remove EvidenceRecord
```

---

# 250. Observability Red-Team

Attempt:

```text
log injection
cardinality explosion
secret exfiltration via logs
cross-tenant dashboard access
trace-context abuse
alert suppression abuse
```

---

# 251. Cardinality Attack

Attacker submits unique strings to inflate metrics.

Mitigation:

```text
bounded enums
normalization
drop unsafe labels
```

---

# 252. Log Flood Attack

Mitigation:

```text
rate limits
sampling
deduplication
bounded payload
```

---

# 253. Telemetry Exfiltration Threat

Treat observability backend as protected data system.

---

# 254. Dashboard Injection Threat

Never render untrusted raw HTML/script from logs.

---

# 255. Alert Injection Threat

Untrusted content must not become executable notification content.

---

# 256. Incident Evidence Correlation

Telemetry helps discover evidence IDs.

Evidence store proves the material event.

---

# 257. Current Health Evidence

A current health report should contain:

```text
observed_at
environment
service/resource
check
status
```

---

# 258. Health Report Example

```yaml
service: "control-plane"
environment: "production"
observed_at: "..."
status: "HEALTHY"
checks:
  database: "PASS"
  queue: "PASS"
  policy: "PASS"
```

Example only.

---

# 259. Current Health Expiration

Do not use yesterday’s health report as proof of current health without policy-defined freshness.

---

# 260. Observability Current-State Report

Recommended:

```text
Environment:
Release:
Observed at:
Overall status:
Degraded dependencies:
Active alerts:
SLO status:
Recent deployment:
```

---

# 261. Unknown Is Valid

If health cannot be observed:

```text
UNKNOWN
```

is more truthful than guessing HEALTHY.

---

# 262. Service Dependency Map

Observability should allow dependency mapping:

```text
API
→ Control Plane
→ DB
→ Queue
→ Worker
→ Provider/Tool
```

---

# 263. Dynamic Dependency Discovery

Tracing may reveal unexpected dependencies.

Unexpected direct dependency may indicate architecture drift.

---

# 264. Architecture Drift Signal

Examples:

```text
factory directly contacting provider
worker directly contacting DB admin endpoint
client contacting vector DB
```

Observability can help detect these.

---

# 265. No-Bypass Telemetry

Production paths should expose enough telemetry to detect canonical boundary bypass.

---

# 266. Audit vs Observability

Audit events may be stored as evidence/security audit.

Observability can index/project them.

Do not downgrade audit records into disposable logs.

---

# 267. Security Audit Event

Examples:

```text
role change
policy change
approval
secret rotation
provider enablement
deployment authorization
```

These often belong to canonical evidence/audit.

---

# 268. Telemetry Schema Versioning

Structured telemetry contracts should evolve compatibly.

---

# 269. Event Field Changes

Avoid silently changing metric/log field meaning.

---

# 270. Metric Rename

Metric rename requires dashboard/alert migration.

---

# 271. Label Change

Label change may cause series explosion or query breakage.

Review carefully.

---

# 272. Trace Attribute Change

Keep stable keys for important cross-service debugging.

---

# 273. Observability Ownership

Each service/capability should own:

```text
its instrumentation
its health checks
its runbook links
its critical alerts
```

Platform observability owns shared pipeline/standards.

---

# 274. Central Platform Observability

Shared concerns:

```text
collector
backend
retention
redaction
global dashboards
paging integration
```

---

# 275. Factory Observability

Factories should expose domain outcomes, not create private telemetry backends.

---

# 276. Agent Observability

Agent telemetry may include:

```text
agent_id
role
task
decision/evaluation result
```

not chain-of-thought/private reasoning.

---

# 277. Reasoning Privacy

Do not attempt to store hidden model chain-of-thought as operational telemetry.

Record structured decisions/evidence instead.

---

# 278. Prompt Metadata

Safe metadata may include:

```text
input size
language
modality
```

if useful.

Do not log prompt text by default.

---

# 279. Model Output Metadata

Safe:

```text
output size
latency
usage
validation result
```

---

# 280. User Feedback Observability

User feedback may be correlated to:

```text
job
artifact
release
```

with privacy-safe identifiers.

---

# 281. Quality Regression Signal

Monitor decline in:

```text
acceptance rate
first-pass yield
groundedness
artifact validation
```

---

# 282. Provider Drift Signal

A provider/model change may show:

```text
latency shift
quality shift
failure shift
cost shift
```

---

# 283. Cost-Quality Dashboard

Useful dimensions:

```text
provider
capability
cost per accepted result
repair rate
quality
latency
```

---

# 284. Privacy-Quality Tradeoff

Dashboards must not encourage routing to privacy-ineligible provider for better cost/quality.

Policy eligibility remains first.

---

# 285. Observability for Approvals

Monitor:

```text
pending approvals
approval wait duration
approval expiry
rejection rate
```

---

# 286. Approval Content Privacy

Do not expose sensitive action content to broad dashboards.

---

# 287. Observability for User Input

Monitor jobs:

```text
WAITING_FOR_INPUT
```

and wait duration.

---

# 288. Stuck Job Detection

Potential stuck condition:

```text
state unchanged
no heartbeat
no queue activity
no valid wait reason
```

Exact threshold belongs to operations.

---

# 289. Orphan Task Detection

Detect tasks with:

```text
no active lease
not terminal
not queued
```

---

# 290. Orphan Artifact Detection

Detect artifact records with incomplete lineage.

---

# 291. Evidence Gap Detection

Detect completed jobs missing required evidence.

---

# 292. Budget Drift Detection

Detect usage ledger vs runtime budget inconsistencies.

---

# 293. Deployment Drift Detection

Observe version/config mismatch across replicas.

---

# 294. Config Drift Signal

Compare declared vs observed configuration version.

---

# 295. Secret Rotation Drift

Detect services still using revoked/old credential version where observable.

---

# 296. Certificate Expiry Monitoring

Monitor TLS/signing certificate expiry where applicable.

---

# 297. Queue Poisoning Signal

Monitor schema failures/invalid task messages.

---

# 298. Fencing Abuse Signal

Repeated stale-token commits may indicate bug/attack.

---

# 299. RAG Deleted-Source Signal

Any retrieval of logically deleted source is critical correctness/security issue.

---

# 300. RAG Provenance Gap Signal

Retrieved unit without source/version lineage should fail/alert.

---

# 301. Artifact Hash Mismatch Signal

Critical integrity signal.

---

# 302. Acceptance Manifest Gap

If final job lacks required acceptance record, alert or block according to state logic.

---

# 303. Observability Data Export

External export must preserve:

```text
redaction
tenant boundaries
retention
access
```

---

# 304. Third-Party Observability Vendor

If used, vendor must be reviewed for:

```text
data handling
region
retention
access
security
exit plan
```

---

# 305. Self-Hosted Observability

Self-hosting is an implementation choice.

It does not change observability authority.

---

# 306. Vendor Independence

Observability backend should be replaceable.

Application instrumentation should prefer open/stable standards where practical.

---

# 307. OpenTelemetry

OpenTelemetry-style concepts are suitable for vendor-neutral tracing/metrics/log export when implementation adopts them.

Specific library/version is not fixed by this document.

---

# 308. Instrumentation Abstraction

Do not spread vendor-specific SDK semantics through domain code unnecessarily.

---

# 309. Collector Layer

A collector/processor may handle:

```text
batch
redaction
sampling
routing
export
```

---

# 310. Multi-Backend Export

Possible:

```text
metrics backend
logs backend
traces backend
security SIEM
```

Each must obey data policy.

---

# 311. Security SIEM

Security telemetry may integrate with SIEM.

SIEM alerts do not replace canonical evidence.

---

# 312. Log Search

Operators should search by:

```text
request_id
job_id
task_id
route_id
deployment_id
```

---

# 313. Trace Search

Trace by:

```text
service
error
job_id
route_id
```

where supported.

---

# 314. Metric Drill-Down

Dashboard metric should link/drill to logs/traces when possible.

---

# 315. Evidence Drill-Down

Operational UI may link to EvidenceRecord using authorized access.

---

# 316. Tenant-Safe Support Tooling

Support tooling should default to metadata, not customer content.

---

# 317. Temporary Content Inspection

If content inspection is required for support:

```text
authorized
scoped
time-bounded
audited
```

---

# 318. Observability and GDPR/Privacy

Telemetry may itself contain personal data.

Apply data protection principles.

This document does not claim regulatory compliance by itself.

---

# 319. Right-to-Delete Interactions

Operational logs may have different retention/legal treatment than primary data.

Data governance decides exact deletion behavior.

---

# 320. Evidence Retention Exception

Evidence may have justified retention independent from ordinary telemetry.

---

# 321. Operational Analytics

Observability data may support capacity/performance analytics.

Avoid repurposing sensitive telemetry for unrelated product analytics without governance.

---

# 322. Product Analytics Boundary

Product analytics and operational observability may overlap but have different purposes.

Keep purpose explicit.

---

# 323. LLM Observability

LLM-specific observability may track:

```text
provider
model
latency
input/output units
tool-use count
validation
cost
```

---

# 324. No Chain-of-Thought Logging

Do not log hidden model chain-of-thought.

Store structured rationale/decision fields where required.

---

# 325. Prompt Injection Observability

Record:

```text
source category
detector/rule
policy result
blocked side effect
```

not malicious content verbatim by default.

---

# 326. Safety Evaluation Observability

Track:

```text
evaluation result
hard-fail dimension
```

without exposing sensitive artifact content.

---

# 327. Agent Handoff Observability

If agent-to-agent delegation exists:

```text
source agent
target agent
task ID
allowed scope
result
```

---

# 328. Capability Resolution Observability

Track:

```text
required capabilities
selected factory/capability
resolution failure
```

---

# 329. Planner Observability

Track:

```text
plan created
task count
DAG depth
validation failures
```

Do not log private reasoning.

---

# 330. DAG Explosion Alert

Alert on abnormal:

```text
task count
graph depth
```

near bounded limits.

---

# 331. Policy Observability

Track decisions:

```text
ALLOW
DENY
REQUIRE_APPROVAL
```

by bounded reason class.

---

# 332. Policy Latency

Monitor policy evaluation latency.

Policy failure should not fail open.

---

# 333. Routing Observability

Track both:

```text
decision
execution result
```

to compare expected vs actual provider usage.

---

# 334. Routing Integrity Check

Detect:

```text
provider call without route_id
provider mismatch with RoutingDecision
```

---

# 335. Tool Integrity Check

Detect:

```text
tool call without valid ToolRequest/ExecutionGrant correlation
```

---

# 336. Worker Integrity Check

Detect:

```text
result commit with stale lease/fencing token
```

---

# 337. Evidence Integrity Check

Detect:

```text
material action lacking evidence
```

---

# 338. Observability for Idempotency

Track:

```text
idempotency hit
duplicate request
conflict
```

---

# 339. Replay Detection

Monitor repeated webhook/idempotency/grant replay attempts.

---

# 340. Webhook Observability

Track:

```text
signature failure
replay rejection
delivery retries
handler latency
```

---

# 341. External Connector Observability

Track:

```text
connector auth health
request success
rate limit
permission failure
```

---

# 342. GitHub Connector Observability

Possible:

```text
API errors
rate limits
auth failure
repo mutation result
```

without leaking token/repo protected content broadly.

---

# 343. Cloud Connector Observability

Track:

```text
API failure
permission denial
region mismatch
resource mutation
```

---

# 344. Email Connector Observability

Track:

```text
send request
provider acceptance
failure
```

Do not log message body by default.

---

# 345. Calendar Connector Observability

Track:

```text
create/update/delete result
```

without exposing sensitive event content broadly.

---

# 346. Payment Connector Observability

Track:

```text
payment request ID
amount/currency metadata where authorized
result
reconciliation
```

No card/payment secret.

---

# 347. DNS Observability

Track:

```text
zone/record reference
mutation result
verification
```

---

# 348. Deployment Connector Observability

Track:

```text
target
artifact
deployment ID
result
health
```

---

# 349. Store Publishing Observability

Track:

```text
submission
external review state
publication
```

Current state must come from external platform evidence.

---

# 350. Media Observability

Track:

```text
render duration
codec failure
provider generation
asset retrieval
timeline/render success
```

---

# 351. Video Quality Observability

Track evaluation results:

```text
visual QA
audio QA
caption QA
```

---

# 352. Web Factory Observability

Track:

```text
build success
browser QA
a11y
performance
visual evaluation
deployment
```

---

# 353. Software Factory Observability

Track:

```text
repo analysis
patch
tests
build
security scan
CI
```

---

# 354. Security Factory Observability

Track:

```text
scan
finding
severity
remediation proposal
verification
```

Security Factory cannot self-authorize remediation.

---

# 355. Research/Data Observability

Track:

```text
source fetch
citation
claim verification
knowledge promotion
```

---

# 356. Creative/Document Observability

Track:

```text
artifact generation
format validation
review
```

---

# 357. Commerce/Growth Observability

Track:

```text
external communication
ad/spend tool use
approval
```

with strict privacy/FinOps controls.

---

# 358. Personal Operations Observability

Track:

```text
email/calendar/file actions
approval
result
```

---

# 359. Observability Maturity

Observability capability uses canonical maturity:

```text
DESIGNED
→ SPECIFIED
→ IMPLEMENTED
→ TESTED
→ VERIFIED
→ DEPLOYED / PRODUCTION
```

---

# 360. DESIGNED Gate

Requires:

```text
telemetry domains
ownership
privacy model
critical signals
```

---

# 361. SPECIFIED Gate

Requires:

```text
logs
metrics
traces
health
alerts
retention
redaction
```

contracts/standards.

---

# 362. IMPLEMENTED Gate

Requires actual instrumentation/pipeline.

---

# 363. TESTED Gate

Requires:

```text
instrumentation tests
redaction tests
correlation tests
alert tests
health tests
```

---

# 364. VERIFIED Gate

Requires:

```text
TESTED
+
representative end-to-end visibility
+
security/privacy verification
+
operational usefulness
```

---

# 365. DEPLOYED / PRODUCTION Gate

Requires:

```text
production telemetry
production alerting
health visibility
access controls
retention
runtime evidence
```

for claimed scope.

---

# 366. Control Plane Observability DoD

Requires:

```text
API/request metrics
state transition visibility
policy visibility
routing visibility
health
alerts
correlation
```

---

# 367. Worker Observability DoD

Requires:

```text
lease
heartbeat
task latency
resource utilization
failures
stale commit
```

---

# 368. Provider Observability DoD

Requires:

```text
provider/model
latency
success/failure
quota/rate limit
usage/cost
route correlation
```

---

# 369. Tool Gateway Observability DoD

Requires:

```text
tool class
allow/deny
latency
failure
grant correlation
security denials
```

---

# 370. RAG Observability DoD

Requires:

```text
ingestion
retrieval
auth denials
latency
provenance failures
DLP
quality evaluation
```

---

# 371. Evidence Observability DoD

Requires:

```text
write success
write failure
completeness failure
integrity failure
```

without duplicating evidence payload.

---

# 372. Deployment Observability DoD

Requires:

```text
deployment ID
release/version
result
health
rollback
```

---

# 373. FinOps Observability DoD

Requires:

```text
usage
cost
budget utilization
anomaly
retry/repair waste
```

---

# 374. Security Observability DoD

Requires:

```text
auth anomalies
tenant violations
grant/tool denials
secret events
critical alerts
```

---

# 375. Observability Production Gate

Before production claim:

```text
critical services instrumented
health checks active
critical alerts routed
redaction verified
tenant access controlled
correlation works
```

---

# 376. Observability Release Gate

A release changing telemetry contract must update:

```text
dashboards
alerts
tests
runbooks
```

---

# 377. Telemetry Backward Compatibility

During rolling release, telemetry schemas should remain usable across mixed versions.

---

# 378. Dashboard Versioning

Dashboards should be version-controlled where practical.

---

# 379. Alert Versioning

Alert rules should be version-controlled where practical.

---

# 380. Runbook Versioning

Runbook changes should be reviewed and traceable.

---

# 381. Observability IaC

Telemetry pipeline/dashboards/alerts may be managed as code.

IaC presence does not prove deployment.

---

# 382. Observability Cost

Observability has real cost:

```text
ingestion
storage
query
retention
cardinality
```

Optimize within required reliability/security.

---

# 383. Cost Guardrail

Do not reduce critical security visibility solely to lower telemetry bill.

---

# 384. Sampling Cost Optimization

Sample high-volume low-value telemetry first.

---

# 385. Aggregation Cost Optimization

Use recording/aggregate metrics for long-term trend.

---

# 386. Retention Tiers

Possible:

```text
hot
warm
archive
delete
```

according to policy.

---

# 387. Tenant-Specific Observability Cost

Per-tenant detailed telemetry may be premium/enterprise feature, but security boundary remains universal.

---

# 388. Observability Capacity Planning

Plan for:

```text
peak logs/sec
metric series
trace spans/sec
retention
query load
```

---

# 389. Telemetry Pipeline Health

Monitor the observability system itself:

```text
dropped logs
dropped spans
export failures
collector queue
backend ingestion failures
```

---

# 390. Meta-Monitoring

Observability needs observability.

Use independent health where possible.

---

# 391. Dead Man’s Switch

For critical scheduled signals, absence itself may alert.

---

# 392. Clock Skew

Distributed telemetry should tolerate clock skew.

Use authoritative timestamps plus sequence IDs where needed.

---

# 393. Time Synchronization

Production hosts/services should use reliable time synchronization.

---

# 394. Timezone

Store telemetry timestamps in UTC.

Display local timezone in UI when useful.

---

# 395. Log Ordering

Logs are not guaranteed globally ordered.

Use:

```text
timestamps
sequence
job/task state
```

for reconstruction.

---

# 396. Trace Ordering

Trace causality helps but does not replace durable workflow order.

---

# 397. Queue Ordering

Queue semantics should be understood and visible.

---

# 398. State Sequence Observability

Track state sequence/version in logs for debugging stale updates.

---

# 399. Lease/Fencing Sequence

Include fencing generation/token in protected diagnostic telemetry where safe.

---

# 400. Data Store Observability

Monitor:

```text
connections
latency
errors
capacity
replication
backup
```

---

# 401. Operational DB

Critical:

```text
query latency
connection saturation
transaction failures
replication/failover
```

---

# 402. Vector Store

Monitor:

```text
query latency
index size
index failures
update/delete lag
```

---

# 403. Graph Store

Monitor:

```text
query latency
write failures
consistency
```

---

# 404. Object Store

Monitor:

```text
upload/download errors
latency
storage growth
integrity mismatch
```

---

# 405. Evidence Store

Monitor:

```text
append latency
write failure
integrity check
capacity
```

---

# 406. Secret Store

Monitor:

```text
resolution latency
denial
rotation
backend health
```

Never log secret values.

---

# 407. Cache

Monitor:

```text
hit rate
miss rate
eviction
tenant-key anomalies
```

---

# 408. Cache Security Signal

Cross-tenant cache key collision is critical.

---

# 409. Backup Observability

Monitor:

```text
backup success
backup age
restore test result
```

---

# 410. DR Observability

Monitor:

```text
replication
failover readiness
restore drill
```

---

# 411. Production Health Rollup

Overall health must be derived transparently.

Do not hide critical dependency failure behind green aggregate.

---

# 412. Degraded Health

Use `DEGRADED` when service works with meaningful impairment.

---

# 413. Unknown Health

Use `UNKNOWN` when evidence is insufficient.

---

# 414. Health Aggregation

Example:

```text
critical dependency UNHEALTHY
→ service cannot be HEALTHY
```

Exact logic is service-specific.

---

# 415. Maintenance Mode

During maintenance:

```text
status may be MAINTENANCE
```

if product adopts it.

It must not mask security incident.

---

# 416. Observability Incident Levels

Possible:

```text
SEV0
SEV1
SEV2
SEV3
```

Exact incident taxonomy belongs in `FAILURE_RECOVERY.md`.

---

# 417. Observability to Incident Handoff

When alert triggers incident:

```text
alert ID
service
environment
time
correlation refs
initial impact
```

should transfer.

---

# 418. Post-Incident Telemetry Review

Ask:

```text
Did we detect fast enough?
Were signals actionable?
Was there noise?
Were critical fields missing?
Did telemetry leak sensitive data?
```

---

# 419. Regression Telemetry

Every fixed operational issue may add:

```text
metric
alert
test
```

if it improves future detection.

---

# 420. No Alert-as-Fix

Adding alert does not fix root cause.

---

# 421. No Dashboard-as-Control

Dashboard visibility does not enforce policy.

---

# 422. No Log-as-Audit Shortcut

If action requires canonical audit/evidence, emit EvidenceRecord.

---

# 423. No Metric-as-Billing Truth

FinOps ledger remains canonical for spend attribution.

---

# 424. No Trace-as-State Store

Durable state remains canonical state store.

---

# 425. No Status Page-as-Health Authority

Status page is a projection.

---

# 426. Observability Data Ownership

Each telemetry dataset needs:

```text
owner
classification
retention
access
```

---

# 427. Data Lineage for Telemetry

Know:

```text
source service
collector
processor
backend
```

---

# 428. Telemetry Processor Changes

Redaction/sampling processor changes are security/operations-sensitive.

---

# 429. Export Failure

Export failure should be observable locally/through alternate channel.

---

# 430. Buffer Overflow

Telemetry buffer overflow should not crash critical service.

Drop lowest-value telemetry first.

---

# 431. Critical Event Durability

Critical audit/evidence must not depend on best-effort log buffer.

---

# 432. Observability API

If ILAIOS exposes observability APIs, they must enforce:

```text
Principal
Tenant
Project
Role
```

---

# 433. Tenant Metrics API

Tenant metrics must not leak provider/account-level global data unless allowed.

---

# 434. Admin Metrics API

Admin visibility should still minimize content exposure.

---

# 435. Health API

Public health API should avoid sensitive dependency detail.

---

# 436. Internal Diagnostics API

Internal diagnostic endpoints need strong authorization.

---

# 437. Debug Endpoint Governance

Debug endpoints must be disabled/restricted in production.

---

# 438. Profiling

Performance profiling may be enabled in controlled environments.

Profiling data can contain sensitive information.

---

# 439. Memory Dump Risk

Heap/core dumps can expose secrets/data.

Protect or disable according to security policy.

---

# 440. Distributed Profiling

Use only when privacy/security controls allow.

---

# 441. Query Governance

Observability backend queries may be expensive.

Apply access/rate controls.

---

# 442. Dashboard Query Cost

Avoid queries that scan unbounded high-volume logs unnecessarily.

---

# 443. Saved Search Governance

Saved searches should use safe filters and access permissions.

---

# 444. Alert Query Performance

Alert queries must be efficient/reliable enough for intended cadence.

---

# 445. Multi-Region Observability

If multi-region:

```text
regional telemetry
global aggregation
residency
failover
```

must be defined.

---

# 446. Residency of Telemetry

Telemetry containing protected metadata may itself have residency requirements.

---

# 447. Cross-Region Export

Do not export restricted telemetry to disallowed region.

---

# 448. On-Prem Observability

Enterprise/on-prem deployment may use customer-controlled observability backend.

Canonical semantics remain.

---

# 449. Hybrid Observability

Hybrid deployment must preserve correlation across cloud/on-prem boundaries.

---

# 450. Air-Gapped Observability

Air-gapped environments may use local backend/export.

No dependency on public SaaS observability required architecturally.

---

# 451. Provider Independence

ILAIOS observability must not require one specific vendor.

---

# 452. Local-First Debugging

Developers should be able to diagnose basic issues locally without production telemetry access.

---

# 453. Least-Privilege Debugging

Access production telemetry only when necessary.

---

# 454. Sensitive Search Audit

Searching highly sensitive production telemetry may itself be auditable.

---

# 455. Support Session Correlation

Support tooling may create support_session_id to correlate authorized investigation.

---

# 456. Data Minimization During Support

Support should not copy full telemetry into tickets if references suffice.

---

# 457. External Ticketing

If exporting incidents to external ticketing:

```text
redact
minimize
link internally
```

---

# 458. ChatOps

Alerts may route to chat systems.

Do not include secrets/sensitive customer content.

---

# 459. Email Alerts

Same minimization rules.

---

# 460. Pager Alerts

Keep concise/actionable.

---

# 461. Observability Documentation

Each critical service should document:

```text
key metrics
health
alerts
dashboards
runbook
```

---

# 462. Instrumentation Review

Code review asks:

```text
Does new critical path have enough telemetry?
Are fields safe?
Is cardinality bounded?
Can failures be diagnosed?
```

---

# 463. Telemetry Change Review

A telemetry change that removes visibility from security-critical path requires review.

---

# 464. Alert Removal Review

Before removing alert:

```text
why obsolete?
replacement?
risk?
```

---

# 465. Dashboard Removal

Removing dashboard is lower risk unless it is operationally critical.

---

# 466. Health Check Change

Health semantics changes can affect routing/deployment.

Review carefully.

---

# 467. SLO Change Review

SLO target changes should not be used to hide regression.

---

# 468. Metric Definition Registry

Maintain catalog:

```text
name
type
unit
labels
owner
description
```

---

# 469. Alert Registry

Maintain:

```text
name
severity
condition
owner
runbook
```

---

# 470. Dashboard Registry

Maintain:

```text
dashboard
audience
owner
source
```

---

# 471. Observability Inventory

Inventory is mutable operational metadata.

Not canonical architecture truth.

---

# 472. Observability Evidence Package

For production observability verification:

```text
instrumentation revision
dashboards
alerts
redaction tests
health tests
sample traces/logs/metrics
access controls
```

---

# 473. Observability Definition of Done — Service

A service is observability-ready when:

```text
structured logs
core metrics
trace correlation
health
critical alerts
redaction
runbook
```

are in place for its risk.

---

# 474. Observability Definition of Done — Job Path

A canonical job path should allow:

```text
request
→ job
→ task
→ route
→ worker
→ provider/tool
→ artifact
→ evaluation
```

correlation.

---

# 475. Observability Definition of Done — Security

Requires:

```text
auth
authz
tenant
grant
approval
tool
secret
```

signals without data leakage.

---

# 476. Observability Definition of Done — RAG

Requires:

```text
ingestion
auth retrieval
latency
provenance failure
DLP
quality
```

signals.

---

# 477. Observability Definition of Done — Deployment

Requires:

```text
release attribution
deployment result
health
rollback
```

---

# 478. Observability Definition of Done — FinOps

Requires:

```text
cost
budget
provider
retry/repair
```

operational visibility.

---

# 479. Observability Verification Gate

Cannot claim `VERIFIED` if:

```text
critical path uncorrelated
secrets appear in telemetry
tenant data leaks through dashboard
alerts cannot be tested
health semantics undefined
```

---

# 480. Production Observability Gate

Cannot claim production observability for a scope unless:

```text
instrumentation deployed
pipeline works
critical alerts active
health observable
access controlled
runtime evidence exists
```

---

# 481. Observability Anti-Patterns

Reject:

```text
printf debugging as production strategy
logs as database
prompts as metric labels
one giant dashboard
alert on every error
no alert ownership
provider calls without route_id
tool calls without task/grant correlation
```

---

# 482. “Everything Is Green” Anti-Pattern

A single green dashboard cannot prove:

```text
security
tenant isolation
artifact correctness
evidence completeness
```

---

# 483. “No Alerts = Healthy” Anti-Pattern

No alerts may mean:

```text
healthy
or
monitoring broken
```

Use meta-monitoring.

---

# 484. “Logs Exist = Observable” Anti-Pattern

Observability requires:

```text
structured
correlated
actionable
```

signals.

---

# 485. “More Telemetry = Better” Anti-Pattern

Excess telemetry can increase:

```text
cost
privacy risk
noise
```

---

# 486. “Sample Everything” Anti-Pattern

Security/rare critical failures may need retention even when normal traces are sampled.

---

# 487. “Store Raw Payloads for Debugging” Anti-Pattern

Prefer:

```text
hash
reference
size
classification
```

---

# 488. “Per-Tenant Metric Labels Everywhere” Anti-Pattern

Can cause privacy/cardinality issues.

---

# 489. “Dashboard Decides Policy” Anti-Pattern

Dashboards display.

Policy decides.

---

# 490. Observability Red Lines

Never:

```text
log secrets
use telemetry as execution authority
expose cross-tenant telemetry
hide failed health checks
silence critical security alerts indefinitely
claim LIVE_HEALTHY from stale data
store chain-of-thought
```

---

# 491. Current Health Reporting Rule

Every current health claim must include:

```text
scope
environment
observed_at
source
```

---

# 492. Current Deployment Health Rule

Deployment health must identify:

```text
release/artifact
target
observation time
checks
```

---

# 493. Current Provider Health Rule

Provider health is mutable.

Do not encode as canonical constant.

---

# 494. Current Cost Health Rule

Spend/budget alerts use current ledger/pricing data.

---

# 495. Current RAG Health Rule

RAG health may include:

```text
ingestion
retrieval
index
authorization
provider
```

No single query proves full health.

---

# 496. Current Queue Health Rule

Queue depth alone does not prove unhealthy.

Interpret against workload/SLO.

---

# 497. Current Worker Health Rule

Worker count alone does not prove execution capacity.

Consider:

```text
leases
capabilities
resource availability
```

---

# 498. Current DB Health Rule

Connection succeeds does not prove all queries/integrity healthy.

---

# 499. Current Evidence Health Rule

Evidence store health includes write/read/integrity as required.

---

# 500. Observability Review Checklist

```text
[ ] Critical path instrumented
[ ] IDs correlated
[ ] No raw secret
[ ] PII minimized
[ ] Metrics bounded cardinality
[ ] Errors classified
[ ] Health checks defined
[ ] Alerts actionable
[ ] Dashboard access scoped
[ ] Evidence not replaced by logs
```

---

# 501. New Service Checklist

```text
[ ] service identity
[ ] structured logs
[ ] base metrics
[ ] trace propagation
[ ] liveness
[ ] readiness
[ ] dependency health
[ ] alert ownership
[ ] runbook
```

---

# 502. New Provider Checklist

```text
[ ] provider metrics
[ ] latency
[ ] failures
[ ] quota
[ ] usage/cost
[ ] route correlation
[ ] fallback
```

---

# 503. New Tool Checklist

```text
[ ] allow/deny metrics
[ ] latency
[ ] failure class
[ ] task/grant correlation
[ ] security denial telemetry
```

---

# 504. New RAG Component Checklist

```text
[ ] tenant/project correlation
[ ] source/version
[ ] auth denial
[ ] retrieval latency
[ ] provenance failure
[ ] DLP
[ ] quality metrics
```

---

# 505. New Deployment Checklist

```text
[ ] release version
[ ] deployment ID
[ ] environment
[ ] result
[ ] health
[ ] rollback
```

---

# 506. New Alert Checklist

```text
[ ] actionable
[ ] owner
[ ] severity
[ ] threshold/rationale
[ ] dedupe
[ ] runbook
[ ] tested
```

---

# 507. New Metric Checklist

```text
[ ] name
[ ] type
[ ] unit
[ ] bounded labels
[ ] owner
[ ] purpose
```

---

# 508. New Log Event Checklist

```text
[ ] event name
[ ] severity
[ ] safe fields
[ ] correlation
[ ] no content leak
```

---

# 509. New Trace Span Checklist

```text
[ ] meaningful boundary
[ ] safe attributes
[ ] parent propagation
[ ] no huge payload
```

---

# 510. Incident Feedback Checklist

```text
[ ] Was incident detected?
[ ] Was alert actionable?
[ ] Could root cause be correlated?
[ ] Were critical fields missing?
[ ] Was there telemetry noise?
[ ] Did telemetry leak data?
```

---

# 511. Observability Milestone Gate

A milestone adding new critical runtime path must include observability requirements before `VERIFIED`.

---

# 512. RAG Milestone Alignment

RAG observability should be established no later than the RAG operational hardening phase.

---

# 513. Release Alignment

Release/deployment changes should include observability validation before broad production promotion.

---

# 514. Failure Recovery Alignment

`FAILURE_RECOVERY.md` should reference canonical signals from this document.

---

# 515. Governance Alignment

Changes to critical alerts/health semantics are governed operational changes.

---

# 516. Engineering Alignment

`ENGINEERING_STANDARDS.md` instrumentation rules remain authoritative for code quality.

---

# 517. Testing Alignment

`TESTING_AND_EVALUATION.md` defines how observability/redaction/health/alert behavior is tested.

---

# 518. FinOps Alignment

`FINOPS.md` owns cost truth.

Observability owns operational visibility of cost behavior.

---

# 519. Security Alignment

`SECURITY_ARCHITECTURE.md` owns access/redaction/security control placement.

Observability implements visibility around those controls.

---

# 520. Data Alignment

`DATA_ARCHITECTURE.md` owns telemetry data classification/storage semantics where formalized.

---

# 521. API Alignment

`API_CONTRACTS.md` owns public/internal telemetry API contracts if exposed.

---

# 522. Deployment Alignment

`DEPLOYMENT_ARCHITECTURE.md` owns where observability components are deployed.

---

# 523. Canonical Observability Flow

```text
REQUEST / JOB / TASK
        │
        ▼
STRUCTURED INSTRUMENTATION
        │
        ├─ LOG
        ├─ METRIC
        └─ TRACE
        │
        ▼
REDACTION / SAMPLING / ENRICHMENT
        │
        ▼
OBSERVABILITY BACKEND
        │
        ├─ DASHBOARD
        ├─ SEARCH
        ├─ SLO
        └─ ALERT
        │
        ▼
OPERATOR / INCIDENT RESPONSE
```

Separate and parallel:

```text
MATERIAL ACTION
        │
        ▼
EVIDENCE RECORD
        │
        ▼
EVIDENCE STORE
```

---

# 524. Observability Causality Formula

```text
REQUEST_ID
+
JOB_ID
+
TASK_ID
+
ROUTE_ID
+
WORKER / TOOL / PROVIDER IDs
+
ARTIFACT / EVALUATION IDs
=
TRACEABLE OPERATIONAL CAUSALITY
```

---

# 525. Observability Safety Formula

```text
STRUCTURED TELEMETRY
+
REDACTION
+
TENANT-SAFE ACCESS
+
BOUNDED CARDINALITY
+
SAMPLING
+
OWNERED ALERTS
+
HEALTH SEMANTICS
=
SAFE OPERABILITY
```

---

# 526. Evidence Separation Formula

```text
LOGS
+
METRICS
+
TRACES
=
OBSERVABILITY

OBSERVABILITY
≠
EVIDENCE AUTHORITY

EVIDENCE RECORDS
+
AUTHORITATIVE STATE
=
PROVABLE EXECUTION TRUTH
```

---

# 527. Final Observability Invariant

The defining ILAIOS observability rule is:

> **ILAIOS must be understandable in production without making telemetry a new source of authority or a new source of sensitive-data leakage.**

Therefore:

```text
Logs
≠
State

Metrics
≠
Evidence

Traces
≠
Authorization

Dashboard
≠
Policy

No Alert
≠
Healthy

Historical Health
≠
Current Health
```

The operational objective is:

```text
SEE THE PATH
UNDERSTAND THE FAILURE
MEASURE THE OUTCOME
PROTECT THE DATA
CORRELATE THE ACTION
VERIFY THE HEALTH
WITHOUT DUPLICATING AUTHORITY
```

**Observability exists to make ILAIOS operable, diagnosable, and accountable while preserving the platform’s one canonical authority chain.**
