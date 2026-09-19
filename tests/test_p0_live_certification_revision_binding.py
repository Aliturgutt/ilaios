from __future__ import annotations

import pytest

from services.p0_live_certification import (
    P0LiveCertificationError,
    _required_revision_sha,
)


def test_p0_live_certification_requires_exact_revision_sha(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_SHA", raising=False)

    with pytest.raises(P0LiveCertificationError, match="exact 40-hex GITHUB_SHA"):
        _required_revision_sha()


def test_p0_live_certification_rejects_malformed_revision_sha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_SHA", "not-a-git-sha")

    with pytest.raises(P0LiveCertificationError, match="exact 40-hex GITHUB_SHA"):
        _required_revision_sha()


def test_p0_live_certification_binds_normalized_exact_revision_sha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision = "A" * 40
    monkeypatch.setenv("GITHUB_SHA", revision)

    assert _required_revision_sha() == revision.lower()
