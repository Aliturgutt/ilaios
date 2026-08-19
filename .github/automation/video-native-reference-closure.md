# Video Native Reference Closure Automation Checkpoint

This file is the durable execution checkpoint for the ILAIOS Video Factory native photo-reference closure. Automation runs must read this file first, then re-read current `master`, the authoritative PR/successor, exact-head CI, and the relevant implementation files before changing anything. GitHub code/tests/CI/runtime/deployment evidence always overrides stale text in this checkpoint.

## Goal

Close the native photo-reference path end-to-end:

1. secure short-lived HTTPS photo relay,
2. provider `input_references` / `frame_images` wiring,
3. Desktop-uploaded admitted reference bytes relayed directly to the selected provider,
4. visible subject/product/logo consistency QA,
5. deterministic original-logo asset-lock repair when native generation distorts the logo,
6. fresh final technical + semantic + reference-consistency QA after any logo repair,
7. real managed provider video generation,
8. exact-head CI,
9. merge on exact current master,
10. real relay deployment/configuration,
11. trusted-master native-reference live production certification,
12. exact-SHA `VERIFIED` only after receipt/artifact validation.

## Non-negotiable invariants

- Do not redesign or duplicate Core, Policy, Approval, Tool Gateway, router, planner, QA engine, or governance.
- Preserve `verified-free` default behavior and the existing private multimodal visual-brief fallback.
- No automatic free-to-paid fallback.
- Managed provider hard cap remains `<= $1.00` total for the certification path.
- Do not weaken security, CI, semantic QA, technical QA, or consistency thresholds to obtain green status.
- Raw Desktop reference bytes remain private except for the bounded short-lived relay publication required by the selected provider.
- Relay URLs must be HTTPS, unguessable, signed, expiring, integrity-bound, and released when the provider job no longer needs them. Tenant/principal identities must not be embedded in public URLs.
- Subject consistency is visible continuity only (appearance/clothing/hair/silhouette/non-sensitive cues). Do not perform biometric identity verification or infer sensitive traits.
- Product consistency checks visible geometry/proportions/materials/colors/markings.
- Logo consistency checks visible shape/text-mark structure/colors/placement.
- Native reference + QA is the first line of defense for photo/subject/product/logo continuity.
- Logo integrity must not depend only on generative redraw. If native generation fails logo consistency while subject/product critical scores still pass, use the exact admitted original logo bytes through deterministic asset-lock compositing, then re-run final QA.
- Logo asset-lock must never silently resize, crop, recolor, redraw, regenerate, or substitute the logo. If the exact original asset cannot be composited safely at its admitted dimensions, fail closed rather than degrade it.
- Logo asset-lock may not hide subject or product drift. If subject/product critical scores fail, reject/regenerate rather than overlaying a logo and accepting the video.
- Any asset-lock repair must produce fresh technical evidence, fresh semantic QA, fresh reference-consistency QA, a new final artifact SHA-256, and append-only EvidenceStore provenance. Final receipt must state whether asset-lock was applied and the exact source-logo SHA-256.
- `frame_images` exact first/last-frame mode takes deterministic precedence over general `input_references` when both semantics could otherwise collide.
- Unknown/unproven native model capability must fail closed for required first/last-frame semantics; general references may retain private visual-brief fallback.
- Never use stale green CI after master advances. Replay reviewed delta onto exact current master and re-run all gates.

## Current authoritative checkpoint — 2026-08-19

- Repo: `Aliturgutt/ilaios`
- Master last observed: `a654ba997db335fdf45836ed076334ee8b015471`
- Authoritative native-reference PR: `#561`
- Branch: `agent/video-native-reference-relay-r2`
- PR base last observed: `a654ba997db335fdf45836ed076334ee8b015471`
- PR head is advancing under this checkpoint; always re-read exact head before acting.
- PR state: draft/open/mergeable.

Implemented on the native branch so far:

- fail-closed OpenRouter `input_references` request shaping,
- deterministic `frame_images` precedence,
- short-lived HMAC-signed HTTPS relay core,
- authenticated relay HTTP upload/delete boundary,
- SHA-256 and MIME/magic integrity checks,
- tenant/principal server-side relay binding,
- no signed-query logging,
- relay expiry and explicit release,
- native reference binder with private visual-brief fallback on unproven models,
- managed provider lifecycle wiring that keeps relay alive through provider execution and releases on terminal status,
- Desktop managed-only relay configuration gate,
- Desktop `first_frame` / `last_frame` roles and backend admission only when relay configuration is present,
- subject/product/logo independent visual-consistency reviewer,
- consistency reviewer explicitly forbids biometric identity/sensitive-trait inference,
- native relay configuration negative tests,
- evidence artifact/provenance support for consistency QA,
- native relay-enabled Desktop composition selects consistency-verified managed runtime,
- deterministic original-logo asset-lock compositor using canonical M18 FFmpeg overlay,
- no-resize/no-crop/no-recolor/no-redraw logo preservation policy,
- deterministic EN/TR placement vocabulary with bottom-right safe default and ambiguity fail-closed behavior,
- runtime policy that permits asset-lock only for logo-only critical drift and never for subject/product failures,
- post-asset-lock technical + semantic + reference-consistency revalidation,
- distinct append-only `video.logo_asset_lock` evidence with source logo SHA and repaired artifact SHA.

Re-read exact current head and workflow runs every iteration; old PASS/FAIL evidence is stale after any branch update.

## Baseline prerequisite blocker

Trusted-master `Video Reference Production Certification` on exact master `a654ba997db335fdf45836ed076334ee8b015471` was rerun after an initial ffmpeg package-download timeout. On rerun, ffmpeg installed successfully and the real E2E started. It then failed before video generation because private reference image analysis returned HTTP 404 from OpenRouter while using analyzer route/model `openrouter/free`.

Do not hide this failure. Diagnose against the live authoritative OpenRouter catalog/API. Select only an actually supported free multimodal analysis route or another evidence-backed configuration that preserves the existing reference-analysis semantics. Restore the baseline private visual-brief production certification before claiming native closure.

## Required exact-head gates before merge

All of the following must PASS on the same exact native PR head:

- Required CI Gate
- Software Factory Final Evidence
- ILAIOS Desktop CI
- ILAIOS Desktop Windows Gate
- ILAIOS Desktop MSIX Packaging

If any fails, inspect the exact job/log and fix only the root cause. Do not merge while draft or while any exact-head gate is incomplete/failing.

## Remaining native implementation/certification work

1. Re-read the current PR head and current master; create a successor if stale.
2. Resolve all strict pytest/Ruff/Mypy/Flutter/Windows/MSIX failures on exact head.
3. Verify native consistency QA and logo asset-lock output are surfaced into the final execution/receipt evidence used by certification; add regression tests if any fields are dropped by an upper runtime layer.
4. Add a separate trusted-master native-reference production certification workflow/status; do not reuse the private-brief certification as proof of native provider references.
5. The native certification must use a real HTTPS relay deployment/configuration with secrets outside the repository.
6. Certification must upload a Desktop reference image and prove the provider fetched a signed relay URL.
7. Prove `provider_native_reference_url_used=true` and native mode (`input-references` or `frame-images`) in durable receipt evidence.
8. Generate a real provider MP4 under `managed-bounded` with actual terminal provider cost evidence `<= $1.00`.
9. Validate H.264/AAC, 1920x1080, requested-duration tolerance, artifact size/digest, semantic QA, technical QA, and generated shot count.
10. Validate subject/product/logo consistency QA where applicable, including threshold and evidence digest/provenance hash.
11. Include a logo-drift certification case: native generation must either pass logo consistency directly or trigger deterministic original-asset lock; if asset-lock is applied, prove source-logo SHA, no resize/crop/recolor/redraw, repaired artifact SHA, final technical QA PASS, final semantic QA PASS, final logo consistency PASS, and evidence-chain provenance.
12. Prove immutable reference binding remains retained, private local raw blob is released after success, and relay item is released/expired after provider use.
13. Validate exact revision SHA in receipt/artifact and publish a distinct native-reference live certification status.
14. Only then report `VERIFIED` for that exact certified SHA.

## Automation behavior

At each run:

1. Read this checkpoint file.
2. Read current `master` SHA.
3. Read PR `#561`; if stale/closed/superseded, follow the explicit successor only.
4. Read exact-head workflow runs and failing job logs.
5. Read changed implementation files relevant to the next fix before writing.
6. Perform all non-blocked repo work autonomously.
7. Treat logo asset-lock as mandatory closure scope, not a future enhancement.
8. If master advanced, compare/replay onto a current-master successor; never reuse stale green evidence.
9. If all exact-head gates PASS and branch is current, make PR ready and merge only with expected-head protection and the appropriate trusted-master certification trigger token.
10. Run/verify baseline and native live certifications and validate uploaded artifacts/receipts, including logo asset-lock evidence when exercised.
11. If blocked by external provider availability, missing secrets, relay deployment infrastructure, or CI infrastructure, leave repo safe and report the precise blocker with evidence. Never fabricate `DONE`, `PRODUCTION`, or `VERIFIED`.
