# ILAIOS Desktop Work Checkpoint

Temporary evidence-only checkpoint for Desktop functional closure. CURRENT REALITY only; this file is not a runtime authority and must not replace canonical Core/control-plane/router/scheduler/governance/evidence authorities.

## Current phase

- Phase: Governed Live Workspace read projections
- Working branch: `desktop/live-workspace-authority-current-20260819-v2`
- Fresh base: `master@f75a0c35c3d920a82123d318bbd573d1929b2bc4`
- Approvals closure is merged through PR #473 at merge commit `e00cabadb0677aca6a3b5f4949f835d75b18fd80`.
- Agents closure is merged through PR #468 at merge commit `91d7c049ee008e7940f709babc7f3a049f1955c0`.
- PR #515 was based on older `master@3d2ab156980826e5ea3fed2861e64b61b51d4433` and is superseded by the current replay after master advanced.

## Live Workspace authority audit evidence

Exact-head CI on PR #515 proved the authority-precedence regression was real, not flaky: Required CI Gate and Software Factory Final Evidence passed, while all three Desktop workflows failed because the new regression test observed the latest generic live event overriding authoritative scheduler workspace/session values. The failing test expected `Authoritative Project` but the UI projected the event-supplied poison metadata instead.

The current branch preserves raw `liveEvents` for indexed activity/log rendering, but wraps only the `.last` fallback projection seen by child surfaces. When scheduler/governance carries an authoritative value for a workspace/session semantic group, colliding synonyms are removed from the fallback last-event view so scheduler/governance remains authoritative. The underlying event list/evidence is not mutated and no synthetic event is created.

Regression coverage: `apps/desktop/test/live_workspace_authoritative_projection_test.dart` proves an unrelated provider event cannot override authoritative project, mode, owner, preview URL, or session identity while the existing Live Workspace activity/log behavior remains sourced from the raw event list.

## Merge gate

Do not merge the active Live Workspace phase until the exact active PR head has PASS evidence for all five:

- ILAIOS Desktop CI
- ILAIOS Desktop Windows Gate
- ILAIOS Desktop MSIX Packaging
- Required CI Gate
- Software Factory Final Evidence

No local Flutter execution authority, provider state, workspace mutation authority, screenshot telemetry, fabricated session data, or bypass of Policy / Approval / Tool Gateway / Evidence is permitted.

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
