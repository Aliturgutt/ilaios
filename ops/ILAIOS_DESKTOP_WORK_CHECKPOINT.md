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
Previous exact head 4548f5afe6e73e797ae2add741c32ca73389caec:
- Required CI: PASS
- Software Factory Final Evidence: PASS
- Desktop CI: FAIL at Flutter analyze
- Windows Gate: FAIL
- MSIX Packaging: FAIL
- Root cause proven from Desktop CI log: new regression test constructed ControlPlaneProjection without required `lastEvent` argument.

Remediation committed on exact head 1be576df1165503c82bdc10e144d64d016e3ba66:
- add `lastEvent: null` to the regression projection fixture only
- no product/runtime/API behavior changed
- fresh exact-head gates must now decide merge readiness

## Non-negotiable invariants
- No fake/demo KPI values in production.
- No clickable no-op controls.
- Flutter must not mint permissions, providers, workers or privileged capabilities.
- Privileged workspace actions must go through Policy -> Approval when required -> Tool Gateway -> Runtime -> Evidence/Event.
- Canonical Core remains the single authority; no parallel runtime/registry/control plane.
- Missing authority renders unavailable/disabled, never fabricated.

## Next action
Check all workflow runs for exact head 1be576df1165503c82bdc10e144d64d016e3ba66. If all mandatory gates PASS, merge #417 with this expected head SHA, update master/checkpoint, and proceed to Workflows closure. If any gate fails, inspect the exact failing job/log and apply the smallest safe fix before merge.
