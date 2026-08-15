# Web Factory Finished-Product Evidence — 2026-08-16

## Purpose

This is an observed implementation/evidence snapshot for the Web Factory closure work in PR #206. It is not a canonical architecture replacement and it does not claim production deployment.

## Truth boundary

Current repository implementation in this changeset adds a bounded finished-product Web path:

```text
authenticated Desktop intent
-> canonical Execution Coordinator
-> ilaios.capability.web-factory
-> web.product-runtime.v1
-> WebsiteSpec
-> native DesignStrategy
-> generated multi-route artifact
-> structural/security/SEO/accessibility QA
-> content-addressed acceptance evidence
```

The path remains under the existing Control Plane, governance, tenant/session ownership and durable grant boundaries. No second Core, second coordinator, factory-owned deployment authority, provider-owned orchestration authority, DNS mutation or billing mutation is introduced.

## Implemented evidence surface

- `services/integrations/web_factory.py`
  - deterministic generic `WebsiteSpec` derivation;
  - context-derived native design strategy;
  - EN/TR route generation when requested;
  - semantic HTML, CSP, canonical/OG metadata, robots/sitemap;
  - focus/reduced-motion and responsive transformations;
  - per-file SHA-256, artifact hash, spec hash and tamper-evident acceptance manifest;
  - explicit `NOT_DEPLOYED` truth.
- `services/integrations/web_product_runtime.py`
  - canonical `web.product-runtime.v1` adapter;
  - Control Plane goal/job/proposal lifecycle;
  - governance admission;
  - durable execution grant;
  - tenant/principal-bound result manifest;
  - no production deployment claim.
- `services/execution_coordinator.py`
  - Web intent routes to `web.product-runtime.v1` when the runtime is configured;
  - unsupported capabilities remain fail-closed.
- `apps/desktop/sidecar/ilaios_control_plane_sidecar.py`
  - shared Desktop composition root wires the Web runtime without changing the canonical coordinator authority.
- `services/integrations/web_deployment.py`
  - provider-neutral deployment receipt validation only;
  - exact source SHA + artifact digest + site identity linkage;
  - HTTPS live URL, health verification, browser verification and rollback reference required before deployment evidence can be trusted;
  - the contract itself performs no provider, DNS, secret, billing or deployment mutation.

## Test and CI acceptance rule

Before merge, the exact PR head must pass all relevant current repository gates, including:

- Required CI Gate;
- Platform full pytest, Ruff and strict MyPy;
- Website CI including native design, golden Web Factory, finished-product Web runtime/browser rendering and deployment-receipt tests;
- secret scanning;
- repository malware scan;
- CI supply-chain hardening;
- Desktop CI;
- Windows release/bundled-control-plane E2E;
- Desktop MSIX packaging.

Browser evidence for the generated artifact is intentionally local/CI evidence, not a production-domain claim. The generated-site test launches a real headless Chrome/Chromium render at 320, 360, 390, 412, 430, 768, 1024 and 1440 pixel widths.

## Deployment boundary

A generated website must not be called `DEPLOYED` or `PRODUCTION` merely because source or an artifact exists. Production promotion requires a canonical deployment actuator to produce evidence that can satisfy `WebDeploymentReceipt`:

```text
verified artifact digest
+ exact source commit SHA
+ site identity
+ provider deployment ID
+ HTTPS live URL
+ health verification
+ real browser verification
+ rollback reference
```

Until that external deployment evidence exists, the finished-product runtime truth remains `NOT_DEPLOYED`.

## Remaining scope distinction

This changeset verifies the governed local finished website artifact path and its deployment-evidence contract. It does not claim that arbitrary paid provider accounts, customer DNS, production credentials, third-party form/newsletter/search services, ecommerce payments or external publishing effects are provisioned. Those effects remain separate governed adapters and must fail closed when unavailable.
