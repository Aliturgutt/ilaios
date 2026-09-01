# PLATFORM.P01 Identity Migration

PLATFORM.P01 changes the active repository/runtime identity from HermesEnterpriseOS to ILAIOS without rewriting Git history or historical provenance.

## Active identity

- Project distribution name: `ILAIOS`
- Python identity package: `src/ilaios`
- Active source and test package descriptions: ILAIOS
- Generated Remotion composition export: `ilaiosComposition`

## Preserved provenance

Historical roadmap/status files, canonical Video Automation architecture documents, prior evidence, commit messages, and Git history retain their original Hermes terminology. Their text describes the provenance of the system and is not an active runtime identity.

Canonical authority and OpenClaw controller/plan files were not modified by PLATFORM.P01.

## Compatibility validation

The migration is accepted only when the complete repository regression, strict type checking, linting, pre-commit hooks, and identity-specific tests pass on synchronized `master`.
