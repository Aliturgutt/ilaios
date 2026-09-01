# Contributing to ILAIOS

ILAIOS uses evidence-driven, bounded changes. This repository is publicly visible and owner-operated; public visibility does not grant an open-source reuse license, and every change should remain reviewable and reproducible.

## Before changing code

1. Identify the exact component and intended result.
2. Confirm that the change does not conflict with canonical architecture or current release authority.
3. Check current repository/runtime evidence rather than relying on old status prose.
4. Keep Website, Desktop and other product surfaces outside scope unless explicitly included.
5. For production-sensitive work, confirm the required human approval before execution.

## Change workflow

- Start from current `master`.
- Use a focused branch.
- Change only files required for the bounded purpose.
- Add or update tests for behavior changes.
- Run the relevant targeted checks and repository-wide gates required by the component.
- Inspect the final diff for unrelated changes.
- Open a focused PR with evidence and remaining limitations.
- Do not merge failing code or weaken checks to obtain PASS.

## Core repository quality gates

Python/platform changes should preserve the established gates where applicable:

```text
python -m pytest -q
ruff check .
mypy --strict src tests
pre-commit run --all-files
git diff --check
```

Component-specific workflows may add stronger gates. A command existing in this document is not proof that it passed for a particular commit; use CI/test evidence.

## Security

Follow `SECURITY.md`. Never commit real credentials, tokens, private keys, customer secrets or sensitive production payloads.

## Commit and PR discipline

- One bounded purpose per PR whenever practical.
- No routine force-push/history rewrite.
- No unrelated cleanup hidden inside functional changes.
- State what was tested.
- State what was not tested or remains externally blocked.
- Do not claim production, certification or approval without direct evidence.

## Canonical authority

Planning documents and comments do not override canonical authority. If a new post-v1 milestone or dependency graph is needed, introduce it through a dedicated governed proposal rather than inventing IDs during implementation.
