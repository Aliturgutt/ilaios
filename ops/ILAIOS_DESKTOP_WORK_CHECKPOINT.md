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
- Active branch: desktop/agents-functional-closure
- Branch base: master@3d37597993172e2046ea487fe587ea360005c796

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

## Active phase 6 Agents pre-audit
- DesktopBootstrap already exposes governed `onProvisionAgent` -> ControlPlaneClient `/v1/agents/commands`.
- Server command rejects caller-supplied authorities/capabilities/permissions and resolves canonical authority from CANONICAL_AGENT_REGISTRY.
- `/v1/agents/state` projects canonical registry + runtime/readiness truth.
- Current Agents UI does not consume `snapshot.agentState`, does not receive `onProvisionAgent`, has presentation-only Role/Status/Capability filters, fake paging and a toolbar no-op More control.
- Assignment API has not been proven; `Assign Task` must remain disabled/unavailable rather than fabricated.

## Non-negotiable invariants
No fake/demo KPI. No clickable no-op. Flutter cannot mint authority. Privileged actions route Policy -> Approval if needed -> Tool Gateway -> Runtime -> Evidence/Event. No parallel Core/runtime/registry. Missing authority is disabled/unavailable.

## Next action
Implement Agents closure from exact master. Bind canonical agent-state projection and governed provisioning only; close filters/paging/no-op controls; add regression tests; open PR and require all five exact-head gates before merge.
