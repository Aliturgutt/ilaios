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
| Telemetry | Operational snapshot carries runtime/scheduler/governance projections; the cost UI accepts explicit USD cost fields from those authoritative roots and their `costs`/`finops`/`cost_telemetry` projections | PARTIAL BY CAPABILITY; unavailable values remain unavailable |
| Approval Engine | Desktop sends approve/deny decisions to the authoritative governance boundary | IMPLEMENTED |
| Agent Runtime | Agent/worker state is projected from authoritative scheduler/runtime/live-event data; the canonical runtime command boundary supports `register_agent` and scheduler supports `register_worker` | READ/PROJECTION IMPLEMENTED; Desktop-safe creation semantics are not yet bound |
| Workflow Engine | Goals/jobs plus control-center operational state are authority-derived | IMPLEMENTED for existing job/workflow contract |
| Evidence | Verified evidence projection and digest-verified artifact retrieval are implemented | IMPLEMENTED |
| Costs | Reference-faithful UI is authority-derived | READ IMPLEMENTED; branch adds real, allowlisted JSON Export action |
| Outputs | Deliveries expose only artifacts already present in verified evidence and save verified bytes explicitly | IMPLEMENTED |
| Authentication | Provider-neutral OIDC/PKCE adapter exists; packaged Google registration is supported; Microsoft real registration remains external acceptance work | PARTIAL EXTERNAL DEPENDENCY |

## Surface-to-source map

| Desktop surface | Authoritative source | Current action state |
| --- | --- | --- |
| Home | `ControlPlaneProjection` + `OperationalSnapshot` | Read/refresh |
| Goals | identity adapter -> canonical goal/job execution boundary | Prompt submission implemented |
| Workflows | projection + runtime/scheduler/live events | Read/refresh; one internal navigation action still needs shell binding |
| Agents | scheduler/runtime/live-event projection | Read/search implemented; create-agent and several presentation controls need governed/action binding |
| Live Workspace | live-event projection only | Events/log-derived state available; safe code/terminal/browser/files projections absent |
| Artifacts | verified evidence records + `/v1/evidence/artifacts/{sha256}` | Verified save implemented |
| Approvals | grants/governance state + authoritative decision command | Approve/deny implemented |
| Evidence | `/v1/evidence/verify` | Read-only verified projection |
| Costs | explicit authoritative cost fields from governance/scheduler roots and nested cost projections | Read implemented; branch adds allowlisted JSON export |
| Settings | authoritative connection/identity/provider state | Read/config presentation; external provider registration remains outside Flutter |

## Red-team gaps discovered

### RT-01 — operational state depended on explicit refresh

Execution status already had bounded one-second polling, but general operational state was refreshed at startup and after explicit actions. That could leave costs, evidence, routes and live-event projections stale while the application remained open.

**Branch remediation:** `IlaiosDesktopApp` requests an authoritative refresh every two seconds while the app is resumed. The existing bootstrap `_refreshing` guard prevents overlapping refresh calls. No background synthetic state is generated.

### RT-02 — Costs Export looked actionable but had no action

The approved Costs design rendered an Export control as presentation only.

**Branch remediation:** add `CostExportService` and bind the visible Export target to a real action. The service uses the same authoritative cost-root family consumed by the UI, exports only an explicit allowlist of cost fields, records each projection source, verifies a non-empty file, rejects malformed/non-JSON data, and recursively fails closed if selected telemetry contains sensitive keys. It never exports the full governance or scheduler state.

### RT-03 — Live Workspace does not have safe workspace APIs

No `/v1/workspace` endpoint was found in the repository audit. The current Desktop copy correctly declares Live Code, Terminal, Browser and Files unavailable rather than fabricating content.

**Required next architecture work:** define and implement governed, read-only workspace projection contracts before enabling those tabs. Any write/terminal execution contract must pass the canonical authorization/policy/tool boundary rather than grant Flutter direct runtime access.

### RT-04 — Agent creation is not bound to a Desktop-safe command

The Agents surface explicitly reports that new-agent creation is not bound to a Desktop API contract. There is no dedicated `/v1/agents` route, but the canonical control plane already exposes `register_agent` through `/v1/runtime/commands` and `register_worker` through `/v1/scheduler/commands`.

**Required next architecture work:** define which authorities/capabilities a Desktop-created agent may request and route the action through those existing governed command boundaries. Do not let Flutter invent privileged authorities or bypass admission/policy rules.

### RT-05 — Workflows internal navigation can degrade to a notice

`ReferenceWorkflowsView` requests real navigation to Goals for the New Workflow action, but the current `ControlCenterView` compatibility wrapper converts that request into a SnackBar rather than switching the persistent shell destination.

**Required remediation:** thread the shell navigation callback through `ControlCenterView` and regression-test New Workflow -> Goals.

### RT-06 — Agents contains presentation controls without product actions

The Agents toolbar includes a More control with an empty callback, and some reference-faithful filter/pagination controls are presentation-only.

**Required remediation:** every visible control must either execute a real bounded action, mutate real local UI state (for client-side filtering/paging), or be explicitly disabled/unavailable. No clickable no-op control may remain in the verified product path.

## Tests added by this branch

- cost export writes only allowlisted authoritative snapshot telemetry;
- top-level governance cost telemetry can be exported when it is the UI source;
- nested scheduler FinOps telemetry follows the same export contract;
- unrelated governance/scheduler state is not exported;
- nested sensitive data makes cost export fail closed;
- Costs export fails closed without telemetry;
- visible Costs Export target invokes a real action;
- unavailable Costs telemetry disables Export;
- Desktop requests periodic authoritative refresh while active.

The previous branch head passed Flutter analyze/tests, Desktop Windows release build, Desktop CI, unsigned MSIX packaging and Software Factory Final Evidence. Because the export self-review produced a newer branch head, all merge-authoritative gates must run again on that exact newer head.

## Verification already represented by repository tests

- all ten primary navigation destinations are reachable through semantic Desktop navigation;
- Home has explicit truthful empty-state and authoritative populated-state coverage;
- reference/demo telemetry is asserted absent from runtime truth;
- target layout covers 1920x1080, 1600x900, 1280x720, 1024x720 and 820x700;
- 125% and 150% text scaling are covered.

These claims remain subordinate to exact-head CI success.

## Remaining verification gates

1. Run Flutter analyze and complete Desktop tests on the newest exact branch head.
2. Run Desktop CI and Windows Gate on the newest exact branch head.
3. Run MSIX packaging on the newest exact branch head.
4. Complete RT-05 workflow internal navigation binding.
5. Complete RT-06 Agents no-op/presentation-control closure.
6. Run packaged sidecar -> Desktop E2E on Windows.
7. Run one real governed workflow and verify runtime state, cost changes where authoritative USD telemetry exists, output, evidence and completion all project into Desktop.
8. Keep unsupported workspace actions fail-closed until their backend contracts are implemented and tested.
9. Bind agent creation only after bounded authorities/capabilities are explicitly defined; use existing governed runtime/scheduler commands rather than a Flutter privilege bypass.
10. Keep signed MSIX/Store publication separate from functional Desktop verification; external publisher identity/signing/Partner Center gates cannot be inferred from application tests.
