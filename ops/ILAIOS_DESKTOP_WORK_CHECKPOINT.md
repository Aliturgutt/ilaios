# ILAIOS Desktop Work Checkpoint

Temporary evidence-only checkpoint for Desktop functional closure. CURRENT REALITY only; this file is not a runtime authority and must not replace canonical Core/control-plane/router/scheduler/governance/evidence authorities.

## Current phase

- Phase: Governed Live Workspace read projections
- Working branch: `desktop/live-workspace-authority-current-20260819`
- Fresh base at phase start: `master@3d2ab156980826e5ea3fed2861e64b61b51d4433`
- Approvals closure is merged through PR #473 at merge commit `e00cabadb0677aca6a3b5f4949f835d75b18fd80`.
- Agents closure is merged through PR #468 at merge commit `91d7c049ee008e7940f709babc7f3a049f1955c0`.
- The prior `desktop/live-workspace-read-projections` branch is stale and fully behind current master; do not merge it.
- The prior `desktop/live-workspace-read-projections-v2` branch diverged from an older master and is superseded by the current branch.

## Live Workspace authority audit evidence

`apps/desktop/lib/features/operations/live_workspace_view.dart` renders workspace/session data from `OperationalSnapshot`, but current master gives the latest `liveEvents` entry precedence over `schedulerState` and `governanceState` in `_sessionProjection`. A non-workspace event carrying generic keys such as `project_name`, `owner`, `mode`, or `url` can therefore override authoritative workspace/session fields in the Desktop projection.

The active branch adds a regression test proving that unrelated live-event metadata must not override authoritative scheduler workspace/session values. This is a correctness and trust-boundary regression guard; it does not create new runtime authority or fabricate telemetry.

The intended bounded repair is to preserve live events for activity/log rendering while preventing them from outranking the canonical scheduler/governance state for workspace session identity, owner, mode, project, branch/environment, synchronization, preview URL and related session fields.

## Merge gate

Do not merge the active Live Workspace phase until the exact active PR head has PASS evidence for all five:

- ILAIOS Desktop CI
- ILAIOS Desktop Windows Gate
- ILAIOS Desktop MSIX Packaging
- Required CI Gate
- Software Factory Final Evidence

No local Flutter execution authority, provider state, workspace mutation authority, screenshot telemetry, or fabricated session data is permitted.

## Closure sequence

1. Agents — MERGED via PR #468
2. Approvals — MERGED via PR #473
3. Governed Live Workspace read projections — ACTIVE
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
