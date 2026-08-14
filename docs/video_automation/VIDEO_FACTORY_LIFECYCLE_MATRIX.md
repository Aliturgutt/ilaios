# ILAIOS Video Factory lifecycle matrix

Truth-sync baseline before this revision: `d1b851ca09dbd8d55eabcb86001cda4d6ef6a151` (2026-08-14), after PR #72 merged.

This matrix separates **TARGET TRUTH** from **CURRENT REALITY**. Code, tests, deterministic local media, or CI do not prove credentialed production-provider success, external perceptual review, real social publication, legal rights clearance, production observability, or production end-to-end acceptance. Website/Vercel deployment status is outside Video Factory acceptance; a Vercel quota or `build-rate-limit` signal must not be treated as a Video Platform CI failure.

| Workstream | Target truth | Current reality | Lifecycle state | Evidence / remaining proof |
|---|---|---|---|---|
| 1. M01-M30 lifecycle | One canonical dependency-ordered workflow; M30 coordinates the complete chain | M01-M30 implementations/tests/evidence exist; M30 remains the single canonical workflow orchestrator | TEST-ACCEPTED; production-unproven | `src/video_automation`, `tests/test_video_automation_*`, `dev/openclaw/evidence/VIDEO.V01`-`VIDEO.V30` |
| 2. Canonical registries | One capability registry, one governed SkillRegistry, one Video provider registry | Existing registries are reused; no Video-specific duplicate authority was introduced | IMPLEMENTED / CI-VERIFIED | capability/provider registry tests; `services/integrations/video_skill_governance.py` |
| 3. ILAIOS-native Video skills | Ownable, digest-bound ILAIOS-native edit/direction/QA/repair/thumbnail/publish capabilities | Native manifests are registered and governed through the existing SkillRegistry | IMPLEMENTED / CI-VERIFIED | `src/video_automation/video_skills.py`; PR #68/#70/#72 CI |
| 4. Native editing | Governed immutable `video.edit.*` operations over registered media | Real FFmpeg editing exists; exact edit skill authority is validated before mutation | IMPLEMENTED / CI-VERIFIED; production-provider run unproven | `video_editing.py`, `ffmpeg_media_engine.py`, `services/integrations/video_editing.py`; real FFmpeg tests |
| 5. Creative direction | Structured cinematography, visual intent, pacing, palette, continuity | Native structured direction contract and governance exist; no learned creative model behavior is falsely claimed | IMPLEMENTED contract / CI-VERIFIED; production creative-model quality unproven | `CreativeDirection`; governed cinematography tests |
| 6. Visual QA | Deterministic signal checks plus independent semantic/perceptual review | Real FFmpeg black/freeze signal QA is implemented and artifact-bound; this revision adds fail-closed external perceptual evidence admission | IMPLEMENTED / CI-VERIFIED foundation; production perceptual evidence pending | `media_signal_quality.py`, `perceptual_review.py`; real FFmpeg signal test; external production review receipt still required |
| 7. Audio QA | Deterministic signal checks plus independent semantic/perceptual review | Real FFmpeg silence QA is implemented and artifact-bound; this revision adds fail-closed external perceptual evidence admission | IMPLEMENTED / CI-VERIFIED foundation; production perceptual evidence pending | `audio_processing.py`, `media_signal_quality.py`, `perceptual_review.py`; external production review receipt still required |
| 8. Brand QA | Explicit independent brand criteria and artifact-bound evidence | External human/independent-model evidence can be admitted only with reviewer independence, criteria version/digest, provenance, score/threshold and bounded repair target | IMPLEMENTED / CI-VERIFIED ingress; production brand review pending | `perceptual_review.py`; actual production brand-review evidence still required |
| 9. Independent final evaluator | Fail closed across VISUAL/AUDIO/BRAND/TECHNICAL observations from the same artifact | Four-domain evaluator, observer/producer/evaluator independence and exact artifact binding are implemented | IMPLEMENTED / CI-VERIFIED | `video_quality.py`, `services/integrations/video_quality.py`, PR #68 |
| 10. Complete quality composition | Technical + signal + perceptual evidence converge on one existing final acceptance authority | This revision composes exact assembly evidence, technical validation, signal QA, external perceptual evidence, governed four-domain QA and the existing final acceptance coordinator | IMPLEMENTED / CI-VERIFIED foundation; production evidence pending | `services/integrations/video_quality_pipeline.py`; no second acceptance gate |
| 11. Selective repair | Repair only failed bounded targets with attempt limits and immutable evidence | Repair planning and governed artifact-bound repair execution are implemented; source/output SHA and byte evidence are verified and no-op repair is rejected | IMPLEMENTED / CI-VERIFIED; production regeneration run unproven | `SelectiveRepairController`, `selective_repair_execution.py`, `services/integrations/video_repair.py` |
| 12. Production providers/fallback | Real provider adapters behind existing routing/registry with governed fallback | Seedance/Ark adapter and provider contracts exist; no credentialed production success/fallback receipt is present in repository evidence | PARTIAL / production-unproven | production API credentials, generation receipt, artifact receipt and fallback evidence required |
| 13. One-prompt lifecycle | One authenticated prompt reaches completed governed Video delivery | Deterministic local composition crosses M30, FFmpeg rendering, governance, FinOps, evidence and local delivery in tests | TEST-ACCEPTED only | `services/integrations/video_runtime.py`; real provider-to-publication production E2E still required |
| 14. Licensing/provenance | Versioned ownable native capabilities with traceable source/evidence | Native skill ownership/provenance contracts and artifact evidence bindings exist | IMPLEMENTED code contract; legal/release proof external | repository distribution/license review and release evidence remain external |
| 15. Media security/copyright | Sandboxed, integrity-checked, provenance-aware media with rights evidence | Path/type/size/SHA/provenance controls exist; new thumbnail/repair/QA paths also fail closed on substitution/symlinks | IMPLEMENTED technical controls; legal rights proof pending | real copyright/license/consent evidence and legal review remain external |
| 16. FinOps/observability | Per-operation cost/latency/quality telemetry with production SLO evidence | Existing M28/central telemetry and local runtime accounting are implemented | TEST-ACCEPTED; production observability unproven | production dashboards, alerts, cost traces and SLO evidence required |
| 17. Thumbnail generation/QA | Content-addressed generation plus evaluated production output | Real FFmpeg thumbnail generation is implemented, exact-source bound, governed and CI-tested; optional text is file-fed rather than shell-interpolated | IMPLEMENTED / CI-VERIFIED generation; production perceptual thumbnail acceptance pending | PR #70; real FFmpeg thumbnail test; production thumbnail review evidence required |
| 18. Social publishing | Governed real platform publication with post verification | Provider-neutral packaging/execution exists and `video.publish.social` authority is checked before external side effects | IMPLEMENTED boundary / CI-VERIFIED; production publication unproven | real platform adapters/credentials, account identity, post IDs/URLs and receipts required |

## Exact CI evidence already merged

- PR #68: governed four-domain QA foundation merged at `9d6a7cd82b72bf1d2ce8eea0dcc461d517a29484`.
- PR #70: artifact-bound technical evidence bridge and real FFmpeg thumbnail generation merged at `10dc22ec999a67ebc1bd97f148f94b3500e89df6`; exact-head Platform CI reported **1163 passed / 1 skipped**, Ruff PASS, strict mypy PASS and diff hygiene PASS.
- PR #72: governed edit/repair/publish boundaries, final-acceptance binding and real FFmpeg visual/audio signal QA merged at `d1b851ca09dbd8d55eabcb86001cda4d6ef6a151`; exact-head Platform CI reported **1186 passed / 1 skipped**, pre-commit PASS, Ruff PASS, strict mypy PASS and diff hygiene PASS.

The exact-head CI for the revision containing this truth-sync must also pass before the new code-level rows above are considered CI-verified.

## Remaining external promotion blockers

The repository can close code/test/CI gaps, but it cannot honestly manufacture external production evidence. Video Factory must remain **production-unproven** until the applicable evidence exists:

1. real Seedance/Ark (or other approved production provider) credentials and successful generation receipts;
2. real provider fallback execution evidence;
3. real external VISUAL/AUDIO/BRAND perceptual-review evidence admitted against the exact production artifact;
4. real social platform credentials/adapters/account identity plus publication IDs/URLs and verification receipts;
5. copyright/license/consent and legal release evidence for production media;
6. production cost, latency, availability, quality dashboards/alerts and SLO evidence;
7. one-prompt, real-provider-to-real-publication production end-to-end acceptance evidence.

Vercel is not one of these Video acceptance gates. Do not consume or force Vercel capacity to certify Video Factory platform work.

## Promotion rule

A row advances only from observed evidence at the exact revision: code, exact-head required CI, real media artifacts, immutable SHA/provenance records, provider/publisher receipts, independent review evidence, production telemetry and legal/rights evidence as applicable. Target descriptions, synthetic TEST-mode results, stale status prose, website deployment state, or self-certification cannot promote a Video capability to production.
