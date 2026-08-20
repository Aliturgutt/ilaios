# Video Native Reference Closure Automation Checkpoint

Durable checkpoint for the ILAIOS Video Factory native photo-reference closure. Every automation run must read this file first, then re-read current `master`, the authoritative PR/successor, exact-head/exact-master CI, failing logs, relevant implementation, deployment/runtime evidence, and current provider documentation/catalog where provider behavior is material. Live GitHub source/CI/runtime/deployment evidence overrides stale text here.

## Goal

Close the native photo-reference path end-to-end: secure signed short-lived HTTPS relay; OpenRouter `input_references` / `frame_images`; Desktop admitted-reference relay; visible subject/product/logo consistency QA without biometric/sensitive-trait inference; deterministic exact-original logo asset-lock when logo-only drift occurs; fresh technical + semantic + reference-consistency QA after repair; real managed provider video; exact-head CI; merge on exact current master; real relay deployment/configuration; baseline private visual-brief live certification; separate trusted-master native-reference live certification; receipt/artifact validation; exact-SHA `VERIFIED` only after all evidence passes.

## Non-negotiable invariants

- Preserve canonical Core, Policy, Approval, Tool Gateway, router, planner, QA, Evidence and tenant/security authorities.
- Preserve `verified-free` default and private multimodal visual-brief fallback; no automatic free-to-paid fallback.
- Managed certification provider spend remains `<= $1.00`.
- Relay URLs must be HTTPS, unguessable, HMAC-signed, expiring, SHA-bound and explicitly released; tenant/principal identities stay server-side.
- Native reference + QA is first-line continuity defense.
- Subject consistency is visible continuity only; never biometric identity or sensitive-trait inference.
- Logo asset-lock is allowed only for logo-only critical drift after subject/product critical scores pass. It uses exact admitted original logo bytes through canonical M18 FFmpeg and may not resize, crop, recolor, redraw, regenerate or substitute the logo.
- If exact safe logo compositing cannot be established, fail closed.
- After asset-lock require a new final artifact SHA-256, H.264/AAC/1920x1080/duration technical PASS, fresh independent semantic PASS, fresh reference-consistency PASS, exact source-logo SHA, repaired-artifact SHA and append-only `video.logo_asset_lock` provenance.
- `frame_images` deterministically wins over general `input_references` when frame roles are present.
- Unknown/unproven general native capability retains private visual-brief fallback; required frame semantics fail closed.
- Never reuse stale CI after master advances.

## Current authoritative state — 2026-08-20

- Repo: `Aliturgutt/ilaios`.
- Native implementation merge: PR #573, merge SHA `142b511051adbb00a786c523be8b72d0390c1eca`.
- Exact current master at this checkpoint: `af2f5206185cd79e56ed2431449d2bbb0e8ceed3`.
- Current master is 69 commits ahead of the native implementation merge and 0 commits behind it.
- A live commit comparison from `142b511051adbb00a786c523be8b72d0390c1eca` to `af2f5206185cd79e56ed2431449d2bbb0e8ceed3` shows no changes to the native Video reference implementation/workflow paths. Intervening changes are Desktop/App/Web-side work only.
- Current exact-master combined status includes `ilaios/required-ci-exact-master=success` targeting Actions run `32346877376`.
- Native source scope is therefore still present on current master and source/CI-implemented, but native production remains NOT VERIFIED.
- Stale checkpoint PR #585 is superseded by the current-master checkpoint successor created from `af2f5206185cd79e56ed2431449d2bbb0e8ceed3`.

## Implemented on master

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
- real native reference Desktop E2E harness at `apps/desktop/e2e/provider_video_native_reference_finished_product_e2e.py` using product + logo references, managed cap, final MP4/QA/SHA checks and relay access-ledger fetch proof;
- separate trusted-master workflow `.github/workflows/video-native-reference-production-certification.yml` with exact-SHA `ILAIOS Video Native Reference Live Certification` status and immutable proof artifact;
- baseline private visual-brief reference analyzer source-pinned to explicit `google/gemma-3-27b-it:free`; semantic QA routing remains separate.

## Baseline private visual-brief certification

The baseline source correction is merged, but a real exact-master trusted-master `Video Reference Production Certification` PASS is still required. Do not infer certification from source merge or CI. The PR #573 merge commit did not contain `[video-reference-live-cert]`, so baseline production certification must be proven by a real exact-master workflow run with real reference analysis, managed provider MP4, QA, receipt and bounded cost evidence.

## External native relay blocker — revalidated 2026-08-20

Repository relay code exists, but no real public relay deployment/configuration evidence exists. Connected Vercel team `Aliturgut` (`team_xU1uFo3O6KclATgxI6LsumnA`) was rechecked and still has zero Vercel projects. There is no existing safe Vercel deployment target for the relay.

Do not invent a project, spend money, alter billing/DNS, or silently broaden the existing AWS production ALB owner `/32` boundary. Native provider certification remains externally blocked until a separately authorized public HTTPS relay origin exists with bounded secrets/storage and the Production environment is configured.

Required Production secrets for native certification:

- `OPENROUTER_API_KEY`;
- `ILAIOS_REFERENCE_RELAY_UPLOAD_URL`;
- `ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN`.

Relay server additionally requires server-side:

- `ILAIOS_REFERENCE_RELAY_PUBLIC_BASE_URL`;
- `ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN`;
- `ILAIOS_REFERENCE_RELAY_SIGNING_SECRET`.

## Remaining order

1. Keep this checkpoint/current-master evidence accurate; never reuse stale master/CI evidence.
2. If a safe workflow-dispatch connector becomes available, run baseline `Video Reference Production Certification` on exact current master and require real PASS evidence; otherwise do not bypass governance merely to synthesize a trigger.
3. Establish a separately authorized real public HTTPS relay deployment without weakening the existing AWS network boundary; configure bounded Production secrets.
4. Run separate native-reference trusted-master certification only after relay URL/token Production secrets exist.
5. Require provider relay fetch evidence for product + logo, `provider_native_reference_url_used=true`, `native_reference_mode=input-references`, managed terminal cost `<= $1.00`, real MP4, H.264/AAC/1920x1080/duration PASS, fresh semantic + reference-consistency PASS, and logo direct-PASS or deterministic asset-lock PASS.
6. Validate receipt/artifact SHA, coordinator `ACCEPTED`, append-only evidence/provenance; only then publish exact-SHA native-reference `VERIFIED`.

If external relay deployment remains blocked, continue all non-blocked repository/CI work. Never fabricate `DONE`, `PRODUCTION`, `%100`, or `VERIFIED`.
