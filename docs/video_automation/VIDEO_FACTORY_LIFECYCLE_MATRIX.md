# ILAIOS Video Factory lifecycle matrix

Current Video truth-sync source baseline: canonical `master` through Video free-only provider certification merge `670ac0c6f51cd7686c073c26a150e1d8a3c3a3b1` (2026-08-16 Türkiye / 2026-08-15 UTC). This documentation-only truth-sync follows that source baseline; the repository history is authoritative for the final documentation commit SHA.

This matrix separates **TARGET TRUTH** from **CURRENT REALITY**. Code, tests, deterministic local media, successful CI, test doubles, synthetic receipts, architecture intent, or self-certification do not prove credentialed external-provider generation, independent perceptual review, real social publication, legal rights clearance, live production SLOs, or provider-backed production end-to-end acceptance.

**Current Video Factory promotion state: `PRODUCTION_UNPROVEN / BLOCKED`.**

The zero-cost local Windows finished-product path is now runtime-verified. External/provider-backed production promotion is not.

| Workstream | Target truth | Current reality | Lifecycle state | Evidence / remaining proof |
|---|---|---|---|---|
| 1. M01-M30 lifecycle | One canonical dependency-ordered workflow; M30 coordinates the complete chain | M01-M30 implementation/tests/evidence exist and the canonical Windows finished-product composition executes planning, media/audio/caption/timeline/render/validation stages without a second Core | IMPLEMENTED / TESTED / CI-VERIFIED; local runtime path VERIFIED | `src/video_automation`, `services/integrations/video_runtime.py`, `src/video_automation/workflow_orchestrator.py`; PR #182/#185; Windows Gate evidence below |
| 2. Canonical registries | One capability registry, one governed SkillRegistry, one Video provider registry | Existing registries are reused; no Video-specific duplicate authority is accepted | IMPLEMENTED / CI-VERIFIED | capability/provider registry tests; `services/integrations/video_skill_governance.py` |
| 3. ILAIOS-native Video skills | Ownable digest-bound editing/direction/QA/repair/thumbnail/publish capabilities | Native manifests are registered and governed through the existing SkillRegistry | IMPLEMENTED / CI-VERIFIED | `src/video_automation/video_skills.py` |
| 4. Native editing | Governed immutable `video.edit.*` operations over registered media | Real FFmpeg editing and exact edit-skill authority validation exist; local Windows finished-product render is runtime-verified | IMPLEMENTED / TESTED / RUNTIME-VERIFIED locally | `video_editing.py`, `ffmpeg_media_engine.py`, `services/integrations/video_editing.py`; Windows Gate evidence below |
| 5. Creative direction | Structured cinematography, visual intent, pacing, palette and continuity | Native structured direction contract/governance exist; no learned-model quality is falsely claimed | IMPLEMENTED contract / CI-VERIFIED | creative-direction contracts/tests |
| 6. Visual QA | Deterministic signal checks plus independent semantic/perceptual review | Real FFmpeg black/freeze/technical checks execute locally; external VISUAL evidence admission is exact-artifact bound | Local technical QA VERIFIED; independent production VISUAL review pending | `media_signal_quality.py`, `perceptual_review.py`; real independent reviewer evidence required |
| 7. Audio QA | Deterministic signal checks plus independent semantic/perceptual review | Real FFmpeg silence/audio checks exist and local final artifact includes AAC audio; external AUDIO review remains a separate evidence authority | Local technical/audio path VERIFIED; independent production AUDIO review pending | `audio_processing.py`, `media_signal_quality.py`, `perceptual_review.py` |
| 8. Brand QA | Independent brand criteria and artifact-bound evidence | Official logo immutability is verified in the local finished-product E2E; production BRAND review still requires an independent reviewer, criteria version/digest and score/threshold | Local asset-integrity VERIFIED; independent production BRAND review pending | `perceptual_review.py`; Windows E2E reports `logo_immutable=true` |
| 9. Independent final evaluator | Fail closed across VISUAL/AUDIO/BRAND/TECHNICAL observations from one artifact | Four-domain evaluator and producer/reviewer/evaluator independence rules are implemented | IMPLEMENTED / CI-VERIFIED; external perceptual evidence pending | `video_quality.py`, `services/integrations/video_quality.py` |
| 10. Complete quality composition | Technical + signal + perceptual evidence converge on one final acceptance authority | Assembly evidence, technical validation, signal QA, external perceptual ingress and governed final QA compose without creating a second acceptance authority | IMPLEMENTED / CI-VERIFIED; local technical acceptance VERIFIED; external perceptual acceptance pending | `services/integrations/video_quality_pipeline.py` |
| 11. Selective repair | Repair only failed bounded targets with attempt limits and immutable evidence | Governed artifact-bound repair execution verifies source/output SHA and rejects no-op repair; local product runtime has bounded repair integration | IMPLEMENTED / CI-VERIFIED; real external-perceptual-triggered repair unproven | `SelectiveRepairController`, `selective_repair_execution.py`, `services/integrations/video_repair.py` |
| 12. Production provider execution | Credentialed real provider generation through governed routing/FinOps with receipts | Canonical managed OpenRouter/Seedance certification exists. PR #195 added a free-only mode to the same manual Production workflow: explicit `:free` IDs only, exact provider-reported cost `0`, no paid/managed-credit fallback, MP4 signature check and SHA-256 receipt | IMPLEMENTED / TESTED / CI-VERIFIED; real provider artifact UNPROVEN | `provider_production_certification.py`, `free_provider_production_certification.py`, `video-provider-production-certification.yml`; credentialed real run still required |
| 13. Provider fallback | Real provider failure/fallback evidence without bypassing provider/cost/security authority | Fallback contracts exist. Free-only certification may try only explicitly free candidates; a paid fallback is prohibited and controlled failure is correct when no free candidate is usable | IMPLEMENTED policy / CI-VERIFIED; real fallback behavior unproven | real provider failure + permitted alternate receipt required when applicable |
| 14. One-prompt lifecycle | Authenticated user prompt reaches completed governed Video delivery and, where promoted, governed external publication | PR #182 connected authenticated Desktop intent to the canonical coordinator and Video runtime. PR #185 and the latest #195 Windows Gate prove a real local 20s finished MP4 with AcceptanceManifest PASS and content-addressed artifact identity | LOCAL WINDOWS FINISHED-PRODUCT PATH RUNTIME-VERIFIED / CI-VERIFIED; provider-backed production E2E unproven | latest exact-head Windows proof: 20.0s, 1920x1080, H.264/AAC, SHA-256 `f085ed3b35cb96f185d50d3906302855c8c36969247b2f3321da2679726ac5af`, 10 stage evidence records, `ACCEPTED` |
| 15. Legal/provenance | Every production asset has traceable source, rights/terms and consent as applicable | Admission requires expected production asset inventory, exact asset-to-rights-record equality and commercial-use clearance; no unknown-license production asset may pass | IMPLEMENTED admission gate; final legal release external | actual final external/provider asset inventory, licenses/terms, consent and release evidence required |
| 16. Production operations | Cost/latency/availability/quality observations produce deterministic SLI/SLO evidence and alerts | Exact-artifact production observation projection exists; production proof requires at least 20 real observed production samples | CODE COMPLETE / CI-VERIFIED; live SLO unproven | real production samples, telemetry/alerts and accepted SLO snapshot required |
| 17. Thumbnail generation/QA | Content-addressed generation plus evaluated production output | Real FFmpeg thumbnail generation is exact-source bound, governed and tested | IMPLEMENTED / CI-VERIFIED; production perceptual thumbnail acceptance pending | real final-artifact thumbnail review evidence required |
| 18. Publication safety | OAuth-bound account authority, durable side-effect ledger, duplicate prevention and reconciliation | OAuth-reference-bound adapters, durable publication ledger, ambiguous-outcome handling and publication observability exist | IMPLEMENTED / CI-VERIFIED | real OAuth account authorization + post evidence required |
| 19. Concrete social transports | Governed YouTube/TikTok/Instagram platform API execution without parallel retry/account authority | Exact-MP4-bound YouTube, TikTok and Instagram transports exist behind the existing coordinator | IMPLEMENTED / CI-VERIFIED; real publication unproven | real test-account OAuth credentials, exact final MP4 and returned IDs/URLs required |
| 20. Production promotion authority | One fail-closed promotion decision bound to one revision, product and final MP4 SHA | Six-class production evidence gate exists and retains minimum SLO/legal evidence requirements | IMPLEMENTED / CI-VERIFIED | all mandatory external proof classes must pass simultaneously before `PRODUCTION` |

## Latest local finished-product runtime evidence

The current free-provider certification change was validated without regressing the existing Windows finished-product path. On exact PR #195 head `f92253c6708c696f308b2dbe6115205937236a67`:

- **Required CI Gate** run `31912487504` — PASS. Supply-chain hardening, secret scanning, ClamAV repository scan, API safety, structural audit, full Pytest, Ruff, strict Mypy and diff hygiene all passed.
- **ILAIOS Desktop Windows Gate** run `31912487410` — PASS. Flutter analyze/tests, Windows release build, bundled authoritative control plane, packaged Desktop E2E and real 20-second finished-product Video E2E all passed.
- Finished-product observation: `AcceptanceManifest=PASS`, `execution_status=ACCEPTED`, `duration=20.0s`, `1920x1080`, `H.264 + AAC`, artifact SHA-256 `f085ed3b35cb96f185d50d3906302855c8c36969247b2f3321da2679726ac5af`, `stage_evidence_count=10`, official logo input remained immutable.

This is strong runtime proof for the **local zero-cost Windows motion-graphics finished-product path**. It is not proof of external generative-provider availability, independent external perceptual QA, publication, production SLO compliance or legal clearance.

## Merged Video production-closeout evidence

- PR #140 — fail-closed six-class Video production acceptance gate; merge `f44b480c1d12496241de4ae8ee4ebc1d8fcc48ef`.
- PR #141 — durable publication safety/observability; merge `2b91f30a6d89bf48db781d4d7c9435994c1d0b11`.
- PR #142 — exact-artifact production SLI/SLO operational evidence; merge `28b4efa5a9f6aefa20a0b1c2aab905309c2053a4`.
- PR #143 — minimum 20 production SLO samples + exact legal asset-set hardening; merge `e63b68522db745b8bcc1532ca2fbce351cc76a15`.
- PR #144 — manual canonical real-provider production certification; merge `29f20ca7f3f9238bee3eb0b43d5e391414a774f5`.
- PR #148 — governed concrete YouTube/TikTok/Instagram transports; merge `4ea368723df92bd85ff9f1b4b51737feb5266427`.
- PR #182 — authenticated Desktop one-prompt → canonical Video finished-product runtime integration; merge `86a199d19dd5457a07ca7ee623fd64d7555adaf1`.
- PR #185 — real Windows finished-product acceptance E2E; merge `e8d3bf32698108bfefc993677d1e3d792b7899e7`.
- PR #195 — latest-master free-only provider certification hardening; merge `670ac0c6f51cd7686c073c26a150e1d8a3c3a3b1`.

Every merged implementation above was gated by repository validation at its reviewed head. A code/CI/runtime PASS for the local path is not an external production PASS.

## Executed real-provider proof attempts

Two credentialed-proof workflows were executed on 2026-08-15 before PR #195 and both stopped **before any billable provider POST** because `OPENROUTER_API_KEY` was unavailable to those runs:

1. repository-level proof run `31878382034` → `BLOCKED_MISSING_SECRET`; evidence artifact ID `9245354463`, artifact SHA-256 `95f4a934af838c40d51b63758fdf551fb41c23015ddce888c01b8184f814c5cd`; receipt only, no MP4;
2. GitHub `Production` environment proof run `31878662220` → `BLOCKED_MISSING_SECRET`; evidence artifact ID `9245423347`, artifact SHA-256 `b15622aa5a9359de93251c1219aa27f5bdfc42e5f22c7eeec2563ef403875255`; receipt only, no MP4.

PR #195 does not convert either attempt into a PASS. It adds a current, fail-closed free-only certification path so a future manual Production run can prove or reject real zero-cost availability without silently spending money.

## Stale Video PR cleanup

During this truth-sync, superseded PRs #151, #170, #172 and #191 were closed rather than merged over newer canonical work. The free-only implementation was rebuilt on current master and merged as PR #195 after fresh exact-head CI.

## Remaining external promotion blockers

Repository-side implementation/test/CI gaps addressed by this closeout are closed, but Video Factory cannot honestly be promoted while these external evidence classes are absent:

1. **Real provider proof** — one valid Production provider credential and a successful manual free-only/provider certification run yielding a real provider receipt, exact zero-cost evidence for the free path, and a real generated MP4 SHA-256. If no usable free provider exists, the truthful result is controlled `BLOCKED_FREE_PROVIDER_UNAVAILABLE`, not paid fallback.
2. **Real independent perceptual QA** — independent VISUAL + AUDIO + BRAND evaluation against the exact external/provider-backed final MP4, including repair/re-review evidence when any domain fails.
3. **Real publication proof** — real authorized test-account OAuth, actual platform publication where that capability is promoted, returned post ID/URL and post-publication verification/reconciliation evidence.
4. **Production operations proof** — at least 20 exact-artifact real production observations with accepted cost, p95 latency, availability and quality SLO evidence plus alert/telemetry references.
5. **Legal/provenance proof** — exact final external production asset inventory with source, copyright/license/model-output terms, commercial-use clearance, consent where applicable, and release evidence.
6. **External production E2E proof** — authenticated user → one prompt → governed external generation/acquisition → independent QA → bounded repair if required → final MP4 → governed delivery/publication as promoted → immutable sealed evidence.

The local zero-cost Windows finished-product E2E itself is no longer an unproven repository capability.

## Promotion rule

Video Factory may be marked **`PRODUCTION` only when `evaluate_video_production(...)` returns `PRODUCTION` for one exact repository revision, one finished-product identity and one final MP4 SHA-256 with every mandatory external production proof class present and passing.**

Until then the authoritative state is **`PRODUCTION_UNPROVEN / BLOCKED`**. Target architecture, synthetic tests, local deterministic media, website/Vercel status, stale prose, or self-certification must never promote Video Factory.
