# ILAIOS Video Factory lifecycle matrix

Audit baseline: `c68d6d96394359200293eb557e567546c2c8de60` (2026-08-14).

This matrix separates target truth from current repository reality. A unit test,
contract, deterministic local render, or synthetic asset never proves production
provider, perceptual-quality, publishing, or end-to-end acceptance.

| Workstream | Target truth | Current reality at baseline | Lifecycle state | Evidence |
|---|---|---|---|---|
| 1. M01-M30 | One canonical dependency-ordered workflow; M30 orchestrates | Implementations and tests exist for all modules | TEST-ACCEPTED; production-unproven | `src/video_automation`, `tests/test_video_automation_*`, `dev/openclaw/evidence/VIDEO.V01`-`VIDEO.V30` |
| 2. Canonical registries | One capability registry and one video provider registry | Factory capability is in `services/capability_registry.py`; M04 is `ProviderRegistry` | IMPLEMENTED | `tests/test_capability_registry.py`, `tests/test_video_automation_provider_registry.py` |
| 3. Native skill contracts | Ownable ILAIOS video skills, distinct from agents | Added on this workstream; no second authority | IMPLEMENTED; PR/CI pending | `src/video_automation/video_skills.py` |
| 4. Native editing | `video.edit.*` immutable operations over registered assets | Contract coverage added; FFmpeg operations pre-exist below orchestration | PARTIAL; production execution evidence absent | `video_skills.py`, `ffmpeg_media_engine.py` |
| 5. Creative direction | Structured cinematography intent and continuity | Contract added; no learned creative model is claimed | PARTIAL | `CreativeDirection` |
| 6. Visual QA | Measured visual observations from real decoded media | Technical probes exist; no production perceptual observation evidence | NOT PRODUCTION-ACCEPTED | M21 tests; no real visual QA evidence |
| 7. Audio and brand QA | Measured audio plus explicit brand checks | Audio processing/content validation exist; independent domain findings added | PARTIAL; real evidence absent | M15/M22 tests, `QaFinding` |
| 8. Independent final evaluator | Fail closed across visual/audio/brand/technical evidence | Deterministic independent aggregator added | IMPLEMENTED; evidence inputs remain external | `IndependentVideoEvaluator` tests |
| 9. Selective repair | Target only failed spans/assets with bounded attempts | Bounded controller added; production regeneration not yet evidenced | PARTIAL | `SelectiveRepairController` tests |
| 10. Production providers/fallback | Real adapters behind M03/M04 and governed deterministic selection | Seedance Ark adapter exists; production credential/API run not evidenced | PARTIAL; production-unproven | provider and Seedance tests |
| 11. One-prompt composition | Real composition root injects steps into M30 | Control-plane local composition exists; no production one-prompt acceptance | TEST-ACCEPTED only | `services/integrations/video_runtime.py` |
| 12. Licensing/provenance | Versioned, digest-bound ILAIOS-native skill manifests | Native manifests added; repository-wide distribution review remains separate | IMPLEMENTED; legal release review pending | `VIDEO_SKILLS`, governance provenance audit |
| 13. Media security/copyright | Sandboxed inputs, size/type/provenance/copyright gates | Path/type/size/provenance admission added; copyright rights evidence still external | PARTIAL | `MediaSecurityPolicy` tests |
| 14. FinOps/observability | Per-operation costs and quality telemetry without authority duplication | M28 and central telemetry exist; no production video dashboards/SLO evidence | PARTIAL | `cost_control.py`, `services/observability.py` |
| 15. Thumbnail generation/QA | Content-addressed generation and evaluated output | Request contract added; generation and real QA evidence absent | PARTIAL | `ThumbnailRequest` tests |
| 16. Social publishing and production E2E | Real platform adapters, post verification, real acceptance evidence | Provider-neutral execution/queue/verification exist; no real platform adapters or production posts evidenced | NOT PRODUCTION-ACCEPTED | M24-M25 tests; no external publication evidence |

## Baseline validation observation

The repository suite began successfully but the local real-video control-plane test
could not execute because this machine had no `ffmpeg`/`ffprobe` executable. This is
an environment blocker, not production evidence and not a reason to weaken or skip
the test. The exact failing test was
`test_real_local_video_crosses_grant_finops_evidence_and_delivery_boundaries`.

## Promotion rule

Only verified artifacts, provider receipts, publisher observations, admitted
evidence, required CI checks, and independent QA at the exact revision can advance a
row. Target descriptions and synthetic TEST-mode results cannot do so.
