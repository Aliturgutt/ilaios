from pathlib import Path


POLICY_PATH = Path("docs/governance/RELEASE_VERSION_POLICY.md")


def test_release_policy_exists_and_uses_ilaios_identity() -> None:
    text = POLICY_PATH.read_text(encoding="utf-8")
    assert "# ILAIOS Release and Version Policy" in text
    assert "vMAJOR.MINOR.PATCH" in text
    assert "Semantic Versioning" in text
    assert "Hermes, ILAKOS and ILATEN" in text
    assert "must not be introduced into active release identifiers" in text


def test_release_policy_keeps_maturity_separate_from_release_state() -> None:
    text = POLICY_PATH.read_text(encoding="utf-8")
    assert "`VERIFIED` does not mean `PRODUCTION`" in text
    assert "Release state and capability maturity are recorded independently." in text


def test_release_policy_forbids_tag_rewrite_and_autonomous_production_release() -> None:
    text = POLICY_PATH.read_text(encoding="utf-8")
    assert "Do not force-move release tags." in text
    assert "create or publish a formal production release merely because CI is green" in text
    assert "rewrite Git history to manufacture release lineage" in text


def test_release_policy_does_not_invent_retroactive_version() -> None:
    text = POLICY_PATH.read_text(encoding="utf-8")
    assert "does not retroactively invent a version" in text
    assert "first formal ILAIOS GitHub Release" in text
