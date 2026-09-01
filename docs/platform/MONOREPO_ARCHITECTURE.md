# ILAIOS Monorepo Boundaries

## Logical roots

- `apps/`: non-authoritative user-facing projections.
- `services/`: authoritative deployable composition roots.
- `packages/`: versioned contracts and reusable libraries.
- `infra/`: deployment and environment definitions.
- `src/`: proven pre-monorepo Python domains retained during controlled migration.
- `tests/`: repository and architecture validation.

## Dependency direction

- Shared packages never import apps, services, or infrastructure.
- Services never import app implementations.
- Apps never import infrastructure implementations.
- Existing `src` domains do not acquire dependencies on new apps, services, or infrastructure roots.
- Infrastructure is not imported as runtime application code.

These rules are enforced by `tests/test_architecture_boundaries.py`. New adapters must be introduced by their governed milestone rather than weakening the rules.

## Toolchain

The repository bootstrap remains deterministic and dependency-light:

- pytest for executable validation;
- Ruff for lint and import formatting;
- strict mypy for type validation;
- pre-commit for repository-wide hooks;
- Git diff checks for whitespace integrity.

The canonical bootstrap command set is:

```text
python -m pytest -q
ruff check .
mypy --strict src tests
pre-commit run --all-files
git diff --check
```
