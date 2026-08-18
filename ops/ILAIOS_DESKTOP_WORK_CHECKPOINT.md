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
- Active exact head: 4548f5afe6e73e797ae2add741c32ca73389caec

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

## Current PR #417 evidence
- Software Factory Final Evidence: PASS
- Desktop CI: running at last checkpoint
- Windows Gate: running at last checkpoint
- MSIX Packaging: running at last checkpoint
- Required CI: running at last checkpoint

## Non-negotiable invariants
- No fake/demo KPI values in production.
- No clickable no-op controls.
- Flutter must not mint permissions, providers, workers or privileged capabilities.
- Privileged workspace actions must go through Policy -> Approval when required -> Tool Gateway -> Runtime -> Evidence/Event.
- Canonical Core remains the single authority; no parallel runtime/registry/control plane.
- Missing authority renders unavailable/disabled, never fabricated.

## Next action
Re-check PR #417 exact-head workflows. If all mandatory gates PASS, merge #417 with expected head SHA. If any gate fails, inspect the exact failing job/log, apply the smallest safe fix on the same branch, update this checkpoint, and rerun exact-head gates.
