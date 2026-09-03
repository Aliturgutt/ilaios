# ILAIOS — FAILURE RECOVERY

**Document Type:** Canonical Failure Recovery & Resilience Standard  
**Format:** GitHub Markdown + ASCII recovery diagrams  
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
**Observability Companion:** `OBSERVABILITY.md`  
**Core Recovery Principle:** **FAIL SAFELY, RECOVER BOUNDEDLY, RESUME FROM VERIFIED STATE, AND NEVER TURN UNCERTAINTY INTO FALSE SUCCESS**

> This document defines the canonical ILAIOS failure and recovery model: failure taxonomy, retry and repair semantics, checkpointing, durable resume, cancellation, stale-worker fencing, compensation, degraded modes, rollback, disaster recovery, provider/tool failure handling, evidence continuity, incident linkage, and recovery Definition of Done. It defines target resilience behavior and must not be used to claim that any current environment is healthy, recovered, or production-ready without direct current evidence.

---

# 00. Purpose

ILAIOS executes long-running autonomous work across:

```text
Control Plane
Policy
Routing
Queues
Workers
Providers
Tools
Knowledge
Artifacts
Evidence
Deployment
External systems
```

Failure is therefore expected.

The architecture must assume:

```text
provider fails
worker crashes
queue redelivers
network partitions
tool times out
approval expires
budget is exhausted
artifact validation fails
deployment fails
storage is unavailable
process restarts
external service lies
user cancels
```

The objective is not:

```text
NEVER FAIL
```

The objective is:

```text
FAIL SAFELY
    │
    ▼
PRESERVE AUTHORITY
    │
    ▼
PRESERVE STATE / EVIDENCE
    │
    ▼
RECOVER WITHIN BOUNDS
    │
    ▼
VERIFY BEFORE CONTINUING
```

---

# 01. Scope

This document owns:

- canonical failure taxonomy;
- retryability classification;
- retry policy;
- repair policy;
- bounded attempt/time/cost semantics;
- checkpoint semantics;
- resume semantics;
- durable recovery;
- cancellation;
- compensation;
- rollback;
- degraded mode;
- read-only mode;
- failover behavior;
- queue/worker failure recovery;
- provider/tool failure recovery;
- RAG/Knowledge failure recovery;
- artifact/evidence failure handling;
- secret/key failure handling;
- deployment recovery;
- disaster recovery;
- incident linkage;
- recovery evidence;
- recovery testing;
- recovery Definition of Done.

This document does **not** own:

```text
threat taxonomy
    → THREAT_MODEL.md

security control placement
    → SECURITY_ARCHITECTURE.md

runtime state schemas
    → API_CONTRACTS.md / DATA_ARCHITECTURE.md

deployment topology
    → DEPLOYMENT_ARCHITECTURE.md

observability signals
    → OBSERVABILITY.md

test strategy
    → TESTING_AND_EVALUATION.md

budget authority
    → FINOPS.md
```

---

# 02. Target Recovery vs Current Reality

This document defines target recovery architecture.

Current recovery capability must be proven from:

```text
current code
current tests
current CI
current recovery drills
current runtime evidence
current deployment evidence
```

Therefore:

```text
checkpoint code exists
≠
resume verified

retry loop exists
≠
safe recovery

rollback script exists
≠
rollback tested

backup exists
≠
restore verified

DR document exists
≠
DR operationally ready
```

---

# 03. Recovery Constitutional Invariants

Mandatory:

```text
NO infinite retry
NO infinite repair
NO silent fail-open
NO success without verification
NO stale-worker commit
NO reuse of expired/revoked authority
NO hidden budget reset
NO evidence loss during recovery
NO recovery by bypassing Policy
NO recovery by bypassing Routing
NO recovery by exposing secrets
NO rollback that revives revoked credentials
NO cancellation that permits late authoritative commit
```

---

# 04. Canonical Recovery Flow

```text
FAILURE
   │
   ▼
CLASSIFY
   │
   ├─ retryable?
   ├─ repairable?
   ├─ compensatable?
   ├─ user input required?
   └─ fatal?
   │
   ▼
CHECK POLICY / BUDGET / ATTEMPTS / TIME
   │
   ├─ permitted
   │     ▼
   │   RETRY / REPAIR / RESUME
   │     ▼
   │   VALIDATE
   │     ▼
   │   EVIDENCE
   │
   └─ not permitted
         ▼
      FAIL / NEEDS_USER_INPUT / WAITING_FOR_APPROVAL
```

---

# 05. Failure Classification

Canonical classes include:

```text
VALIDATION_FAILURE
TRANSIENT_RUNTIME_FAILURE
PROVIDER_FAILURE
PROVIDER_QUOTA_FAILURE
PROVIDER_POLICY_FAILURE
TOOL_FAILURE
TOOL_PERMISSION_FAILURE
QUEUE_FAILURE
WORKER_FAILURE
LEASE_FAILURE
STATE_CONFLICT
CHECKPOINT_FAILURE
BUDGET_EXHAUSTED
TIMEOUT
DEPENDENCY_FAILURE
POLICY_DENIAL
SECURITY_FAILURE
PRIVACY_VIOLATION
TENANT_SCOPE_VIOLATION
APPROVAL_REJECTION
APPROVAL_EXPIRY
ARTIFACT_INTEGRITY_FAILURE
EVIDENCE_FAILURE
DEPLOYMENT_FAILURE
CANCELLED
NEEDS_USER_INPUT
EXTERNAL_OWNER_BLOCKER
```

---

# 06. Retryability

Each failure class must explicitly define:

```text
retryable = true|false|conditional
```

Example:

```text
provider timeout
    = often retryable

invalid tenant authorization
    = not retryable

expired approval
    = not retryable without new approval
```

---

# 07. Repairability

Repair means changing output/work plan, not simply repeating the same operation.

Examples:

```text
artifact validation failure
→ repair content

test failure
→ modify code

RAG citation mismatch
→ reretrieve/rebuild answer
```

---

# 08. Retry vs Repair

```text
RETRY
    = repeat operation because failure may be transient

REPAIR
    = change execution/output because prior result is unacceptable
```

They have separate counters but share governing budget envelope.

---

# 09. Compensation

Compensation reverses or mitigates a completed side effect.

Examples:

```text
delete temporary resource
revert configuration
send correction
rollback deployment
```

Compensation is not always possible.

---

# 10. Fatal Failure

Fatal for current scope means:

```text
cannot safely continue
```

Examples:

```text
tenant isolation violation
evidence integrity failure
unrecoverable schema corruption
required secret unavailable with no approved alternative
```

Fatal does not mean system-wide permanent failure.

---

# 11. Canonical Runtime Recovery States

Job state vocabulary remains aligned with canonical runtime states:

```text
CREATED
CONTEXT_RESOLVING
PLANNING
PLAN_READY
VALIDATING
ADMITTED
QUEUED
RUNNING
WAITING_FOR_APPROVAL
WAITING_FOR_INPUT
VALIDATING_OUTPUT
REPAIRING
FINAL_EVALUATION
DELIVERY_PENDING
SUCCEEDED

FAILED
CANCEL_REQUESTED
CANCELLED
NEEDS_USER_INPUT
```

Recovery logic must not invent conflicting top-level JobStatus values.

---

# 12. Internal Task Recovery States

Internal task-level transient states may include:

```text
RETRY_PENDING
RETRYING
CHECKPOINTED
RESUMING
COMPENSATING
```

These are task/runtime internals and must not be confused with canonical JobStatus unless explicitly projected.

---

# 13. State Transition Safety

Every recovery transition must be validated.

Forbidden:

```text
FAILED → SUCCEEDED
```

without governed re-execution and validation.

---

# 14. Failure Record

Conceptual:

```yaml
failure_id: "failure_..."
tenant_id: "tenant_..."
project_id: "project_..."
job_id: "job_..."
task_id: "task_..."
failure_class: "PROVIDER_FAILURE"
retryable: true
repairable: false
attempt: 1
message_ref: "..."
observed_at: "..."
evidence_id: "..."
```

---

# 15. Retry Policy

Every retry policy must define:

```text
max_attempts
max_elapsed_time
max_cost
retryable classes
backoff
jitter where applicable
idempotency requirements
```

---

# 16. Bounded Retry Formula

```text
RETRY_ALLOWED
if and only if

failure.retryable
AND attempts_remaining > 0
AND elapsed_time_remaining > 0
AND cost_remaining > 0
AND Policy permits
AND authority/grant remains valid
```

---

# 17. Attempt Counting

Attempt counter must be monotonic for the scoped operation.

Do not reset attempts by:

```text
worker restart
provider fallback
process restart
checkpoint resume
```

unless a new governed task version is created.

---

# 18. Retry Budget

Retry spend belongs to same governing budget lineage.

```text
initial attempt
+
retry 1
+
retry 2
≤
authorized job/task budget
```

---

# 19. Retry Backoff

Use bounded backoff.

Possible:

```text
fixed
linear
exponential
```

with jitter where useful.

---

# 20. Retry Storm Prevention

Protect against:

```text
provider outage
queue redelivery storm
network partition
```

using:

```text
circuit breaker
global/provider concurrency
retry budget
backoff
```

---

# 21. Retry and Idempotency

Before retrying side effects:

```text
check idempotency support
check prior result
check external operation state
```

---

# 22. Unsafe Retry

Do not blindly retry:

```text
payment
DNS update
deployment
email send
destructive DB mutation
```

without idempotency/reconciliation.

---

# 23. Unknown Outcome

A timeout after side-effect submission may mean:

```text
operation succeeded externally
but response was lost
```

Required:

```text
reconcile external state
before retry
```

---

# 24. Repair Policy

Repair must define:

```text
what may change
what must remain fixed
acceptance criteria
max attempts
max cost
max elapsed time
```

---

# 25. Bounded Repair Formula

```text
REPAIR_ALLOWED
if and only if

repairable
AND attempts_remaining > 0
AND cost_remaining > 0
AND elapsed_time_remaining > 0
AND no constitutional/security violation
```

---

# 26. Repair Proposal

Conceptual:

```yaml
repair_proposal_id: "repair_..."
failure_ref: "failure_..."
artifact_version_ref: "..."
proposed_changes: []
expected_cost: {}
attempt_number: 1
policy_ref: "..."
```

---

# 27. Repair Scope

Repair should be targeted.

Prefer:

```text
fix one failing scene
```

over:

```text
regenerate entire video
```

when architecture permits.

---

# 28. Repair Cannot Rewrite Acceptance

Forbidden:

```text
artifact fails criterion
→ change criterion to PASS
```

unless user/governance legitimately changes acceptance criteria.

---

# 29. Repair and Artifact Versioning

Every repaired output is a new artifact version.

Old failed artifact remains historical evidence.

---

# 30. Repair and Evaluation

Repaired artifact must rerun affected validations/evaluation.

---

# 31. Repair Exhaustion

When repair bounds exhausted:

```text
FAILED
or
NEEDS_USER_INPUT
```

according to failure semantics.

---

# 32. Checkpoint Purpose

Checkpoint enables safe resume after interruption.

Checkpoint must preserve enough authoritative execution context to avoid restarting blindly.

---

# 33. Checkpoint Contents

A canonical checkpoint may include:

```text
checkpoint_id
job_id
task_id
state/version
completed nodes
pending nodes
artifact refs
evidence cursor
budget remaining
attempt counters
route refs
context refs
approval refs where valid
lease generation
created_at
integrity hash
```

---

# 34. Checkpoint Integrity

Checkpoint must be integrity-verifiable.

Tampered checkpoint must not resume.

---

# 35. Checkpoint Scope

Checkpoint contains references, not raw broad secrets.

---

# 36. Checkpoint Frequency

Frequency depends on:

```text
task duration
cost
side effects
recompute expense
risk
```

Do not checkpoint every trivial operation if unnecessary.

---

# 37. Checkpoint Before Privileged Side Effect

For long-running jobs, consider checkpointing before high-impact irreversible operations.

---

# 38. Checkpoint After Side Effect

Record verified external result/evidence before progressing.

---

# 39. Resume Principle

Resume from:

```text
last verified durable checkpoint
```

not:

```text
last in-memory assumption
```

---

# 40. Resume Revalidation

On resume, revalidate:

```text
Principal/Tenant membership where required
Policy
ExecutionGrant
approval validity
budget
provider eligibility
tool availability
lease/fencing
```

---

# 41. Expired Grant on Resume

```text
checkpoint valid
but grant expired
```

Result:

```text
re-admit / obtain new valid grant
```

not reuse stale authority.

---

# 42. Revoked Permission on Resume

If user/tenant authorization was revoked:

```text
stop
deny
record evidence
```

---

# 43. Policy Change on Resume

Material policy changes may invalidate prior route/approval.

Re-evaluate.

---

# 44. Budget Change on Resume

Resume cannot restore old higher budget if current authoritative budget is lower.

---

# 45. Stale Context on Resume

Task-scoped context may need refresh if:

```text
source changed
authorization changed
retention/deletion changed
```

---

# 46. Resume From Crash

Canonical:

```text
process crash
    │
    ▼
restart service
    │
    ▼
load durable state
    │
    ▼
invalidate stale lease
    │
    ▼
revalidate policy/grant
    │
    ▼
resume pending work
```

---

# 47. Worker Failure

Worker failure must not lose canonical job state.

---

# 48. Worker Lease

Every worker task uses:

```text
lease
expiry
heartbeat
fencing token
```

---

# 49. Lease Expiry

If lease expires:

```text
worker loses authoritative commit right
```

---

# 50. Fencing

New worker gets newer token.

```text
token N+1
```

Old worker with:

```text
token N
```

cannot commit.

---

# 51. Stale Worker Commit

Must be rejected even if output appears correct.

Correctness without current authority is insufficient.

---

# 52. Worker Heartbeat

Heartbeat failure may trigger:

```text
lease expiry
rescheduling
```

not immediate duplicate authoritative commit.

---

# 53. Duplicate Delivery

Queue may redeliver.

System must tolerate at-least-once delivery.

---

# 54. Duplicate Task Protection

Use:

```text
idempotency key
task state
lease
fencing
external deduplication
```

---

# 55. Queue Failure

If queue unavailable:

```text
stop new dispatch
preserve state
do not create ad hoc direct execution bypass
```

---

# 56. Queue Recovery

After queue restore:

```text
reconcile pending tasks
deduplicate
re-establish leases
resume safely
```

---

# 57. Dead-Letter Queue

DLQ may hold unrecoverable messages.

DLQ is not canonical failure resolution.

Every DLQ item needs:

```text
classification
owner
replay policy
data retention
```

---

# 58. Poison Message

Invalid task repeatedly failing schema/processing should not loop forever.

Move to:

```text
FAILED / DLQ
```

with evidence.

---

# 59. Control Plane Failure

Control Plane instances may restart.

Durable state must survive.

---

# 60. Control Plane Recovery

On startup:

```text
load config
validate policy
connect durable stores
reconcile in-flight jobs
invalidate stale leases as needed
resume
```

---

# 61. Control Plane Fail-Closed

If authoritative state/policy cannot be loaded:

```text
not ready
```

rather than permissive execution.

---

# 62. Operational DB Failure

If canonical DB unavailable:

```text
privileged execution should pause/fail safely
```

Do not invent missing state.

---

# 63. DB Recovery

After DB recovery:

```text
reconcile transactions
state sequence
leases
pending tasks
evidence references
```

---

# 64. Transaction Failure

Partial transaction must be rolled back or reconciled.

Never leave:

```text
state = SUCCEEDED
artifact missing
```

---

# 65. State Conflict

Optimistic concurrency conflict should:

```text
reload
re-evaluate
retry only if still valid
```

---

# 66. Cache Failure

Cache loss should degrade performance, not destroy canonical truth.

---

# 67. Cache Recovery

Rebuild from authoritative data.

---

# 68. Secret Store Failure

If required secret unavailable:

```text
bounded failure
```

not embedded fallback credential.

---

# 69. Secret Rotation Failure

If new credential fails:

```text
keep old credential only if still valid and policy allows
```

Never resurrect revoked secret.

---

# 70. Revoked Secret Recovery

A backup/rollback must not reactivate revoked secret.

---

# 71. Key Service Failure

If cryptographic operation required but key service unavailable:

```text
fail safe
```

---

# 72. Evidence Store Failure

If evidence required for material completion cannot be written:

```text
do not mark fully verified success
```

---

# 73. Evidence Recovery

After store restoration:

```text
reconcile missing pending evidence
verify no action occurred without required record
```

---

# 74. Evidence Gap

If action occurred but evidence could not be persisted:

```text
classify incident
reconstruct only from trustworthy sources where possible
mark uncertainty explicitly
```

Never fabricate evidence.

---

# 75. Artifact Store Failure

If artifact cannot be durably stored:

```text
final acceptance cannot complete
```

---

# 76. Artifact Integrity Failure

Hash mismatch:

```text
reject
quarantine
recreate/recover from trusted version
```

---

# 77. Artifact Recovery

Recover only if:

```text
exact version
hash
lineage
```

can be verified.

---

# 78. Provider Failure

Provider failure classes:

```text
timeout
rate limit
quota exhausted
service unavailable
invalid response
policy ineligible
credential failure
quality failure
```

---

# 79. Provider Timeout

May retry/fallback if:

```text
idempotent
budget remains
policy allows
```

---

# 80. Provider Rate Limit

Prefer:

```text
backoff
queue
alternative eligible provider
```

---

# 81. Provider Quota Exhaustion

Fallback only if:

```text
alternate provider eligible
budget permits
quality floor satisfied
```

---

# 82. Provider Invalid Response

Treat provider output as untrusted.

Schema/validation failure may:

```text
retry
fallback
repair
```

depending on class.

---

# 83. Provider Credential Failure

Do not retry endlessly.

Escalate configuration/secret issue.

---

# 84. Provider Policy Ineligibility

Not a failure to be retried.

It is:

```text
DENY / choose another eligible provider
```

---

# 85. Provider Quality Failure

If output fails acceptance:

```text
repair
or
re-route
```

within bounds.

---

# 86. Provider Fallback

Every fallback creates/references a governed RoutingDecision.

---

# 87. Tool Failure

Tool failure classes:

```text
permission denied
network timeout
external service failure
invalid result
conflict
rate limit
unknown outcome
```

---

# 88. Tool Permission Failure

Not retryable unless authority changes.

---

# 89. Tool Network Failure

May retry if side effect is idempotent or reconciled.

---

# 90. Tool Unknown Outcome

Must reconcile external state before retry.

---

# 91. Repository Mutation Failure

Possible:

```text
branch conflict
push rejected
CI failure
permission denied
```

Recovery:

```text
rebase/reconcile
minimal fix
rerun tests
```

Never force-bypass governance.

---

# 92. Deployment Failure

Deployment failure is not artifact failure.

A verified artifact may remain valid even if deployment fails.

---

# 93. Deployment Failure Classes

```text
config
credential
network
artifact mismatch
migration
health check
external platform
approval
```

---

# 94. Deployment Recovery

Canonical:

```text
deployment fails
    │
    ▼
classify
    │
    ├─ retry safe?
    ├─ rollback?
    ├─ fix-forward?
    └─ external blocker?
```

---

# 95. Rollback

Rollback returns service/environment to a previously known-good state.

Rollback requires:

```text
known artifact
known config
migration compatibility
secret state
verification
evidence
```

---

# 96. Rollback Is Not Undo Everything

Some changes are irreversible.

Examples:

```text
sent email
external payment
public release downloaded
schema data transformation
```

Use compensation/forward-fix where rollback impossible.

---

# 97. Rollback Trigger

Examples:

```text
health failure
security regression
migration failure
critical functional regression
```

---

# 98. Rollback Verification

After rollback:

```text
health
tenant isolation
policy
secrets
state
```

must be verified.

---

# 99. Rollback Security Invariant

Rollback must not restore:

```text
revoked key
revoked token
known-vulnerable config
expired approval
```

---

# 100. Fix-Forward

Use when rollback would be unsafe or impossible.

Requires:

```text
bounded patch
risk analysis
tests
deployment evidence
```

---

# 101. Database Migration Failure

Migration may fail:

```text
before changes
midway
after schema expansion
during backfill
```

Recovery plan must match phase.

---

# 102. Expand/Migrate/Contract Recovery

Preferred migration:

```text
EXPAND
MIGRATE
CONTRACT
```

allows safer rollback during compatibility window.

---

# 103. Partial Migration

If partial:

```text
stop new incompatible writes
assess source/target state
resume or roll forward
```

Do not guess.

---

# 104. Data Corruption

Suspected corruption:

```text
contain
stop writes if necessary
preserve evidence
restore/reconstruct from trusted source
verify integrity
```

---

# 105. Backup Recovery

Backup recovery must prove:

```text
restore succeeds
tenant IDs preserved
artifact/evidence lineage preserved
revoked credentials remain revoked
```

---

# 106. Backup Is Not Recovery

Backup existence alone is insufficient.

Restore must be tested.

---

# 107. RPO

Recovery Point Objective defines acceptable data-loss window.

Numeric targets belong to operational policy.

---

# 108. RTO

Recovery Time Objective defines acceptable recovery duration.

Numeric targets belong to operational policy.

---

# 109. Disaster Recovery

DR handles environment/site-scale failure.

---

# 110. DR Invocation

DR may be triggered by:

```text
region failure
major platform outage
data-plane failure
security containment
```

according to governance.

---

# 111. DR Canonical Flow

```text
PRIMARY FAILURE
      │
      ▼
CONFIRM / CLASSIFY
      │
      ▼
FREEZE DANGEROUS WRITES
      │
      ▼
ACTIVATE / RESTORE DR DATA
      │
      ▼
START CONTROL PLANE
      │
      ▼
RECONCILE STATE
      │
      ▼
INVALIDATE STALE LEASES / GRANTS
      │
      ▼
VERIFY TENANT ISOLATION / POLICY
      │
      ▼
RESUME BOUNDED WORKLOAD
```

---

# 112. DR Security

DR must not use:

```text
no-auth mode
global admin fallback
disabled tenant checks
disabled evidence
```

---

# 113. DR Data Residency

DR region/provider must still satisfy residency policy.

---

# 114. DR Credentials

Use DR-scoped credentials.

Do not keep broad emergency secret in documentation.

---

# 115. DR Fencing

Failover must advance fencing generation so old environment cannot later commit stale work.

---

# 116. Split-Brain Prevention

Multi-region/DR must prevent two authoritative writers unless architecture explicitly supports conflict-safe model.

---

# 117. Failback

Returning to primary environment requires:

```text
data sync
state reconciliation
lease invalidation
health verification
```

---

# 118. Degraded Mode

Degraded mode preserves safe partial functionality.

Examples:

```text
read-only
provider-limited
RAG-disabled
delivery-disabled
```

---

# 119. Degraded Mode Red Line

Degraded mode must not weaken:

```text
authentication
tenant isolation
Policy
evidence
secret scope
```

---

# 120. Read-Only Mode

Useful when writes/side effects unsafe.

May allow:

```text
view job state
retrieve existing artifacts
inspect status
```

while blocking mutations.

---

# 121. Provider-Degraded Mode

If premium provider unavailable:

```text
eligible fallback
or
queue/fail
```

not privacy downgrade.

---

# 122. RAG-Degraded Mode

If Knowledge unavailable:

```text
fail task
ask user
use explicitly allowed non-RAG path
```

Never query unauthorized alternative source.

---

# 123. Tool-Degraded Mode

If tool unavailable:

```text
skip optional task
queue
fail
ask user
```

depending on acceptance criteria.

---

# 124. Evidence-Degraded Mode

If required evidence unavailable:

```text
do not claim VERIFIED
```

---

# 125. Artifact-Degraded Mode

If artifact storage unavailable:

```text
do not claim final delivery
```

---

# 126. Queue-Degraded Mode

If queue unavailable:

```text
stop scheduling
```

not direct worker bypass.

---

# 127. User Input Recovery

Some failures require clarification.

Use:

```text
NEEDS_USER_INPUT
or
WAITING_FOR_INPUT
```

depending on canonical state semantics.

---

# 128. User Input Criteria

Ask user only when required information cannot be safely inferred.

---

# 129. Owner Gate Recovery

External owner action may resolve:

```text
store account
branch protection
license decision
payment account
DNS ownership
```

Milestone/runtime remains blocked until evidence.

---

# 130. Approval Recovery

If approval expires:

```text
request new approval
```

Do not extend automatically.

---

# 131. Approval Rejection

Rejection is not a transient failure.

System should:

```text
stop action
record decision
continue alternate safe path only if allowed
```

---

# 132. Approval Scope Change

If action changes materially:

```text
old approval invalid
```

---

# 133. Cancellation

Canonical flow:

```text
RUNNING
    │
    ▼
CANCEL_REQUESTED
    │
    ▼
stop scheduling new work
    │
    ▼
signal active tasks
    │
    ▼
safe point / compensation
    │
    ▼
CANCELLED
```

---

# 134. Cancellation Authorization

Only authorized principal/system policy may cancel.

---

# 135. Cancellation Idempotency

Repeated cancel request should be safe.

---

# 136. Cancellation and External Side Effects

Already-completed side effects may remain.

Cancellation does not magically undo them.

---

# 137. Late Result After Cancel

Reject authoritative commit from task completing after cancellation if no longer valid.

---

# 138. Compensation

Use for reversible/mitigatable external effects.

---

# 139. Compensation Proposal

Conceptual:

```yaml
compensation_id: "comp_..."
original_action_ref: "..."
reason: "..."
proposed_action: "..."
approval_required: true
status: "PROPOSED"
```

---

# 140. Compensation Authorization

Compensation may itself be privileged.

It requires policy/approval.

---

# 141. Compensation Failure

If compensation fails:

```text
record partial state
escalate
do not mark original action fully reversed
```

---

# 142. Saga-Like Workflows

Long multi-step side effects may use compensating-action patterns.

No assumption every action has inverse.

---

# 143. External Email Compensation

Cannot unsend reliably.

Possible compensation:

```text
send correction
notify user
```

---

# 144. Payment Compensation

May use:

```text
refund
void
```

if provider supports and authority exists.

---

# 145. DNS Compensation

Can restore previous record value if known/authorized.

---

# 146. Deployment Compensation

Rollback to prior release.

---

# 147. Repository Compensation

Use:

```text
revert commit
follow-up fix
```

not history rewriting by default.

---

# 148. Artifact Compensation

Mark version superseded/invalid.

Do not rewrite immutable history.

---

# 149. Evidence Continuity

Recovery path must preserve:

```text
failure
retry
repair
resume
compensation
rollback
final outcome
```

as evidence.

---

# 150. Recovery Evidence

Every material recovery event should answer:

```text
what failed
when
which job/task
classification
attempt
decision
authority
action
result
cost
```

---

# 151. Recovery Evidence Record

Conceptual:

```yaml
recovery_event_id: "recovery_..."
failure_ref: "failure_..."
action: "RETRY|REPAIR|RESUME|ROLLBACK|COMPENSATE"
attempt: 2
policy_ref: "..."
approval_ref: null
result: "SUCCEEDED|FAILED"
evidence_id: "..."
```

---

# 152. No Evidence Fabrication

If telemetry exists but canonical evidence is missing:

```text
do not invent completed evidence retroactively
```

Reconstruction must be explicitly marked as reconstructed and uncertain.

---

# 153. Recovery and Observability

`OBSERVABILITY.md` supplies signals.

Examples:

```text
provider timeout
queue backlog
worker heartbeat loss
DB errors
evidence write failure
deployment health fail
```

---

# 154. Detection vs Recovery

```text
Observability
    detects

Failure Recovery
    decides/executes recovery

Evidence
    proves
```

---

# 155. Incident Escalation

A failure becomes incident when impact/risk crosses operational threshold.

Exact severity taxonomy belongs to operational policy.

---

# 156. Incident Trigger Examples

```text
tenant isolation violation
production outage
evidence integrity failure
secret compromise
wide provider outage
data corruption
```

---

# 157. Incident Containment

Containment may include:

```text
disable provider
disable tool
revoke secret
pause deployments
read-only mode
stop queue consumption
```

according to authority.

---

# 158. Incident Recovery

After containment:

```text
identify safe state
restore dependency
reconcile state
verify security
resume gradually
```

---

# 159. Incident Resolution

Do not resolve incident until:

```text
service restored
critical integrity/security checked
known residual risk recorded
```

---

# 160. Post-Incident Review

Review:

```text
root cause
detection
containment
recovery
evidence
missed safeguards
new tests
new alerts
architecture impact
```

---

# 161. Root Cause Classes

```text
code defect
configuration defect
dependency/provider
operator error
security incident
capacity
data corruption
test gap
architecture gap
```

---

# 162. Recovery Does Not Equal Root Cause Fix

Restarting service may restore availability.

It does not necessarily fix underlying defect.

---

# 163. Temporary Mitigation

Temporary mitigation needs:

```text
owner
scope
risk
exit condition
```

---

# 164. Recovery Checkpoint

For long remediation:

```text
current safe state
completed actions
remaining actions
exact next step
```

---

# 165. Retry Decision Matrix

```text
Transient network failure
    → RETRY

Policy denial
    → DO NOT RETRY

Quota exhaustion
    → WAIT / FALLBACK / FAIL

Artifact validation failure
    → REPAIR

Unknown external side-effect outcome
    → RECONCILE FIRST
```

---

# 166. Provider Failure Matrix

```text
timeout
    → bounded retry/fallback

rate limit
    → backoff/fallback

quota exhausted
    → fallback if eligible

bad output
    → validate/repair/re-route

credential failure
    → configuration/secret recovery

privacy ineligible
    → never retry as eligible
```

---

# 167. Tool Failure Matrix

```text
permission denied
    → stop / approval

timeout
    → reconcile before retry

rate limit
    → backoff

invalid response
    → validate/fail

external conflict
    → reconcile
```

---

# 168. Worker Failure Matrix

```text
process crash
    → lease expiry → resume

heartbeat lost
    → lease expiry → reschedule

stale output
    → fencing reject

resource exhaustion
    → classify / resize / fail
```

---

# 169. Data Failure Matrix

```text
DB unavailable
    → fail closed / pause

cache unavailable
    → degrade / rebuild

vector store unavailable
    → RAG degrade/fail

object store unavailable
    → artifact completion blocked

evidence store unavailable
    → verified completion blocked
```

---

# 170. Deployment Failure Matrix

```text
artifact mismatch
    → stop

config failure
    → fix/rollback

migration failure
    → phase-aware recovery

health failure
    → rollback/fix-forward

credential failure
    → rotate/fix secret

external owner blocker
    → NEEDS_OWNER
```

---

# 171. FinOps Failure Matrix

```text
budget exhausted
    → stop / approval

pricing unknown
    → conservative deny/approval

retry cost spike
    → circuit break

repair cost exhausted
    → FAIL / NEEDS_USER_INPUT
```

---

# 172. Security Failure Matrix

```text
tenant leak
    → CRITICAL STOP / incident

secret leak
    → revoke / rotate / incident

grant mismatch
    → deny

approval replay
    → deny

sandbox escape
    → contain / revoke / incident
```

---

# 173. RAG Failure Matrix

```text
source parse fails
    → source-specific fail/repair

embedding fails
    → retry/fallback

index unavailable
    → fail/degrade

authorization fails
    → deny

provenance missing
    → fail validation

deleted source appears
    → critical data integrity issue
```

---

# 174. Artifact Failure Matrix

```text
generation fail
    → retry/repair

hash mismatch
    → reject

validation fail
    → repair

delivery fail
    → artifact remains valid, delivery state separate
```

---

# 175. Evaluation Failure Matrix

```text
hard criterion fail
    → repair/fail

evaluator unavailable
    → retry/fallback/NEEDS_REVIEW

evaluator injection suspected
    → reject evaluation
```

---

# 176. Recovery and Routing

Every provider fallback or re-route must preserve one canonical RoutingDecision truth.

---

# 177. Recovery and Policy

Recovery action is itself governed.

Examples:

```text
retry provider
use fallback
rollback deployment
compensate payment
```

may require Policy evaluation.

---

# 178. Recovery and Approval

If recovery action is privileged:

```text
approval may be required
```

---

# 179. Recovery and Security

Recovery must not:

```text
disable auth
disable tenant checks
bypass secrets policy
```

---

# 180. Recovery and Privacy

Fallback provider must re-evaluate:

```text
privacy
residency
classification
```

---

# 181. Recovery and FinOps

Retry/repair/fallback consume existing budget.

---

# 182. Recovery and Testing

Every recovery path requires tests appropriate to risk.

---

# 183. Recovery Testing Categories

```text
unit
state-transition
retry
repair
checkpoint
resume
lease/fencing
cancellation
compensation
rollback
DR
```

---

# 184. Retry Tests

Required:

```text
retryable error retries
non-retryable does not
attempt count increments
budget consumed
backoff bounded
```

---

# 185. Repair Tests

Required:

```text
new artifact version
criteria unchanged
repair limit enforced
final evaluation rerun
```

---

# 186. Checkpoint Tests

Required:

```text
create
hash
restore
tamper rejection
budget preservation
attempt preservation
```

---

# 187. Resume Tests

Required:

```text
process restart
worker restart
provider timeout
approval wait
policy change
expired grant
```

---

# 188. Fencing Tests

Golden:

```text
Worker A token 10
lease expires
Worker B token 11
A commits
→ REJECT
```

---

# 189. Cancellation Tests

Required:

```text
authorized cancel
unauthorized cancel denied
late result rejected
final CANCELLED
```

---

# 190. Compensation Tests

Test:

```text
proposal
approval
execution
failure
partial compensation
```

---

# 191. Rollback Tests

Test:

```text
known-good artifact
config
migration compatibility
secret revocation preserved
post-rollback health
```

---

# 192. Backup Restore Tests

Required for critical stores.

---

# 193. DR Drill

DR readiness requires drill or equivalent controlled verification.

---

# 194. Provider Outage Test

Simulate:

```text
primary provider down
fallback eligible
fallback ineligible
```

---

# 195. Queue Outage Test

Verify no direct execution bypass.

---

# 196. Evidence Store Outage Test

Verify no false verified completion.

---

# 197. Secret Store Outage Test

Verify no embedded fallback credential.

---

# 198. RAG Index Outage Test

Verify safe degraded/failure behavior.

---

# 199. Data Corruption Test

Controlled simulation where feasible.

---

# 200. Recovery Chaos Testing

For mature environments, inject:

```text
worker loss
network partition
provider outage
queue delay
DB failover
```

---

# 201. Chaos Safety

Chaos must not jeopardize unrelated production tenants.

---

# 202. Recovery Observability Requirements

Every recovery-capable subsystem should expose:

```text
failure class
attempt
retry
repair
checkpoint
resume
rollback
final state
```

signals.

---

# 203. Recovery Alerts

Alert on:

```text
retry storm
repair exhaustion
checkpoint failure
stale commit
DR invocation
rollback failure
evidence failure
```

---

# 204. Recovery SLOs

Possible measures:

```text
resume success rate
mean time to recover
rollback success
stuck-job rate
```

Numeric targets require operational governance.

---

# 205. Recovery Cost Metrics

Track:

```text
retry cost
repair cost
recovery compute
rollback cost
DR cost
```

---

# 206. Recovery Waste

High retry/repair cost may indicate poor upstream quality.

---

# 207. Recovery Evidence Completeness

A recovered successful job must still have complete lineage.

---

# 208. Recovery Status Semantics

Recovery may yield:

```text
SUCCEEDED
FAILED
CANCELLED
NEEDS_USER_INPUT
```

according to final canonical state.

Do not introduce:

```text
RECOVERED
```

as top-level JobStatus unless future canonical contract explicitly adopts it.

---

# 209. Recovery History

Recovery events are history, not final status.

---

# 210. Successful Recovery

Definition:

```text
failure occurred
safe recovery action executed
authoritative state reconciled
required validation passed
evidence complete
```

---

# 211. Partial Recovery

System available but some capabilities unavailable.

Use:

```text
DEGRADED
```

operational health, not false success.

---

# 212. Failed Recovery

If recovery action fails:

```text
do not loop indefinitely
```

Escalate/fail according to bounds.

---

# 213. Unknown Recovery State

If external outcome cannot be determined:

```text
UNKNOWN / BLOCKED
```

operationally until reconciled.

Do not guess.

---

# 214. Recovery Governance

Recovery policies are governed changes.

---

# 215. Emergency Recovery Authority

Emergency containment may permit bounded high-priority actions under governance.

---

# 216. Break-Glass Recovery

Requires:

```text
strong auth
reason
scope
time limit
evidence
post-review
```

---

# 217. Break-Glass Red Line

Break-glass cannot disable:

```text
tenant isolation
evidence integrity
```

---

# 218. Recovery Documentation

Critical services should document:

```text
failure modes
retry
checkpoint
rollback
dependencies
runbook
```

---

# 219. Runbook Structure

Recommended:

```text
symptom
impact
preconditions
safe checks
containment
recovery
verification
rollback
escalation
```

---

# 220. No Dangerous Copy/Paste

Runbooks must not embed:

```text
production root password
broad secret
unsafe destructive command without guardrails
```

---

# 221. Automation Runbook

Recovery automation must enforce the same permissions as manual process.

---

# 222. Manual Recovery

Manual actions must be recorded/reconciled.

---

# 223. Recovery Audit

Post-recovery audit asks:

```text
Was policy respected?
Were attempts bounded?
Was budget respected?
Was stale authority rejected?
Was evidence complete?
```

---

# 224. Recovery Technical Debt

Temporary manual workaround should produce remediation task if repeated.

---

# 225. Recovery Anti-Patterns

Reject:

```text
while true retry
retry all exceptions
reset budget on restart
reuse old approval
reuse expired grant
mark success after restart without validation
force commit stale worker
delete failure evidence
fallback to global admin credentials
```

---

# 226. “Retry Until It Works” Anti-Pattern

User instruction does not override bounded retry.

---

# 227. “Just Use Another Provider” Anti-Pattern

Fallback must remain eligible.

---

# 228. “Ignore Failed Test and Deploy” Anti-Pattern

Recovery cannot bypass verification.

---

# 229. “Restore Old Backup” Anti-Pattern

Restore must account for:

```text
revoked secrets
schema
tenant integrity
evidence
```

---

# 230. “Restart Everything” Anti-Pattern

Broad restart may increase impact.

Use scoped recovery.

---

# 231. “Clear Queue” Anti-Pattern

Deleting queue may lose work/evidence.

Reconcile first.

---

# 232. “Delete State and Start Over” Anti-Pattern

Forbidden for durable governed jobs unless explicit cancellation/restart semantics exist.

---

# 233. “Re-run Side Effect” Anti-Pattern

Unknown external outcome must be reconciled first.

---

# 234. “Logs Prove Recovery” Anti-Pattern

Logs help diagnose.

Authoritative state/evidence prove final recovery.

---

# 235. Recovery Maturity

Recovery capability uses canonical maturity:

```text
DESIGNED
→ SPECIFIED
→ IMPLEMENTED
→ TESTED
→ VERIFIED
→ DEPLOYED / PRODUCTION
```

---

# 236. DESIGNED Gate

Requires:

```text
failure classes
ownership
recovery strategy
```

---

# 237. SPECIFIED Gate

Requires:

```text
retry
repair
checkpoint
resume
cancellation
rollback
evidence
```

contracts.

---

# 238. IMPLEMENTED Gate

Requires actual durable recovery paths.

---

# 239. TESTED Gate

Requires:

```text
failure injection
retry tests
resume tests
fencing tests
rollback tests
```

---

# 240. VERIFIED Gate

Requires representative end-to-end failure/recovery with evidence.

---

# 241. DEPLOYED / PRODUCTION Gate

Requires production recovery mechanisms deployed and runtime/drill evidence for defined scope.

---

# 242. Control Plane Recovery DoD

Requires:

```text
durable state
restart
reconciliation
policy reload
lease invalidation
```

---

# 243. Worker Recovery DoD

Requires:

```text
lease expiry
fencing
reschedule
checkpoint/resume
```

---

# 244. Queue Recovery DoD

Requires:

```text
redelivery
deduplication
DLQ
backpressure
replay controls
```

---

# 245. Provider Recovery DoD

Requires:

```text
retry/fallback
policy eligibility
quota handling
budget
evidence
```

---

# 246. Tool Recovery DoD

Requires:

```text
idempotency/reconciliation
permission
timeout
external-state verification
```

---

# 247. RAG Recovery DoD

Requires:

```text
ingestion retry
index failure
retrieval failure
source update/delete reconciliation
authorization revalidation
```

---

# 248. Artifact Recovery DoD

Requires:

```text
version/hash
restore/recreate
validation
delivery separation
```

---

# 249. Evidence Recovery DoD

Requires:

```text
durability
write failure handling
integrity
no fabricated evidence
```

---

# 250. Deployment Recovery DoD

Requires:

```text
rollback/fix-forward
migration handling
health verification
evidence
```

---

# 251. DR DoD

Requires:

```text
RPO/RTO targets defined
restore path
state reconciliation
fencing
security verification
drill evidence
```

---

# 252. Cancellation DoD

Requires:

```text
authorized request
stop scheduling
active-task handling
late-result fencing
final CANCELLED
evidence
```

---

# 253. Compensation DoD

Requires:

```text
supported side effects identified
proposal
approval rules
execution
failure handling
evidence
```

---

# 254. Recovery Production Gate

Do not claim production recovery unless:

```text
recovery mechanisms deployed
critical paths tested
observability active
evidence available
```

---

# 255. RAG Milestone Alignment

`RAG.12` should prove recovery for:

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

# 256. Milestone Failure Handling

A milestone failure:

```text
does not advance downstream
```

Use:

```text
BLOCKED / IN_PROGRESS
```

until fixed/reclassified.

---

# 257. Hard Tool Limit Checkpoint

If development tooling stops due to tool/session limit:

```text
record checkpoint
do not claim milestone complete
```

---

# 258. Continuation Record

Include:

```text
active milestone
branch/revision
completed work
pending evidence
exact next action
```

---

# 259. Recovery and Current State Claims

Do not say:

```text
"recovered"
"healthy"
"production stable"
```

without current direct evidence.

---

# 260. Historical Recovery Evidence

Historical successful recovery proves only that scenario/version/environment.

---

# 261. Recovery Regression

A later change may invalidate prior recovery behavior.

Re-test impacted path.

---

# 262. Change Triggers for Recovery Review

Review when:

```text
new provider
new tool
new queue
new state store
new deployment topology
new side effect
new factory
new RAG store
```

---

# 263. Core Change Recovery Review

Any Core change must assess:

```text
restart
state migration
backward compatibility
rollback
evidence
```

---

# 264. Contract Change Recovery Review

Version changes must preserve resume of in-flight jobs or define migration/termination policy.

---

# 265. Worker Version Compatibility

During rolling deployment, old/new workers may coexist.

Queue/task contracts must remain compatible.

---

# 266. Checkpoint Versioning

Checkpoint schema must be versioned.

---

# 267. Old Checkpoint Migration

If incompatible:

```text
migrate
or
fail safely with explicit recovery path
```

---

# 268. Artifact Version Compatibility

Old accepted artifacts remain immutable history.

---

# 269. Evidence Schema Compatibility

Recovery history must remain readable after schema evolution.

---

# 270. Provider Adapter Version Compatibility

In-flight jobs may need route/adapter version awareness.

---

# 271. Tool Adapter Version Compatibility

Same principle for external side effects.

---

# 272. Rolling Deployment Recovery

Mixed versions must not break:

```text
state
queue messages
checkpoint
evidence
```

---

# 273. Canary Recovery

Canary failure should:

```text
stop promotion
rollback/disable canary
preserve evidence
```

---

# 274. Feature Flag Recovery

Feature flag can disable failing new feature if architecture allows.

It must not disable security.

---

# 275. Circuit Breaker

Circuit breaker states may include:

```text
CLOSED
OPEN
HALF_OPEN
```

implementation-specific.

---

# 276. Circuit Breaker Use

Appropriate for:

```text
provider
tool
external dependency
```

not tenant authorization.

---

# 277. Bulkhead Isolation

Separate worker/resource pools may prevent one failing class from exhausting entire platform.

---

# 278. Backpressure

When downstream saturated:

```text
queue
admission
rate limits
```

should reduce new work.

---

# 279. Load Shedding

May reject/defer low-priority work under overload.

Security/policy remains enforced.

---

# 280. Priority Recovery

Critical recovery work may receive priority according to policy.

---

# 281. Tenant Fairness During Recovery

One tenant’s retry storm must not monopolize resources.

---

# 282. Provider Fairness

Rate-limit/retry policy should avoid consuming all provider quota on failed jobs.

---

# 283. Recovery Rate Limit

Recovery operations themselves may need rate limits.

---

# 284. Human-in-the-Loop Recovery

Use when:

```text
risk high
unknown external state
irreversible side effect
ambiguous data corruption
```

---

# 285. Automated Recovery Ceiling

Automation may recover only within explicit policy.

Beyond ceiling:

```text
NEEDS_OWNER / NEEDS_USER_INPUT / FAILED
```

---

# 286. Recovery Confidence

Do not expose fake probability of safe recovery unless model is validated.

Use explicit state/evidence.

---

# 287. Recovery Decision Traceability

Every automated recovery decision should reference:

```text
failure class
policy
budget
attempt
action
```

---

# 288. Recovery Causality Map

```text
FAILURE
  │
  ▼
FAILURE RECORD
  │
  ▼
RECOVERY DECISION
  │
  ├─ RETRY
  ├─ REPAIR
  ├─ RESUME
  ├─ COMPENSATE
  ├─ ROLLBACK
  └─ STOP
  │
  ▼
VALIDATION
  │
  ▼
STATE UPDATE
  │
  ▼
EVIDENCE
```

---

# 289. Recovery Formula

```text
CLASSIFIED FAILURE
+
BOUNDED POLICY
+
DURABLE STATE
+
CHECKPOINT
+
LEASE / FENCING
+
IDEMPOTENCY
+
BUDGET
+
VALIDATION
+
EVIDENCE
=
SAFE RECOVERY
```

---

# 290. Failure Safety Formula

```text
UNKNOWN
    ≠
SUCCESS

TIMEOUT
    ≠
FAILURE OF SIDE EFFECT

RETRY
    ≠
NEW BUDGET

RESTART
    ≠
STATE RESET

ROLLBACK
    ≠
SECURITY RESET

RECOVERY
    ≠
BYPASS
```

---

# 291. Final Recovery Invariant

The defining ILAIOS failure-recovery rule is:

> **Every failure must end in a state that is safer and more truthful than pretending the failure did not happen.**

Therefore:

```text
If authority is uncertain
    → stop

If tenant scope is uncertain
    → deny

If side-effect outcome is uncertain
    → reconcile

If budget is exhausted
    → stop or request approval/input

If worker authority is stale
    → reject

If evidence is missing
    → do not claim verified success

If recovery fails
    → fail explicitly
```

The canonical resilience objective is:

```text
PRESERVE AUTHORITY
+
PRESERVE STATE
+
PRESERVE EVIDENCE
+
BOUND RETRY / REPAIR
+
REJECT STALE EXECUTION
+
VERIFY BEFORE RESUME
=
ILAIOS FAILURE RECOVERY
```

**ILAIOS must recover from failure without converting uncertainty into authority, cost into infinity, or partial execution into false completion.**
