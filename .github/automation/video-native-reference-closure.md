# Video Native Reference Closure Automation Checkpoint

Durable checkpoint for the ILAIOS Video Factory native photo-reference closure. Every automation run must read this file first, then re-read current `master`, the authoritative PR/successor, exact-head CI, failing logs, relevant implementation, deployment/runtime evidence, and current provider documentation/catalog where provider behavior is material. Live GitHub source/CI/runtime/deployment evidence overrides stale text here.

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

- Repo: `Aliturgutt/ilaios`
- Exact master re-read before successor creation: `01eb6bcfe5a98d2833a77683c973062f87cb1e73`
- Stale PR #561 was closed unmerged after its exact head became 12 master commits stale.
- Intervening master changes were compared and did not overlap the native Video reference paths.
- Authoritative PR: #573
- Branch: `agent/video-native-reference-relay-r3`
- PR base: exact master `01eb6bcfe5a98d2833a77683c973062f87cb1e73`
- Current head before this checkpoint update: `53b0d01d39f8252d7c6853fbb757423722a41aff`; this checkpoint write advances the head again, so re-read it before any action.
- PR remains DRAFT until fresh exact-head CI, real relay deployment, baseline private-brief certification and native live certification are evidence-backed.

## Implemented on authoritative branch

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
- baseline private visual-brief reference analyzer corrected from the prior `openrouter/free` alias to explicit `google/gemma-3-27b-it:free` after current official OpenRouter evidence confirmed that exact route is free and vision-language/multimodal. This is source-implemented only; trusted-master live certification is still required.

## Provider truth revalidated on 2026-08-20

Current official OpenRouter documentation confirms:

- `/api/v1/videos` supports `input_references` for reference-to-video and `frame_images` for image-to-video;
- if both are present, `frame_images` takes precedence;
- reference assets for provider generation require stable directly downloadable public HTTPS URLs;
- `google/gemma-3-27b-it:free` is currently listed as free and supports vision-language/image input.

Provider documentation/catalog truth must be re-checked again before any paid/native live call if material provider behavior changes.

## Current exact-head CI

Head `53b0d01d39f8252d7c6853fbb757423722a41aff` triggered fresh CI after the analyzer correction. At last read:

- Software Factory Final Evidence: running
- Product Surface Parity Gate: running
- Required CI Gate: pending
- ILAIOS Desktop CI: pending
- ILAIOS Desktop Windows Gate: pending
- ILAIOS Desktop MSIX Packaging: pending
- Browser Skill Playwright E2E: pending

This checkpoint update creates a newer head. The next run must ignore the above as merge evidence and read workflows for the new exact head.

## Baseline private visual-brief certification

Last real trusted-master blocker was OpenRouter HTTP 404 while reference analysis used `openrouter/free`. The source now pins the analyzer to explicit current free multimodal `google/gemma-3-27b-it:free`; semantic QA routing remains separate. This is not `VERIFIED`. After safe merge, rerun trusted-master `Video Reference Production Certification` on the exact merge SHA and require real reference analysis + real provider MP4 + QA + receipt + bounded cost evidence.

## External relay blocker

Repository relay code exists, but no real public relay deployment/configuration evidence exists yet. Vercel was re-checked through the connected account on 2026-08-20: team `Aliturgut` (`team_xU1uFo3O6KclATgxI6LsumnA`) currently has zero Vercel projects. There is therefore no existing Vercel project onto which this relay can be safely deployed from the connected tooling. Do not invent a deployment or create paid/billing/DNS state.

Existing ILAIOS AWS production ALB is intentionally restricted to the approved owner `/32`; widening it for provider fetch would violate the current network boundary. Do not silently broaden that ALB. A real native provider certification remains externally blocked until there is a separately authorized public HTTPS relay origin with bounded secrets/storage and the Production environment is configured.

Required Production secrets for native certification:

- `OPENROUTER_API_KEY` (existing provider credential),
- `ILAIOS_REFERENCE_RELAY_UPLOAD_URL` (real HTTPS upload endpoint),
- `ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN` (server-held upload/delete/access-evidence bearer).

Relay server additionally requires server-side `ILAIOS_REFERENCE_RELAY_PUBLIC_BASE_URL`, `ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN`, and `ILAIOS_REFERENCE_RELAY_SIGNING_SECRET` outside the repository.

## Remaining order

1. Re-read new exact head and fresh exact-head gates; repair only evidenced failures.
2. Keep PR #573 current with master; if master advances, replay only the reviewed bounded delta plus the explicit analyzer correction onto one exact-current-master successor and rerun all gates.
3. When repo work is current and exact-head green, mark PR ready and merge only with expected-head protection and the exact trusted-master trigger token required by the native workflow (`[video-native-reference-live-cert]`) if native live prerequisites are actually configured. Do not deliberately trigger a known-unconfigured native cert just to create a failure.
4. Establish a separately authorized real public HTTPS relay deployment without weakening the existing R03 network boundary; configure bounded Production secrets.
5. Rerun baseline private visual-brief trusted-master certification on exact merged master and require PASS.
6. Run separate native-reference trusted-master certification. Require provider relay fetch evidence for product + logo, `provider_native_reference_url_used=true`, `native_reference_mode=input-references`, managed terminal cost `<= $1.00`, real MP4, final technical/semantic/reference-consistency PASS, and logo direct-PASS or deterministic asset-lock PASS.
7. Validate receipt/artifact SHA and append-only evidence/provenance; only then publish exact-SHA native-reference `VERIFIED`.

If external relay deployment remains blocked, continue all non-blocked repository/CI work. Never fabricate `DONE`, `PRODUCTION`, `%100`, or `VERIFIED`.
