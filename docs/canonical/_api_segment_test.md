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

