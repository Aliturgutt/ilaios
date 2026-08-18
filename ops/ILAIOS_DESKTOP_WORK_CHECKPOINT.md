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
- Active exact head: ac8e5ea73a487d668ebc531b3b784ce46035265c

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

## Active PR #433 Agents
Implemented:
- canonical `/v1/agents/state` projection + scheduler/runtime/live telemetry
- governed canonical provisioning; Flutter sends only server-projected `agent_id`
- real Role / Status / Capability filters, six-row paging and Clear Filters
- toolbar More = Refresh / Provision
- Assign Task disabled because governed assignment API is not proven
- missing capacity telemetry now renders static unavailable track + `—`; it no longer uses an indeterminate progress animation
- regression test proves missing capacity has no `LinearProgressIndicator` and settles normally

CI history:
- 6897ea23... analyzer found style/lint issues; fixed
- e70662fb... analyze/build PASS; new tests exposed indeterminate-capacity `pumpAndSettle` behavior
- 632c5ae2... made fixtures determinate to isolate control behavior
- c2f74d45... fixed product truthfulness for missing capacity
- ac8e5ea73a487d668ebc531b3b784ce46035265c adds the missing-capacity regression and is the current exact-head authority
- all five mandatory workflows started fresh for ac8e5ea73a487d668ebc531b3b784ce46035265c

## Phase 7 Approvals pre-audit
Authority path is already real: governance `work` + `admissions`, independent approver checks and approve/deny callback. Remaining visible gaps found on master:
- Type/Requester/Status filters are presentation-only while risk filter is real
- table pagination is presentation-only
- row trailing More icon is not actionable
- header Export is disabled/unbound
- Policy Rules card is visually prominent but unbound
- selected-request View Details is a no-op
- Add Note is disabled/unbound
Close only with real local behavior or authoritative contracts; never fabricate policy/notes data.

## Later-phase pre-audit
No implemented `/v1/workspace` HTTP API exists on current master. SoftwareFactory already owns isolated bounded Workspace execution state; Live Workspace must project/control that canonical workspace, not create a parallel runtime.

## Non-negotiable invariants
No fake/demo KPI. No clickable no-op. Flutter cannot mint authority. Privileged actions route Policy -> Approval if needed -> Tool Gateway -> Runtime -> Evidence/Event. No parallel Core/runtime/registry. Missing authority is disabled/unavailable.

## Next action
Check all five PR #433 workflows for exact head ac8e5ea73a487d668ebc531b3b784ce46035265c. Fix any exact failing job with the smallest safe change. Merge only when all five PASS; then fetch fresh master, update checkpoint to phase 7 and start Approvals closure from that exact master.
