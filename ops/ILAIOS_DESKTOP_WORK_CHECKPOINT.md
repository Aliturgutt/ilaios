# ILAIOS Desktop Functional Closure Checkpoint

TEMPORARY FILE — delete after the full Desktop functional closure, Windows certification, final package verification, and live Windows acceptance are complete.

## Recovery rule
If the ChatGPT session times out, re-read this file plus the current GitHub PR/CI state before continuing. GitHub code, PRs, commits, and CI remain the source of truth.

## Acceptance target
All 10 approved Desktop surfaces must be real-data, real-action, real-time and Windows-E2E verified: Home, Goals, Workflows, Agents, Live Workspace, Outputs, Approvals, Evidence, Costs, Settings. Microsoft OIDC/App Registration is the only allowed external dependency to remain open at final functional closeout.

## Current authority
- Repository: Aliturgutt/ilaios
- Current master: 55d86dffa8ccfc2a786c27df4781392b518fd6fa
- Phase 4 / Home + Goals: MERGED via PR #417 after 5/5 exact-head gates PASS
- Active phase: 5 / Workflows functional closure
- Active PR: #421
- Active branch: desktop/workflows-functional-closure
- Active exact head: 1883cf5486305a1aa953a819d7718181fe49aefd

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

## Completed evidence
### PR #417 — Home command center
Exact head 1be576df1165503c82bdc10e144d64d016e3ba66:
- Software Factory Final Evidence: PASS
- Desktop CI: PASS
- Windows Gate: PASS
- MSIX Packaging: PASS
- Required CI: PASS
Merged master: 55d86dffa8ccfc2a786c27df4781392b518fd6fa.

## Active PR #421 — Workflows
Implementation:
- real Type / Priority / Owner / Stage filters over authority-derived workflow records
- real 5-row pagination with bounded previous/next controls
- Clear Filters resets filter state and visible search text
- toolbar More no-op replaced by bounded Refresh / New Workflow actions
- row menu now performs Details / Approvals / Live Workspace actions
- widget regression coverage for filtering, clearing, pagination and menus
- no backend/schema/privilege changes; no fabricated telemetry

Previous head 70e47aff40a4257833aadbc252b96f5cc7d3d005:
- Flutter analyze: PASS
- 124 widget tests PASS / 1 FAIL
- failure was test-only ambiguity: `Open Details` exists both in the persistent selected-workflow panel and opened row popup, so `findsOneWidget` was invalid
- product behavior itself was not the failing assertion

Current exact head 1883cf5486305a1aa953a819d7718181fe49aefd:
- test assertions now tolerate/scoped duplicate visible action labels and select the popup action explicitly
- all five mandatory exact-head workflows have started; awaiting results

## Pre-audit for next phases
- Agents bootstrap already exposes a governed `onProvisionAgent` callback backed by `/v1/agents/commands`, but ReferenceAgentsView does not receive it and still declares New Agent unavailable.
- Canonical `/v1/agents/state` already projects registry-backed agents and rejects authority drift; `/v1/agents/commands` provisioning rejects caller-supplied authorities/capabilities/permissions and resolves them server-side from CANONICAL_AGENT_REGISTRY.
- Current Agents UI also ignores `snapshot.agentState` in its record aggregation, has presentation-only Role/Status/Capability filters, fake paging, and a toolbar no-op More control. Phase 6 must close these without inventing assignment authority.
- Assign Task remains unavailable unless a governed assignment API is proven; do not fake it.
- No implemented `/v1/workspace` HTTP API exists on current master; SoftwareFactory already owns an isolated bounded Workspace abstraction. Live Workspace must project that canonical execution workspace safely instead of creating a parallel runtime.

## Non-negotiable invariants
- No fake/demo KPI values in production.
- No clickable no-op controls.
- Flutter must not mint permissions, providers, workers or privileged capabilities.
- Privileged workspace actions must go through Policy -> Approval when required -> Tool Gateway -> Runtime -> Evidence/Event.
- Canonical Core remains the single authority; no parallel runtime/registry/control plane.
- Missing authority renders unavailable/disabled, never fabricated.

## Next action
Check PR #421 exact-head 1883cf5486305a1aa953a819d7718181fe49aefd gates. If any fails, inspect exact job/log and apply the smallest safe fix. Merge only when Desktop CI, Windows Gate, MSIX, Required CI and Software Factory Final Evidence all PASS. Then fetch fresh master, update this checkpoint to phase 6 and start Agents closure from that exact master.
