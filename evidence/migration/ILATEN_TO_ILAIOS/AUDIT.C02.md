# AUDIT.C02 — Requirement-Specific Matrix

## Pre-state

- Baseline HEAD: `cfef061`
- Existing matrix: 8,250 legacy rows
- Prior evidence behavior: any row in a mapped section inherited the same thematic evidence
- Prior totals: 1,933 `MIGRATED`, 2,749 `PARTIAL`, 3,568 `MISSING_IMPLEMENTATION`

## Repair

- Added 96 normative requirements from approved canonical Sections 8 and 9.
- Restricted evidence attachment to section plus requirement-pattern matches.
- Preserved conservative semantics: related evidence remains `PARTIAL`; no row becomes `IMPLEMENTED` without an exact proof rule.
- Added a dependency-aware implementation package register.

## Result before new implementation packages

- Total: 8,346
- `MIGRATED`: 1,967
- `PARTIAL`: 1,101
- `MISSING_IMPLEMENTATION`: 5,278
- `IMPLEMENTED`: 0
- `MISSING_DOCUMENTATION`: 0
- `CONFLICT`: 0

The decrease in `PARTIAL` is intentional: rows that had only section-level thematic evidence now remain `MISSING_IMPLEMENTATION`.

## Validation

Status: `PASS`

- `python -m pytest -q tests/test_migration_audit.py`: 6 passed
- `ruff check .`: PASS
- `python -m pytest -q`: 892 passed
- `mypy --strict src tests`: PASS, 149 source files
- `pre-commit run --all-files`: PASS
- `git diff --check`: PASS
