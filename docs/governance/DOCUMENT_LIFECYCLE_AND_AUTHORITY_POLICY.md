# Document Lifecycle and Authority Policy

Status: CONTROLLED
Owner: Repository owner

## Purpose
Defines how ILAIOS documentation becomes authoritative without changing the canonical architecture by implication.

## Authority
This policy is subordinate to the governed canonical architecture, canonical implementation specification, milestone/dependency definitions, `GOVERNANCE.md`, and executable repository evidence for implementation state. Lower-authority documents MUST NOT silently override higher-authority sources.

## Lifecycle
Documents use: `DRAFT -> CONTROLLED -> CANONICAL -> DEPRECATED`.

- DRAFT: proposal; non-binding.
- CONTROLLED: approved operational standard within its scope.
- CANONICAL: explicit architecture/product authority; requires dedicated governed change.
- DEPRECATED: retained for history but MUST NOT drive new decisions.

Status promotion requires a bounded PR, owner approval, conflict review, and dated evidence. Canonical promotion requires explicit declaration; file location alone does not make a document canonical.

## Conflict rule
When two documents conflict, apply the higher authority. If authority is equal, use the newer explicitly approved rule only after confirming it does not contradict executable evidence or canonical constraints. Ambiguity is fail-closed and must be resolved before production-impacting action.

## Change control
Every controlled document SHOULD identify purpose, scope, owner, status, enforcement/evidence, exceptions, and review triggers. Material policy changes require PR review and traceable commit history. Production/security exceptions require explicit human authorization and expiry/review conditions.

## Review triggers
Review after architecture changes, release model changes, material incidents, platform/provider changes, or at least annually while active.
