# Video Native Reference Closure Automation Checkpoint

Durable checkpoint for the ILAIOS Video Factory native photo-reference closure. Every automation run must read this file first, then re-read current `master`, PR #561 or its explicit successor, exact-head CI, failing logs, and relevant implementation. GitHub source/CI/runtime/deployment evidence overrides stale text here.

## Goal

Close the native photo-reference path end-to-end: secure signed short-lived HTTPS relay; OpenRouter `input_references` / `frame_images`; Desktop admitted-reference relay; visible subject/product/logo consistency QA without biometric/sensitive-trait inference; deterministic exact-original logo asset-lock when logo-only drift occurs; fresh technical + semantic + reference-consistency QA after repair; real managed provider video; exact-head CI; merge on exact current master; real relay deployment/configuration; separate trusted-master native-reference live certification; receipt/artifact validation; exact-SHA `VERIFIED` only after all evidence passes.

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

## Current authoritative state — 2026-08-19

- Repo: `Aliturgutt/ilaios`
- Current master last re-read: `c5b59325c88b5a0e047a21682da5d3cbf588507a`
- Authoritative PR: #561
- Branch: `agent/video-native-reference-relay-r2`
- PR base: exact current master `c5b59325c88b5a0e047a21682da5d3cbf588507a`
- Latest head before this checkpoint update: `5691741a59f3fc22df04d3119584873d337461ea`; re-read exact head before every action because this file update advances it.
- PR remains DRAFT until repo CI, live relay, baseline private-brief certification and native live certification are all evidence-backed.

## Implemented on branch

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
- baseline private reference analyzer moved from failing `openrouter/free` route to current live-catalog free multimodal model `google/gemma-4-26b-a4b-it:free`; this is source-implemented but still requires trusted-master live certification before declaring restoration;
- real native reference Desktop E2E harness added at `apps/desktop/e2e/provider_video_native_reference_finished_product_e2e.py`; it uses product + logo references, managed provider cap, final MP4/QA/SHA checks and relay access-ledger fetch proof;
- separate trusted-master workflow added at `.github/workflows/video-native-reference-production-certification.yml` with distinct `ILAIOS Video Native Reference Live Certification` exact-SHA status and immutable proof artifact.

## Current exact-head CI

On head `5691741a59f3fc22df04d3119584873d337461ea` at last read:

- Software Factory Final Evidence: PASS
- Required CI Gate: pending
- ILAIOS Desktop CI: pending
- ILAIOS Desktop Windows Gate: queued
- ILAIOS Desktop MSIX Packaging: pending

This checkpoint update creates a newer head, so the next run must ignore the above as merge evidence and read the fresh exact-head runs.

## Baseline private visual-brief certification

Last trusted-master failure was real OpenRouter HTTP 404 while reference analysis used `openrouter/free`. Live official OpenRouter catalog/API research on 2026-08-19 confirmed explicit free multimodal `google/gemma-4-26b-a4b-it:free` with image input and structured-output support. PR #561 pins the private reference analyzer to that explicit free model while leaving semantic QA routing separate. This is not yet VERIFIED: after merge, rerun trusted-master `Video Reference Production Certification` on the exact merge SHA and require real analysis + real provider MP4 + QA + receipt + cost evidence.

## External relay blocker

Repository relay code is implemented, but no real public relay deployment/configuration evidence exists yet. Existing ILAIOS AWS production ALB is intentionally restricted to the approved owner `/32`; widening it for provider fetch would violate the existing network boundary. A native provider relay therefore needs a separately authorized public HTTPS deployment with bounded secrets/storage and cost. Do not silently broaden the existing production ALB or incur new infrastructure spend without an explicit bounded authority. Until a real public relay URL and bearer credential exist in the GitHub Production environment, native live certification must remain blocked/fail-closed.

Required Production secrets for the new native cert are:

- `OPENROUTER_API_KEY` (existing provider credential),
- `ILAIOS_REFERENCE_RELAY_UPLOAD_URL` (real HTTPS upload endpoint),
- `ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN` (server-held upload/delete/access-evidence bearer).

Relay server itself additionally requires server-side `ILAIOS_REFERENCE_RELAY_PUBLIC_BASE_URL`, `ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN`, and `ILAIOS_REFERENCE_RELAY_SIGNING_SECRET` outside the repository.

## Remaining order

1. Read fresh head + fresh exact-head five gates; repair only evidenced failures.
2. Add/fix regression/security tests for the new native live workflow if CI identifies any issue.
3. Keep PR current with master; if master advances, create/replay a current-master successor rather than reusing stale green evidence.
4. Obtain/establish a separately authorized real public HTTPS relay deployment without weakening the existing R03 network boundary; configure Production secrets.
5. When repo work is exact-head green and current, mark PR ready and merge with expected-head protection and appropriate trusted-master trigger token(s).
6. Rerun baseline private visual-brief trusted-master certification and require PASS on exact merge SHA.
7. Run separate native-reference trusted-master certification. Require provider relay fetch evidence for both product and logo, `provider_native_reference_url_used=true`, `native_reference_mode=input-references`, managed terminal cost `<= $1.00`, real MP4, final technical/semantic/reference-consistency PASS, and logo direct-PASS or deterministic asset-lock PASS.
8. Validate receipt/artifact SHA and append-only evidence/provenance; only then publish exact-SHA native-reference VERIFIED.

If external relay deployment remains blocked, continue all non-blocked repository/CI work and report the precise blocker. Never fabricate `DONE`, `PRODUCTION`, or `VERIFIED`.
