# ILAIOS Assistant + Li Desktop Implementation Spec

## Status

Implementation specification for the existing foundation PR. This document does not claim runtime completion.

Follow-up checkpoint for PR #1531 (2026-09-13): live PR HEAD before this pass was
`68891fcc5b6b1fcbd907f51b46bfb37944c8c4be`; live master/PR base was
`c53d387609c0bab9c6c86e7b6d1724c3548f9e53`. Canonical owner files inspected below
are identical between that master and the branch; only the Assistant handler
has branch-specific changes. No master synchronization was needed for these contracts.

This pass adds transport occupancy (one active operation per authenticated
user/tenant/session, at most 16 occupied sessions, no queued duplicate session),
released in `finally`. It complements, not replaces, the existing two-second
conversation lock wait and canonical model `UsageGovernor`. Same-account concurrent
writers/replays are now tested across two authenticated sessions; same-session
saturation returns 429 and does not consume another user's slot. Error, timeout and
revocation tests assert release. This admission occurs AFTER HTTP parsing and does
not claim to bound all threads in the shared `ThreadingHTTPServer`. Shared listener
resource admission remains outside this Assistant-local guard.

Accessibility source changes are confined to Assistant focus nodes and the V11
Assistant trigger/open/close wiring. Before editing, the V11 file was compared
byte-for-byte with current #1485 HEAD `c2ccb1ce87fdaf63b15ad769c165db1eff87303b`
and was identical. No historical Desktop implementation was used. Closed overlays
exclude keyboard focus; opening/restoring focuses the composer (or close control
while busy); close restores the existing sidebar trigger. Widget tests cover
keyboard Enter/Tab, close/reopen focus, normal-user semantics, TR/EN, light/dark and
1.0/1.25/1.5 text scaling. The existing callback test now sends eleven natural-language
action intents and requires zero executions until explicit confirmation. These
widget tests are SOURCE ONLY until Flutter executes them. This pass modifies V11
only for the necessary Assistant focus wiring; it does not modify #1485 itself,
Home/Agents, geometry, brand assets, attachments or workflows.

Canonical model and grant investigation (contracts and their existing tests):

| Question | Current canonical owner and exact constraint |
| --- | --- |
| Model selection | `routing_runtime.GovernedRoutingRuntime.resolve` obtains catalog/runtime snapshots, calls `RoutingIntelligenceEngine` and delegates final selection to `ai_governance.route_model`; evidence is persisted through `EvidenceStore`. |
| Provider dispatch | `runtime.ai_provider_adapter.GovernedAIProviderAdapter` supplies adapters to `runtime.execution.GovernedRuntime`; `NamedAgentExecutor.execute` first invokes `PermissionFirewall.admit`. No Assistant code calls a provider. |
| Conversational request | `AgentInvocation` must match a registered target, allowed caller, capability, permission, input/output classes, security scan, DLP approval and `ExecutionGrant`. The inspected `agent_registry`, agent execution bindings and `ALLOWED_AGENT_AI_CAPABILITIES` expose no Assistant conversation binding. Borrowing an unrelated factory/agent permission would not establish human chat authorization. |
| Skills | `NamedAgentExecutor.ensure_skill` and `GovernedRuntime` own immutable skills. `_structured_response_format` currently provides a strict provider schema for the independent verifier; this is not an admitted Assistant skill. |
| Pricing/free | `openrouter_routing_sources` reads prompt/completion prices into `ai_governance.ModelRecord`. That contract carries input/output cost, but does not carry request-fee evidence. Zero token prices alone cannot prove the required prompt + completion + request = zero rule. No safe free route was inferred. |
| Model limits | `UsageGovernor.admit/complete/reconcile_cost` enforce configured scopes, tokens, concurrency, retries and cost. It does not grant a Desktop human an Assistant conversation capability. |
| Billable admission | `governance.runtime.GovernedRuntimeGateway.authorize_billable/reconcile_billable` consume persisted admission; `commercial_access.TrustedCommercialGrant` binds user/tenant/plan/period. No Assistant request binding into these contracts is configured. |
| Unknown result | Adapter retries use attempt-specific usage request IDs and retryable transport errors. This is not proof of durable conversational unknown-billable-result reconciliation; no paid inference was enabled. |
| Human Knowledge | `knowledge_runtime.DurableKnowledgeRuntime` creates an `IdentityKind.SERVICE` principal and fixed project policy. `knowledge_rag.PrincipalScope`/`AuthorizedContext` bind retrieval to caller-supplied authorized scope, but do not resolve a human Desktop session to revocable workload/resource grants. `identity.AuthorizationEngine` is generic; `runtime.ExecutionGrant` authorizes agent actions/resources. Neither may be substituted for that missing human resolver. |
| Freshness | `ProviderCatalogSnapshot.is_fresh` and routing intelligence enforce catalog/state TTL and reject future/stale observations. Assistant has no configured live catalog/model/evidence consumer; existing public guidance is explicitly snapshot-only. No fake live connector was introduced. |

Environment evidence: `ILAIOS_AGENT_AI_CONFIG_JSON` is absent (presence-only check;
no secret values read or printed). ZERO-COST REAL MODEL E2E = BLOCKED; PAID MODEL
E2E = NOT AUTHORIZED. Model-input sentinel capture, malicious retrieved-content
integration and fresh/live Assistant response acceptance remain BLOCKED at the
unconnected canonical conversational/grant boundaries, not falsely passed by the
fallback tests. Existing canonical routing freshness and Knowledge quarantine tests
were executed, but are not represented as end-to-end Assistant integration.

Python validation: 132 tests passed across Assistant, Li, identity, routing runtime,
AI governance, agent governance, Knowledge RAG/runtime; an additional 28 canonical
provider/structured-output/routing/named-executor tests passed. The 132-test command
used `test_desktop_assistant_conversations.py`, `test_desktop_li_memory_transport.py`,
`test_desktop_li_founder_route.py`, `test_desktop_oidc.py`,
`test_desktop_oidc_persistence.py`, `test_li_app_runtime.py`, `test_routing_runtime.py`,
`test_ai_governance.py`, `test_agent_governance.py`, `test_knowledge_rag.py`, and
`test_knowledge_runtime.py`. The 28-test command used
`test_ai_provider_usage_diagnostics.py`, `test_named_agent_executor_e2e.py`,
`test_routing_intelligence.py`, `test_ai_provider_structured_output.py`, and
`test_openrouter_routing_sources.py`. All commands used the isolated workspace venv;
PyJWT now matches CI's 2.13.0 pin. No live provider calls were made.

Pre-commit root cause was environment-only: inherited PYTHONPATH exposed the
external tool directory inside hook environments, allowing dependency resolution
without installing the Ruff/Mypy executables there. A clean venv and separate
PRE_COMMIT_HOME resolved it. All applicable hooks passed, including Ruff, strict
Mypy, SF-19 and SF-20; YAML had no matching files. No hook configuration changed.
Standalone strict Mypy in the new test venv encountered missing optional NumPy in
pytest's installed package; strict Mypy in the canonical isolated hook passed.
`command -v flutter` returned no executable. Flutter analyze/test/pub get, screenshots,
Windows scaling/runtime acceptance remain NOT RUN / ENVIRONMENT BLOCKED.

Current status is BLOCKED for full closure, not SOURCE COMPLETE: real model admission,
complete zero-cost pricing, human Knowledge grants, actual pre-model input leakage
acceptance, and live Assistant evidence require the canonical dependencies above;
Flutter/Windows execution evidence is unavailable. No direct provider path, duplicate
authority, file/heading rename, merge, deployment or CI monitoring was introduced.
The older checkpoints below retain their historical evidence only.


Continuation checkpoint (2026-09-13), based on live-fetched master
`ddb49269c46ca6fa150976681712b7118ea6b0ca`, which contains merged #1521:
branch `assistant/full-production-closure-20260913`. This is PARTIAL hardening,
not full conversational intelligence or production closure. Earlier checkpoints
below are historical evidence and are not test results for this continuation.

The existing Assistant handler now revalidates session/user/tenant/persona after
waiting for its existing lock, before saving/deleting, after guidance generation,
and before responding. The same serialization lock has a two-second acquisition
limit; timeout returns 503 without mutation. This bounds lock waiting, not the
number of HTTP threads or a canonical per-session rate quota. No second rate-limit
authority was introduced. Requests are limited to 65,536 encoded bytes; existing
8,000-character input, 200-message and 100-conversation limits remain enforced.

Every newly generated deterministic fallback passes an exact-field envelope
validator, including output length and public-source provenance bounds. It records
`live=false`, `cost_state=UNKNOWN`, `approval_state=NOT_REQUESTED`, and
`model_status=ASSISTANT_UNAVAILABLE`. Source observation time, content version and
evidence ID identify a snapshot, explicitly `SNAPSHOT_NOT_LIVE`. Historical
responses are not reclassified as live evidence. This validator is NOT evidence
of a model-output validation path: no conversational model is dispatched.

Desktop adds confirmed deletion through the existing authenticated delete operation
and 30-second waits for Assistant transport/founder checks. Stop waiting and widget
disposal discard the pending UI result; they do not claim to abort a server write.
After an ambiguous write the user must reload the durable conversation before
retrying. No paid/model dispatch exists on this path. Focus traversal uses Flutter's
reading-order policy; full keyboard/focus restoration acceptance remains unverified.
No V11, Home, Agents, attachment, factory, brand, workflow or database schema file
was changed by this continuation.

Mandatory 28.5 acceptance accounting:

| Area | Current evidence / remaining requirement |
| --- | --- |
| A UI / geometry | Existing L-overlay and canonical symbols preserved; new controls need executable Flutter/screenshot evidence. |
| B Authorization | In-flight logout/user/tenant/founder change tests reject response and leave version/messages unchanged. Rechecks are not a transaction with the separate identity store. |
| C History | Concurrent writers/replays, send-delete race, restart and account isolation covered by HTTP tests. Confirmed delete UI test added. |
| D Intelligence | BLOCKED: no admitted Assistant conversational invocation/skill binding in the current canonical provider configuration. No provider SDK or substitute authority added. |
| E Knowledge | BLOCKED: `DurableKnowledgeRuntime` constructs `IdentityKind.SERVICE`; authenticated human session to revocable project/workload/resource grant identity/provenance is missing from this adapter. Private retrieval remains closed. |
| F Factories | Add/remove registry regression covers dynamic discovery; names never imply runtime availability. |
| G Actions | Chat remains read-only. Existing explicit work confirmation/callback preserved; no publish/deploy/paid dispatch added. |
| H Cost | UNKNOWN. Canonical `GovernedRuntimeGateway.authorize_billable/reconcile_billable` and `GovernedAIProviderAdapter` exist, but no Assistant human-admission/reservation/unknown-result reconciliation binding is proven. Paid and zero-cost real model E2E NOT RUN. |
| I Security | 26 TR/EN fallback cases plus malformed envelope, bounds and concurrency tests. Pre-model forbidden-context/injected-retrieval tests remain BLOCKED because neither model input nor private retrieval is connected. No claim of model red-team completion. |
| J UX | Delete, timeout and late-response tests added; Flutter execution pending. Timeout only stops UI waiting, not backend execution. |
| K Accessibility | Normal-user founder semantics assertions added; reading-order traversal explicit. Keyboard-only navigation, focus restoration, text scaling, Windows 125/150 scaling and screenshots remain UNVERIFIED. |
| L Quality | See actual validation record below. No exact-head CI result, packaged runtime, production or deployment claim. |

Actual local validation for this continuation: focused/broader HTTP and Li/session
suite (`test_desktop_assistant_conversations.py`, `test_desktop_li_memory_transport.py`,
`test_desktop_li_founder_route.py`, `test_desktop_oidc.py`,
`test_desktop_oidc_persistence.py`, `test_li_app_runtime.py`) passed: **86 tests**.
Strict Mypy 1.8.0 passed both changed Python files; Ruff 0.1.9 passed both files;
`git diff --check` passed. These are local source-tree results, not CI evidence.
Python tools were installed under the scratch workspace after session renewal
removed the earlier installation. Local PyJWT is 2.14.0 (CI pins 2.13.0), so this is
not claimed to reproduce the complete locked CI environment.

Pre-commit was run once: end-of-file, whitespace, SF-19 secret scan and SF-20 DB
migration safety passed; YAML skipped; Ruff/Mypy hooks failed because the hook
executables were not found. Standalone Ruff/Mypy PASS does not turn that invocation
into pre-commit PASS. Flutter is not installed: focused/full Flutter tests, analyze,
pub get, screenshots and Windows scaling/runtime acceptance are ENVIRONMENT BLOCKED.
No SDK installation was attempted. No real model call, paid expenditure, merge,
deployment or Windows final acceptance was performed. CI start will be checked once
after publication; no CI results are claimed in this document.

Other incomplete 28.5 requirements: end-to-end model timeout/cancellation,
billable reservation/retry reconciliation, context/retrieval token and byte bounds,
canonical per-session concurrency admission, full sentinel coverage across model
inputs/logs/audit/serialized state, and live evidence TTL enforcement. These are
not completed by disabling retrieval or by the deterministic acceptance corpus.
The corpus proves the currently connected fallback contract only. Existing server
access logs do not include Assistant request bodies; no new telemetry authority
or prompt logging was added.


Source integration checkpoint (2026-09-13): PR #1485 at
`0a9a88bd26337aab7eafcaa21d2100070e2fefbc` is the current Desktop baseline.
Its 14 changed paths are inherited byte-for-byte into #1521. Assistant-specific
presentation changes are additive in V11 and its current app/bootstrap/client
owners; Home, Agents, Pixel Agents, attachments, and their tests are not rewritten.
Older open PR patches are not implementation sources.

V11 now owns a single localized Assistant trigger and an overlay above the
unchanged Home subtree. It keeps the overlay state on close/navigation and drops
it on session/principal/tenant/entitlement changes. Founder panel identity requires
the existing server-authoritative Li verification; normal users do not instantiate
the founder memory view. Explicit work submission reuses `onPromptSubmit` and the
existing governed Desktop intent path. Sending a chat message cannot execute work.

The existing Desktop identity HTTP adapter owns `/v1/assistant`; no second server,
identity/session authority, memory service, router, or execution gateway is added.
Account conversations use versioned private JSON documents under the existing
runtime root, atomically replaced after authenticated writes. Their namespace and
stored binding include canonical user, tenant, persona, and explicit null project/
workload scope. User-supplied scope/persona fields are rejected. Reauthentication
with the same account restores history; a different account/tenant/persona cannot
read, append, or delete it. Optimistic versions and message IDs reject stale writes
and mismatched replays. Limits: 100 conversations/account/persona, 200 messages per
conversation, 8000 characters per input. Explicit authenticated deletion is
supported; no implicit expiry. These documents are chat history, never Li memory
or Knowledge records. No existing database schema is changed.

Current grounding is bounded, deterministic public product guidance, with source
IDs/content versions and UNKNOWN for unconnected live or privileged sources.
This is not an unrestricted model copilot. User/project/workload-authorized private
retrieval and live job/CI/price sources remain unconnected. The existing Knowledge
runtime's service-principal tenant/project policy is not sufficient evidence of a
particular user's grants; no grant or model context is fabricated to close this gap.
These acceptance items remain BLOCKED pending canonical authenticated source
contracts. No private source is fetched on this fallback path.

Geometry reconciliation: the overlay now anchors to V11 viewport constraints,
independently of sidebar trigger spacing. At 1536x1024 the left arm targets
(0,482)-(290,995), and the chat arm (290,637)-(1524,995). Opening no longer changes
the selected page. Home/Agents/top bar remain the same underlying subtree; the
left arm may cover the lower sidebar while open, with its own close control.
Focused regression assertions cover these rectangles and preservation of existing
surfaces. Rendered geometry remains UNVERIFIED until Flutter evidence exists.

Private Knowledge dependency inspection at #1521 HEAD
`1fa5e3ad1cfbce106d6977446d5732b5dc04e32c`: `services.identity.AuthorizationEngine`
is the canonical generic authority, but `services/knowledge_runtime.py` constructs
an `IdentityKind.SERVICE` principal from fixed server policy. Its `_principal_scope`
and `services/knowledge_rag.py::PrincipalScope` do not resolve authenticated human
session grants or workload-bound grant identity. `services/app_auth_rbac_plan.py`
is explicitly planning-only. The missing dependency is a canonical resolver from
validated human session to revocable user/tenant/project/workload/resource grants,
with authorization identity/provenance before retrieval. No replacement authority
or service-principal substitution is introduced; private retrieval remains closed.

Pre-CI bounded follow-up validation (2026-09-13): `git diff --check` and Python
AST syntax parsing passed. Home, both Agents owner files, and the pixel office
asset were compared byte-for-byte with the current #1485 HEAD and are unchanged.
Flutter is unavailable; analyze/test and rendered geometry/theme/no-reflow evidence
are ENVIRONMENT BLOCKED. One pre-commit invocation returned `No module named
pre_commit`. The focused pytest invocation returned `No module named pytest`;
Ruff and strict Mypy modules are also absent. Added tests have not executed in
this follow-up. Earlier 23-test evidence belongs to the previous checkpoint only.
No installation/retry loop, CI monitoring, merge, deployment, or Windows final
acceptance was performed.

Authoritative repository: `Aliturgutt/ilaios`

Live master verified before this spec update: `9ac49d9407ff3062260780647220ff94a9890db5`

Foundation branch: `assistant/founder-user-copilot-foundation-20260913`

Foundation PR: `#1521`

Tracking issue: `#1520`

Historical merged Li foundations that MUST be reused, not duplicated:

- PR `#1274` — founder-only Desktop Li surface and server-authoritative `li_founder` entitlement
- PR `#1298` — Desktop Li persistent memory via the existing server-side Li authority

## Current canonical Desktop facts

The active Desktop application is Flutter and the active canonical shell is `ReferenceDesktopShellV11`.

Current relevant source paths:

- `apps/desktop/lib/app/desktop_app.dart`
- `apps/desktop/lib/app/desktop_bootstrap.dart`
- `apps/desktop/lib/app/ilaios_locale.dart`
- `apps/desktop/lib/features/dashboard/reference_desktop_shell_v11.dart`
- `apps/desktop/lib/features/dashboard/reference_home_dashboard_v3.dart`
- `apps/desktop/lib/features/navigation/desktop_section.dart`
- `apps/desktop/lib/features/li/li_view.dart`
- `apps/desktop/lib/identity/identity_client_core.dart`
- `apps/desktop/test/widget_test.dart`
- `apps/desktop/test/identity_client_test.dart`
- `services/desktop_identity_server_core.py`
- `services/desktop_oidc.py`
- `services/desktop_oidc_threaded.py`
- `services/desktop_oidc_windows.py`
- `apps/web_app_runtime/server.py`
- `tests/test_desktop_li_founder_route.py`
- `tests/test_desktop_li_memory_transport.py`
- `tests/test_li_app_runtime.py`

Current canonical shell geometry facts:

- `ReferenceDesktopShellV11` states that visual geometry follows the user-approved `1536 x 1024` reference set.
- `_CanonicalSidebar` currently has canonical width `219` px.
- Home is `ReferenceHomeDashboardV3`.
- The lower agent cards are rendered by `_AgentSection`; each `_AgentGroupCard` is `212` px high.
- Desktop locale already flows through `IlaiosLocaleScope` and must remain the single presentation-language source for Assistant/Li.

Important current-state gap:

- `LiView` exists and still enforces founder-only state/memory behavior.
- The current `DesktopSection` enum and the canonical 7-page `ReferenceDesktopShellV11` navigation do not currently expose Assistant/Li as a canonical overlay trigger.
- Therefore, do not create a second Li authority; integrate the approved presentation into the current canonical shell while reusing existing callbacks and server-side authorization.

## Final product split

### Shared sidebar product entry

The sidebar product entry is ALWAYS the localized Assistant label:

- Turkish Desktop locale -> `Asistan`
- English Desktop locale -> `Assistant`

This rule applies to BOTH founder and normal-user sessions.

Founder identity MUST NOT replace the sidebar label with `Li`.

### Founder experience

Authenticated canonical founder sees the same localized `Asistan` / `Assistant` sidebar entry below Settings.

Opening it presents `Li — Founder Intelligence` inside the panel.

Li uses the existing founder-only authority. Founder status is never inferred from label, email text, prompt text, local environment, or client-selected IDs.

### Normal-user experience

Normal authenticated users see the same localized `Asistan` / `Assistant` sidebar entry.

Opening it presents `ILAIOS Assistant`.

They MUST NOT see a Li label, Li tab, founder-memory control, founder-only state, or hidden-but-rendered founder content.

Normal-user Assistant is a product copilot, not a founder operator.

## Final Desktop visual contract

The user-approved target appearance is the supplied `1536 x 1024` reference mockup.

Do not redesign the Desktop home page. Do not shift, resize, reflow, or replace the nine factory cards when Assistant/Li opens.

Canonical/repo-derived value:

- normal sidebar width: `219 px`

Reference-image target measurements; these are visual targets and MUST be adapted to the live Flutter constraints instead of blindly hard-coded if the real viewport differs:

- Assistant/Li expanded left panel right edge: approximately `x = 289-290 px`
- left vertical panel starts: approximately `y = 482 px`
- left vertical panel ends: approximately `y = 995 px`
- left vertical panel height: approximately `513 px`
- lower horizontal chat arm starts: approximately `x = 289-290 px`
- lower horizontal chat arm top: approximately `y = 637 px`
- lower horizontal chat arm bottom: approximately `y = 995 px`
- lower horizontal chat arm width: approximately `1235 px`
- lower horizontal chat arm height: approximately `358 px`

The shape is intentionally an L-shaped overlay, not one large rectangle:

- from approximately `y=482` to `y=637`, only the left history/control column is expanded
- from approximately `y=637` to `y=995`, the chat surface extends right across the lower Home area
- the `Start work` surface remains visible and stationary
- all nine factory cards remain visible and stationary
- the `Agents` area may be covered by the lower chat arm while Assistant/Li is open
- no factory or top surface may be pushed sideways or vertically reflowed
- closing Assistant/Li returns the normal shell geometry without destroying conversation state

The visual must use the existing Desktop theme, spacing system, radius, typography, logos and monochrome UI rules. Do not introduce a parallel visual system.

The shared Assistant sidebar entry and authorized panel must consume the same
canonical symbol: `brand/assets/05-ilaios-app-icon.jpg` on dark surfaces and
`brand/assets/04-ilaios-symbol-light.jpg` on light surfaces. The existing
`Theme.of(context)` brightness and Desktop asset bundle remain the presentation
and loading authorities. Both symbols are already declared in Desktop
`pubspec.yaml`; do not copy raster files or edit that manifest for this feature.
Use scale-only `BoxFit.contain`, without tint, crop, gradient, glow, shadow, or
3D treatment. Do not introduce a Li-specific, robot, chat, star, or sparkle icon.
If genuinely needed, horizontal logos remain canonical 02 (dark) / 13 (light).
Verify against `brand/manifest.yaml` and `brand/README.md` before implementation.
Include both themes and runtime theme switching in tests and screenshot evidence.

## Language contract

There is no independent language selector inside Assistant/Li v1.

Desktop UI locale is authoritative:

- Turkish Desktop -> sidebar `Asistan`; opened normal-user panel copy in Turkish; opened founder Li panel copy in Turkish
- English Desktop -> sidebar `Assistant`; opened normal-user panel copy in English; opened founder Li panel copy in English
- changing Desktop locale changes Assistant/Li presentation language

Canonical product names may remain canonical where appropriate, but explanations, errors, guidance and conversation chrome follow the Desktop locale.

Authorization, policy, cost, approval, blocked, failed, UNKNOWN and UNVERIFIED states are computed before localization and MUST NOT differ by language.

## Attachment contract

Do not add a duplicate file/attachment button in the Assistant/Li composer.

The existing canonical Desktop file/reference input mechanisms remain the only upload/input authority. If Assistant/Li needs a file for a governed workflow, it must reuse the existing mechanism or prepare a proposal that transitions the user to the canonical flow.

## Conversation persistence contract

Closing Assistant/Li, navigating to another Desktop surface, or restarting Desktop MUST NOT implicitly delete the conversation.

Required conceptual binding for persisted conversations:

- `conversation_id`
- authenticated `user_id`
- `tenant_id`
- authorized `project_id` when applicable
- authorized `workload_id` when applicable
- mode/persona (`assistant` or founder `li`)
- Desktop locale/presentation preference
- `created_at`
- `updated_at`
- messages
- authorized context references/provenance

Chat history and memory are distinct:

- Chat history = previous conversations/messages
- Memory/Authorized Context = explicitly permitted durable preferences/facts/context

Do not store normal-user chat history in the founder Li memory store. Do not create a Desktop-local duplicate of the existing server-side Li memory authority.

## Knowledge and grounding contract

Assistant/Li must not treat model memory as ILAIOS source of truth.

Use the existing authorized knowledge/context architecture and enforce authorization before retrieved content is exposed to the model.

Minimum knowledge classes remain:

- `PUBLIC_PRODUCT`
- `USER_DOCUMENTATION`
- `TENANT_PROJECT`
- `INTERNAL_ENGINEERING`
- `FOUNDER_ONLY`

Normal users cannot retrieve founder memory, internal engineering content not explicitly authorized, private roadmap, privileged security details, or another tenant/project/workload context.

Li can consume founder-only context only when the current authenticated founder is authorized and the source is actually connected/current.

Repo, CI, deployment, runtime, job, pricing, factory capability and UI-state claims require authoritative/current sources. Missing or stale evidence yields `UNKNOWN` or `UNVERIFIED`, never fabricated certainty.

## Execution contract

Assistant/Li is advisory until the existing governed execution system accepts a proposal.

Required mutation path:

`Assistant/Li -> intent/proposal -> existing Policy/Approval/Budget authorities -> canonical ToolGateway -> existing factory/runtime`

Forbidden:

- direct Assistant/Li -> provider mutation
- direct Assistant/Li -> factory mutation that bypasses canonical gates
- second router
- second ToolGateway
- second policy/approval/budget authority
- second identity/session authority
- second Li memory authority

Paid/external work must use existing quote/budget/entitlement/approval rules. The Assistant must never invent a price or label a run free from model knowledge.

## Reuse requirements from merged Li work

PR `#1274` already established the intended security boundary:

- Li founder entitlement comes from canonical Desktop identity/session canonicalization
- customer OWNER is insufficient
- founder access is revalidated server-side
- non-founder fails closed

PR `#1298` already established persistent founder memory behavior:

- server-side `LiFounderOperator` remains the memory authority
- no Desktop-local Li memory database
- raw OIDC credential remains adapter-owned
- memory reads/writes reauthenticate and reauthorize founder access

The implementation must preserve these invariants while adapting the UI to the current canonical shell.

## Expected Desktop implementation surfaces

Astra must first verify current master and inspect these files before editing. These are the expected owner surfaces, not permission to modify all of them unnecessarily.

Primary UI owners likely required:

- `apps/desktop/lib/features/dashboard/reference_desktop_shell_v11.dart`
  - render a localized `Asistan` / `Assistant` entry below Settings for BOTH founder and normal users
  - choose the opened panel persona from authenticated authorization: founder -> `Li — Founder Intelligence`; normal user -> `ILAIOS Assistant`
  - host the L-shaped overlay without changing Home/factory geometry
  - preserve current canonical shell and top bar
- `apps/desktop/lib/features/dashboard/reference_home_dashboard_v3.dart`
  - expose/identify the lower Agents region only if needed for exact overlay anchoring
  - do not redesign Start Work or factory cards
- `apps/desktop/lib/features/li/li_view.dart`
  - evolve founder UI from minimal memory screen into the approved Li conversation surface while preserving founder verification/memory authority
  - do not make this founder-only view responsible for the shared sidebar label
  - do not add an independent locale picker or attachment authority
- `apps/desktop/lib/features/navigation/desktop_section.dart`
  - change only if the cleanest canonical integration actually requires a new section identity; an overlay trigger may be preferable if it avoids turning Assistant/Li into a normal page
- `apps/desktop/lib/app/ilaios_locale.dart`
  - add only required localized labels/copy; keep Desktop locale authoritative
- `apps/desktop/lib/app/desktop_app.dart`
  - thread only genuinely required callbacks/state into the canonical shell; existing Li callbacks must be reused

Identity/client owners to reuse and modify only if required by missing current behavior:

- `apps/desktop/lib/identity/identity_client_core.dart`
- `apps/desktop/lib/app/desktop_bootstrap.dart`
- `services/desktop_identity_server_core.py`
- `services/desktop_oidc.py`
- `services/desktop_oidc_threaded.py`
- `services/desktop_oidc_windows.py`
- `apps/web_app_runtime/server.py`

Do not edit those identity/server paths merely for visual work if current contracts already satisfy the requirement.

## Normal-user Assistant backend scope

The normal-user Assistant must not reuse founder-only Li memory or simply relax `li_founder` checks.

If current master lacks a canonical normal-user Assistant conversation API, implement the smallest additive contract that:

- binds every request/conversation to authenticated user + tenant and project/workload where applicable
- applies pre-retrieval authorization
- uses one authoritative knowledge model for TR/EN presentation
- separates user chat history from founder memory
- produces grounded answers with source provenance
- can prepare governed proposals without creating a direct execution shortcut

If implementing that backend would cross an unrelated active workstream or require a new authority, STOP and report the exact blocker rather than inventing an architecture.

## Required tests

Desktop visual/navigation tests:

- founder Turkish session sees `Asistan` below Settings, not `Li`
- founder English session sees `Assistant` below Settings, not `Li`
- opening founder Assistant entry presents `Li — Founder Intelligence` inside the panel
- normal Turkish user sees `Asistan`, never `Li`
- normal English user sees `Assistant`, never `Li`
- opening normal-user Assistant entry presents `ILAIOS Assistant`
- signed-out/non-founder cannot render founder Li controls
- opening Assistant/Li leaves Start Work and all nine factory cards at the same geometry
- lower overlay covers the Agents region rather than pushing/reflowing factories
- L-shape preserves the distinct left-only `482 -> 637` region and lower horizontal `637 -> 995` target geometry at the `1536 x 1024` reference viewport, allowing small implementation tolerance
- closing overlay restores the normal shell
- no independent Assistant/Li TR/EN selector exists
- no duplicate Assistant/Li attachment control exists
- Desktop locale switch changes Assistant/Li presentation language

Founder/security regressions:

- canonical founder accepted
- customer OWNER rejected
- forged prompt cannot elevate to founder
- malformed/false `li_founder` remains fail-closed
- `/v1/li/state` non-founder rejection remains intact
- founder memory read/write/reload remains server-authorized
- logout/session expiry removes founder access

Normal-user isolation regressions:

- cross-tenant retrieval rejected
- cross-project retrieval rejected
- cross-workload conversation/evidence reuse rejected where binding is required
- normal user cannot retrieve founder memory
- founder-only knowledge never appears in normal-user model context
- language change does not change authorization result

Persistence regressions:

- close/reopen retains conversation
- navigation away/back retains conversation
- full Desktop restart reloads authorized conversation history
- deletion/retention behavior is explicit and does not conflate chat history with memory

Grounding/action regressions:

- stale/missing source -> UNKNOWN/UNVERIFIED
- source provenance survives retrieval
- paid action cannot bypass quote/budget/entitlement/approval
- Assistant/Li cannot bypass Policy/Approval/ToolGateway

Likely test owners to inspect/reuse:

- `apps/desktop/test/widget_test.dart`
- `apps/desktop/test/identity_client_test.dart`
- `tests/test_desktop_li_founder_route.py`
- `tests/test_desktop_li_memory_transport.py`
- `tests/test_li_app_runtime.py`

Add narrowly named new tests when needed; do not overload unrelated tests or weaken existing assertions.

## Validation and closure

Before implementation:

1. fetch current remote `master` and record exact SHA
2. verify PR `#1521` head and base/currentness
3. inspect any active Desktop PRs that overlap the same files; if unsafe overlap exists, report BLOCKED instead of modifying another workstream
4. preserve all unrelated local/remote changes

Before any DONE claim:

- focused Desktop/Li/Assistant tests PASS
- relevant full Flutter tests PASS
- `flutter analyze` PASS
- relevant Python Pytest PASS
- Ruff PASS
- strict Mypy PASS where touched
- pre-commit PASS
- exact-head CI PASS
- current 1536 x 1024 screenshot evidence confirms approved geometry
- packaged/restart evidence confirms conversation persistence if that behavior is claimed
- real founder/non-founder runtime evidence confirms authorization behavior if production behavior is claimed

Do not merge automatically from stale evidence. Re-read current master immediately before merge and revalidate if master moved.

## Non-goals

- no redesign of Desktop
- no change to the nine factory taxonomy
- no new factory
- no new Core
- no second knowledge system for Turkish vs English
- no duplicate file uploader
- no separate Assistant language control
- no founder-data exposure to customers
- no replacement of current identity/session authority
- no weakening of fail-closed behavior
