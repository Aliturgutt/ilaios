# OpenRouter Production Telemetry Activation

Date: 2026-08-18

## Objective

Activate real OpenRouter catalog/pricing, account-quota and observed gateway-health
telemetry beneath the existing ILAIOS canonical routing authority without
installing a second router, changing Core, or persisting provider credentials.

## Architecture boundary

The implementation is additive:

```text
OPENROUTER_API_KEY (secret injection only)
        |
        +--> GET /api/v1/models/user
        |       -> authenticated model eligibility + live pricing
        |
        +--> GET /api/v1/key
                -> current key limit / remaining credit

read-only telemetry
        |
        v
OpenRouterCatalogSource + OpenRouterRuntimeSource
        |
        v
existing GovernedRoutingRuntime
        |
        v
existing RoutingIntelligenceEngine
        |
        v
existing route_model canonical authority
        |
        v
ilaios.routing-evidence.v1
```

`services/openrouter_routing_sources.py` does not call inference endpoints and
does not select a final model. It implements the already-defined
`ProviderCatalogSource` and `ProviderRuntimeSource` contracts and delegates the
actual routing decision through the existing runtime.

## Catalog / pricing truth

Only model IDs explicitly supplied by the ILAIOS caller are admitted. The
authenticated OpenRouter user catalog cannot add models or capabilities to the
caller configuration.

For every configured model, current prompt/completion pricing must be present,
finite and non-negative. Per-token prices are normalized to the existing
`ModelRecord` per-million-token cost fields. Missing, malformed, duplicate or
unavailable configured models fail closed.

The catalog snapshot identity is a SHA-256 digest over normalized, non-secret
model/capability/context/pricing facts.

## Quota truth

The authenticated `/key` observation supplies the current key
`limit_remaining` value. The existing routing quota schema is token-based, so a
finite positive credit balance is converted conservatively using the most
expensive live per-token price among the configured models:

```text
remaining_tokens = floor(limit_remaining_usd / worst_live_per_token_price)
```

This conversion cannot overstate the purchasable token count for the configured
model set. A zero remaining credit balance yields zero token quota for paid
models and existing routing fails closed. If all configured models have exactly
zero prompt/completion price, credit exhaustion is not falsely represented as a
token quota failure. An unlimited/null provider credit limit remains `None`
rather than inventing a number.

OpenRouter's deprecated rate-limit metadata is not treated as live remaining
request quota. `remaining_requests` therefore stays unknown instead of being
fabricated.

## Health truth

The provider identity at this boundary is `openrouter`. Health evidence is the
bounded, actually observed authenticated OpenRouter gateway telemetry path, not
a fabricated underlying-provider uptime claim. The shared probe window records:

- success ratio of catalog/quota observations;
- p95 successful probe latency;
- consecutive observation failures.

A current catalog/key observation failure fails the route before selection, so
no optimistic health default is used. This does not claim model-host endpoint
health for OpenRouter's underlying providers; such per-endpoint health can be a
later, separately governed management-key enhancement if required.

## Secret boundary

`OPENROUTER_API_KEY` is read from the configured secret environment at
observation time. It is never part of:

- a catalog snapshot;
- a runtime snapshot;
- routing evidence;
- cache/version material;
- exception text;
- production certification artifacts.

No API key or token is committed to the repository.

## Production certification

`.github/workflows/openrouter-production-telemetry-certification.yml` performs a
read-only production proof using GitHub Environment `Production` and its
`OPENROUTER_API_KEY` secret.

The proof calls only:

- `GET /api/v1/key`
- `GET /api/v1/models/user`

It submits no inference request and therefore cannot intentionally consume model
inference spend. The persisted receipt contains only sanitized quota/catalog
facts and a pricing digest.

Repository workflow security policy forbids `pull_request_target`, forbids
secrets in ordinary workflows, and requires external/secret-sensitive workflows
to be manual-only. This certification is therefore explicitly registered in the
existing `_MANUAL_ONLY` and `_SECRET_ALLOWED` workflow allowlists and exposes
only `workflow_dispatch`. It grants `contents: read`, performs no checkout, and
uses only an immutable pinned artifact-upload action.

This means production credential proof cannot be auto-triggered by an arbitrary
branch or pull request. A trusted operator must dispatch the workflow after the
implementation is merged. This is an intentional security boundary, not a
missing routing feature.

## Red-team invariants

Activation is rejected if any of the following becomes true:

- live provider data can widen caller model/capability policy;
- a second final-selection or fallback authority is created;
- stale/malformed/missing pricing or quota is silently accepted;
- secret material enters evidence, logs, errors or source;
- provider read failure is converted into optimistic availability;
- a production certification submits inference or a paid generation request;
- production secrets become available to automatic PR/push workflows;
- Core, Video Factory routing authority, or the fixed SF-7 registry is rewritten.

## Verification requirement

Repository implementation is not a production claim. Required CI must pass on
the exact implementation head. After merge, the manual production certification
must produce an observed PASS receipt from the real `Production`
`OPENROUTER_API_KEY` before provider telemetry may be reported as production
verified.
