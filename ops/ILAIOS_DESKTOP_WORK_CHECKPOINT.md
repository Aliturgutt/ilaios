# ILAIOS Desktop Functional Closure Checkpoint

TEMPORARY FILE — delete after the full Desktop functional closure, Windows certification, final package verification, and live Windows acceptance are complete.

## Recovery rule
If the ChatGPT session times out, re-read this file plus the current GitHub PR/CI state before continuing. GitHub code, PRs, commits, and CI remain the source of truth.

## Acceptance target
All 10 approved Desktop surfaces must be real-data, real-action, real-time and Windows-E2E verified: Home, Goals, Workflows, Agents, Live Workspace, Outputs, Approvals, Evidence, Costs, Settings. Microsoft OIDC/App Registration is the only allowed external dependency to remain open at final functional closeout.

## Current authority
- Repository: Aliturgutt/ilaios
- Baseline master at start: 6347518064dd44e4087a714cd172c536b0422956 (PR #393 merged)
- Active phase: 4 / Home + Goals direct prompt wiring
- Active PR: #417
- Active branch: desktop/home-direct-prompt-wiring
- Active exact head: 1be576df1165503c82bdc10e144d64d016e3ba66

## Mandatory phase order
0. Acceptance baseline / no screenshot demo telemetry
1. Bundled runtime connection
2. Identity (Google/session/tenant/principal; Microsoft external blocker only)
3. Canonical Desktop operational data contract
4. Home + Goals
5. Workflows
6. Agents
7. Approvals
8. Live Workspace read projections
9. Workspace governed actions
10. Outputs lifecycle
11. Evidence
12. Costs / FinOps
13. Settings persistence + authoritative platform settings
14. Global shell action audit
15. Telemetry producers
16. Golden E2E
17. Exact-master Windows certification
18. Final Windows package + live installation acceptance
19. Microsoft OIDC remains only allowed external blocker

## Gate rule for every code phase
CODE -> unit/widget/integration tests -> Flutter analyze -> Flutter test -> Desktop CI -> Windows Gate -> MSIX -> Required CI -> exact-head PASS -> merge -> next phase.

## PR #417 evidence history
Previous exact head 4548f5afe6e73e797ae2add741c32ca73389caec failed because the new regression test omitted required `lastEvent` from ControlPlaneProjection. The smallest test-only fix was committed on exact head 1be576df1165503c82bdc10e144d64d016e3ba66.

Current exact-head evidence for 1be576df1165503c82bdc10e144d64d016e3ba66:
- Software Factory Final Evidence: PASS
- Desktop CI: PASS (analyze + tests + Windows build)
- Windows Gate: PASS, including packaged Desktop -> control-plane E2E and real Video/Software/App factory Windows evidence
- MSIX Packaging: PASS, including bundled control plane and package inspection
- Required CI: IN PROGRESS; structural/security jobs are green and full Platform validation is still in pytest/Ruff/Mypy quality sequence

## Pre-audit for next phases
- Workflows current view has real authority-derived records, search/tabs and persistent navigation, but top More is a no-op, four filter boxes are presentation-only, clear only resets query state, and pagination is presentation-only. Phase 5 will close these locally without inventing backend authority.
- Agents bootstrap already exposes a governed `onProvisionAgent` callback backed by `/v1/agents/commands`, but ReferenceAgentsView does not receive it and still declares New Agent unavailable. Phase 6 will bind the existing governed command and close filters/paging/no-ops.
- No implemented `/v1/workspace` HTTP API exists on current master; SoftwareFactory already owns an isolated bounded Workspace abstraction. Live Workspace must project that canonical execution workspace safely instead of creating a parallel runtime.

## Non-negotiable invariants
- No fake/demo KPI values in production.
- No clickable no-op controls.
- Flutter must not mint permissions, providers, workers or privileged capabilities.
- Privileged workspace actions must go through Policy -> Approval when required -> Tool Gateway -> Runtime -> Evidence/Event.
- Canonical Core remains the single authority; no parallel runtime/registry/control plane.
- Missing authority renders unavailable/disabled, never fabricated.

## Next action
Re-check Required CI for exact head 1be576df1165503c82bdc10e144d64d016e3ba66. If PASS, merge #417 with this expected head SHA, fetch the new master SHA, update this checkpoint to phase 5, and create a Workflows closure branch from the exact new master. If Required CI fails, inspect the exact failing job/log and apply the smallest safe fix before merge.
