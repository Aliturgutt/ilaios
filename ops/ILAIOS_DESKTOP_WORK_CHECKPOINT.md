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
- Active exact head: e70662fbfdd7cf8aa11ca56966bbf94627426da5

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
Final exact head 1883cf5486305a1aa953a819d7718181fe49aefd: Desktop CI PASS, Windows Gate PASS, MSIX PASS, Required CI PASS, Software Factory Final Evidence PASS. Merge master 3d37597993172e2046ea487fe587ea360005c796.
Closed: real Type/Priority/Owner/Stage filters, real paging, search clearing, toolbar More actions, row Details/Approvals/Live Workspace actions. No fabricated telemetry or privilege changes.

## Active PR #433 Agents
Implemented:
- consumes canonical `/v1/agents/state` plus scheduler/runtime/live telemetry
- carries existing governed `onProvisionAgent` through a scoped UI binding
- New Agent selects only server-projected, unregistered canonical agent IDs and sends only `agent_id`
- server remains authority for capabilities/permissions/allowed callers/targets
- real Role / Status / Capability filters
- real six-row paging and Clear Filters
- toolbar More replaced with bounded Refresh / Provision actions
- Assign Task remains disabled because no governed assignment API is proven
- regression tests cover canonical projection, filters, paging, provisioning and disabled assignment

Initial exact head 6897ea23b03e4f1528d3d674d8e319e29ef0484e:
- Software Factory Final Evidence PASS
- Desktop CI Flutter analyze failed on six style/lint infos only: one separator callback naming lint, four missing-brace lints, and one redundant test import
- no compile/runtime failure was reported by that analyzer pass

Remediation:
- redundant test import fixed in commit 65460f0b700f25f54c727e5f6c8db9c418350240
- remaining source lints fixed in commit e70662fbfdd7cf8aa11ca56966bbf94627426da5
- no product/runtime authority behavior changed by lint remediation
- fresh five-gate exact-head CI is running on e70662fbfdd7cf8aa11ca56966bbf94627426da5

## Next-phase pre-audit
Approvals is already substantially authority-backed: governance `work` + `admissions`, approve/deny callback, independent approver fail-closed checks, search/risk/tabs/selection. Phase 7 will audit every visible action/filter/paging control and close any remaining presentation-only behavior without changing governance authority.

No implemented `/v1/workspace` HTTP API exists on current master. SoftwareFactory already owns isolated bounded Workspace execution state. Live Workspace phases must project/control that canonical workspace rather than create a parallel runtime.

## Non-negotiable invariants
No fake/demo KPI. No clickable no-op. Flutter cannot mint authority. Privileged actions route Policy -> Approval if needed -> Tool Gateway -> Runtime -> Evidence/Event. No parallel Core/runtime/registry. Missing authority is disabled/unavailable.

## Next action
Check all five PR #433 workflows for exact head e70662fbfdd7cf8aa11ca56966bbf94627426da5. Fix any exact failing job with the smallest safe change. Merge only when all five are PASS; then fetch fresh master, update this checkpoint to phase 7 and start Approvals closure from that exact master.
