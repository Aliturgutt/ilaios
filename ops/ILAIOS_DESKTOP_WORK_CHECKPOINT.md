# ILAIOS Desktop Work Checkpoint

Temporary evidence-only checkpoint for Desktop functional closure. CURRENT REALITY only; this file is not a runtime authority and must not replace canonical Core/control-plane/router/scheduler/governance/evidence authorities.

## Current phase

- Phase: Approvals functional closure
- Working branch: `desktop/approvals-functional-closure-master-sync`
- Fresh/latest synced base: `master@7a1f68349f76896659d891384594c8653f38bfb1`
- Supersedes stale-base Approvals PR #470 without rewriting its history.
- Master changes since the prior Desktop base do not overlap the three Approvals closure paths replayed here; the latest sync preserves current master history.
- Agents closure is merged through PR #468 after exact-head 5/5 required gates passed on `20c878b0ac6b9e4fbd28ebdb40f6eabc1852c5a5`.
- Agents merge commit: `91d7c049ee008e7940f709babc7f3a049f1955c0`.

## Approvals audit evidence

Current `apps/desktop/lib/features/operations/approvals_view.dart` is authority-derived for request state and preserves the existing governed decision callback. Pending decisions are allowed only when a real callback and approver identity are present; self-approval is fail-closed when requester and approver IDs match. Existing regression coverage proves authoritative approval callback dispatch and no fabricated screenshot metrics.

The visible `Export` and `Policy Rules` toolbar controls have no governed callback. They are therefore retained as explicitly unavailable/disabled controls rather than made visually actionable or connected to invented local authority. Regression coverage proves both remain non-interactive and visibly disabled.

## Merge gate

Do not merge the active Approvals phase until the exact active PR head has PASS evidence for all five:

- ILAIOS Desktop CI
- ILAIOS Desktop Windows Gate
- ILAIOS Desktop MSIX Packaging
- Required CI Gate
- Software Factory Final Evidence

Approval/denial must continue through the authoritative control-plane callback. No local Flutter approval authority, policy mutation, or fabricated export is permitted.

## Closure sequence

1. Agents — MERGED via PR #468
2. Approvals — ACTIVE
3. Governed Live Workspace read projections
4. Workspace actions through Policy / Approval / Tool Gateway
5. Outputs lifecycle
6. Evidence
7. Costs / FinOps
8. Settings persistence and integrations truthfulness
9. Global shell action audit
10. Telemetry producers
11. Golden Windows E2E
12. Exact-master Windows certification/package

Microsoft OIDC/App Registration remains an agreed external dependency; never fabricate it.
