# PLATFORM.P00 Migration Baseline

This document freezes the reproducible pre-migration baseline. It does not perform identity migration.

## Immutable reference

- Baseline commit: `0bd18cb873e6e44611c9e53bad073f43c0aa9699`
- Branch: `master`
- Upstream at capture: `origin/master`
- Tracked files at capture: 331
- PRE.S01 evidence: `dev/openclaw/evidence/PRE.S01/decision.yaml`
- VIDEO.V30 evidence: `dev/openclaw/evidence/VIDEO.V30/decision.yaml`

## Current logical capabilities

- Core runtime controls: audit, evidence chain, immutable context, validation, confidence, tool gateway, bootstrap validation.
- Code intelligence: source models and source-file analysis.
- Knowledge graph: graph domain models.
- Project manager: project domain models.
- Video Automation: canonical VIDEO.V01-V30 workflow with deterministic local validation.

Current source roots are `src/core`, `src/code_intelligence`, `src/knowledge_graph`, `src/project_manager`, `src/hermes`, and `src/video_automation`. No `apps`, `services`, `packages`, or `infra` implementation roots existed at capture.

## Identity inventory

Active and historical identifiers include `HermesEnterpriseOS`, `Hermes`, `ILAIOS`, `ILATEN`, and `ILAKOS`. PLATFORM.P01 must distinguish active identity from historical provenance and must preserve Git history. Canonical authority documents and prior evidence are immutable migration inputs, not rewrite targets.

## Validation snapshot

- Repository tests collected: 833
- Ruff: 0.16.2
- mypy: 2.3.0
- pre-commit: 4.6.1
- PRE.S01 full regression and all quality gates: PASS

## Rollback reference

Before any PLATFORM.P01 mutation, the recoverable baseline is commit `0bd18cb873e6e44611c9e53bad073f43c0aa9699` plus its synchronized `origin/master` reference. Rollback must follow the active governed package and must not rewrite pushed history.

## Reproduction

Checkout the baseline commit, use the repository-declared Python environment, and run:

```text
python -m pytest -q
ruff check .
mypy --strict src tests
pre-commit run --all-files
git diff --check
```

The baseline is a migration input. Later status text cannot supersede repository, Git, test, or durable evidence.
