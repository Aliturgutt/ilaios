# ILAIOS Assistant + Li Desktop Implementation Spec

## Status

Implementation specification for the existing foundation PR. This document does not claim runtime completion.

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
- The current `DesktopSection` enum and the canonical 7-page `ReferenceDesktopShellV11` navigation do not currently expose Li as a canonical section.
- Therefore, do not create a second Li authority; restore/integrate the presentation surface into the current canonical shell while reusing existing callbacks and server-side authorization.

## Final product split

### Founder experience

Authenticated canonical founder sees `Li` below Settings.

Opening it presents `Li — Founder Intelligence`.

Li uses the existing founder-only authority. Founder status is never inferred from label, email text, prompt text, local environment, or client-selected IDs.

### Normal-user experience

Normal authenticated users see:

- `Asistan` when Desktop locale is Turkish
- `Assistant` when Desktop locale is English

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

## Language contract

There is no independent language selector inside Assistant/Li v1.

Desktop UI locale is authoritative:

- Turkish Desktop -> `Asistan` and Turkish Assistant/Li copy
- English Desktop -> `Assistant` and English Assistant/Li copy
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
  - render Assistant/Li entry below Settings according to authenticated persona
  - host the L-shaped overlay without changing Home/factory geometry
  - preserve current canonical shell and top bar
- `apps/desktop/lib/features/dashboard/reference_home_dashboard_v3.dart`
  - expose/identify the lower Agents region only if needed for exact overlay anchoring
  - do not redesign Start Work or factory cards
- `apps/desktop/lib/features/li/li_view.dart`
  - evolve founder UI from minimal memory screen into the approved Li conversation surface while preserving founder verification/memory authority
  - do not add an independent locale picker or attachment authority
- `apps/desktop/lib/features/navigation/desktop_section.dart`
  - change only if the cleanest canonical integration actually requires a new section identity; an overlay trigger may be preferable if it avoids turning Li/Assistant into a normal page
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

- founder sees `Li` below Settings
- normal Turkish user sees `Asistan`, never `Li`
- normal English user sees `Assistant`, never `Li`
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
