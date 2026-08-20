# Video Native Reference Closure Automation Checkpoint

Durable checkpoint for the ILAIOS Video Factory native photo-reference closure. Every automation run must read this file first, then re-read current `master`, the authoritative PR/successor, exact-head CI, failing logs, relevant implementation, deployment/runtime evidence, and current provider behavior where material. Live GitHub source/CI/runtime/deployment evidence overrides stale text here.

## Goal

Close the native photo-reference path end-to-end: secure signed short-lived HTTPS relay; OpenRouter `input_references` / `frame_images`; Desktop admitted-reference relay; visible subject/product/logo consistency QA without biometric/sensitive-trait inference; deterministic exact-original logo asset-lock when logo-only drift occurs; fresh technical + semantic + reference-consistency QA after repair; real managed provider video; exact-head CI; real relay deployment/configuration; baseline private visual-brief live certification; separate trusted-master native-reference live certification; receipt/artifact validation; exact-SHA `VERIFIED` only after all evidence passes.

## Non-negotiable invariants

- Preserve canonical Core, Policy, Approval, Tool Gateway, router, planner, QA, Evidence and tenant/security authorities.
- Preserve `verified-free` default and private multimodal visual-brief fallback; no automatic free-to-paid fallback.
- Managed certification provider spend remains `<= $1.00`.
- Relay URLs must be HTTPS, unguessable, HMAC-signed, expiring, SHA-bound and explicitly released; tenant/principal identities stay server-side.
- Subject consistency is visible continuity only; never biometric identity or sensitive-trait inference.
- Logo asset-lock is allowed only for logo-only critical drift after subject/product critical scores pass. It uses exact admitted original logo bytes through canonical M18 FFmpeg and may not resize, crop, recolor, redraw, regenerate or substitute the logo.
- If exact safe logo compositing cannot be established, fail closed.
- After asset-lock require a new final artifact SHA-256, H.264/AAC/1920x1080/duration technical PASS, fresh independent semantic PASS, fresh reference-consistency PASS, exact source-logo SHA, repaired-artifact SHA and append-only `video.logo_asset_lock` provenance.
- `frame_images` deterministically wins over general `input_references` when frame roles are present.
- Unknown/unproven general native capability retains private visual-brief fallback; required frame semantics fail closed.
- Never reuse stale CI after master advances.

## Current authoritative state — 2026-08-20

- Repo: `Aliturgutt/ilaios`.
- Exact current master at successor creation: `c1488404d233e79f756e321ad3130256dd55181a`.
- PR #573 is merged; native-reference source implementation is present on master. It is source+CI implemented, not production VERIFIED.
- Current master combined status includes `ilaios/required-ci-exact-master=success`.
- The old checkpoint PR #596 was based on stale master `af2f5206185cd79e56ed2431449d2bbb0e8ceed3`; do not merge it as authoritative current-state evidence.
- This successor checkpoint branch starts exactly from current master and changes this checkpoint file only.
- Connected Vercel team `Aliturgut` (`team_xU1uFo3O6KclATgxI6LsumnA`) was rechecked on 2026-08-20 and still has zero projects.
- No real public HTTPS relay deployment/configuration evidence exists yet. Do not invent deployment, paid/billing/DNS state, or widen the existing AWS owner-/32 ALB boundary.

## Implemented source truth

Master contains the reviewed native-reference source path merged by PR #573, including:

- fail-closed OpenRouter `input_references` request shaping;
- deterministic `frame_images` precedence;
- short-lived signed HTTPS relay store + authenticated upload/delete + provider GET;
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
- native provider relay evidence preservation into final result/QA;
- real native reference Desktop E2E harness using product + logo references, managed cap, final MP4/QA/SHA checks and relay access-ledger fetch proof;
- separate trusted-master native-reference production certification workflow;
- baseline private visual-brief analyzer source-pinned to `google/gemma-3-27b-it:free`.

## Production truth

Production verification is still incomplete.

Baseline private visual-brief certification still requires a real trusted-master `Video Reference Production Certification` run on exact current master with real reference analysis, real managed provider MP4, QA, receipt and bounded cost evidence.

Native live certification remains blocked until a separately authorized public HTTPS relay origin is genuinely deployed and Production secrets are configured. Do not trigger `[video-native-reference-live-cert]` while relay prerequisites are missing.

Required Production secrets:

- `OPENROUTER_API_KEY`
- `ILAIOS_REFERENCE_RELAY_UPLOAD_URL`
- `ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN`

Relay server also requires:

- `ILAIOS_REFERENCE_RELAY_PUBLIC_BASE_URL`
- `ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN`
- `ILAIOS_REFERENCE_RELAY_SIGNING_SECRET`

## Remaining order

1. Keep this checkpoint aligned with exact current master; if master advances, never reuse stale PASS.
2. Continue non-blocked repo/CI verification and repair only evidenced failures via smallest bounded PR.
3. Establish a separately authorized real public HTTPS relay without weakening the existing AWS network boundary; configure bounded Production secrets.
4. Run baseline private visual-brief trusted-master certification on exact current master and require PASS.
5. Run separate native-reference trusted-master certification and require provider fetch evidence for product + logo, `provider_native_reference_url_used=true`, `native_reference_mode=input-references`, actual provider cost `<= $1.00`, real MP4, H.264/AAC/1920x1080/duration PASS, fresh semantic + reference-consistency PASS, and direct logo fidelity PASS or deterministic asset-lock PASS.
6. Validate receipt/artifact SHA, coordinator ACCEPTED and append-only provenance.
7. Only then publish exact-SHA native-reference `VERIFIED`.

If relay deployment remains blocked, continue non-blocked repository/CI work. Never fabricate `DONE`, `PRODUCTION`, `%100`, or `VERIFIED`.
