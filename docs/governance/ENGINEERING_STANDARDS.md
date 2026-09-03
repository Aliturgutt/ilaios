# ILAIOS — ENGINEERING STANDARDS

**Document Type:** Canonical Engineering Standards  
**Format:** GitHub Markdown + ASCII workflow diagrams  
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
**Core Engineering Principle:** **SMALL, TRACEABLE, TESTED, REVIEWABLE CHANGES — NO ARCHITECTURE BYPASS**

> This document defines the canonical engineering standards for ILAIOS: coding discipline, repository structure, naming, ADRs, documentation, testing, quality gates, CI/CD, branch/commit/review/merge policy, versioning, release discipline, dependency management, security hygiene, observability obligations, and change evidence. It defines how engineers and autonomous development agents must change ILAIOS without fragmenting its architecture or weakening its controls.

---

# 00. Purpose

ILAIOS is a governed autonomous AI operating system.

Its engineering process must protect the same invariants as its runtime architecture.

Therefore engineering work must optimize for:

```text
correctness
clarity
traceability
security
testability
reviewability
reversibility
evidence
```

not merely speed.

The canonical engineering rule is:

```text
UNDERSTAND
    │
    ▼
BOUND THE CHANGE
    │
    ▼
IMPLEMENT
    │
    ▼
TEST
    │
    ▼
REVIEW
    │
    ▼
EVIDENCE
    │
    ▼
MERGE / RELEASE
```

No change may bypass architecture, policy, quality gates, or required evidence merely because the implementation appears obvious.

---

# 01. Scope

This document owns:

- coding standards;
- repository organization rules;
- naming standards;
- source layout principles;
- dependency discipline;
- configuration discipline;
- error-handling conventions;
- logging/telemetry engineering rules;
- ADR discipline;
- documentation standards;
- test-writing standards;
- quality gates;
- CI/CD engineering standards;
- branch policy;
- commit standards;
- review standards;
- merge standards;
- versioning;
- release policy;
- deprecation discipline;
- migration discipline;
- engineering evidence;
- autonomous-development guardrails;
- architecture drift prevention;
- maintenance standards.

This document does **not** own:

```text
system architecture
    → SYSTEM_ARCHITECTURE.md

product behavior
    → PRODUCT_REQUIREMENTS.md

implementation contracts
    → IMPLEMENTATION_SPEC.md

security controls
    → SECURITY_ARCHITECTURE.md

test acceptance criteria
    → TESTING_AND_EVALUATION.md

deployment topology
    → DEPLOYMENT_ARCHITECTURE.md

cost policy
    → FINOPS.md
```

---

# 02. Target Engineering Standard vs Current Repository Reality

This document defines what engineering work **must** conform to.

Current repository reality must be proven from:

```text
current source
current configuration
current tests
current CI
current branch protections
current review history
current release evidence
```

Therefore:

```text
standard documented
≠
standard currently enforced

quality gate listed
≠
quality gate currently passing

branch policy defined
≠
branch protection currently configured

release policy defined
≠
latest release complied
```

Mutable repository status belongs to current evidence and operational/governance status.

---

# 03. Engineering Constitutional Invariants

The following are mandatory:

```text
NO second Core
NO second Control Plane
NO second planner authority
NO second routing truth
NO second evidence truth
NO duplicate canonical capability identity
NO architecture rewrite for local convenience
NO direct factory → provider bypass
NO worker → unrestricted secret access
NO test weakening to manufacture PASS
NO silent security downgrade
NO unbounded retry/repair
NO undocumented breaking contract change
NO merge of failing required gates
NO current-state claim without evidence
```

---

# 04. Canonical Change Philosophy

Every change should be:

```text
bounded
minimal
additive where possible
backward-compatible where reasonable
explicit
testable
reversible where practical
evidence-producing
```

The preferred change is the smallest change that fully satisfies the requirement without creating hidden future debt.

---

# 05. Engineering Decision Order

When implementing a change:

```text
1. Read the canonical authority.
2. Identify the exact requirement.
3. Identify existing implementation ownership.
4. Identify dependencies.
5. Identify security/data/test obligations.
6. Reuse existing canonical capability boundaries.
7. Implement the minimal coherent change.
8. Test positive and negative behavior.
9. Review final diff.
10. Record evidence.
```

---

# 06. Core Evolution Rule

The ILAIOS Core is:

```text
FROZEN BY DEFAULT
EVOLVABLE BY PROOF
```

A Core change is justified only when evidence proves that a platform-wide invariant or canonical contract cannot be correctly implemented inside an existing governed capability boundary.

Core must not absorb:

```text
factory logic
provider-specific logic
model-specific logic
third-party behavior
UI behavior
domain-specific heuristics
replaceable integrations
```

for convenience.

---

# 07. Existing-Boundary-First Rule

Before creating a new module/service/capability, ask:

```text
Does an existing canonical owner already exist?
Can the requirement be implemented there?
Would a new component duplicate authority?
```

Default:

```text
EXTEND EXISTING CANONICAL OWNER
```

rather than:

```text
CREATE PARALLEL SYSTEM
```

---

# 08. Autonomous Development Agent Rule

Codex, Claude Code, Gemini CLI, OpenClaw, or any other development-time agent may assist engineering.

They are not engineering authorities.

They must obey:

```text
canonical docs
repository state
tests
CI
review
human/governance permissions
```

No autonomous development tool may:

```text
invent new architecture authority
weaken tests
bypass branch protection
merge failed checks
expose secrets
claim deployment without evidence
```

---

# 09. Engineering Change Contract

Every non-trivial change should be expressible as:

```text
Intent
Scope
Owned files/modules
Dependencies
Security impact
Data impact
API impact
Tests
Migration impact
Rollback
Evidence
```

---

# 10. 4.1 Coding Standards

## 10.1 Correctness First

Code must favor correctness and explicit invariants over cleverness.

Prefer:

```python
if grant.task_id != task.task_id:
    raise AuthorizationError(...)
```

over implicit assumptions.

---

## 10.2 Readability

Code should be readable without requiring hidden context.

Prefer:

```text
clear names
small focused functions
explicit contracts
predictable control flow
```

Avoid:

```text
deep hidden side effects
opaque metaprogramming
unnecessary abstraction layers
```

---

## 10.3 Single Responsibility

A module/class/function should have one coherent responsibility.

Bad:

```text
Router
    also authenticates
    also stores secrets
    also deploys
```

Good:

```text
Router
    produces canonical RoutingDecision
```

---

## 10.4 Authority Must Be Visible in Code

Security/authority decisions should be explicit.

Prefer:

```text
authorize()
validate_grant()
require_approval()
```

over hidden permission checks buried in unrelated utility functions.

---

## 10.5 Fail Closed

When mandatory context is absent:

```text
DENY / ERROR
```

not:

```text
assume default
```

Examples:

```text
missing tenant
missing grant
unknown capability
unsupported schema
unverified approval
```

---

## 10.6 Explicit State Machines

Authoritative lifecycle state must use explicit allowed transitions.

Do not scatter state mutation through arbitrary code.

Prefer:

```text
transition_job(...)
```

with validation.

---

## 10.7 Idempotency

Side-effecting operations must be idempotent where practical.

Especially:

```text
job creation
deploy
publish
payment
external send
artifact finalize
approval decision
```

---

## 10.8 Determinism

Deterministic logic should remain deterministic.

Examples:

```text
DAG validation
topological sort
route tie-break
budget calculations
state transitions
hashing
contract validation
```

Do not introduce model/non-deterministic calls into logic that should be deterministic.

---

## 10.9 Pure Logic Separation

Prefer separating:

```text
pure decision logic
from
I/O / side effects
```

This improves testability and auditability.

---

## 10.10 Side Effects

Side effects must be isolated behind explicit boundaries:

```text
Tool Gateway
Provider Adapter
Repository Connector
Deployment Adapter
Secret Manager
```

---

## 10.11 No Hidden Network Calls

A helper function should not unexpectedly call external services.

Network behavior must be explicit in naming/contracts.

---

## 10.12 No Hidden Provider Calls

Factories/skills/domain code must not directly create provider SDK clients outside canonical adapter boundaries.

---

## 10.13 No Hidden Secret Access

Secret access must be explicit and scoped.

Ordinary utility code must not casually read broad environment secrets.

---

## 10.14 Types

Use strong typing where language/tooling supports it.

For Python target code:

```text
type annotations
strict static checking for critical paths
explicit Optional/None semantics
typed domain contracts
```

---

## 10.15 Untyped Escape Hatches

Avoid:

```text
Any
type: ignore
dynamic dicts
unvalidated JSON
```

in critical cross-boundary code.

When necessary, document why and isolate the boundary.

---

## 10.16 Data Classes / Typed Models

Canonical records should use typed schema/model constructs appropriate to the language.

Examples:

```text
dataclass
TypedDict
Pydantic/model equivalent
Protocol/interface
```

depending on design.

---

## 10.17 Validation

Validate data:

```text
at external boundary
at persistence boundary
at cross-process boundary
```

Do not repeatedly re-validate trusted internal invariants unnecessarily, but never assume untrusted input is valid.

---

## 10.18 Exceptions

Exceptions should be:

```text
typed/classified
safe to handle
specific enough for retry/repair
```

Avoid broad:

```python
except Exception:
    pass
```

---

## 10.19 Error Swallowing

Never silently suppress a failure that affects:

```text
security
state
artifact integrity
evidence
cost
external side effect
```

---

## 10.20 Error Messages

Internal errors may contain diagnostic detail in protected telemetry.

Public errors must be safe.

Never expose:

```text
secret
token
raw credential
sensitive path
cross-tenant existence
```

---

## 10.21 Resource Cleanup

Use structured cleanup:

```text
context managers
finally
defer equivalents
```

for:

```text
files
network
locks
leases
temporary resources
```

---

## 10.22 Timeouts

All external calls must use explicit bounded timeout.

No infinite network wait.

---

## 10.23 Retries

Retry must be:

```text
bounded
classified
budget-aware
idempotency-aware
```

---

## 10.24 Backoff

Transient retries should use appropriate backoff/jitter where useful.

Do not create synchronized retry storms.

---

## 10.25 Concurrency

Concurrent code must document:

```text
ownership
locking/transaction model
ordering
idempotency
fencing
```

for authoritative state.

---

## 10.26 Race Conditions

Security/state critical code must be tested for race conditions.

Especially:

```text
budget reservation
worker leases
state transitions
approval consumption
artifact finalization
```

---

## 10.27 Cryptography

Do not invent cryptographic primitives.

Use vetted libraries and approved algorithms.

Cryptographic design changes require security review.

---

## 10.28 Randomness

Security-sensitive randomness must use cryptographically secure sources.

Test randomness should be deterministic/seeding-friendly when appropriate.

---

## 10.29 Time

Use UTC for authoritative machine timestamps.

Use monotonic clocks for elapsed-time measurement where appropriate.

Do not use wall-clock timestamps alone for distributed ordering.

---

## 10.30 Identifiers

Use canonical opaque IDs.

Do not embed:

```text
tenant secrets
privilege
business-sensitive meaning
```

inside IDs.

---

## 10.31 Numeric Money

Use:

```text
decimal/fixed point
minor units
```

for money.

Never authoritative floating-point financial arithmetic.

---

## 10.32 Serialization

Every durable/cross-process contract must define:

```text
version
types
required fields
optional fields
enum behavior
```

---

## 10.33 Backward Compatibility

Prefer additive changes:

```text
new optional field
new compatible endpoint
new capability
```

over breaking changes.

---

## 10.34 Deprecation

Deprecated code/contracts need:

```text
replacement
timeline/condition
migration
usage visibility
```

No permanent dead compatibility layer.

---

## 10.35 Comments

Comments explain:

```text
why
invariant
tradeoff
security rationale
```

not obvious syntax.

---

## 10.36 TODOs

TODO must include enough context to be actionable.

Prefer:

```text
TODO(owner/issue): reason and exit condition
```

Avoid permanent vague:

```text
TODO: fix later
```

---

## 10.37 Feature Flags

Feature-flagged code must:

```text
test both states
have owner
have retirement condition
```

No flag may disable constitutional security.

---

## 10.38 Configuration

Configuration must be:

```text
explicit
validated
versionable where material
environment-aware
```

Secrets are references, not normal config values.

---

## 10.39 Environment Variables

Use environment variables only for appropriate runtime configuration.

Do not use environment variables as an untyped dumping ground for complex policy.

---

## 10.40 Logging

Use structured logging.

Recommended fields:

```text
request_id
tenant-safe tenant/project IDs where permitted
job_id
task_id
capability_id
route_id
status
error_class
```

---

## 10.41 Logging Redaction

Never log:

```text
raw secret
auth token
private key
unnecessary protected payload
```

---

## 10.42 Metrics

Metrics labels must avoid high-cardinality/sensitive text.

Do not use:

```text
prompt
email
artifact text
```

as metric labels.

---

## 10.43 Tracing

Trace cross-service execution with stable IDs.

Do not make traces the sole evidence authority.

---

## 10.44 Security Comments

Critical authorization/security code should explain non-obvious invariants.

Example:

```text
# Fencing token must be checked atomically with authoritative commit.
```

---

## 10.45 Generated Code

AI-generated code is treated as untrusted engineering output until:

```text
reviewed
tested
security-checked
```

---

# 11. Language-Specific Python Standard

Where Python is used:

```text
PEP 8-compatible formatting
type annotations
mypy strict for canonical typed scope
ruff for linting
pytest for tests
```

Exact tool versions are repository configuration.

---

# 12. Python Imports

Prefer:

```text
standard library
third-party
local
```

with no circular import architecture.

Imports should reflect dependency direction.

---

# 13. Python Public API

Modules should expose deliberate public interfaces.

Avoid cross-module dependence on private implementation names.

---

# 14. Python Mutable Defaults

Never use unsafe mutable default arguments.

---

# 15. Python Dataclass Immutability

Use frozen/immutable models where domain semantics benefit:

```text
RoutingDecision
PolicyDecision
ArtifactVersion metadata
```

---

# 16. Python Async

Async functions must avoid blocking I/O on event loop.

Use explicit concurrency limits.

---

# 17. Python Subprocess

Prefer argument arrays.

Avoid shell interpolation.

Use:

```python
subprocess.run([...], check=True, timeout=...)
```

or equivalent safe abstraction.

---

# 18. Python Path Handling

Use `pathlib` or safe normalized path APIs.

Validate workspace boundary before file access.

---

# 19. 4.2 Repository Management and Naming Standards

Repository structure must make ownership clear.

Canonical top-level categories may include:

```text
src/
services/
tests/
docs/
scripts/
infra/
```

Exact tree may evolve.

Directory creation must reflect real ownership, not arbitrary grouping.

---

# 20. Repository Naming Principles

Names should be:

```text
descriptive
stable
lowercase where convention requires
consistent
non-duplicative
```

Avoid vague:

```text
utils2
new_core
misc
temp_final
router_v2
```

---

# 21. Canonical Capability Naming

Capability IDs use:

```text
ilaios.capability.*
```

Examples:

```text
ilaios.capability.core
ilaios.capability.provider-routing
ilaios.capability.web-factory
```

---

# 22. Module Naming

Module names should reflect capability responsibility.

Examples:

```text
routing.py
policy.py
evidence.py
checkpoint.py
```

Avoid names that imply authority the module does not own.

---

# 23. Service Naming

A service name must correspond to one logical responsibility.

Do not call a provider adapter:

```text
control-plane
```

or a UI:

```text
runtime
```

---

# 24. File Naming

Use consistent project-language conventions.

Canonical documentation names are exact and stable.

Do not create duplicate canonical docs with suffixes such as:

```text
_FINAL
_NEW
_v2
_latest
```

unless versioning policy explicitly requires separate published versions.

---

# 25. Canonical Documentation Location

Canonical documentation should live in governed documentation locations and maintain one authority per concern.

No duplicate architecture truth.

---

# 26. Test File Naming

Tests should map clearly to production behavior.

Examples:

```text
test_routing.py
test_policy_gateway.py
test_tenant_isolation.py
```

---

# 27. Fixture Naming

Fixture names describe intent/scope.

Example:

```text
tenant_a_project
expired_execution_grant
stale_worker_lease
```

---

# 28. Branch Naming

Suggested focused branch patterns:

```text
feature/<scope>
fix/<scope>
docs/<scope>
security/<scope>
refactor/<scope>
```

Exact prefixes are governance configuration.

---

# 29. No Long-Lived Parallel Mainline

Do not maintain:

```text
master
and
master-v2
```

as competing product truths.

---

# 30. Generated Files

Generated files should:

```text
be clearly marked
have reproducible generation path
not be hand-edited if regenerated
```

---

# 31. Binary Artifacts

Large build/render artifacts should not be committed unless repository policy explicitly requires them.

Use artifact/object storage or release assets where appropriate.

---

# 32. Secrets in Repository

Forbidden:

```text
API keys
tokens
private keys
production credentials
```

Use secret management.

---

# 33. Sample Configuration

Use safe placeholders:

```text
YOUR_API_KEY
example.invalid
localhost
```

Never live credentials.

---

# 34. Dependency Lockfiles

Applications/services should use lockfiles where ecosystem supports them.

Lockfile changes require review.

---

# 35. Vendoring

Vendored third-party code requires:

```text
license
provenance
reason
update process
security review
```

---

# 36. 4.3 Architecture Decision Records (ADR)

ADR records significant architectural decisions.

Use ADR when a change affects:

```text
authority
major dependency
cross-service contract
data ownership
security model
deployment model
provider abstraction
irreversible technology choice
```

---

# 37. ADR Is Not a Status Report

ADR answers:

```text
What did we decide?
Why?
What alternatives were rejected?
What consequences follow?
```

It does not prove implementation.

---

# 38. ADR Minimum Structure

```markdown
# ADR-XXXX — Title

Status:
Date:
Decision Owners:

## Context
## Decision
## Alternatives
## Consequences
## Security / Data Impact
## Migration
## Verification
## Supersedes / Superseded By
```

---

# 39. ADR Status

Recommended:

```text
PROPOSED
ACCEPTED
SUPERSEDED
DEPRECATED
REJECTED
```

These are ADR lifecycle states, not capability maturity.

---

# 40. ADR Numbering

Use stable monotonic ID.

Never reuse old ADR number for unrelated decision.

---

# 41. ADR Supersession

New decision does not erase history.

Use:

```text
ADR-001 superseded by ADR-027
```

---

# 42. ADR Scope

Small local implementation detail does not require ADR.

Avoid ADR noise.

---

# 43. Core ADR Requirement

Any approved Core evolution must have ADR/equivalent governance evidence.

---

# 44. Routing ADR Requirement

Any change creating/merging routing authority requires ADR.

---

# 45. Data Ownership ADR

Moving authoritative data between stores/services requires ADR if architecture-impacting.

---

# 46. Security ADR

Material security model changes require ADR and threat review.

---

# 47. 4.4 Documentation Standards

Documentation is part of the product engineering system.

Required properties:

```text
accurate
scoped
version-aware
non-duplicative
traceable
```

---

# 48. Documentation Authority

Each concern has one canonical owner.

Do not repeat large normative sections across many files.

Use references.

---

# 49. Normative Language

Use:

```text
MUST
MUST NOT
SHOULD
MAY
```

consistently when prescribing requirements.

---

# 50. Target vs Current Reality

Every canonical architecture/specification document must distinguish:

```text
what should be true
vs
what is currently evidenced
```

---

# 51. No Mutable Current State in Canonical Architecture

Avoid embedding:

```text
current PR number
current branch HEAD
current live status
current selected workstream
current provider health
```

inside timeless canonical architecture unless clearly non-authoritative example.

---

# 52. Examples

Examples must be marked as examples.

Example numeric values must not become accidental policy.

---

# 53. Diagrams

ASCII diagrams are preferred when they improve portability/readability.

Diagrams must not contradict prose.

---

# 54. Links

Canonical docs should link to authoritative related documents.

Avoid broken/duplicate links.

---

# 55. Code Examples

Code examples must:

```text
be syntactically plausible
avoid real secrets
avoid unsafe patterns
match contract semantics
```

---

# 56. Documentation Review

Architecture-affecting code changes must update relevant docs in same change where feasible.

---

# 57. Documentation Tests

Where practical, automate:

```text
link checks
filename checks
duplicate canonical authority checks
schema example validation
```

---

# 58. README Role

README is orientation.

README must not replace detailed canonical documents.

---

# 59. Changelog / Release Notes

Release notes describe user/developer-visible change.

They are not architecture authority.

---

# 60. Comments vs Documentation

Source comments explain local implementation.

Canonical docs explain platform contract/architecture.

Do not bury critical architecture only in code comments.

---

# 61. 4.5 Testing Standards

All behavior changes require appropriate tests.

The testing authority remains `TESTING_AND_EVALUATION.md`.

Minimum principle:

```text
positive test
+
negative test where authority/security relevant
```

---

# 62. Test Behavior, Not Implementation Trivia

Prefer:

```text
cross_tenant_read_is_denied
```

over:

```text
method_called_three_times
```

unless call count is the contract.

---

# 63. Test Determinism

Tests should be deterministic.

Flaky tests are defects.

---

# 64. Test Independence

Tests should not depend on:

```text
execution order
shared mutable global state
production account state
```

unless explicitly integration testing such systems.

---

# 65. Unit Test Standard

Unit tests:

```text
fast
isolated
deterministic
```

---

# 66. Contract Test Standard

Every cross-boundary schema needs producer/consumer compatibility tests.

---

# 67. Integration Test Standard

Integration tests exercise real platform boundaries.

---

# 68. Security Test Standard

Security-critical changes require negative tests.

---

# 69. Tenant Test Standard

Every data/retrieval/artifact feature touching tenant data must include cross-tenant negative coverage.

---

# 70. E2E Standard

A canonical E2E must exercise:

```text
Control Plane
Policy
Routing where applicable
Scheduler/Worker
Tool/Provider boundary
Evidence
```

No hidden bypass.

---

# 71. AI Output Tests

Avoid exact-string tests for inherently non-deterministic output.

Test:

```text
schema
required facts
forbidden behavior
acceptance rubric
```

---

# 72. Golden Tests

Each factory should maintain representative golden workflows.

---

# 73. Regression Tests

Every meaningful defect fix should add regression coverage when practical.

---

# 74. Test Data

Use synthetic/controlled data.

Never casually use real production customer data.

---

# 75. Test Secrets

Use fake credentials.

Never real production secrets.

---

# 76. Test Timeouts

Every integration/E2E/external test must be bounded.

---

# 77. Test Retry

Do not rerun failing tests until green as a quality strategy.

---

# 78. Flake Quarantine

Quarantine requires:

```text
owner
reason
impact
exit condition
```

Required security tests cannot be silently quarantined.

---

# 79. Coverage

Coverage metrics inform quality.

They do not prove correctness.

---

# 80. 4.6 Quality Gates

Quality gates are mandatory for applicable changes.

Baseline repository gates may include:

```text
python -m pytest -q
ruff check .
mypy --strict src tests
pre-commit run --all-files
git diff --check
```

The repository configuration is the source of current executable details.

Listing a command does not prove PASS.

---

# 81. Gate Categories

```text
syntax/build
format
lint
type
unit
contract
integration
security
dependency
E2E
artifact/evidence
```

---

# 82. Required Gate Integrity

Never remove/weaken a required gate to merge a change.

A gate change must be reviewed as a product/security change.

---

# 83. Impact-Based Gate Selection

Not every tiny documentation change must run every expensive E2E.

But required gates must follow a documented impact strategy.

---

# 84. Security-Critical Change Gate

Security-critical changes should run:

```text
relevant unit
contract
integration
negative
security
E2E
```

---

# 85. Core Change Gate

Core changes require widest relevant regression suite.

---

# 86. Dependency Change Gate

Dependency updates require:

```text
build
tests
security scanning
license/provenance review
```

where applicable.

---

# 87. Migration Gate

Schema/data migrations require:

```text
migration test
backward compatibility
rollback/forward-fix plan
tenant preservation
```

---

# 88. Documentation Gate

Canonical docs must be internally consistent before PASS.

---

# 89. Gate Evidence

Record:

```text
command/suite
revision
environment
result
```

---

# 90. 4.7 CI/CD Standards

CI/CD is a controlled execution system.

It must not become a privileged bypass.

---

# 91. CI Principle

```text
SOURCE
  │
  ▼
BUILD
  │
  ▼
TEST
  │
  ▼
VERIFY
  │
  ▼
ARTIFACT
```

---

# 92. CI Reproducibility

Use:

```text
pinned runtime versions
lockfiles
reproducible commands
clean environment
```

where practical.

---

# 93. CI Least Privilege

CI tokens must have minimum required permissions.

---

# 94. Pull Request Secrets

Untrusted PR/fork code must not automatically receive production secrets.

---

# 95. CI Dependency Pinning

Third-party CI actions/tools should be pinned according to security policy.

---

# 96. CI Artifacts

Build/test artifacts should be:

```text
versioned
traceable
retained according to policy
```

---

# 97. CI Failure

Required gate failure blocks merge/release.

No silent bypass.

---

# 98. CI Infrastructure Failure

Distinguish from product test failure.

Rerun allowed only with transparent reason/evidence.

---

# 99. CD Principle

Deployment is a governed side effect.

CI success does not itself authorize production deployment.

---

# 100. Production CD

Canonical:

```text
CI PASS
   │
   ▼
VERIFIED ARTIFACT
   │
   ▼
DEPLOYMENT POLICY
   │
   ▼
APPROVAL IF REQUIRED
   │
   ▼
DEPLOY
   │
   ▼
HEALTH VERIFY
```

---

# 101. Build Once Promote

Prefer one immutable artifact promoted across environments.

---

# 102. Protected Environments

Production deployment credentials/settings should be environment-protected.

---

# 103. Deployment Identity

Use dedicated service/workload identity.

Never personal developer credential as default automation identity.

---

# 104. Release Provenance

Release should trace:

```text
commit
build
tests
artifact digest
approval
deployment
```

---

# 105. CI/CD Audit

Material workflow/config changes require review.

---

# 106. 4.8 Branch, Commit, Review, Merge Standards

## Branching

Default workflow:

```text
master/main canonical branch
        │
        ▼
focused branch
        │
        ▼
bounded change
        │
        ▼
tests
        │
        ▼
review / PR
        │
        ▼
merge
```

Exact branch name is repository configuration.

---

# 107. Focused Branch

One branch should represent one coherent change.

Avoid mixing:

```text
architecture
feature
formatting
dependency update
unrelated cleanup
```

unless inherently linked.

---

# 108. Small Diff Preference

Prefer reviewable diffs.

A large change should be decomposed when doing so preserves architectural coherence.

---

# 109. Atomic Commits

Commits should represent logical steps.

Avoid:

```text
"misc"
"stuff"
"final"
"fix again"
```

---

# 110. Commit Message

Recommended:

```text
<scope>: <imperative summary>
```

Examples:

```text
routing: enforce canonical route decision
security: reject stale execution grants
docs: define tenant isolation contract
```

---

# 111. Commit Content

A commit should not knowingly include:

```text
secret
debug file
temporary artifact
unrelated formatting
```

---

# 112. Review Before Commit/Push

Inspect:

```text
git diff
git diff --check
changed files
unexpected generated artifacts
secret risk
```

---

# 113. Pull Request Description

Should state:

```text
Problem
Change
Why
Architecture impact
Security/data impact
Tests
Evidence
Migration
Rollback
```

---

# 114. Reviewer Goal

Review asks:

```text
Is requirement satisfied?
Is change in correct owner boundary?
Any architecture bypass?
Any security/data regression?
Are tests sufficient?
Is diff minimal?
```

---

# 115. Architecture Review

Required when change affects:

```text
Core
Control Plane
Routing
Policy
tenant isolation
cross-service contract
data ownership
deployment topology
```

---

# 116. Security Review

Required for:

```text
identity
authorization
secrets
network
sandbox
provider data
tenant boundary
high-risk tools
```

---

# 117. Review of Generated Code

AI-generated code receives the same review standard.

No special trust.

---

# 118. Self-Review

Author performs final self-review before requesting merge.

---

# 119. Merge Requirements

Merge only when:

```text
required reviews satisfied
required checks PASS
no unresolved blocking feedback
diff scope understood
```

---

# 120. No Bypass Merge

Do not merge:

```text
failed required check
security-critical unresolved issue
known tenant isolation regression
```

without explicit governed exception.

---

# 121. Merge Strategy

Repository may use:

```text
squash
merge commit
rebase
```

according to governance.

History should remain understandable.

---

# 122. Force Push

Avoid force push to protected canonical branch.

Branch force-push policy should be explicit.

---

# 123. Direct Push

Direct push to canonical branch should be restricted according to governance.

---

# 124. Emergency Merge

Emergency path still requires:

```text
documented reason
minimum safe tests
evidence
follow-up review
```

---

# 125. 4.9 Versioning Standards

Version every public/durable contract where breaking change is possible.

Version domains include:

```text
API
event schema
artifact metadata
evidence schema
skill
agent manifest
capability descriptor
policy
data migration
release
```

---

# 126. Semantic Versioning

Use SemVer where it correctly models compatibility.

```text
MAJOR
MINOR
PATCH
```

Exact product release scheme may extend SemVer.

---

# 127. Contract Versioning

Breaking contract changes require:

```text
new major/schema version
migration
compatibility window
consumer updates
```

---

# 128. Internal Versioning

Internal contracts also need versioning when persisted or cross-process.

---

# 129. Artifact Version

Artifact version identifies immutable output.

Do not overwrite validated artifact bytes under same version.

---

# 130. Skill Version

Skill changes that affect behavior/permissions require version/digest change.

---

# 131. Agent Version

AgentManifest changes affecting authority/behavior require versioning.

---

# 132. Policy Version

Material PolicyDecision must reference exact policy version.

---

# 133. Pricing Version

FinOps cost decisions reference pricing version when material.

---

# 134. Schema Version

Durable schemas require explicit version.

---

# 135. Deprecation

Deprecation plan includes:

```text
replacement
announcement/documentation
migration
telemetry/usage visibility
removal condition
```

---

# 136. Compatibility Window

Temporary dual-read/write or multi-version support must have retirement condition.

---

# 137. Version Truth

Repository version, artifact version, deployment version, and current runtime version are distinct facts.

---

# 138. 4.10 Release Policy and Standards

A release is a governed packaging/promotion event.

It requires:

```text
known revision
verified artifact
required test evidence
security status
release notes
deployment/promotion plan
rollback plan
```

---

# 139. Release Types

Possible categories:

```text
development snapshot
pre-release
candidate
stable
security patch
hotfix
```

Exact labels are product governance.

---

# 140. Release Candidate

A release candidate is not production until deployment/promotion occurs.

---

# 141. Release Checklist

```text
[ ] scope finalized
[ ] canonical docs updated
[ ] tests PASS
[ ] security gates PASS
[ ] artifact built
[ ] artifact hash recorded
[ ] migration reviewed
[ ] release notes ready
[ ] rollback path known
[ ] approvals satisfied
```

---

# 142. Release Notes

Describe:

```text
user-visible changes
developer-visible changes
breaking changes
migrations
known issues
```

---

# 143. Security Release

Security patches may limit vulnerability disclosure until safe release.

But internal evidence/review remains required.

---

# 144. Hotfix

Hotfix path minimizes process only as necessary for urgency.

It does not waive:

```text
security
tenant isolation
evidence
post-release verification
```

---

# 145. Production Promotion

Production promotion follows `DEPLOYMENT_ARCHITECTURE.md`.

---

# 146. Rollback

Release must define rollback or justified forward-fix path.

---

# 147. Release Tagging

Tags/releases should reference immutable source revision.

---

# 148. Release Signing

Use signing where product/distribution requirements justify it.

Signing key remains protected.

---

# 149. SBOM / Provenance

Release may include SBOM/provenance for supply-chain assurance.

Enterprise/security-critical releases should increasingly adopt these controls.

---

# 150. Dependency Management

Every new dependency must answer:

```text
Why needed?
Can standard library/existing dependency solve it?
License?
Maintenance health?
Security?
Supply-chain risk?
Size/runtime impact?
```

---

# 151. Minimal Dependency Principle

Do not add a dependency for trivial functionality.

Each dependency increases:

```text
attack surface
maintenance
build complexity
license complexity
```

---

# 152. Dependency Source

Use trusted registries/sources.

Avoid unverified package URLs.

---

# 153. Dependency Pinning

Pin versions/lock according to ecosystem.

---

# 154. Dependency Updates

Updates require:

```text
release notes review
security advisories
tests
compatibility
```

---

# 155. Major Dependency Upgrade

Major version upgrade requires migration/review plan.

---

# 156. Transitive Dependencies

Security review considers transitive dependencies.

---

# 157. License

Dependency license must be compatible with ILAIOS distribution/use.

---

# 158. Abandoned Dependency

Avoid critical dependency with unacceptable maintenance/security risk unless governed exception exists.

---

# 159. External Open-Source Assimilation

Default:

```text
REFERENCE
→ REQUIREMENT EXTRACTION
→ ILAIOS-NATIVE IMPLEMENTATION
```

not direct permanent dependency.

---

# 160. Supply-Chain Review

For external code:

```text
source
commit/tag
license
install behavior
network behavior
credential behavior
dependencies
update mechanism
```

---

# 161. Model Dependency

Downloaded local models require provenance/hash/license review.

---

# 162. Container Dependency

Production images should be minimal, pinned, scanned.

---

# 163. CI Action Dependency

Third-party workflow actions should be pinned according to security policy.

---

# 164. Security Engineering Standard

Security is part of engineering, not a final review phase.

Every change asks:

```text
Does this expand authority?
Does this expose data?
Does this change tenant scope?
Does this add network?
Does this add secret?
Does this add side effect?
```

---

# 165. Threat Model Update Trigger

Update `THREAT_MODEL.md` when change introduces:

```text
new trust boundary
new tool
new provider
new data class
new auth method
new external side effect
new deployment topology
```

---

# 166. Secrets Engineering Standard

Use:

```text
secret reference
vault/key manager
scoped runtime injection
```

---

# 167. Secret Leak Response

If secret reaches repository/log:

```text
revoke/rotate
remove exposure where feasible
audit impact
add regression prevention
```

Removing the text alone is not enough.

---

# 168. Security Test Standard

Every security fix should add regression coverage when possible.

---

# 169. Secure Defaults

Defaults should be:

```text
deny
private
least privilege
non-production
bounded
```

---

# 170. Dependency Security

Automate vulnerability scanning where practical.

A scanner PASS does not prove dependency safe.

---

# 171. Data Engineering Standard

Every protected record should have:

```text
owner/scope
tenant
project where applicable
classification
lifecycle
provenance where applicable
```

---

# 172. Schema Change Standard

Schema change requires:

```text
migration
compatibility
tests
rollback/forward-fix
```

---

# 173. No Silent Data Rewrite

Material historical records such as:

```text
evidence
approval
routing decision
artifact version
```

must not be silently rewritten.

---

# 174. Tenant Migration Standard

Data migration must preserve tenant/project identity.

---

# 175. Data Deletion Engineering

Deletion includes derived data/indexes.

Do not delete required evidence improperly.

---

# 176. API Engineering Standard

Public APIs remain Control Plane-facing.

Do not expose internal privileged contracts casually.

---

# 177. API Compatibility

Public breaking change requires version/migration.

---

# 178. API Error Stability

Machine-readable error codes should remain stable.

---

# 179. API Idempotency

Replay-sensitive mutations support idempotency.

---

# 180. API Pagination

Use stable cursor pagination for scalable lists.

---

# 181. API Authorization

Every protected route validates:

```text
Principal
Tenant
Project/resource
Action
```

server-side.

---

# 182. Runtime Engineering Standard

Runtime code must preserve:

```text
durable state
leases
fencing
bounded retry
checkpoint
cancellation
```

---

# 183. Worker Engineering Standard

Worker code must assume:

```text
input untrusted
tool/provider output untrusted
grant bounded
lease temporary
```

---

# 184. Scheduler Engineering Standard

Scheduler assigns work.

It does not expand permissions.

---

# 185. Routing Engineering Standard

One canonical RoutingDecision.

Any routing-related change must preserve deterministic/no-bypass tests.

---

# 186. Provider Adapter Standard

Provider-specific SDK logic stays behind adapter.

Normalize:

```text
request
response
errors
usage
```

---

# 187. Tool Adapter Standard

Tool adapters must not perform actions outside ToolRequest/ExecutionGrant.

---

# 188. Knowledge Engineering Standard

Knowledge/RAG must preserve:

```text
tenant
project
source version
classification
authorization
provenance
```

---

# 189. Artifact Engineering Standard

Artifacts are versioned/hashed.

Validation points to exact version.

---

# 190. Evidence Engineering Standard

Evidence must be:

```text
structured
traceable
integrity-aware
privacy-aware
```

---

# 191. Evaluation Engineering Standard

Producer and verifier separation where meaningful.

AI evaluator is not authority.

---

# 192. FinOps Engineering Standard

Every paid provider/tool path produces usage attribution.

Retry/repair use same budget envelope.

---

# 193. Observability Engineering Standard

Every production service should expose suitable:

```text
logs
metrics
traces
health
```

without leaking secrets.

---

# 194. Health Endpoint Standard

Health endpoints must be safe and scoped.

Do not expose sensitive dependency details publicly.

---

# 195. SLO Engineering

Engineering decisions should respect SLOs defined by operations/governance.

---

# 196. Performance Engineering

Measure before optimizing.

Do not trade away correctness/security for micro-optimizations.

---

# 197. Optimization Standard

Optimization must preserve tests and invariants.

Benchmark before/after.

---

# 198. Refactoring Standard

Refactor means behavior-preserving unless explicitly part of feature change.

Tests prove preservation.

---

# 199. Large Refactor

Large refactors need:

```text
bounded phases
compatibility
migration
architecture review
```

---

# 200. Dead Code

Remove dead code when safe.

Do not preserve obsolete parallel authorities “just in case”.

---

# 201. Legacy Code

Legacy compatibility must be explicit.

Historical names may remain provenance-only, not active authority.

---

# 202. Technical Debt

Debt must be:

```text
visible
owned
scoped
prioritized
```

Do not hide security debt inside TODO comments.

---

# 203. Code Ownership

Critical components should have explicit logical ownership.

Examples:

```text
Core
Policy
Routing
Evidence
Identity
```

---

# 204. Review Ownership

Sensitive changes require appropriate reviewers/owners.

In small teams/solo-founder context, roles may be logically separated but evidence remains explicit.

---

# 205. Autonomous Merge Guardrail

An automation may merge only if governance explicitly allows and all required checks/conditions are satisfied.

No test/branch protection bypass.

---

# 206. Repository Evidence

Every completed engineering change should be able to identify:

```text
base revision
branch
commits
diff
tests
CI
review
merge commit/revision
```

---

# 207. Change Evidence Record

Conceptual:

```yaml
change_id: "change_..."
base_revision: "..."
head_revision: "..."
scope: "..."
requirements: []
files_changed: []
tests: []
ci_runs: []
reviews: []
security_impact: "..."
migration_ref: null
release_ref: null
```

---

# 208. Engineering PASS

A change may be considered engineering PASS when:

```text
requirement satisfied
architecture respected
tests applicable PASS
quality gates PASS
final diff reviewed
evidence complete
```

---

# 209. Engineering VERIFIED

For capability/platform claims, `VERIFIED` additionally follows `TESTING_AND_EVALUATION.md`.

Engineering PASS for a change is not automatically capability VERIFIED.

---

# 210. Documentation PASS

A canonical document PASS means:

```text
internally consistent
aligned with higher authority
no known material contradiction
```

It does not mean implementation exists.

---

# 211. Current-State Claim Standard

When reporting current state, cite/record evidence.

Never say:

```text
"production ready"
```

because a design doc says so.

---

# 212. Status Language

Use precise statements:

```text
DESIGNED
SPECIFIED
IMPLEMENTED
TESTED
VERIFIED
DEPLOYED / PRODUCTION
```

for capability maturity.

Use operational status separately.

---

# 213. No “Done” Without Scope

Prefer:

```text
"Provider adapter VERIFIED for text-generation scope"
```

over:

```text
"Provider done"
```

---

# 214. Engineering Incident Feedback

Production defects should feed:

```text
regression tests
threat model
failure recovery
engineering standards
```

where applicable.

---

# 215. Post-Incident Change

Avoid rushing broad unrelated cleanup into incident fix.

First restore safely.

Then improve separately.

---

# 216. Break-Glass Engineering Change

Emergency change still records:

```text
reason
scope
tests
approval
deployment
follow-up
```

---

# 217. Maintenance Windows

Operational policy may define windows.

Engineering architecture remains same.

---

# 218. Dependency Removal

When removing dependency:

```text
remove usage
remove config
revoke secrets
update docs
run tests
```

---

# 219. Provider Removal

Preserve historical evidence/IDs.

Disable future routing.

---

# 220. Feature Removal

Removal requires:

```text
usage/deprecation review
migration
data handling
documentation
```

---

# 221. Capability Deprecation

`DEPRECATED` is lifecycle exit.

It does not appear in maturity progression.

---

# 222. Engineering Maturity

Engineering process itself should improve through:

```text
automation
faster tests
stronger typing
better observability
better evidence
```

without adding bureaucracy that does not reduce risk.

---

# 223. Complexity Budget

Every abstraction has maintenance cost.

Prefer fewer clear concepts over many thin wrappers.

---

# 224. Architecture Complexity

Do not solve local problems by creating platform-wide new authorities.

---

# 225. Dependency Direction

Dependency direction follows canonical architecture.

Higher-level domain code may depend on platform contracts.

Platform authority must not depend on domain/factory implementation.

---

# 226. Circular Dependencies

Avoid code/package cycles.

Architecture-level authority cycles are forbidden.

---

# 227. Interface Segregation

Consumers should depend on narrow contracts.

Avoid giant service interfaces granting unrelated capabilities.

---

# 228. Dependency Injection

Use dependency injection/interfaces where it improves:

```text
testing
provider replaceability
tool replaceability
```

Do not overengineer simple logic.

---

# 229. Factory Standard

Factories:

```text
compose domain DAG
declare capabilities
define quality gates
produce artifacts
```

Factories do not own runtime authority.

---

# 230. Skill Standard

Skills are bounded expertise.

They do not own credentials or authority.

---

# 231. Agent Standard

Agents coordinate.

They do not mint permission.

---

# 232. Provider Standard

Providers execute replaceable resource calls.

They do not own product semantics.

---

# 233. Worker Standard

Workers perform scoped task execution.

They do not own policy/routing truth.

---

# 234. Client Standard

Clients project state and collect user intent.

They do not own authoritative job state.

---

# 235. Code Review Red Flags

Reviewers should immediately question:

```text
new "core" directory
new router class
provider SDK inside factory
tenant_id trusted from client
raw env secret access
catch-all exception swallowing
disabled test
skipped required check
unbounded while retry
artifact overwrite
```

---

# 236. Pull Request Red-Team Questions

Ask:

```text
Could this create second authority?
Can tenant boundaries be crossed?
Can untrusted content gain permission?
Can retry exceed budget?
Can stale worker commit?
Can secrets leak?
Can current-state claims become stale?
```

---

# 237. Merge Blockers

Block merge for:

```text
known tenant isolation defect
known auth bypass
failed required gate
unreviewed breaking contract
secret leak
architecture authority duplication
```

---

# 238. Quality Culture

Quality is not:

```text
more files
more abstractions
more tests by count
```

Quality is:

```text
correct requirements
clear ownership
sufficient tests
safe failure
traceable evidence
```

---

# 239. Change Completeness Checklist

```text
[ ] Requirement identified
[ ] Higher-authority docs read
[ ] Correct owner boundary used
[ ] No duplicate authority
[ ] API impact assessed
[ ] Data impact assessed
[ ] Security impact assessed
[ ] FinOps impact assessed
[ ] Migration assessed
[ ] Tests added/updated
[ ] Negative tests added where required
[ ] Quality gates run
[ ] Final diff reviewed
[ ] Docs updated
[ ] Evidence recorded
```

---

# 240. Core Change Checklist

```text
[ ] Existing capability cannot correctly own requirement
[ ] Platform-wide invariant demonstrated
[ ] ADR
[ ] Architecture review
[ ] Security review
[ ] Dependency review
[ ] Broad regression
[ ] No second Core
```

---

# 241. Provider Integration Checklist

```text
[ ] ProviderDescriptor
[ ] Adapter boundary
[ ] Secrets scoped
[ ] Privacy/residency
[ ] Routing integration
[ ] Error normalization
[ ] Usage/FinOps
[ ] Tests
[ ] Fallback
[ ] Evidence
```

---

# 242. Tool Integration Checklist

```text
[ ] ToolDescriptor
[ ] ToolRequest/ToolResult
[ ] ExecutionGrant
[ ] Permission scope
[ ] Secret scope
[ ] Filesystem scope
[ ] Network scope
[ ] Sandbox
[ ] Tests
[ ] Evidence
```

---

# 243. Knowledge/RAG Checklist

```text
[ ] Tenant/project metadata
[ ] Source version
[ ] Classification
[ ] Authorization-aware retrieval
[ ] Provenance
[ ] Prompt injection tests
[ ] Deletion propagation
[ ] Negative isolation tests
```

---

# 244. Factory Checklist

```text
[ ] Canonical capability ID
[ ] Correct dependencies
[ ] Shared runtime
[ ] No private router
[ ] No private policy
[ ] Artifact contract
[ ] Validation
[ ] Bounded repair
[ ] Evidence
[ ] E2E
```

---

# 245. Release Checklist — Engineering

```text
[ ] Source revision fixed
[ ] Tests PASS
[ ] Required CI PASS
[ ] Security gate PASS
[ ] Artifact digest
[ ] Release notes
[ ] Migration plan
[ ] Rollback
[ ] Approval
[ ] Deployment evidence path
```

---

# 246. Engineering Anti-Patterns

Forbidden/rejected patterns:

```text
God module
parallel Core
parallel router
utility dumping ground
provider SDK everywhere
raw SQL with tenant omitted
silent exception
global mutable state
shared production secrets
test-only security bypass
magic environment behavior
copy-pasted contract schemas
manual current-status claims
```

---

# 247. “Just Temporary” Rule

Temporary bypasses frequently become permanent.

Any temporary workaround requires:

```text
owner
reason
scope
expiration/removal condition
test ensuring no expansion
```

---

# 248. Prototype vs Production

Prototype code may relax some engineering ergonomics.

It may not be mislabeled production.

Promotion requires standards/tests appropriate to production scope.

---

# 249. Experimental Capability

Experimental capability must still preserve:

```text
tenant isolation
auth
policy
secret safety
```

Feature maturity does not waive constitutional controls.

---

# 250. Sandbox/Research Code

Keep research/prototype code clearly isolated from production execution path.

---

# 251. Generated Migration

Generated migration must be reviewed.

Generated does not mean safe.

---

# 252. Generated Configuration

AI-generated IaC/configuration must pass validation/security review.

---

# 253. Generated Tests

AI-generated tests must be reviewed for:

```text
real assertion
requirement coverage
false positives
test weakening
```

---

# 254. Test-Driven Security

For security invariants, write failing negative test before/with fix when practical.

---

# 255. Architecture-Driven Development

Implementation follows:

```text
architecture
→ contracts
→ dependency graph
→ code
```

not code-first authority invention.

---

# 256. Evidence-Driven Completion

Completion statements must use evidence:

```text
tests
CI
runtime
deployment
```

according to claim.

---

# 257. No Completion by Documentation

A canonical document cannot prove feature completion.

---

# 258. Engineering Definition of Done — Code Change

A code change is complete when:

```text
scope correct
code implemented
tests appropriate PASS
quality gates PASS
docs updated
diff reviewed
evidence available
```

---

# 259. Engineering Definition of Done — Security Change

Adds:

```text
threat mapping
negative tests
no regression
security evidence
```

---

# 260. Engineering Definition of Done — API Change

Adds:

```text
schema/version
compatibility
contract tests
docs
```

---

# 261. Engineering Definition of Done — Data Change

Adds:

```text
migration
tenant preservation
rollback/forward-fix
data tests
```

---

# 262. Engineering Definition of Done — Infrastructure Change

Adds:

```text
IaC/config diff
security
deployment test
rollback
deployment evidence
```

---

# 263. Engineering Definition of Done — Dependency Update

Adds:

```text
provenance/license
security
compatibility
tests
```

---

# 264. Engineering Definition of Done — Canonical Document

Requires:

```text
authority alignment
internal consistency
no duplicate truth
correct target/current separation
review
```

---

# 265. Canonical Engineering Workflow

```text
REQUEST / REQUIREMENT
        │
        ▼
READ CANONICAL AUTHORITIES
        │
        ▼
LOCATE EXISTING OWNER
        │
        ▼
BOUND CHANGE
        │
        ▼
IMPLEMENT
        │
        ▼
UNIT / CONTRACT TESTS
        │
        ▼
INTEGRATION / NEGATIVE TESTS
        │
        ▼
QUALITY GATES
        │
        ▼
FINAL DIFF REVIEW
        │
        ▼
PR / REVIEW
        │
        ▼
MERGE
        │
        ▼
RELEASE / DEPLOYMENT IF AUTHORIZED
        │
        ▼
EVIDENCE
```

---

# 266. Engineering Evidence Formula

```text
REQUIREMENT
+
DIFF
+
TEST RESULTS
+
CI RESULTS
+
REVIEW
+
MERGE REVISION
+
RELEASE / DEPLOYMENT EVIDENCE WHEN APPLICABLE
=
TRACEABLE ENGINEERING CHANGE
```

---

# 267. Final Engineering Invariant

The defining ILAIOS engineering rule is:

> **Every change must strengthen or preserve the one canonical ILAIOS architecture; no local implementation convenience may create a second source of authority, weaken a required control, or manufacture a PASS without evidence.**

Therefore:

```text
Fast
≠
Correct

Compiles
≠
Tested

Tests locally
≠
CI PASS

Merged
≠
Released

Released
≠
Deployed

Deployed
≠
Currently Healthy
```

And:

```text
SMALL
+
EXPLICIT
+
TYPED
+
TESTED
+
SECURE
+
REVIEWED
+
TRACEABLE
=
ILAIOS ENGINEERING STANDARD
```

**The engineering system exists to make ILAIOS easier to evolve without making it easier to bypass.**
