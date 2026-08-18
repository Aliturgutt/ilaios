from pathlib import Path

from services.github_workflow_security_audit import audit_repository


def _write(root: Path, name: str, body: str) -> None:
    path = root / ".github" / "workflows" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_repository_workflow_security_policy_passes_current_tree() -> None:
    assert audit_repository(Path.cwd()) == ()


def test_mutable_action_is_blocked(tmp_path: Path) -> None:
    _write(tmp_path, "validation.yml", "on:\n  workflow_dispatch:\npermissions:\n  contents: read\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n        with:\n          ref: ${{ github.sha }}\n          persist-credentials: false\n")
    assert any(item.rule == "IMMUTABLE_ACTION" for item in audit_repository(tmp_path))


def test_external_mutation_push_trigger_is_blocked(tmp_path: Path) -> None:
    _write(tmp_path, "aws-r03-production-apply.yml", "on:\n  push:\n    branches: [master]\n  workflow_dispatch:\npermissions:\n  contents: read\njobs: {}\n")
    assert any(item.rule == "MANUAL_ONLY" for item in audit_repository(tmp_path))


def test_reference_live_secret_cannot_run_from_pull_request(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "video-reference-production-certification.yml",
        "on:\n"
        "  pull_request:\n"
        "  push:\n"
        "    branches:\n"
        "      - master\n"
        "permissions:\n"
        "  contents: read\n"
        "jobs:\n"
        "  proof:\n"
        "    environment: Production\n"
        "    runs-on: ubuntu-latest\n"
        "    env:\n"
        "      API_KEY: ${{ secrets.OPENROUTER_API_KEY }}\n"
        "    steps:\n"
        "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n"
        "        with:\n"
        "          ref: ${{ github.sha }}\n"
        "          persist-credentials: false\n",
    )
    assert any(
        item.rule == "TRUSTED_SECRET_TRIGGER" for item in audit_repository(tmp_path)
    )
