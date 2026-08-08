# M01-M30 Canonical Repair Audit

Status: static implementation audit for branch `fix/m01-m30-canonical-repair`.
Runtime PASS remains the responsibility of the deterministic OpenClaw validation run.

| Module | Canonical implementation evidence | Test evidence | Static action |
|---|---|---|---|
| M01 | `models.py` | `test_video_automation_models.py` | retained |
| M02 | `configuration.py` | `test_video_automation_configuration.py` | retained |
| M03 | `providers.py` | `test_video_automation_providers.py` | retained |
| M04 | `provider_registry.py` | `test_video_automation_provider_registry.py` | retained |
| M05 | `provider_selection.py` | `test_video_automation_provider_selection.py` | retained |
| M06 | `research.py` | `test_video_automation_research.py` | retained |
| M07 | `script_generation.py` | `test_video_automation_script_generation.py` | retained |
| M08 | `scene_planning.py::ScenePlanner` | `test_video_automation_scene_planning.py` | repaired: `VideoScript -> Scene` |
| M09 | `scene_planning.py::ShotPlanner` | `test_video_automation_scene_planning.py` | repaired: separated shot planning from M08 |
| M10 | `asset_planning.py` | `test_video_automation_asset_planning.py` | retained |
| M11 | `local_test_media_provider.py` | `test_video_automation_local_test_media_provider.py` | retained |
| M12 | `media_acquisition_orchestrator.py` plus generation execution/polling/retrieval modules | corresponding acquisition/generation tests | retained |
| M13 | `asset_store.py` | `test_video_automation_asset_store.py` | retained |
| M14 | `voice_generation.py` | `test_video_automation_voice_generation.py` | retained |
| M15 | `audio_processing.py` | `test_video_automation_audio_processing.py` | retained |
| M16 | `caption_subtitle.py` | `test_video_automation_caption_subtitle.py` | retained |
| M17 | `timeline_engine.py` | `test_video_automation_timeline_engine.py` | retained |
| M18 | `ffmpeg_media_engine.py` | `test_video_automation_ffmpeg_media_engine.py` | retained |
| M19 | `remotion_composition.py` | `test_video_automation_remotion_composition.py` | retained |
| M20 | `render_engine.py` | `test_video_automation_render_engine.py` | retained |
| M21 | `assembled_output_technical_validation.py` / `media_technical_validation.py` | matching technical-validation tests | retained |
| M22 | `content_validation.py` | `test_video_automation_content_validation.py` | retained |
| M23 | `platform_profiles.py` | `test_video_automation_platform_profiles.py` | added canonical profile layer |
| M24 | `publishing_execution.py` plus `providers.py` publishing abstraction | `test_video_automation_publishing_execution.py` | retained |
| M25 | `publishing_queue.py` | `test_video_automation_publishing_queue.py` | added validated scheduler/queue |
| M26 | `job_state_machine.py` | `test_video_automation_job_state_machine.py` | added deterministic state machine |
| M27 | `retry_recovery.py` | `test_video_automation_retry_recovery.py` | added bounded retry recovery |
| M28 | `cost_control.py` | `test_video_automation_cost_control.py` | added budget enforcement |
| M29 | `audit_evidence.py` + Core Audit/Evidence | `test_video_automation_audit_evidence.py` | added core integration |
| M30 | `workflow_orchestrator.py` | `test_video_automation_workflow_orchestrator.py` | added gated end-to-end orchestration |

## Binding validation requirement

No row in this document is runtime PASS merely because a file exists. OpenClaw must validate the branch in M01 -> M30 dependency order using targeted tests plus repository-wide `ruff`, full `pytest`, strict `mypy`, `pre-commit`, clean-tree and dependency-evidence gates. Any contradiction or failure invalidates the affected milestone and all downstream milestone activation until repaired.
