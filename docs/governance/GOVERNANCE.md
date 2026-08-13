# ILAIOS — GOVERNANCE

**Document Type:** Canonical Governance Standard  
**Format:** GitHub Markdown + ASCII governance diagrams  
**Status:** Canonical Baseline v1.0 — Pending Repository Publication  
**Canonical Repository Location:** `docs/governance/GOVERNANCE.md`  
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
**Core Governance Principle:** **ONE ILAIOS — ONE AUTHORITY CHAIN — NO PARALLEL GOVERNANCE**

> This document defines the canonical governance model of ILAIOS: authority, decision rights, architecture change control, Core evolution, capability promotion, policy ownership, exceptions, approvals, engineering/release governance, evidence requirements, external dependency adoption, owner-controlled gates, and governance Definition of Done. It defines target governance rules, not mutable repository status or current implementation state.

---

# 00. Purpose

ILAIOS must remain one governed AI operating system while it evolves.

Governance exists to prevent the project from fragmenting into:

```text
multiple Cores
multiple Control Planes
multiple planners
multiple routing authorities
multiple capability registries
multiple evidence truths
multiple incompatible execution models
```

Every material decision must answer:

```text
Who is authorized to decide?
Which canonical authority governs?
What exact scope may change?
Which evidence is required?
Which reviews are mandatory?
What may be automated?
What requires human authority?
How is the decision recorded?
How can it be reversed or superseded?
```

The governing formula is:

```text
EXPLICIT AUTHORITY
+ BOUNDED CHANGE
+ REQUIRED REVIEW
+ TEST / EVALUATION
+ EVIDENCE
+ REVERSIBILITY
= GOVERNED EVOLUTION
```

---

# 01. Governance Scope

This document owns:

- canonical authority hierarchy;
- governance roles and logical decision rights;
- architecture change governance;
- Core evolution governance;
- capability/factory governance;
- policy and routing governance;
- security/data/API governance decision boundaries;
- test and verification governance;
- deployment/release governance;
- FinOps/spend-governance decision rights;
- external provider/tool/skill governance;
- open-source/reference assimilation governance;
- exceptions and waivers;
- emergency and break-glass governance;
- owner-controlled external gates;
- maturity/status claim governance;
- ADR and documentation governance;
- autonomous-agent governance;
- change evidence and auditability.

This document does not redefine architecture, implementation, tests, deployment topology, or data/API schemas. Those remain owned by their canonical documents.

---

# 02. Target Governance vs Current Reality

This document defines **target governance**.

Current governance reality is established from:

```text
current repository configuration
current branch protection
current required checks
current CI configuration
current policy configuration
current identity/permission configuration
current deployment permissions
current evidence
```

Therefore:

```text
governance rule documented
≠ governance rule currently enforced

branch protection required
≠ branch protection currently enabled

approval required
≠ approval currently configured

release policy defined
≠ latest release complied
```

Mutable enforcement status belongs to `MILESTONES.md`, operational status, and direct evidence.

---

# 03. Canonical Authority Model

Authority depends on the question.

For **what ILAIOS must be**:

```text
SYSTEM_ARCHITECTURE.md
        ↓
PRODUCT_REQUIREMENTS.md
        ↓
IMPLEMENTATION_SPEC.md
        ↓
DEPENDENCY_GRAPH.md
        ↓
specialized canonical specifications
```

For **what ILAIOS actually is today**:

```text
current code
    ↓
current tests
    ↓
current CI
    ↓
current runtime evidence
    ↓
current deployment evidence
```

For planning/status prose:

```text
roadmap
milestone prose
status summaries
comments
historical notes
```

are descriptive only and may not override direct evidence.

---

# 04. Canonical Documentation Order

```text
01  SYSTEM_ARCHITECTURE.md
02  AUTONOMOUS_NODE_ARCHITECTURE.md
03  README.md
04  PRODUCT_REQUIREMENTS.md
05  IMPLEMENTATION_SPEC.md
06  DEPENDENCY_GRAPH.md
07  API_CONTRACTS.md
08  SECURITY_ARCHITECTURE.md
09  DATA_ARCHITECTURE.md
10  THREAT_MODEL.md
11  TESTING_AND_EVALUATION.md
12  DEPLOYMENT_ARCHITECTURE.md
13  FINOPS.md
14  ENGINEERING_STANDARDS.md
15  docs/governance/GOVERNANCE.md
16  MILESTONES.md
17  ADR/
18  OBSERVABILITY.md
19  FAILURE_RECOVERY.md
```

A downstream document may specialize an upstream authority. It may not silently contradict it.

---

# 05. Constitutional Governance Invariants

```text
ONE Constitutional Core
ONE authoritative Control Plane
ONE canonical identity / tenant truth
ONE policy authority
ONE planner authority
ONE capability registry
ONE RoutingDecision truth
ONE evidence / provenance truth
ONE canonical runtime state authority
```

No individual, team, factory, provider, worker, agent, tool, client, or external project may create a competing authority.

---

# 06. Core Governance Rule

The ILAIOS Core is:

```text
FROZEN BY DEFAULT
EVOLVABLE BY PROOF
```

A Core change is permitted only when evidence proves that a platform-wide invariant cannot be correctly implemented inside an existing governed capability boundary.

Core must not absorb for convenience:

```text
factory logic
provider-specific logic
model-specific logic
domain-specific intelligence
third-party behavior
UI behavior
replaceable integrations
```

---

# 07. Core Change Acceptance

A Core change requires:

```text
platform-wide invariant
existing-boundary analysis
alternative analysis
architecture impact
dependency impact
security impact
data/API impact
testing plan
migration/compatibility plan
ADR
broad regression evidence
```

Any proposal named or behaving like `core_v2`, `new_core`, or a parallel Control Plane must be rejected unless it is a bounded migration mechanism with one final authority and an explicit retirement condition.

---

# 08. Logical Governance Roles

Canonical logical roles include:

```text
Product Owner
Architecture Authority
Security Authority
Data Authority
Engineering Owner
Release Authority
FinOps Authority
Tenant Administrator
Reviewer
Approver
Auditor
Operator
```

One human may hold several roles, especially in a solo-founder/small-team phase. Role boundaries still remain explicit in evidence.

---

# 09. Role vs Person

```text
ROLE
    = decision responsibility

PERSON
    = individual exercising that responsibility
```

Logical separation is sufficient when organizational separation is not practical.

Automated agents are never allowed to infer self-approval from the fact that one human holds multiple roles.

---

# 10. Product Owner

Owns product direction, user outcome priorities, and product-level scope.

Product preference may not silently override constitutional security, tenant isolation, or evidence requirements.

---

# 11. Architecture Authority

Owns material decisions affecting:

```text
Core
Control Plane
planner authority
capability boundaries
routing authority
factory boundaries
cross-service authority/dependencies
canonical execution model
```

---

# 12. Security Authority

Owns review/decision rights affecting:

```text
authentication
authorization
tenant isolation
secrets
cryptography
sandboxing
network trust
high-risk tools
security policy
threat boundaries
```

---

# 13. Data Authority

Owns material decisions affecting:

```text
authoritative data ownership
tenant data model
retention/deletion
data lineage
knowledge ownership
evidence schema ownership
cross-store migration
```

---

# 14. Engineering Owner

Owns implementation quality, repository discipline, test quality, CI quality, and maintainability.

Engineering code cannot redefine architecture authority merely by existing.

---

# 15. Release Authority

Determines whether a verified release candidate is eligible to enter a governed deployment/release process.

Release eligibility does not equal deployment authorization or live-health proof.

---

# 16. FinOps Authority

Owns budget policy, spend thresholds, cost-model governance, provider cost governance, and internal showback/chargeback rules.

FinOps cannot override security/privacy eligibility to obtain a cheaper route.

---

# 17. Reviewer / Approver / Auditor

Reviewer assesses correctness and compliance.

Approver authorizes a specific proposed action.

Auditor verifies evidence and governance compliance.

These are distinct responsibilities even when one person performs more than one role.

---

# 18. Automated Agent Governance

Development/runtime agents may:

```text
analyze
propose
implement within granted scope
run tests
produce evidence
prepare artifacts
```

They may not:

```text
self-grant
self-approve
change constitutional authority
bypass required checks
weaken tests to obtain PASS
claim deployment/live state without evidence
```

---

# 19. Agent Authority Ceiling

Agent authority is bounded by:

```text
task scope
ExecutionGrant
tool/repository scope
policy
approval
```

Capability is not authority.

---

# 20. Human Approval Governance

Human approval is used when policy determines autonomous authorization is insufficient.

Potential approval candidates include:

```text
production deployment
DNS mutation
external communication
payment/spend
store publication
destructive repo/database action
security policy weakening
high-risk export
```

Approval must bind to the exact action, resource, risk/cost, scope, and expiration.

---

# 21. No Generic Privileged Approval

A phrase such as:

```text
"do whatever is necessary"
```

may express broad intent, but it is not a generic authorization for arbitrary privileged side effects.

---

# 22. No Automated Self-Approval

The proposing agent/process cannot create the authoritative approval for its own privileged action.

---

# 23. Policy Authority

Policy Gateway is the authoritative execution-admission boundary.

Factories, workers, providers, clients, and agents cannot override PolicyDecision.

---

# 24. Policy Precedence

```text
Constitutional Platform Policy
        ↓
Environment Policy
        ↓
Tenant Policy
        ↓
Project Policy
        ↓
Task Restrictions
```

Lower scopes may tighten rules. They may not weaken higher mandatory restrictions.

---

# 25. Policy Change Governance

Material policy changes require:

```text
reason
scope
version/diff
security impact
tenant impact
tests
approval where required
rollback
change evidence
```

---

# 26. Capability Governance

Every canonical capability requires:

```text
canonical capability ID
owner
responsibility
dependencies
contracts
security/data obligations
evidence obligations
maturity state
```

Canonical IDs use `ilaios.capability.*`.

---

# 27. Capability Creation Test

Create a new capability only when:

```text
responsibility is stable and distinct
existing capability cannot coherently own it
no duplicate authority results
dependencies are explicit
contracts can be defined
```

A new provider, skill, UI feature, or folder alone is not necessarily a new capability.

---

# 28. Capability Maturity Governance

Canonical maturity:

```text
DESIGNED
→ SPECIFIED
→ IMPLEMENTED
→ TESTED
→ VERIFIED
→ DEPLOYED / PRODUCTION
```

`DEPRECATED` is a lifecycle exit state.

No maturity transition may occur without the evidence required by the canonical testing/implementation standards.

---

# 29. Maturity vs Operational Status

Operational terms such as:

```text
ACTIVE
BLOCKED
DORMANT
SELECTED
LIVE_HEALTHY
DEGRADED
```

are not capability maturity states.

They belong to `MILESTONES.md`, execution status, or live operational evidence.

---

# 30. MILESTONES.md Boundary

`MILESTONES.md` owns mutable delivery planning/status.

Correct separation:

```text
GOVERNANCE.md
    defines how a workstream may be selected/promoted

MILESTONES.md
    records which workstream is currently selected/promoted
```

---

# 31. Dependency Governance

`DEPENDENCY_GRAPH.md` owns prerequisite relationships.

Governance defines how those relationships may change.

A dependency cannot be removed merely because it is inconvenient.

---

# 32. Dependency Change Gate

Changing dependency edges requires:

```text
need/rationale
cycle analysis
owner analysis
security impact
coupling impact
replaceability impact
tests
```

---

# 33. Factory Governance

Factories may:

```text
declare capabilities
compose/instantiate domain DAGs
define domain quality gates
produce domain artifacts
request privileged actions
```

Factories may not:

```text
own a second Control Plane
own a second policy authority
own a second RoutingDecision truth
own a second evidence truth
invoke providers outside approved boundaries
```

---

# 34. Factory Creation Governance

A new Factory requires:

```text
distinct finished-product domain
reusable workflow boundary
canonical capability dependencies
shared workflow runtime
artifact contract
quality/evaluation gates
```

---

# 35. Knowledge Governance

Knowledge/RAG is a governed platform capability and knowledge plane.

It does not become a Factory merely because it has a workflow.

---

# 36. Provider Governance

Providers are replaceable resources, never platform authorities.

Production eligibility requires review of:

```text
capabilities
security/privacy
residency
credential model
cost
adapter
routing integration
tests/evidence
```

---

# 37. Routing Governance

There is one canonical `RoutingDecision` truth.

Any change that creates a competing final route decision is rejected.

Material routing changes require architecture, security/privacy, FinOps, and regression review as applicable.

---

# 38. External Router Governance

An external routing system may exist only beneath ILAIOS authority:

```text
ILAIOS Policy
    ↓
ILAIOS Routing Authority
    ↓
External Routing Adapter
    ↓
External Router
```

It may not replace ILAIOS policy or canonical route truth.

---

# 39. Tool Governance

Every production tool requires:

```text
ToolDescriptor
allowed operations
risk class
ExecutionGrant rules
secret scope
network scope
filesystem scope
sandbox requirement
evidence requirement
```

Changing a tool from read-only to write/destructive is a governance-significant change.

---

# 40. Skill Governance

Skills are bounded expertise, not authority.

External skill adoption uses:

```text
reference
→ inspect
→ extract requirements/behavior
→ ILAIOS-native SkillContract
→ security review
→ tests
→ evidence
```

---

# 41. Agent Governance

AgentManifest changes affecting allowed capabilities, caller/target relationships, tool access, or risk ceiling require versioning and review.

ILAIOS has one canonical Agent Registry / AgentManifest identity source. Any agent list, table, dashboard, or documentation view is a projection only and must not become a second identity or authority source. The canonical Agent Registry / AgentManifest defines agent identity and declared boundaries; execution authority remains governed by PolicyDecision / ExecutionGrant and applicable approval rules.

Agents cannot mint permission.

---

# 42. Worker Governance

Workers execute scoped tasks.

Workers cannot create or expand:

```text
PolicyDecision
ExecutionGrant
ApprovalDecision
RoutingDecision authority
```

---

# 43. Scheduler Governance

Scheduler owns assignment and coordination, not authorization.

Changes to lease/fencing/retry/fairness are runtime/reliability-significant.

---

# 44. Data Governance

Every protected record must have explicit ownership/scope and lifecycle.

Moving authoritative ownership between stores/services requires a governed migration decision.

---

# 45. Retention Governance

Retention is policy-driven, not “keep longest by default”.

Balance:

```text
product need
security
privacy
legal/audit
cost
```

---

# 46. Deletion Governance

Deletion must account for:

```text
active data
derived data
knowledge indexes
artifacts
evidence
backups
legal/security holds
```

---

# 47. Evidence Governance

Evidence is canonical proof of material decisions/actions.

Evidence must not be silently rewritten to support a desired status claim.

Corrections should create new evidence or explicit supersession where integrity matters.

---

# 48. Evidence Completeness Governance

A capability/job cannot truthfully claim `VERIFIED` when required evidence is materially incomplete.

---

# 49. Security Governance

Material security changes map to:

```text
threat
control
test
evidence
```

for the applicable scope.

---

# 50. Constitutional Security Controls

The following cannot be silently waived:

```text
tenant isolation
no agent self-approval
no agent self-grant
no raw unrestricted secret exposure
required policy admission
single routing truth
required evidence
```

---

# 51. Security Exception Governance

A security exception requires:

```text
specific rule
risk
scope
compensating control
Security Authority approval
expiration
exit condition
```

Constitutional invariants may be non-waivable.

---

# 52. Secrets Governance

Secrets are created, rotated, and revoked through governed secret/key infrastructure.

They may not be normalized into source code, ordinary config, canonical docs, logs, or evidence payloads.

---

# 53. Cryptographic Governance

Material changes to:

```text
trust roots
key hierarchy
signing
encryption
algorithm policy
rotation
```

require security review and migration/recovery analysis.

---

# 54. API Governance

Public breaking API changes require:

```text
version strategy
consumer migration
compatibility window
contract tests
documentation
```

Persisted/cross-process internal contracts require equivalent discipline.

---

# 55. State Machine Governance

Canonical runtime states/transitions may not be changed casually.

A change must assess:

```text
resume/recovery
API projections
persistence
migration
cancellation
approval
fencing
```

---

# 56. Testing Governance

Testing standards are mandatory evidence requirements.

Forbidden:

```text
test weakening to manufacture PASS
silent quarantine
rerun-until-green as policy
unrecorded waiver
```

---

# 57. Test Waiver

A waiver requires:

```text
specific test/gate
reason
risk
scope
owner
expiration
compensating control
approval
```

---

# 58. Evaluation Governance

Independent final evaluation must remain independent enough for the risk.

Producer-generated “PASS” does not automatically establish verified acceptance.

---

# 59. Human Evaluation Evidence

A human evaluation should record:

```text
reviewer
artifact/version
criteria/version
decision
reason
timestamp
```

---

# 60. Release Governance

A release requires:

```text
known source revision
verified artifact
required test evidence
security status
migration state
release notes
rollback/forward-fix path
```

---

# 61. Production Promotion Governance

Production promotion is a privileged action.

```text
verified artifact
    ↓
deployment admission
    ↓
approval if required
    ↓
deploy
    ↓
verify
    ↓
evidence
```

Passing tests do not themselves authorize production deployment.

---

# 62. Deployment Governance

Deployment must preserve:

```text
artifact identity
target identity
scoped deployment credential
approval scope
verification
rollback/evidence
```

---

# 63. Infrastructure Governance

Infrastructure changes affecting network, identity, data, secrets, HA/DR, or production permissions require appropriate architecture/security review.

IaC describes desired state; it does not self-authorize deployment.

---

# 64. Emergency Change Governance

Emergency does not mean ungoverned.

Minimum required:

```text
reason
scope
authorized actor
minimum safe validation
evidence
post-change review
```

---

# 65. Break-Glass Governance

Break-glass requires:

```text
strong authentication
explicit reason
limited scope
short lifetime
alerting
evidence
post-use review
```

It must not become routine workflow.

---

# 66. FinOps Governance

Budget/spend changes are governed policy changes.

Agents cannot increase hard ceilings through prompt reasoning.

Cost optimization cannot weaken security/privacy/quality/evidence.

---

# 67. Payment Governance

Payment/financial transfer requires stricter authorization than ordinary provider-compute spend.

Approval must bind to exact amount, currency, recipient/resource, and expiration as applicable.

---

# 68. Open-Source Reference Governance

Canonical assimilation path:

```text
External Reference
      ↓
Pin Source / Commit / Tag
      ↓
License Review
      ↓
Security / Supply-Chain Review
      ↓
Architecture / Behavior Study
      ↓
Requirement Extraction
      ↓
ILAIOS Specification
      ↓
ILAIOS-Native Implementation
      ↓
Tests / Evaluation / Evidence
```

External projects are references, not the ILAIOS brain.

---

# 69. Development Tool Governance

Development-time tools such as Codex, Claude Code, Gemini CLI, or OpenClaw may act as bounded engineering actuators.

They are not runtime platform authorities and are not allowed to bypass repository/governance gates.

---

# 70. Runtime Third-Party Adoption

A permanent runtime dependency requires:

```text
license
security
supply-chain review
replaceability
failure behavior
contract ownership
update/retirement plan
```

---

# 71. Provider Independence Governance

Provider independence means:

```text
ILAIOS owns capability, authority, routing, policy, evidence, and product semantics.
```

It does not require an equivalent fallback for every provider-specific capability at all times.

---

# 72. Independence Test

For a replaceable external resource:

```text
disable/remove external resource
      ↓
ILAIOS authority remains coherent
      ↓
eligible fallback or safe bounded failure
```

---

# 73. ADR Governance

ADR records significant architectural decisions.

Typical trigger:

```text
Core
Control Plane
routing/planning authority
data ownership
security trust boundary
deployment model
major permanent technology dependency
```

`ACCEPTED` ADR means the decision is accepted; it does not prove implementation.

---

# 74. ADR Supersession

Decisions are not erased.

```text
ADR-X
    superseded by
ADR-Y
```

preserves history and rationale.

---

# 75. Documentation Governance

Canonical documents are controlled artifacts.

Changes must preserve:

```text
authority order
internal consistency
single truth per concern
target/current separation
```

---

# 76. Document Change Classes

```text
EDITORIAL
CLARIFICATION
SPECIFICATION
ARCHITECTURAL
SECURITY-SIGNIFICANT
BREAKING
```

The change class determines review depth.

---

# 77. Editorial Change

Typographical/format/link changes with no semantic impact require minimal review.

---

# 78. Clarification Change

Clarifies existing meaning without changing authority, behavior, or requirement.

---

# 79. Specification Change

Changes normative behavior inside existing architecture and requires relevant owner review.

---

# 80. Architectural Change

Changes authority, boundary, Core, Control Plane, dependency ownership, planner, routing, or factory model.

Requires architecture governance and typically ADR.

---

# 81. Security-Significant Change

Changes trust boundary or security requirement and requires Security Authority review.

---

# 82. Breaking Change

Changes canonical contract meaning and requires versioning/migration analysis.

---

# 83. No Duplicate Canonical Documents

Do not create competing canonical files such as:

```text
SYSTEM_ARCHITECTURE_V2.md
NEW_GOVERNANCE.md
FINAL_ROUTING.md
```

unless governance explicitly defines them as versioned historical artifacts rather than competing current authority.

---

# 84. Companion Document Governance

A companion view must explicitly state its relationship to the primary authority.

Example:

```text
AUTONOMOUS_NODE_ARCHITECTURE.md
    = companion execution view of SYSTEM_ARCHITECTURE.md
```

---

# 85. Repository Location

Canonical repository path for this governance document is:

```text
docs/governance/GOVERNANCE.md
```

A local/exported `GOVERNANCE.md` file may be used for authoring and transfer, but repository publication must preserve the canonical location.

---

# 86. README Governance

README is orientation, not a competing architecture/governance source.

It should link to canonical documents rather than restating their full normative content.

---

# 87. Mutable Status Governance

Do not embed mutable values such as:

```text
current PR number
current HEAD
current provider health
current selected workstream
current live deployment state
```

as permanent governance truth.

---

# 88. Status Claim Rule

Any claim such as:

```text
VERIFIED
DEPLOYED
LIVE_HEALTHY
ACTIVE
SELECTED
```

must identify its evidence and scope when used as a current-state statement.

---

# 89. Status Conflict Rule

If descriptive status conflicts with current code/tests/CI/runtime/deployment evidence:

```text
CURRENT EVIDENCE WINS
```

---

# 90. Exception Governance

An exception is a temporary, explicit deviation from a non-constitutional standard.

It is not permission to violate constitutional invariants.

---

# 91. Exception Contract

Every exception requires:

```text
exception_id
rule
scope
reason
risk
owner
start
expiration
compensating controls
approval
exit condition
```

---

# 92. Exception Expiry

Expired exceptions are invalid.

No silent automatic renewal.

---

# 93. Waiver vs Exception

```text
WAIVER
    temporarily waives a specific gate/requirement

EXCEPTION
    permits a bounded alternative implementation/process
```

Both require explicit governance.

---

# 94. Non-Waivable Invariants

No waiver/exception may authorize:

```text
cross-tenant leakage
agent self-approval
agent self-grant
parallel Control Plane
parallel canonical routing truth
silent evidence tampering
unbounded secret exposure
```

---

# 95. External Owner Gates

Some work depends on external human/account/platform actions:

```text
store/developer account
DNS/domain ownership
legal/license decision
payment provider account
cloud account verification
branch/repository settings
code-signing identity
```

Governance defines the gate class. `MILESTONES.md` and evidence track current completion.

---

# 96. License Governance

External-code adoption requires:

```text
license identity
compatibility
obligations
distribution impact
recorded decision
```

---

# 97. Privacy Governance

New data use must answer:

```text
purpose
scope
classification
retention
provider processing
user/tenant control
```

---

# 98. Training Data Governance

Tenant/user data does not automatically become training data for ILAIOS or third-party providers.

Any such use requires explicit governed policy/legal basis and appropriate controls.

---

# 99. Analytics Governance

Analytics requires purpose limitation, minimization, access control, tenant safety, and retention.

Analytics stores are not authorization authorities.

---

# 100. Incident Governance

Security/reliability incidents require:

```text
containment authority
evidence
recovery
post-incident review
corrective action
```

Detailed response mechanics belong in `FAILURE_RECOVERY.md`.

---

# 101. Disaster Recovery Governance

DR must preserve:

```text
tenant isolation
policy
identity
revocation state
evidence
```

Emergency recovery must not start a permissive parallel platform.

---

# 102. Change Classification

Material changes should be classified:

```text
C0 — Editorial / No Runtime Impact
C1 — Local Low-Risk
C2 — Cross-Component / Contract
C3 — Security / Data / Runtime Critical
C4 — Constitutional / Core / Production-Critical
```

This classification is a governance aid, not capability maturity.

---

# 103. C0 Change

Examples:

```text
typo
formatting
non-semantic link correction
```

Minimal review.

---

# 104. C1 Change

Examples:

```text
bounded bug fix
local refactor
non-critical internal improvement
```

Normal engineering tests/review.

---

# 105. C2 Change

Examples:

```text
API/internal contract
cross-service interface
new capability dependency
```

Requires contract/integration review.

---

# 106. C3 Change

Examples:

```text
auth
tenant isolation
secrets
routing
runtime state
RAG authorization
deployment credentials
```

Requires architecture/security/data review as applicable and negative tests.

---

# 107. C4 Change

Examples:

```text
Core
Control Plane
planner authority
capability registry
evidence authority
constitutional production governance
```

Requires highest scrutiny and ADR.

---

# 108. Risk Assessment

Change risk considers:

```text
privilege
tenant breadth
data sensitivity
blast radius
financial impact
irreversibility
availability impact
migration complexity
```

---

# 109. Review Matrix

Conceptually:

```text
C0 → author/self-review may suffice
C1 → engineering review
C2 → engineering + affected domain authority
C3 → engineering + architecture/security/data as applicable
C4 → architecture + security + owner/governance decision + ADR
```

One person may exercise several logical roles, but the roles must remain explicit.

---

# 110. Canonical Change Workflow

```text
Requirement
    ↓
Identify Canonical Authority
    ↓
Classify Change / Risk
    ↓
Bound Scope
    ↓
Implement / Specify
    ↓
Tests / Evaluation
    ↓
Required Review
    ↓
Evidence
    ↓
Decision
    ↓
Merge / Release / Deploy if authorized
```

---

# 111. Scope Creep Governance

If implementation discovers materially broader scope:

```text
stop silent expansion
reclassify the change
update proposal/ADR if needed
review expanded impact
```

---

# 112. Repository Governance

Repository mechanics follow `ENGINEERING_STANDARDS.md`.

Governance owns decision rights around:

```text
canonical branch
branch protection
required checks
merge authority
release source
```

Current enforcement remains mutable evidence.

---

# 113. Canonical Branch

There is one canonical integration branch as configured by the repository.

No long-lived competing mainline is permitted.

---

# 114. Branch Protection Governance

The canonical branch should be protected according to project maturity/risk.

Changing required protection is itself a governance-significant action.

---

# 115. Required Check Governance

Required checks cannot be removed or weakened simply to merge a failing change.

---

# 116. Merge Governance

Merge requires:

```text
required checks PASS
required reviews complete
blocking feedback resolved
no known constitutional violation
```

---

# 117. No Autonomous Merge Bypass

An autonomous engineering agent may merge only where governance explicitly permits and all required gates have passed.

---

# 118. CI Governance

CI is an independent quality/evidence system.

CI configuration is governed code.

A failed required check cannot be converted to PASS by status prose.

---

# 119. Release Version Governance

Release version/tag, capability maturity, deployment state, and current live health are distinct facts.

---

# 120. Deprecation Governance

Deprecation requires:

```text
replacement
migration
usage visibility
retirement condition
```

`DEPRECATED` remains outside the capability maturity progression.

---

# 121. Migration Governance

Migration requires:

```text
source state
target state
compatibility
tests
rollback/forward-fix
data integrity
retirement of temporary path
```

---

# 122. Temporary Dual-System Rule

Temporary dual-read/write or compatibility layers may exist only when:

```text
one final authority is explicit
duration is bounded
consistency is checked
retirement is defined
```

Permanent parallel authority is forbidden.

---

# 123. Governance Decision Record

Conceptual record:

```yaml
governance_decision_id: "gov_..."
decision_type: "ARCHITECTURE_CHANGE"
scope: "..."
requested_by: "..."
roles_exercised: []
decision: "APPROVED|REJECTED|REQUIRES_CHANGES"
reason: "..."
evidence_refs: []
adr_ref: null
exception_ref: null
created_at: "..."
```

---

# 124. Governance Auditability

Material governance must answer:

```text
Who decided?
Under which role?
What changed?
Why?
Which evidence?
Which revision/version?
Which exception/ADR?
When?
What later superseded it?
```

---

# 125. Governance Drift

Governance drift occurs when actual engineering/runtime behavior bypasses documented authority.

Examples:

```text
direct provider call
hidden router
unprotected privileged deploy
client-owned tenant authority
worker-owned secret authority
```

---

# 126. Drift Detection

Use:

```text
architecture tests
security negative tests
repository scans
review
runtime evidence
```

Drift affecting Core, tenant isolation, policy, routing, or evidence is high severity.

---

# 127. Drift Remediation

When drift is accidental:

```text
contain
classify
restore canonical path
add regression test
record evidence
```

Do not rewrite architecture merely to legitimize accidental code.

---

# 128. Architecture Change Proposal

Minimum proposal:

```text
problem
current authority
proposed change
why existing boundary is insufficient
alternatives
architecture/dependency impact
security/data/API impact
testing
migration
rollback
```

---

# 129. Architecture Decision Outcomes

```text
ACCEPTED
REJECTED
REQUIRES_REVISION
DEFERRED
```

These are proposal decisions, not implementation states.

---

# 130. Core Change Proposal

Adds:

```text
proof existing capability cannot own invariant
proof no second Core is created
ADR
broad regression plan
```

---

# 131. Security Change Proposal

Adds:

```text
threat mapping
control mapping
negative tests
residual risk
```

---

# 132. Data Change Proposal

Adds:

```text
authoritative store
migration
retention/deletion
tenant impact
```

---

# 133. API Breaking Change Proposal

Adds:

```text
new version
consumer migration
compatibility window
deprecation
```

---

# 134. Provider Adoption Proposal

Adds:

```text
capabilities
privacy/residency
security
cost
credentials
adapter
fallback
verification
```

---

# 135. Tool Adoption Proposal

Adds:

```text
operations
risk
secret scope
network/filesystem scope
sandbox
approval candidates
```

---

# 136. Factory Adoption Proposal

Adds:

```text
finished-product domain
canonical dependencies
artifact contract
shared runtime
evaluation
```

---

# 137. External Reference Assimilation Proposal

Adds:

```text
source/version
license
security/supply chain
behavior extracted
native implementation plan
independence test
```

---

# 138. Release Approval Proposal

Includes:

```text
source revision
artifact hash
test evidence
security evidence
migration
known issues
rollback
```

---

# 139. Production Deployment Proposal

Includes:

```text
release artifact
target
deployment identity
approval scope
expected impact
verification
rollback
```

---

# 140. Decision Conflict Rules

If roles disagree, the higher-risk concern cannot simply be ignored.

Examples:

```text
Security/privacy > cost optimization
Tenant isolation > user convenience
Required quality > cheaper provider
Fail-closed security > availability convenience
Evidence requirement > status prose
```

---

# 141. Security Veto

Security Authority may block a change violating a constitutional security invariant.

---

# 142. Architecture Veto

Architecture Authority may block a change that creates duplicate canonical authority.

---

# 143. Evidence Veto

Missing required evidence means the system cannot truthfully claim `VERIFIED`, `DEPLOYED`, or current live health for that scope.

---

# 144. Governance Automation

Deterministic governance checks should be automated where possible:

```text
dependency cycle checks
required CI gates
architecture import/bypass rules
secret scanning
branch-protection checks
evidence completeness
exception expiry
```

Automation executes governance; it does not expand authority.

---

# 145. Policy-as-Code

Where appropriate, policy may be encoded as versioned/tested configuration or code.

Policy-as-code must remain reviewable and traceable.

---

# 146. Governance-as-Code

Machine-readable governance may encode:

```text
change class
required reviewers
required gates
exception expiry
release approval
```

Human-readable canonical meaning remains documented here.

---

# 147. Governance Reporting

Reports may summarize:

```text
open exceptions
expiring waivers
architecture decisions
maturity transitions
privileged approvals
release decisions
```

Reports are projections; source evidence/decision records remain authoritative.

---

# 148. Current Governance State

Current enforcement should be read from:

```text
repository settings
CI
policy store
identity platform
cloud/deployment platform
evidence store
```

not frozen into this document.

---

# 149. Maturity Promotion Record

A maturity promotion should identify:

```text
capability
scope
from state
to state
evidence
decision owner
```

---

# 150. Verification Is Version-Scoped

A capability verified at one revision/version is not automatically verified after a material change.

Historical verification remains historical evidence.

---

# 151. Provider / Tool / Skill Revocation

Compromised or non-compliant provider/tool/skill versions may be disabled/revoked.

Historical evidence must remain intact.

---

# 152. Emergency Security Containment

Bounded containment may include:

```text
revoke credential
disable provider
disable tool
block route
freeze deployment
```

according to incident/security authority.

Containment remains evidence-bearing.

---

# 153. Solo-Founder Governance

The governance model must remain practical for a solo founder.

Therefore:

```text
one authorized human may exercise multiple logical roles
```

while preserving:

```text
explicit decision role
evidence
no agent self-approval
no bypass
```

---

# 154. Governance Scaling

As the organization grows, logical roles may become separate teams/people without changing the core decision model.

---

# 155. Delegation

Human authority may be delegated only with explicit:

```text
delegate
scope
duration
actions
limits
```

A delegate cannot delegate more authority than received.

---

# 156. Vendor Governance

Critical vendor review may consider:

```text
security
privacy
availability
lock-in
cost
jurisdiction
data processing
exit strategy
```

---

# 157. Vendor Exit

Critical integrations should have a bounded exit path:

```text
disable route/access
revoke credentials
preserve historical evidence
handle retained data
fallback or safe failure
```

---

# 158. Compliance Governance

Specific regulatory/compliance requirements may add controls through the same governance chain.

No separate parallel governance system should be introduced merely for a compliance label.

Compliance claims require direct evidence and explicit scope.

---

# 159. Commercial Policy Boundary

Commercial plans/entitlements may define:

```text
usage limits
included capabilities
support level
```

They may not disable constitutional security or tenant isolation.

---

# 160. Experiment Governance

Experiments may change UI, routing preference, evaluator choice, or rollout behavior within constitutional constraints.

High-risk experiments require review and tenant/data isolation.

---

# 161. Technical Debt Governance

Material debt should be visible, owned, and scoped.

“Temporary debt” cannot justify permanent parallel authority or silent security bypass.

---

# 162. Governance Definition of Done — Canonical Document

Ready for canonical publication when:

```text
authority order is correct
target/current distinction is explicit
roles/decision rights are explicit
Core evolution rule preserved
exception model is explicit
status/milestone boundaries are explicit
no mutable current-state claims are embedded
no duplicate governance authority exists
```

---

# 163. Governance Definition of Done — Core Change

Requires:

```text
proof existing boundary insufficient
ADR
architecture approval
security review
implementation/test plan
migration/compatibility
broad regression
evidence
```

---

# 164. Governance Definition of Done — Capability Promotion

Requires the canonical maturity evidence for the exact claimed scope.

---

# 165. Governance Definition of Done — Provider Adoption

Requires:

```text
security/privacy/residency
adapter
routing
FinOps impact
tests
evidence
```

---

# 166. Governance Definition of Done — Tool Adoption

Requires:

```text
operations
grant scope
secret/network/filesystem policy
sandbox
approval candidates
tests
evidence
```

---

# 167. Governance Definition of Done — Release

Requires:

```text
source revision
artifact digest
required tests
security evidence
migration state
release authorization
```

---

# 168. Governance Definition of Done — Production Deployment

Requires:

```text
verified release
deployment authorization
approval if required
scoped deployment identity
post-deploy verification
deployment evidence
```

---

# 169. Governance Definition of Done — Exception

Requires:

```text
scope
risk
owner
approval
compensating control
expiration
exit condition
```

---

# 170. Governance Definition of Done — External Assimilation

Requires:

```text
pinned source
license
security/supply-chain review
requirements extracted
native implementation
tests
independence
evidence
```

---

# 171. Governance Test Matrix

Machine-enforceable governance should test:

```text
required check blocks merge
expired approval rejected
agent self-approval rejected
client cannot mint grant
parallel router path rejected
provider bypass rejected
exception expiry enforced
maturity promotion requires evidence
```

---

# 172. Governance Negative Tests

Examples:

```text
Factory direct-calls provider
    → FAIL

Agent modifies approval to approve itself
    → FAIL

Worker broadens ExecutionGrant
    → FAIL

Client claims admin role
    → FAIL

Required test waived without valid waiver
    → FAIL

Expired exception reused
    → FAIL
```

---

# 173. Governance Red-Team

Red-team should attempt:

```text
architecture bypass
review bypass
branch-protection bypass
test weakening
approval replay
exception abuse
current-state misreporting
provider authority escalation
```

---

# 174. Status Claim Review

Before publishing a current-state claim, ask:

```text
What exact evidence supports this?
Which revision/environment/scope?
How recent is it?
Is this target truth or current reality?
```

---

# 175. Full Governance Flow

```text
PRODUCT / ENGINEERING NEED
          │
          ▼
IDENTIFY CANONICAL AUTHORITY
          │
          ▼
CLASSIFY CHANGE / RISK
          │
          ▼
BOUND SCOPE
          │
          ▼
REQUIRED REVIEWS
          │
   ┌──────┼─────────────────────────────┐
   │      │        │       │            │
   ▼      ▼        ▼       ▼            ▼
Product Architecture Security Data   FinOps/Engineering
   │      │        │       │            │
   └──────┴────────┴───────┴────────────┘
          │
          ▼
IMPLEMENT / SPECIFY
          │
          ▼
TEST / EVALUATE
          │
          ▼
EVIDENCE
          │
          ▼
DECISION
          │
   ┌──────┼─────────┬──────────────────┐
   │      │         │                  │
   ▼      ▼         ▼                  ▼
REJECT  REVISE   APPROVE    BOUNDED EXCEPTION
                     │
                     ▼
          MERGE / RELEASE / DEPLOY
             ONLY IF AUTHORIZED
                     │
                     ▼
                  VERIFY
                     │
                     ▼
             AUDIT / SUPERSEDE
```

---

# 176. Governance Authority Map

```text
                        PRODUCT OWNER
                             │
                             ▼
                    PRODUCT REQUIREMENTS
                             │
             ┌───────────────┼───────────────┐
             │               │               │
             ▼               ▼               ▼
     ARCHITECTURE        SECURITY          DATA
        AUTHORITY        AUTHORITY       AUTHORITY
             │               │               │
             └───────────────┼───────────────┘
                             ▼
                     IMPLEMENTATION RULES
                             │
                             ▼
                     ENGINEERING CHANGE
                             │
                             ▼
                    TEST / EVALUATION
                             │
                             ▼
                         EVIDENCE
                             │
               ┌─────────────┼─────────────┐
               │             │             │
               ▼             ▼             ▼
            MERGE         RELEASE       EXCEPTION
               │             │             │
               └─────────────┼─────────────┘
                             ▼
                      DEPLOYMENT POLICY
                             │
                             ▼
                     APPROVAL IF REQUIRED
                             │
                             ▼
                         DEPLOYMENT
                             │
                             ▼
                        VERIFICATION
```

---

# 177. Governance Evidence Formula

```text
DECISION
+
AUTHORIZED ROLE
+
SCOPE
+
RATIONALE
+
REQUIRED REVIEWS
+
TEST / EVALUATION EVIDENCE
+
VERSION / REVISION
+
ADR / EXCEPTION IF APPLICABLE
=
GOVERNED CHANGE
```

---

# 178. Constitutional Governance Formula

```text
ONE CORE
+
ONE CONTROL PLANE
+
ONE POLICY AUTHORITY
+
ONE CAPABILITY REGISTRY
+
ONE ROUTING TRUTH
+
ONE EVIDENCE TRUTH
+
BOUNDED HUMAN / AGENT AUTHORITY
+
TRACEABLE DECISIONS
+
NO BYPASS
=
ILAIOS GOVERNANCE
```

---

# 179. Final Governance Invariant

The defining ILAIOS governance rule is:

> **No actor—human, agent, factory, worker, provider, tool, client, or external project—may create authority merely by being able to perform an action. Authority exists only when the canonical ILAIOS governance chain grants it.**

Therefore:

```text
Capability
≠ Authority

Implementation
≠ Approval

Test PASS
≠ Production Permission

Documentation
≠ Current Reality

Provider Availability
≠ Eligibility

Human Request
≠ Unlimited Scope

Agent Confidence
≠ Evidence
```

The canonical change sequence is:

```text
UNDERSTAND AUTHORITY
        ↓
BOUND THE CHANGE
        ↓
APPLY REQUIRED REVIEW
        ↓
TEST
        ↓
PRODUCE EVIDENCE
        ↓
AUTHORIZE
        ↓
EXECUTE
        ↓
VERIFY
```

**ILAIOS governance exists to make the system evolvable without making authority ambiguous.**
