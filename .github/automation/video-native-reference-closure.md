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

- Repo: `Aliturgutt/ilaios`.
- Exact current master before this checkpoint PR: `bc6a0e8a6cdac2a16a5ba0e94bbe96b414d5efbd`.
- PR #605, `Video: expose native-reference semantic rejection evidence`, passed Required CI and was merged to produce that exact master SHA.
- PR #605 did not lower the semantic threshold, change provider choice, alter admission logic, bypass QA, or modify canonical Core. It only preserved bounded final semantic rejection evidence and routed the existing trusted-master certification through that diagnostic wrapper.
- The canonical production certification workflow remains `.github/workflows/video-native-reference-production-certification.yml` and still requires the exact accepted receipt/artifact invariants before publishing `ILAIOS Video Native Reference Live Certification = success`.
- This checkpoint branch exists only to persist current evidence and safely trigger the next exact-master trusted production certification through normal PR/CI/merge flow. Re-read master and this branch head before merge.

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
- bounded semantic diagnostic wrapper at `apps/desktop/e2e/provider_video_native_reference_semantic_diagnostic_e2e.py` that preserves final reviewer score, threshold, repair target, reviewer/review IDs, criteria identity and provenance in failure evidence without changing acceptance behavior;
- separate trusted-master workflow `.github/workflows/video-native-reference-production-certification.yml` with exact-SHA `ILAIOS Video Native Reference Live Certification` status and immutable proof artifact;
- baseline private visual-brief reference analyzer pinned to explicit free multimodal `google/gemma-3-27b-it:free`; semantic QA routing remains separate.

## Provider truth revalidated on 2026-08-20

Current official OpenRouter documentation confirms:

- `/api/v1/videos` supports `input_references` for reference-to-video and `frame_images` for image-to-video;
- if both are present, `frame_images` takes precedence;
- reference assets for provider generation require stable directly downloadable public HTTPS URLs;
- `google/gemma-3-27b-it:free` is currently listed as free and supports vision-language/image input.

Provider documentation/catalog truth must be re-checked again before any paid/native live call if material provider behavior changes.

## Current exact-head CI

PR #605 final head `cedcfac4257700ecedea516778446908d03e0ea3` passed the required merge evidence before merge:

- Required CI Gate: PASS;
- Platform validation / quality: PASS, including Pytest, Ruff and strict Mypy;
- CI supply-chain hardening: PASS;
- Secret scanning: PASS;
- Repository malware / ClamAV scan: PASS;
- API contract, DB migration, operational safety and final structural audits: PASS;
- Software Factory Final Evidence: PASS.

Those PR-head results justified the merge but are not a substitute for a new trusted-master production certification. This checkpoint write creates a new branch head and must itself receive fresh CI before merge.

## Baseline private visual-brief certification

The source path remains configured for explicit free multimodal reference analysis rather than the prior invalid `openrouter/free` analyzer alias. No new baseline private-brief production claim is made by this checkpoint. Any baseline certification required by the closure must still be read from exact trusted-master evidence rather than inferred from source configuration.

## External relay blocker

The prior statement that no real public relay existed is stale and is superseded by live runtime evidence from 2026-08-20.

A real public HTTPS reference relay was exercised end-to-end with:

- authenticated upload PASS;
- SHA-256 binding PASS;
- signed provider-style fetch PASS;
- expected short TTL behavior PASS;
- MIME handling PASS;
- provider fetch access evidence / D1 evidence row PASS;
- explicit delete cleanup PASS;
- post-delete access denial PASS.

The trusted-master production certification run `32355073852` also proved the GitHub `Production` environment has usable `OPENROUTER_API_KEY`, `ILAIOS_REFERENCE_RELAY_UPLOAD_URL`, and `ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN` bindings: setup and native live proof safety-boundary steps passed and execution proceeded through real provider generation to final semantic acceptance. Therefore relay deployment/configuration and Production secret binding are no longer the current blocker.

That exact-master run was attempted twice in bounded fashion on source SHA `c1488404d233e79f756e321ad3130256dd55181a`. Both attempts failed closed at the final independent semantic gate with `VideoRuntimeError: final video semantic acceptance failed`. Neither attempt produced an accepted MP4/receipt certification, and the exact-SHA live-cert status correctly remained failure. Blind retries were stopped.

PR #605 was then merged specifically so the next real production attempt will preserve the final semantic score, threshold, repair target and reviewer identity in the immutable failure proof if that same gate rejects again. The semantic threshold remains `0.78`; it must not be weakened merely to obtain a green certification.

## Remaining order

1. Run fresh exact-head CI for this checkpoint-only PR and repair only evidenced failures.
2. Merge only after required CI passes, using the canonical trusted-master trigger token `[video-native-reference-live-cert]` in the merge commit message so the production workflow executes on the exact new master SHA.
3. Inspect the new trusted-master production run. If the final semantic gate fails, read the immutable `semantic_review` evidence and fix the evidenced content/continuity defect without lowering the threshold, bypassing QA or blindly retrying.
4. If semantic acceptance passes, require provider relay fetch evidence for product + logo, `provider_native_reference_url_used=true`, `native_reference_mode=input-references`, native reference count `2`, managed terminal cost `<= $1.00`, real accepted MP4, technical H.264/AAC/1920x1080/7–9 second PASS, final reference-consistency PASS, and logo direct-PASS or deterministic asset-lock PASS.
5. Validate receipt/artifact SHA, artifact size, relay release, managed cost proof and append-only evidence/provenance against the exact master SHA.
6. Require exact-SHA `ILAIOS Video Native Reference Live Certification = success`; only then may native-reference Video Factory be called `VERIFIED`.

If the real provider or independent reviewer exposes a new external failure, preserve its evidence and fix that exact blocker. Never fabricate `DONE`, `PRODUCTION`, `%100`, or `VERIFIED`.
