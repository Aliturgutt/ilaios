from __future__ import annotations

from pathlib import Path

import pytest

from services.security_factory import SecurityFactory, SecurityFactoryError, SecurityScope


def _scope(root: Path) -> SecurityScope:
    return SecurityScope("security-production-safe-exercise", root)


def test_production_safe_attack_scenarios_fail_closed_and_retest_clean(
    tmp_path: Path,
) -> None:
    factory = SecurityFactory()
    scope = _scope(tmp_path)

    unsafe = tmp_path / "attack_surface.py"
    unsafe.write_text(
        "from flask import request\n"
        "import requests\n"
        "import subprocess\n"
        "path = request.args.get('path')\n"
        "url = request.args.get('url')\n"
        "query = request.args.get('query')\n"
        "command = request.args.get('cmd')\n"
        "open(path)\n"
        "requests.get(url)\n"
        "cursor.execute(query)\n"
        "subprocess.run(command)\n",
        encoding="utf-8",
    )
    (tmp_path / "infra.yaml").write_text(
        "cidr: 0.0.0.0/0\nAction: \"*\"\n",
        encoding="utf-8",
    )
    private_key_marker = "-----BEGIN " + "PRIVATE KEY-----\n"
    (tmp_path / "credential_fixture.txt").write_text(
        private_key_marker,
        encoding="utf-8",
    )

    before = factory.scan_repository(scope)
    before_ids = {item.finding_id for item in before.findings}

    assert "SAST-TAINT-UNTRUSTED-TO-SINK" in before_ids
    assert "INFRA-PUBLIC-CIDR" in before_ids
    assert "INFRA-WILDCARD-ACTION" in before_ids
    assert "SECRET-PRIVATE-KEY" in before_ids
    assert before.passed is False

    with pytest.raises(SecurityFactoryError, match="outside authorized local scope"):
        factory.analyze_dast_observation(
            scope,
            "https://example.com",
            200,
            {},
        )

    unsafe.write_text(
        "path = '/tmp/ilaios-safe-fixture'\n"
        "url = 'http://127.0.0.1:8080/health'\n"
        "query = 'SELECT 1'\n"
        "command = 'status'\n",
        encoding="utf-8",
    )
    (tmp_path / "infra.yaml").write_text(
        "cidr: 10.0.0.0/24\nAction: \"logs:Read\"\n",
        encoding="utf-8",
    )
    (tmp_path / "credential_fixture.txt").write_text(
        "no credential material\n",
        encoding="utf-8",
    )

    after = factory.scan_repository(scope)
    retest = factory.retest(before, after)

    assert after.passed is True
    assert retest.passed is True
    assert retest.resolved
    assert not retest.remaining
    assert not retest.introduced


def test_production_safe_exercise_preserves_independent_verifier_separation(
    tmp_path: Path,
) -> None:
    report = SecurityFactory().scan_repository(_scope(tmp_path))

    with pytest.raises(SecurityFactoryError, match="cannot verify its own report"):
        SecurityFactory.independently_verify(
            report,
            producer_id="ilaios.agent.security.codesec.v1",
            verifier_id="ilaios.agent.security.codesec.v1",
        )

    assert SecurityFactory.independently_verify(
        report,
        producer_id="ilaios.agent.security.codesec.v1",
        verifier_id="ilaios.agent.security.verifier.v1",
    )
