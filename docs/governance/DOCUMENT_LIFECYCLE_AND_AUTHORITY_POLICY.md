# Document Lifecycle and Authority Policy

Status: CONTROLLED
Owner: Repository owner

## Purpose

Defines how ILAIOS documentation becomes authoritative without changing canonical architecture by implication or creating a competing canonical set.

## Authority

The active 19-item canonical set is enumerated by `docs/DOCUMENTATION_INDEX.md`. `docs/canonical/SYSTEM_ARCHITECTURE.md` is the primary architecture authority; scoped specialist canonical documents govern only their declared domain. `docs/governance/GOVERNANCE.md` governs repository/governance semantics within its scope. ADRs record rationale and do not override architecture.

Repository code, tests, CI/runtime, deployment and durable evidence establish current implementation state. A lower-authority document, compatibility shim, archive, status file, roadmap, audit, or projection MUST NOT silently override a higher authority or promote implementation maturity by assertion.

## Lifecycle

Supporting documents use: `DRAFT -> CONTROLLED -> CANONICAL -> DEPRECATED`.

- DRAFT: proposal; non-binding.
- CONTROLLED: approved operational standard within its scope.
- CANONICAL: explicit scoped authority; requires a dedicated governed change and must not create a second authority already owned by the 19-item set.
- DEPRECATED: retained for history but MUST NOT drive new decisions.

Status promotion requires a bounded PR, owner approval, conflict review, and dated evidence. File location alone does not make a document canonical.

## Conflict rule

When two documents conflict, apply the higher scoped authority. If authority is equal, use the newer explicitly approved rule only after confirming it does not contradict executable evidence or canonical constraints. Ambiguity is fail-closed and must be resolved before production-impacting action.

Compatibility redirects under legacy paths and files under `docs/archive/` are explicitly non-authoritative.

## Change control

Every controlled document SHOULD identify purpose, scope, owner, status, enforcement/evidence, exceptions, and review triggers. Material policy changes require PR review and traceable commit history. Production/security exceptions require explicit human authorization and expiry/review conditions.

Changes to the 19-item canonical set require a dedicated governed change with cross-document contradiction review, path/link validation and evidence-impact review.

## Review triggers

Review after architecture changes, release model changes, material incidents, platform/provider changes, or at least annually while active.
