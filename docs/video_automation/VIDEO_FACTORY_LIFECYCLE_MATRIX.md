# ILAIOS Video Factory lifecycle matrix

Current Video truth-sync source baseline: canonical `master` through local Video visual-quality merge `4234d1215f002910d13eaf5323703f3a2e6a64d9` (2026-08-16 Türkiye / 2026-08-16 UTC). Repository history and exact CI/runtime evidence remain authoritative for CURRENT REALITY.

This matrix separates **TARGET TRUTH** from **CURRENT REALITY**. Code, tests, deterministic local media, successful CI, retained CI artifacts, architecture intent, or second-pass local inspection do not by themselves prove credentialed external-provider generation, independent production perceptual review, real social publication, legal rights clearance, live production SLOs, or provider-backed production end-to-end acceptance.

**Current Video Factory promotion state: `PRODUCTION_UNPROVEN / BLOCKED`.**

The zero-cost local Windows finished-product path is now runtime-verified, its exact accepted MP4 is durably retained as SHA-bound CI evidence, and the local motion-graphics composition has passed a second-pass red-team visual inspection after bounded quality repair. External/provider-backed production promotion is still unproven.

| Workstream | Target truth | Current reality | Lifecycle state | Evidence / remaining proof |
|---|---|---|---|---|
| 1. M01-M30 lifecycle | One canonical dependency-ordered workflow; M30 coordinates the complete chain | M01-M30 implementation/tests/evidence exist and the canonical Windows finished-product composition executes planning, media/audio/caption/timeline/render/validation stages without a second Core | IMPLEMENTED / TESTED / CI-VERIFIED; local runtime path VERIFIED | `src/video_automation`, `services/integrations/video_runtime.py`, `src/video_automation/workflow_orchestrator.py`; PR #182/#185/#212/#219 |
| 2. Canonical registries | One capability registry, one governed SkillRegistry, one Video provider registry | Existing registries are reused; no Video-specific duplicate authority is accepted | IMPLEMENTED / CI-VERIFIED | capability/provider registry tests; `services/integrations/video_skill_governance.py` |
| 3. ILAIOS-native Video skills | Ownable digest-bound editing/direction/QA/repair/thumbnail/publish capabilities | Native manifests are registered and governed through the existing SkillRegistry | IMPLEMENTED / CI-VERIFIED | `src/video_automation/video_skills.py` |
| 4. Native editing | Governed immutable `video.edit.*` operations over registered media | Real FFmpeg editing and exact edit-skill authority validation exist; local Windows finished-product render is runtime-verified and its accepted MP4 is now retained | IMPLEMENTED / TESTED / RUNTIME-VERIFIED locally | `video_editing.py`, `ffmpeg_media_engine.py`, `services/integrations/video_editing.py`; PR #212 artifact retention |
| 5. Creative direction | Structured cinematography, visual intent, pacing, palette and continuity | Native structured direction contracts exist. PR #219 repaired repetitive local composition with a bounded enterprise panel hierarchy, scene progression, larger supporting copy/captions and fuller narration without adding a second renderer authority | IMPLEMENTED / CI-VERIFIED; local deterministic presentation red-team accepted | `services/integrations/desktop_video_runtime.py`; PR #219 |
| 6. Visual QA | Deterministic signal checks plus independent semantic/perceptual production review | Real FFmpeg technical checks execute locally. The exact retained local artifact received a second-pass red-team visual inspection outside the runtime acceptance code, but this is not the independent production VISUAL evidence required for external promotion | Local technical + second-pass local review VERIFIED; independent production VISUAL review pending | retained MP4 evidence below; `media_signal_quality.py`, `perceptual_review.py` |
| 7. Audio QA | Deterministic signal checks plus independent semantic/perceptual production review | Real audio checks exist and the retained final artifact contains AAC audio plus a materially fuller local SAPI narration. External AUDIO review remains a separate production evidence authority | Local technical/audio path VERIFIED; independent production AUDIO review pending | retained MP4/voice/music evidence; `audio_processing.py`, `media_signal_quality.py`, `perceptual_review.py` |
| 8. Brand QA | Independent brand criteria and artifact-bound evidence | Official logo immutability is verified and persisted in the local artifact receipt. Production BRAND review still requires an independent reviewer, criteria version/digest and score/threshold | Local asset-integrity VERIFIED; independent production BRAND review pending | retained receipt reports canonical logo SHA and `immutable_during_render=true`; `perceptual_review.py` |
| 9. Independent final evaluator | Fail closed across VISUAL/AUDIO/BRAND/TECHNICAL observations from one artifact | Four-domain evaluator and producer/reviewer/evaluator independence rules are implemented | IMPLEMENTED / CI-VERIFIED; external perceptual evidence pending | `video_quality.py`, `services/integrations/video_quality.py` |
| 10. Complete quality composition | Technical + signal + perceptual evidence converge on one final acceptance authority | Assembly evidence, technical validation, signal QA, external perceptual ingress and governed final QA compose without creating a second acceptance authority | IMPLEMENTED / CI-VERIFIED; local technical acceptance VERIFIED; external perceptual acceptance pending | `services/integrations/video_quality_pipeline.py` |
| 11. Selective repair | Repair only failed bounded targets with attempt limits and immutable evidence | Governed artifact-bound repair execution exists. PR #219 is a bounded repository quality repair driven by retained-artifact inspection; external-perceptual-triggered runtime repair remains unproven | IMPLEMENTED / CI-VERIFIED; real external-perceptual-triggered repair unproven | `SelectiveRepairController`, `selective_repair_execution.py`, `services/integrations/video_repair.py` |
| 12. Production provider execution | Credentialed real provider generation through governed routing/FinOps with receipts | Canonical managed OpenRouter/Seedance certification exists. PR #195 added free-only mode to the same manual Production workflow: explicit `:free` IDs only, exact provider-reported cost `0`, no paid/managed-credit fallback, MP4 signature check and SHA-256 receipt | IMPLEMENTED / TESTED / CI-VERIFIED; real provider artifact UNPROVEN | `provider_production_certification.py`, `free_provider_production_certification.py`, `video-provider-production-certification.yml`; credentialed manual run required |
| 13. Provider fallback | Real provider failure/fallback evidence without bypassing provider/cost/security authority | Fallback contracts exist. Free-only certification may try only explicitly free candidates; paid fallback is prohibited and controlled failure is correct when no free candidate is usable | IMPLEMENTED policy / CI-VERIFIED; real provider fallback behavior unproven | real provider failure + permitted alternate receipt required when applicable |
| 14. One-prompt lifecycle | Authenticated user prompt reaches completed governed Video delivery and, where promoted, governed external publication | Authenticated Desktop intent reaches the canonical coordinator and local Video runtime. Current-master Windows evidence proves a real 20s finished MP4 with AcceptanceManifest PASS, content-addressed identity and durable artifact retention | LOCAL WINDOWS FINISHED-PRODUCT PATH RUNTIME-VERIFIED / CI-VERIFIED / EVIDENCE-RETAINED; provider-backed production E2E unproven | latest exact-head evidence below |
| 15. Legal/provenance | Every production asset has traceable source, rights/terms and consent as applicable | Admission requires expected production asset inventory, exact asset-to-rights-record equality and commercial-use clearance; no unknown-license production asset may pass | IMPLEMENTED admission gate; final external legal release pending | actual external/provider asset inventory, licenses/terms, consent and release evidence required |
| 16. Production operations | Cost/latency/availability/quality observations produce deterministic SLI/SLO evidence and alerts | Exact-artifact production observation projection exists; production proof requires at least 20 real observed production samples | CODE COMPLETE / CI-VERIFIED; live SLO unproven | real production samples, telemetry/alerts and accepted SLO snapshot required |
| 17. Thumbnail generation/QA | Content-addressed generation plus evaluated production output | Real FFmpeg thumbnail generation is exact-source bound, governed and tested | IMPLEMENTED / CI-VERIFIED; production perceptual thumbnail acceptance pending | real external final-artifact thumbnail review evidence required |
| 18. Publication safety | OAuth-bound account authority, durable side-effect ledger, duplicate prevention and reconciliation | OAuth-reference-bound adapters, durable publication ledger, ambiguous-outcome handling and publication observability exist | IMPLEMENTED / CI-VERIFIED | real OAuth account authorization + post evidence required |
| 19. Concrete social transports | Governed YouTube/TikTok/Instagram platform API execution without parallel retry/account authority | Exact-MP4-bound YouTube, TikTok and Instagram transports exist behind the existing coordinator | IMPLEMENTED / CI-VERIFIED; real publication unproven | real authorized test-account OAuth, exact final external MP4 and returned IDs/URLs required |
| 20. Production promotion authority | One fail-closed promotion decision bound to one revision, product and final MP4 SHA | Six-class production evidence gate exists and retains minimum SLO/legal evidence requirements | IMPLEMENTED / CI-VERIFIED | all mandatory external proof classes must pass simultaneously before `PRODUCTION` |

## Latest retained local finished-product evidence

PR #212 closed the previous repository evidence-retention gap: the Windows E2E no longer deletes the only copy of the accepted artifact without preservation. It reuses the existing `_run_finished_product_acceptance` authority, then retains only the exact accepted MP4, a SHA-bound receipt and curated safe stage evidence. Runtime-private SQLite/state/token material is deleted before upload.

PR #219 then repaired the local deterministic presentation quality after inspection of that retained artifact and re-ran the complete current-master validation chain. On exact PR #219 head `21bb62927181b548dde4a88dbdafa422a64f5280`:

- **Required CI Gate** run `31916325224` — PASS, including supply-chain hardening, secret scanning, ClamAV, API/DB safety, full Pytest, Ruff, strict Mypy and diff hygiene.
- **ILAIOS Desktop Windows Gate** run `31916325155` — PASS, including Flutter analysis/tests, Windows release build, bundled control plane, packaged Desktop E2E, real 20-second finished-product Video E2E and exact artifact upload.
- **Software Factory Final Evidence** run `31916325112` — PASS, confirming the bounded Video repair did not regress that repository evidence gate.
- retained Actions artifact ID `9255034344`; archive digest `sha256:f0a27de8fe3c79c220e8b1bcce0da118b39215b2d335d28e53169ebcd5dc94e2`; retention window 30 days;
- receipt `source_revision=21bb62927181b548dde4a88dbdafa422a64f5280`;
- final MP4 SHA-256 `6f593761dd7b9a6f3f1d04d7db71f1d06b1cee856ce0188c080e632bd09d8de7` and actual downloaded bytes matched that receipt exactly;
- `AcceptanceManifest=PASS`, `execution_status=ACCEPTED`, duration `20.000s`, `1920x1080`, H.264 + AAC, canonical logo immutable;
- artifact inspection confirmed no uploaded private SQLite/database/runtime-state files;
- a second-pass contact-sheet/red-team inspection outside the runtime acceptance code confirmed the repaired local five-scene hierarchy is materially more readable and less repetitive than the pre-repair artifact.

This is strong evidence for the **local zero-cost Windows deterministic motion-graphics finished-product path**. It is not proof of external generative-provider availability, canonical independent production perceptual review, real publication, production SLO compliance or legal clearance.

## Merged Video production-closeout evidence

- PR #140 — fail-closed six-class Video production acceptance gate; merge `f44b480c1d12496241de4ae8ee4ebc1d8fcc48ef`.
- PR #141 — durable publication safety/observability; merge `2b91f30a6d89bf48db781d4d7c9435994c1d0b11`.
- PR #142 — exact-artifact production SLI/SLO operational evidence; merge `28b4efa5a9f6aefa20a0b1c2aab905309c2053a4`.
- PR #143 — minimum 20 production SLO samples + exact legal asset-set hardening; merge `e63b68522db745b8bcc1532ca2fbce351cc76a15`.
- PR #144 — manual canonical real-provider production certification; merge `29f20ca7f3f9238bee3eb0b43d5e391414a774f5`.
- PR #148 — governed concrete YouTube/TikTok/Instagram transports; merge `4ea368723df92bd85ff9f1b4b51737feb5266427`.
- PR #182 — authenticated Desktop one-prompt → canonical Video finished-product runtime integration; merge `86a199d19dd5457a07ca7ee623fd64d7555adaf1`.
- PR #185 — real Windows finished-product acceptance E2E; merge `e8d3bf32698108bfefc993677d1e3d792b7899e7`.
- PR #195 — free-only provider certification hardening; merge `670ac0c6f51cd7686c073c26a150e1d8a3c3a3b1`.
- PR #212 — persist exact accepted Windows MP4 + curated stage evidence with SHA-bound receipt; merge `35c66acb82b433cce8618817c67c066686b729ac`.
- PR #219 — bounded local visual-quality repair after retained-artifact red-team inspection; merge `4234d1215f002910d13eaf5323703f3a2e6a64d9`.

Every merged implementation above was gated by repository validation at its reviewed head. A code/CI/runtime/local-red-team PASS is not an external production PASS.

## Executed real-provider proof attempts

Two credentialed-proof workflows were executed on 2026-08-15 before PR #195 and both stopped **before any billable provider POST** because `OPENROUTER_API_KEY` was unavailable to those runs:

1. repository-level proof run `31878382034` → `BLOCKED_MISSING_SECRET`; evidence artifact ID `9245354463`, artifact SHA-256 `95f4a934af838c40d51b63758fdf551fb41c23015ddce888c01b8184f814c5cd`; receipt only, no MP4;
2. GitHub `Production` environment proof run `31878662220` → `BLOCKED_MISSING_SECRET`; evidence artifact ID `9245423347`, artifact SHA-256 `b15622aa5a9359de93251c1219aa27f5bdfc42e5f22c7eeec2563ef403875255`; receipt only, no MP4.

PR #195 does not convert either attempt into a PASS. It provides a fail-closed free-only certification path so a future manual Production run can prove or reject real zero-cost availability without silently spending money.

## Repository-side closeout state

The Video-specific repository gaps identified in this closeout are now closed: stale Video PRs were superseded rather than merged, free-only provider certification is implemented and CI-verified, the authenticated local Windows one-prompt path is runtime-verified, the exact accepted MP4 is retained with an immutable receipt, private runtime state is excluded from the artifact, and the local renderer quality issue found during retained-artifact inspection received a bounded repair plus fresh exact-head CI/runtime verification.

No further repository-only change can truthfully manufacture the missing external evidence classes below.

## Remaining external promotion blockers

1. **Real provider proof** — a valid Production provider credential plus a successful manual free-only/provider certification run yielding a real provider receipt, exact zero-cost evidence for the free path and a generated external MP4 SHA-256. If no usable free provider exists, the truthful result is controlled `BLOCKED_FREE_PROVIDER_UNAVAILABLE`, not paid fallback.
2. **Real independent production perceptual QA** — independent VISUAL + AUDIO + BRAND evaluation against the exact external/provider-backed final MP4, with repair/re-review evidence when any domain fails.
3. **Real publication proof** — real authorized test-account OAuth, actual platform publication where that capability is promoted, returned post ID/URL and post-publication verification/reconciliation evidence.
4. **Production operations proof** — at least 20 exact-artifact real production observations with accepted cost, p95 latency, availability and quality SLO evidence plus alert/telemetry references.
5. **Legal/provenance proof** — exact final external production asset inventory with source, copyright/license/model-output terms, commercial-use clearance, consent where applicable and release evidence.
6. **External production E2E proof** — authenticated user → one prompt → governed external generation/acquisition → independent production QA → bounded repair if required → final MP4 → governed delivery/publication as promoted → immutable sealed evidence.

The local zero-cost Windows finished-product E2E, artifact retention and bounded local presentation quality are no longer repository-side blockers.

## Promotion rule

Video Factory may be marked **`PRODUCTION` only when `evaluate_video_production(...)` returns `PRODUCTION` for one exact repository revision, one finished-product identity and one final MP4 SHA-256 with every mandatory external production proof class present and passing.**

Until then the authoritative state is **`PRODUCTION_UNPROVEN / BLOCKED`**. Target architecture, synthetic tests, local deterministic media, retained local artifacts, website/Vercel status, stale prose or self-certification must never promote Video Factory.
