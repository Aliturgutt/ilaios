# ILAIOS Desktop Functionalization Red-Team Audit

Status authority: code, tests, exact-head CI, packaged runtime evidence and real-Windows acceptance override this audit. A visual reference is never runtime evidence.

Audit base: `master` at `bc1e36c36537dbafb4d9f53a9c602d2a059d9225`.

## Completion rule

Desktop is not considered functionally verified until the relevant chain is proven end to end:

`authoritative runtime -> control-plane API -> Desktop service/client -> state refresh -> interactive component -> user-visible result -> regression/runtime evidence`.

No screenshot value, synthetic telemetry or presentation-only button may satisfy that rule.

## Architecture inventory

| Layer | Current repository evidence | Red-team status |
| --- | --- | --- |
| Desktop UI | Flutter/Dart Windows client under `apps/desktop`; canonical shell routes Home, Goals, Workflows, Agents, Live Workspace, Artifacts, Approvals, Evidence, Costs and Settings | IMPLEMENTED; exact-head UI gates still required |
| Runtime | Packaged canonical Python control plane launched as the Windows sidecar | IMPLEMENTED; exact-head packaged-runtime gate required |
| Backend/API | Desktop client uses canonical loopback authenticated endpoints for goals/jobs, runtime, scheduler, grants, governance, evidence and live events | IMPLEMENTED for exposed projections |
| Database/state | Durable control-plane state is owned by the packaged control plane, not Flutter | BACKEND-AUTHORITATIVE |
| Events | `/v1/events` and incremental `/v1/live/events` projections are consumed by Desktop | IMPLEMENTED |
| Telemetry | Operational snapshot carries runtime/scheduler/governance projections; cost UI consumes authoritative `governanceState.costs` when present | PARTIAL BY CAPABILITY; unavailable values remain unavailable |
| Approval Engine | Desktop sends approve/deny decisions to the authoritative governance boundary | IMPLEMENTED |
| Agent Runtime | Agent/worker state is projected from authoritative scheduler/runtime/live-event data | READ/PROJECTION IMPLEMENTED; no `/v1/agents` creation contract found |
| Workflow Engine | Goals/jobs plus control-center operational state are authority-derived | IMPLEMENTED for existing job/workflow contract |
| Evidence | Verified evidence projection and digest-verified artifact retrieval are implemented | IMPLEMENTED |
| Costs | Reference-faithful UI is authority-derived | READ IMPLEMENTED; branch adds real Export action |
| Outputs | Deliveries expose only artifacts already present in verified evidence and save verified bytes explicitly | IMPLEMENTED |
| Authentication | Provider-neutral OIDC/PKCE adapter exists; packaged Google registration is supported; Microsoft real registration remains external acceptance work | PARTIAL EXTERNAL DEPENDENCY |

## Surface-to-source map

| Desktop surface | Authoritative source | Current action state |
| --- | --- | --- |
| Home | `ControlPlaneProjection` + `OperationalSnapshot` | Read/refresh |
| Goals | identity adapter -> canonical goal/job execution boundary | Prompt submission implemented |
| Workflows | projection + runtime/scheduler/live events | Read/refresh |
| Agents | scheduler/runtime/live-event projection | Read/search/filter implemented; create-agent API contract absent |
| Live Workspace | live-event projection only | Events/log-derived state available; safe code/terminal/browser/files projections absent |
| Artifacts | verified evidence records + `/v1/evidence/artifacts/{sha256}` | Verified save implemented |
| Approvals | grants/governance state + authoritative decision command | Approve/deny implemented |
| Evidence | `/v1/evidence/verify` | Read-only verified projection |
| Costs | authoritative `governanceState.costs` | Read implemented; branch adds JSON export |
| Settings | authoritative connection/identity/provider state | Read/config presentation; external provider registration remains outside Flutter |

## Red-team gaps discovered

### RT-01 — operational state depended on explicit refresh

Execution status already had bounded one-second polling, but general operational state was refreshed at startup and after explicit actions. That could leave costs, evidence, routes and live-event projections stale while the application remained open.

**Branch remediation:** `IlaiosDesktopApp` requests an authoritative refresh every two seconds while the app is resumed. The existing bootstrap `_refreshing` guard prevents overlapping refresh calls. No background synthetic state is generated.

### RT-02 — Costs Export looked actionable but had no action

The approved Costs design rendered an Export control as presentation only.

**Branch remediation:** add `CostExportService` and bind the visible Export target to a real action. The service exports only the authoritative `governanceState.costs` payload, adds source/timestamp metadata, verifies a non-empty written file and fails closed when telemetry is missing or malformed.

### RT-03 — Live Workspace does not have safe workspace APIs

No `/v1/workspace` endpoint was found in the repository audit. The current Desktop copy correctly declares Live Code, Terminal, Browser and Files unavailable rather than fabricating content.

**Required next architecture work:** define and implement governed, read-only workspace projection contracts before enabling those tabs. Any write/terminal execution contract must pass the canonical authorization/policy/tool boundary rather than grant Flutter direct runtime access.

### RT-04 — Agent creation has no Desktop API contract

The Agents surface displays authoritative fleet state but explicitly reports that new-agent creation is not bound to a Desktop API contract. No `/v1/agents` contract was found in the repository audit.

**Required next architecture work:** only add create/stop/reconfigure actions if the control plane exposes bounded governed commands. Do not create privileged worker authority locally in Flutter.

## Tests added by this branch

- authoritative Costs export writes real snapshot telemetry only;
- Costs export fails closed without telemetry;
- visible Costs Export target invokes a real action;
- unavailable Costs telemetry disables Export;
- Desktop requests periodic authoritative refresh while active.

These tests are source changes only until exact-head Flutter/Windows CI executes them successfully.

## Remaining verification gates

1. Run Flutter analyze and complete Desktop tests on the exact branch head.
2. Run Desktop CI and Windows Gate on the exact branch head.
3. Re-run populated/empty/failure-state checks across all ten navigation destinations.
4. Verify 1920x1080, 1600x900, 1280x720, 1024x720 plus 125%/150% scaling.
5. Run packaged sidecar -> Desktop E2E on Windows.
6. Run one real governed workflow and verify runtime state, cost changes, output, evidence and completion all project into Desktop.
7. Keep unsupported workspace and agent-authority actions fail-closed until their backend contracts are implemented and tested.
8. Keep signed MSIX/Store publication separate from functional Desktop verification; external publisher identity/signing/Partner Center gates cannot be inferred from application tests.
