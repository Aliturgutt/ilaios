# ILAIOS Desktop Functional Closure Checkpoint

TEMPORARY FILE — delete after full Desktop functional closure, exact-master Windows certification, final package verification and live Windows acceptance.

## Recovery rule
On timeout, re-read this file and current GitHub PR/CI state before continuing. GitHub code, PRs, commits and CI are source of truth.

## Acceptance target
Home, Goals, Workflows, Agents, Live Workspace, Outputs, Approvals, Evidence, Costs and Settings must be real-data, real-action, real-time and Windows-E2E verified. Microsoft OIDC/App Registration is the only allowed external blocker at final functional closeout.

## Current authority
- Repository: Aliturgutt/ilaios
- Current master: 3d37597993172e2046ea487fe587ea360005c796
- Phase 4 Home + Goals: MERGED PR #417 after 5/5 exact-head PASS
- Phase 5 Workflows: MERGED PR #421 after 5/5 exact-head PASS
- Active phase: 6 / Agents functional closure
- Active PR: #433
- Active branch: desktop/agents-functional-closure
- Active exact head: 632c5ae2d7a408f5c569e39f173552123781a37e

## Mandatory phase order
0 Acceptance baseline
1 Bundled runtime connection
2 Identity (Microsoft external blocker only)
3 Canonical Desktop operational data contract
4 Home + Goals
5 Workflows
6 Agents
7 Approvals
8 Live Workspace read projections
9 Workspace governed actions
10 Outputs lifecycle
11 Evidence
12 Costs / FinOps
13 Settings persistence + authoritative platform settings
14 Global shell action audit
15 Telemetry producers
16 Golden E2E
17 Exact-master Windows certification
18 Final Windows package + live installation acceptance
19 Microsoft OIDC remains only allowed external blocker

## Gate rule
CODE -> unit/widget/integration -> Flutter analyze -> Flutter test -> Desktop CI -> Windows Gate -> MSIX -> Required CI -> Software Factory Final Evidence -> exact-head PASS -> merge -> next phase.

## Completed evidence
### PR #417 Home command center
Exact head 1be576df1165503c82bdc10e144d64d016e3ba66: all five mandatory gates PASS. Merge master 55d86dffa8ccfc2a786c27df4781392b518fd6fa.

### PR #421 Workflows
Final exact head 1883cf5486305a1aa953a819d7718181fe49aefd: all five mandatory gates PASS. Merge master 3d37597993172e2046ea487fe587ea360005c796.
Closed: real Type/Priority/Owner/Stage filters, real paging, search clearing, toolbar More actions, row Details/Approvals/Live Workspace actions.

## Active PR #433 Agents
Implemented:
- canonical `/v1/agents/state` projection + scheduler/runtime/live telemetry
- governed provisioning callback scoped into Agents
- New Agent selects only server-projected unregistered canonical IDs and sends only `agent_id`
- real Role / Status / Capability filters, six-row paging, Clear Filters
- toolbar More = Refresh / Provision
- Assign Task disabled because governed assignment API is not proven

CI history:
- head 6897ea23...: analyze failed on six lint/style infos
- commit 65460f0b... removed redundant test import
- commit e70662fb... fixed source lint/braces; Flutter analyze PASS and Windows release build PASS
- head e70662fb... widget suite: 125 PASS / 4 FAIL; all four failures were `pumpAndSettle timed out` in new agent_controls tests because test fixtures omitted capacity, causing indeterminate progress animations
- existing fidelity, approvals, goals, workflows, costs, output, identity and control-plane tests remained green in that run
- commit 632c5ae2d7a408f5c569e39f173552123781a37e adds determinate authoritative capacity/success telemetry to the regression fixtures; no product authority change
- fresh five-gate CI is running on exact head 632c5ae2d7a408f5c569e39f173552123781a37e

## Phase 7 Approvals pre-audit
Authority path is already real: governance `work` + `admissions`, independent approver checks and approve/deny callback. Remaining visible gaps found on master:
- Type/Requester/Status filters are presentation-only while risk filter is real
- table pagination is presentation-only
- row trailing More icon is not actionable
- header Export is disabled/unbound
- Policy Rules card is visually prominent but unbound
- selected-request View Details uses `onPressed: () {}`
- Add Note is disabled/unbound
These must be closed without bypassing governance authority. No fake policy/notes data.

## Later-phase pre-audit
No implemented `/v1/workspace` HTTP API exists on current master. SoftwareFactory already owns isolated bounded Workspace execution state; Live Workspace must project/control that canonical workspace, not create a parallel runtime.

## Non-negotiable invariants
No fake/demo KPI. No clickable no-op. Flutter cannot mint authority. Privileged actions route Policy -> Approval if needed -> Tool Gateway -> Runtime -> Evidence/Event. No parallel Core/runtime/registry. Missing authority is disabled/unavailable.

## Next action
Check all five PR #433 workflows for exact head 632c5ae2d7a408f5c569e39f173552123781a37e. Fix any exact failing job with the smallest safe change. Merge only when all five are PASS; then fetch fresh master, update this checkpoint to phase 7 and start Approvals closure from that exact master.
