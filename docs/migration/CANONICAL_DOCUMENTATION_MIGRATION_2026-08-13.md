# Canonical Documentation Migration — 2026-08-13

Status: CONTROLLED MIGRATION RECORD
Base master: `31b75faf71243b1534d46369286b3f51532e4ccb`
Locked snapshot SHA-256: `3a7c5b7fab775c0612f516d439be24fb838ad7b177af0b6f8ba76de4942f583d`

## Purpose

Promote the audited 19-item ILAIOS documentation set into the repository without creating a second Core, routing authority, policy authority, agent identity authority, evidence truth, or competing canonical document set.

## Classification

### KEEP

- Product/runtime source, tests, CI, deployment evidence and durable evidence.
- `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`.
- Existing operational/runbook/release/security/platform/migration/status documents that do not redefine canonical architecture.
- `POST_CORE_ROADMAP.md` remains historical because it already declares itself retired/non-authoritative.
- Machine-readable post-v1 dependency/status material remains evidence/status authority only within its declared scope.

### SUPERSEDE-ARCHIVE

- Previous root `GOVERNANCE.md` content: replaced by `docs/governance/GOVERNANCE.md`; legacy path becomes a compatibility redirect.
- `docs/canonical/ILAIOS_ENTERPRISE_AI_OPERATING_SYSTEM_CANONICAL_ARCHITECTURE.md`: superseded by `docs/canonical/SYSTEM_ARCHITECTURE.md`; legacy path becomes a compatibility redirect.
- `ILAIOS_Master_Implementation_Specification_v1_0_CANONICAL_FINAL.docx`: superseded by the Markdown canonical set; root path retained only as a compatibility redirect document for historical tooling.
- `ILAIOS_Canonical_Milestone_Manifest_v1_0.docx`: superseded by `docs/governance/MILESTONES.md` plus the canonical dependency/implementation contracts; root path retained only as a compatibility redirect document for historical tooling.
- Legacy ADR `0001-monorepo-boundaries.md` and `0002-versioned-canonical-contracts.md`: moved out of the active ADR namespace to the historical archive because their numbering collides with the final ADR sequence.

### REMOVE FROM ACTIVE AUTHORITY NAMESPACE

- Any prior file whose only purpose was to act as a competing canonical source after a compatibility redirect or final replacement exists. Git history/archive retains provenance.

## Final authority boundary

The active canonical documentation set is exactly the 19 items listed in `docs/DOCUMENTATION_INDEX.md`. Compatibility shims and archived documents are not canonical items and cannot override them.

## Implementation truth

This migration changes documentation authority and navigation only. It does not promote code maturity. Current implementation state remains established by repository code, tests, CI, runtime, deployment and durable evidence.
