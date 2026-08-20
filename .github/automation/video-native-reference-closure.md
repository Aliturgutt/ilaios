# Video Native Reference Closure Automation Checkpoint

Durable checkpoint for the ILAIOS Video Factory native photo-reference closure. Every automation run must read this file first, then re-read current `master`, exact CI/status, relevant implementation, deployment/runtime evidence, and current provider documentation/catalog where provider behavior is material. Live GitHub source/CI/runtime/deployment evidence overrides stale text here.

## Goal

Close the native photo-reference path end-to-end: secure signed short-lived HTTPS relay; OpenRouter `input_references` / `frame_images`; Desktop admitted-reference relay; visible subject/product/logo consistency QA without biometric/sensitive-trait inference; deterministic exact-original logo asset-lock for logo-only drift; fresh technical + semantic + reference-consistency QA after repair; real managed provider video; exact-head/exact-master CI; real relay deployment/configuration; baseline private visual-brief live certification; separate trusted-master native-reference live certification; receipt/artifact validation; exact-SHA `VERIFIED` only after all evidence passes.

## Non-negotiable invariants

- Preserve canonical Core, Policy, Approval, Tool Gateway, router, planner, QA, Evidence and tenant/security authorities.
- Preserve `verified-free` default and private multimodal visual-brief fallback; no automatic free-to-paid fallback.
- Managed certification provider spend remains `<= $1.00`.
- Relay URLs must be HTTPS, unguessable, HMAC-signed, expiring, SHA-bound and explicitly released; tenant/principal identities stay server-side.
- Native reference + QA is first-line continuity defense.
- Subject consistency is visible continuity only; never biometric identity or sensitive-trait inference.
- Logo asset-lock is allowed only for logo-only critical drift after subject/product critical scores pass. It uses exact admitted original logo bytes through canonical M18 FFmpeg and may not resize, crop, recolor, redraw, regenerate or substitute the logo.
- If exact safe logo compositing cannot be established, fail closed.
- After asset-lock require new final artifact SHA-256, H.264/AAC/1920x1080/duration technical PASS, fresh independent semantic PASS, fresh reference-consistency PASS, exact source-logo SHA, repaired-artifact SHA and append-only `video.logo_asset_lock` provenance.
- `frame_images` deterministically wins over general `input_references` when frame roles are present.
- Unknown/unproven general native capability retains private visual-brief fallback; required frame semantics fail closed.
- Never reuse stale CI after master advances.

## Current authoritative state — 2026-08-20

- Repo: `Aliturgutt/ilaios`
- Exact current master re-read: `3c9ab823d9c7f119c22a87942b3c8a183350a50a`.
- Native source PR #573 is MERGED, not open/draft. Merge SHA: `142b511051adbb00a786c523be8b72d0390c1eca`; merged head: `1abf21228b124596644f48c7798dd34839fcea86`.
- Current master is 46 commits ahead of the native merge. A live compare from `142b511...` to `3c9ab823...` showed no changes to the native Video reference implementation/workflow paths; intervening changes were Desktop/App/CI scoped.
- Native source implementation is therefore MERGED/source+CI implemented, but NOT production VERIFIED.
- Exact current master combined commit-status endpoint returned no standalone statuses during this run; do not infer certification from absence/presence of status rows.
- The baseline `Video Reference Production Certification` workflow still has `workflow_dispatch` and a push trigger guarded by `[video-reference-live-cert]`. The #573 merge did not use that baseline trigger token, so no baseline certification may be assumed from the merge.
- The connected GitHub tool currently exposes read/rerun Actions operations but no safe workflow-dispatch action. Do not synthesize a trigger by bypassing normal PR/master governance.

## Implemented and merged

- fail-closed OpenRouter `input_references` request shaping;
- deterministic `frame_images` precedence;
- short-lived signed HTTPS relay store + authenticated HTTP upload/delete + provider GET;
- SHA-256/MIME/magic validation, tenant/principal server-side binding, expiry/release and no signed-query logging;
- provider fetch access ledger;
- native relay binder with private visual-brief fallback on unproven models;
- relay lifetime bound to provider job lifecycle;
- Desktop managed-only relay configuration;
- subject/product/logo independent visible-consistency reviewer with explicit no-biometric/sensitive-trait rule;
- deterministic exact-original logo asset-lock using canonical M18 FFmpeg;
- logo-only repair policy; subject/product drift cannot be hidden by overlay;
- post-lock technical + semantic + reference-consistency revalidation;
- append-only `video.logo_asset_lock` evidence;
- native consistency/logo evidence preservation into canonical final result/QA;
- native provider relay evidence preservation into final result/QA: URL-used flag, mode, count, dispatch count, SHA bindings, relay-release flag;
- repaired final artifact SHA surfaced as `logo_asset_lock_repaired_artifact_sha256` when asset-lock is applied;
- real native-reference Desktop E2E harness at `apps/desktop/e2e/provider_video_native_reference_finished_product_e2e.py` using product + logo references, managed cap, final MP4/QA/SHA checks and relay access-ledger fetch proof;
- separate trusted-master workflow `.github/workflows/video-native-reference-production-certification.yml` with exact-SHA `ILAIOS Video Native Reference Live Certification` status and immutable proof artifact;
- baseline private visual-brief analyzer pinned to explicit `google/gemma-3-27b-it:free`; semantic QA routing remains separate.

## Baseline private visual-brief certification

Last proven blocker before the analyzer source fix was OpenRouter HTTP 404 while reference analysis used `openrouter/free`. Source now uses `google/gemma-3-27b-it:free` for reference analysis, but this is not runtime proof. A real trusted-master `Video Reference Production Certification` run must still prove exact-master real reference analysis + real managed provider MP4 + QA + receipt + bounded cost evidence. Do not claim baseline `VERIFIED` until that run exists and passes.

## External relay blocker — revalidated 2026-08-20

Repository relay code exists, but no real public relay deployment/configuration evidence exists yet. Connected Vercel was rechecked during this run: team `Aliturgut` (`team_xU1uFo3O6KclATgxI6LsumnA`) still has zero projects. There is no existing safe Vercel target for relay deployment. Do not invent/create paid/billing/DNS state.

Existing ILAIOS AWS production ALB remains intentionally restricted to the approved owner `/32`; do not widen it for provider fetch. Native live certification remains externally blocked until a separately authorized public HTTPS relay origin with bounded secrets/storage exists and Production secrets are configured.

Required Production secrets for native certification:

- `OPENROUTER_API_KEY`
- `ILAIOS_REFERENCE_RELAY_UPLOAD_URL`
- `ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN`

Relay server additionally requires:

- `ILAIOS_REFERENCE_RELAY_PUBLIC_BASE_URL`
- `ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN`
- `ILAIOS_REFERENCE_RELAY_SIGNING_SECRET`

## Remaining order

1. Keep current master/repo truth revalidated; never reuse stale PASS when master moves.
2. Do not create another native source PR unless a real regression/current-master incompatibility is evidenced.
3. When a safe Actions workflow-dispatch path becomes available, run baseline `Video Reference Production Certification` on exact current master and require real reference analysis + managed provider MP4 + QA + receipt + bounded cost PASS.
4. Establish separately authorized public HTTPS relay deployment without weakening the existing R03 network boundary; configure bounded Production secrets.
5. Run separate native-reference trusted-master certification only after relay URL/token prerequisites exist. Require provider fetch evidence for product + logo, `provider_native_reference_url_used=true`, `native_reference_mode=input-references`, managed terminal cost `<= $1.00`, real MP4, H.264/AAC/1920x1080/duration PASS, fresh semantic + reference-consistency PASS, direct logo fidelity PASS or deterministic exact asset-lock PASS, receipt/artifact SHA match, coordinator ACCEPTED, and append-only provenance.
6. Only after all exact-SHA evidence passes may native-reference status become `VERIFIED`.

If relay deployment remains blocked, continue only non-blocked repository/CI/runtime validation. Never fabricate `DONE`, `PRODUCTION`, `%100`, or `VERIFIED`.
