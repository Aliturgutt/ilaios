# External Routing + UI/UX Clean-Room Gap Audit

Date: 2026-08-18
Base repository: `Aliturgutt/ilaios`
Base master audited: `9ba114e3f112c7041acf4f9a80d2a9a56b75d5b4`

## Decision

No third-party runtime is installed.

- OmniRoute is **not** introduced as a router, proxy, dependency, provider
  authority, or fallback authority.
- UI/UX Pro Max is **not** introduced as a runtime skill, design authority, or
  package dependency.
- Existing ILAIOS Core, Control Plane, routing truth, skill runtime, Web Factory,
  App Factory, Video Factory, OpenRouter integration and evidence authorities
  remain in place.

## Research references

- `diegosouzapw/OmniRoute@ea0cdc559ccc087d723f311a4217598cee4bb2b8`
- `nextlevelbuilder/ui-ux-pro-max-skill@a38d04c3d5c298c851dbe5e6ee1965ee3de42cb5`

Research use is limited to identifying general engineering problem classes. No
source code, prompt corpus, design database, template, provider list, proxy
implementation, or routing implementation is copied.

## Existing ILAIOS truth retained

The audited repository already contained:

- one canonical `RoutingDecision` truth and explicit prohibition on parallel
  routing authority;
- `services.ai_governance` with provider/model registry, policy routing, cost
  limits, retry limits and circuit breaking;
- video-specific provider registry/selection and OpenRouter adapters;
- `ilaios-ui-design`;
- website `design-intelligence`;
- native `app-design-quality`;
- the fixed SF-7 Software Factory skill registry.

Therefore creating a second router or adding a third-party design skill runtime
would be an architectural regression.

## Routing gaps closed additively

New ILAIOS-native modules provide bounded intelligence beneath the existing
router:

- `services/provider_catalog.py`
  - immutable versioned provider/model/pricing/quality snapshot;
  - freshness validation;
  - deterministic construction of the existing `ModelProviderRegistry`.
- `services/provider_state.py`
  - health success-rate/latency/circuit evidence;
  - request/token quota evidence;
  - explicit observation timestamps and freshness validation.
- `services/routing_intelligence.py`
  - capability + existing policy filtering;
  - stale/missing-state fail-closed behavior;
  - cost estimation;
  - deterministic weighted scoring over cost, latency, reliability, quality,
    and quota;
  - candidate-level exclusion/selection evidence;
  - policy narrowing only;
  - final model selection delegated to
    `services.ai_governance.route_model`.

The new routing skill is intentionally outside
`tools/software-factory/skills/`; the fixed 25-skill SF-7 registry is not
modified.

## UI/UX gaps closed additively

The existing ILAIOS UI resolver and quality evaluators are extended rather than
replaced.

Website evidence now detects, when applicable:

- missing meaningful text alternatives;
- unlabeled icon controls;
- hover-only interactions;
- missing persistent form labels;
- detached validation/error feedback;
- visible layout instability;
- navigation hierarchy/back behavior failures;
- inaccessible data visualization.

Native app evidence now detects, when applicable:

- platform safe-area/inset failures;
- broken back behavior;
- missing accessible control labels;
- insufficient touch spacing;
- text scaling/dynamic type failures;
- declared deep-link failures;
- inaccessible data visualization.

All new observations default to zero, preserving existing call sites and clean
PASS behavior unless the caller supplies evidence of a defect.

## Red-team invariants

The implementation is rejected if any of the following becomes true:

1. a second `RoutingDecision` authority is introduced;
2. external routing can widen ILAIOS policy;
3. stale provider state is silently treated as current;
4. missing required health/quota state is silently treated as available;
5. provider adapters choose fallback independently of canonical routing;
6. third-party code becomes a runtime dependency without separate review;
7. the SF-7 fixed skill registry is expanded incidentally;
8. UI quality logic can mutate/deploy/sign/authorize its own output;
9. Core files are changed for this feature;
10. existing clean design/routing tests regress.

## Verification targets

- `tests/test_routing_intelligence.py`
- `tests/test_design_intelligence_extension.py`
- existing `tests/test_ai_governance.py`
- existing `tests/test_design_quality.py`
- existing `tests/test_app_design_quality.py`
- existing `tests/test_ui_design_orchestrator.py`
- repository Required CI

Maturity must be derived from code/tests/CI/runtime evidence; this audit itself
does not promote the capability to production.
