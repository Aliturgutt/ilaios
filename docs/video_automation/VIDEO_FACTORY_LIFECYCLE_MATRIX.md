# ILAIOS Video Factory lifecycle matrix

Current Video truth-sync basis: master through social-publication transport merge `4ea368723df92bd85ff9f1b4b51737feb5266427` (2026-08-15).

This matrix separates **TARGET TRUTH** from **CURRENT REALITY**. Code, tests, deterministic local media, successful CI, test doubles, or synthetic receipts do not prove credentialed production-provider generation, independent perceptual review, real social publication, legal rights clearance, live production SLOs, or authenticated production end-to-end acceptance.

**Current Video Factory promotion state: `PRODUCTION_UNPROVEN / BLOCKED`.**

| Workstream | Target truth | Current reality | Lifecycle state | Evidence / remaining proof |
|---|---|---|---|---|
| 1. M01-M30 lifecycle | One canonical dependency-ordered workflow; M30 coordinates the complete chain | M01-M30 implementation/tests/evidence exist; M30 remains the canonical Video workflow orchestrator | TEST-ACCEPTED; production-unproven | `src/video_automation`, `services/integrations/video_runtime.py`, `src/video_automation/workflow_orchestrator.py` |
| 2. Canonical registries | One capability registry, one governed SkillRegistry, one Video provider registry | Existing registries are reused; no Video-specific duplicate authority is accepted | IMPLEMENTED / CI-VERIFIED | capability/provider registry tests; `services/integrations/video_skill_governance.py` |
| 3. ILAIOS-native Video skills | Ownable digest-bound editing/direction/QA/repair/thumbnail/publish capabilities | Native manifests are registered and governed through the existing SkillRegistry | IMPLEMENTED / CI-VERIFIED | `src/video_automation/video_skills.py` |
| 4. Native editing | Governed immutable `video.edit.*` operations over registered media | Real FFmpeg editing and exact edit-skill authority validation exist | IMPLEMENTED / CI-VERIFIED | `video_editing.py`, `ffmpeg_media_engine.py`, `services/integrations/video_editing.py` |
| 5. Creative direction | Structured cinematography, visual intent, pacing, palette and continuity | Native structured direction contract/governance exist; no learned-model quality is falsely claimed | IMPLEMENTED contract / CI-VERIFIED | creative-direction contracts/tests |
| 6. Visual QA | Deterministic signal checks plus independent semantic/perceptual review | Real FFmpeg black/freeze QA exists; external VISUAL evidence admission is exact-artifact bound | IMPLEMENTED foundation; real production review pending | `media_signal_quality.py`, `perceptual_review.py` |
| 7. Audio QA | Deterministic signal checks plus independent semantic/perceptual review | Real FFmpeg silence QA exists; external AUDIO evidence admission is exact-artifact bound | IMPLEMENTED foundation; real production review pending | `audio_processing.py`, `media_signal_quality.py`, `perceptual_review.py` |
| 8. Brand QA | Independent brand criteria and artifact-bound evidence | BRAND review requires reviewer independence, criteria version/digest, score/threshold and bounded repair accounting | IMPLEMENTED ingress; real production review pending | `perceptual_review.py` |
| 9. Independent final evaluator | Fail closed across VISUAL/AUDIO/BRAND/TECHNICAL observations from one artifact | Four-domain evaluator and producer/reviewer/evaluator independence are implemented | IMPLEMENTED / CI-VERIFIED | `video_quality.py`, `services/integrations/video_quality.py` |
| 10. Complete quality composition | Technical + signal + perceptual evidence converge on one final acceptance authority | Assembly evidence, technical validation, signal QA, external perceptual ingress and governed final QA compose without creating a second acceptance authority | IMPLEMENTED / CI-VERIFIED foundation; real evidence pending | `services/integrations/video_quality_pipeline.py` |
| 11. Selective repair | Repair only failed bounded targets with attempt limits and immutable evidence | Governed artifact-bound repair execution verifies source/output SHA and rejects no-op repair | IMPLEMENTED / CI-VERIFIED; real regeneration pending | `SelectiveRepairController`, `selective_repair_execution.py`, `services/integrations/video_repair.py` |
| 12. Production provider execution | Credentialed real provider generation through governed routing/FinOps with receipts | Canonical OpenRouter/Seedance provider path exists; PR #144 added a manual Production-environment certification path that reuses canonical catalog, managed-credit gateway, poller and MP4 retriever | CODE COMPLETE / CI-VERIFIED; real generation BLOCKED | `provider_production_certification.py`; `video-provider-production-certification.yml`; real credential still missing |
| 13. Provider fallback | Real provider failure/fallback evidence, not a mocked transition | Fallback contracts exist and production acceptance requires fallback evidence whenever fallback is required | IMPLEMENTED contract; real fallback unproven | real primary failure + governed alternate-provider receipt required when applicable |
| 14. One-prompt lifecycle | Authenticated user prompt reaches completed governed Video delivery/publication | Local governed M30/FFmpeg/evidence/delivery path exists and the production gate defines exact authenticated E2E stages | TEST-ACCEPTED only | real provider → QA → repair → final MP4 → delivery/publish → sealed-evidence run required |
| 15. Legal/provenance | Every production asset has traceable source, rights/terms and consent as applicable | PR #143 requires an expected production asset inventory, inventory evidence reference/SHA, exact expected-asset-to-rights-record equality and commercial-use clearance | IMPLEMENTED admission gate; legal release external | actual final asset inventory, licenses/terms, consent and legal release evidence required |
| 16. Production operations | Cost/latency/availability/quality observations produce deterministic SLI/SLO evidence and alerts | PR #142 added exact-artifact production observation projection; PR #143 requires at least 20 observed production samples before SLO proof can pass | CODE COMPLETE / CI-VERIFIED; live SLO unproven | real production samples, telemetry/alerts and accepted SLO snapshot required |
| 17. Thumbnail generation/QA | Content-addressed generation plus evaluated production output | Real FFmpeg thumbnail generation is exact-source bound, governed and tested | IMPLEMENTED / CI-VERIFIED; production perceptual thumbnail acceptance pending | real final-artifact thumbnail review evidence required |
| 18. Publication safety | OAuth-bound account authority, durable side-effect ledger, duplicate prevention and reconciliation | PR #141 merged OAuth-reference-bound adapters, durable publication ledger, ambiguous-outcome handling and publication observability | IMPLEMENTED / CI-VERIFIED | real OAuth account authorization + post evidence required |
| 19. Concrete social transports | Governed YouTube/TikTok/Instagram platform API execution without parallel retry/account authority | PR #148 merged exact-MP4-bound YouTube upload/processing verification, TikTok creator-info/consent/direct-post/status flow, and Instagram Reel container/publish/permalink flow behind the existing coordinator | IMPLEMENTED / CI-VERIFIED; real publication unproven | real test-account OAuth credentials, exact final MP4 and returned IDs/URLs required |
| 20. Production promotion authority | One fail-closed promotion decision bound to one revision, product and final MP4 SHA | PR #140 merged six-class production evidence gate; PR #143 hardened SLO sample and legal inventory admission | IMPLEMENTED / CI-VERIFIED | all six external proof classes must pass simultaneously before `PRODUCTION` |

## Merged Video production-closeout evidence

- PR #141 — durable publication safety/observability; merge `2b91f30a6d89bf48db781d4d7c9435994c1d0b11`.
- PR #140 — fail-closed six-class Video production acceptance gate; merge `f44b480c1d12496241de4ae8ee4ebc1d8fcc48ef`.
- PR #142 — exact-artifact production SLI/SLO operational evidence; merge `28b4efa5a9f6aefa20a0b1c2aab905309c2053a4`.
- PR #143 — minimum 20 production SLO samples + exact legal asset-set hardening; merge `e63b68522db745b8bcc1532ca2fbce351cc76a15`.
- PR #144 — manual canonical real-provider production certification; merge `29f20ca7f3f9238bee3eb0b43d5e391414a774f5`.
- PR #148 — governed concrete YouTube/TikTok/Instagram transports; merge `4ea368723df92bd85ff9f1b4b51737feb5266427`.

All merged code above passed the repository Required CI gate at its exact reviewed head before merge. A code/CI PASS is not an external production PASS.

## Executed real-provider proof attempts

Two credentialed-proof workflows were actually executed on 2026-08-15 and both stopped **before any billable provider POST** because `OPENROUTER_API_KEY` was unavailable:

1. repository-level proof run `31878382034` → `BLOCKED_MISSING_SECRET`; evidence artifact ID `9245354463`, artifact SHA-256 `95f4a934af838c40d51b63758fdf551fb41c23015ddce888c01b8184f814c5cd`; receipt only, no MP4;
2. GitHub `Production` environment proof run `31878662220` → `BLOCKED_MISSING_SECRET`; evidence artifact ID `9245423347`, artifact SHA-256 `b15622aa5a9359de93251c1219aa27f5bdfc42e5f22c7eeec2563ef403875255`; receipt only, no MP4.

Therefore no provider spend, no real generated Video artifact and no provider-generation PASS may be claimed from these runs.

## Remaining external promotion blockers

The repository-side code/test/CI gaps above are closed, but Video Factory cannot honestly be promoted while the following observed evidence is absent:

1. **Real provider proof** — production credential plus successful real generation receipt, final generated artifact receipt and real fallback evidence when fallback is required.
2. **Real perceptual QA** — independent VISUAL + AUDIO + BRAND evaluation against the exact real final MP4, including bounded repair/re-review evidence when any domain fails.
3. **Real publication proof** — real test-account OAuth authorization, actual YouTube/TikTok/Instagram publication as applicable, returned post ID/URL, verification and duplicate/retry/reconciliation evidence.
4. **Production operations proof** — at least 20 exact-artifact production observations with accepted cost, p95 latency, availability and quality SLO evidence plus alert/telemetry references.
5. **Legal/provenance proof** — exact final production asset inventory with source, copyright/license/model-output terms, commercial-use clearance, consent where applicable, and release evidence.
6. **FINAL E2E proof** — authenticated user → one prompt → planning → real generation → editing → independent QA → bounded repair → final MP4 → delivery/publication → immutable sealed evidence.

## Promotion rule

Video Factory may be marked **`PRODUCTION` only when `evaluate_video_production(...)` returns `PRODUCTION` for one exact repository revision, one finished-product identity and one final MP4 SHA-256 with all six external production proof classes present and passing.**

Until then the authoritative state is **`PRODUCTION_UNPROVEN / BLOCKED`**. Target architecture, synthetic tests, local deterministic media, website/Vercel status, stale prose, or self-certification must never promote Video Factory.