"""Real isolated Software Factory tests for PLATFORM.P18."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from services.software_factory import IsolatedSoftwareFactory, SoftwareFactoryError


def _factory(tmp_path: Path) -> tuple[IsolatedSoftwareFactory, Path]:
    if shutil.which("unshare") is None or shutil.which("mount") is None:
        pytest.skip("Linux mount-namespace isolation is unavailable")
    production = tmp_path / "production"
    (production / "src").mkdir(parents=True)
    (production / "tests").mkdir()
    (production / "src" / "feature.py").write_text("value = 1\n", encoding="utf-8")
    (production / "production-marker").write_text("protected", encoding="utf-8")
    (production / "tests" / "test_feature.py").write_text(
        "import os\n"
        "from pathlib import Path\n"
        "from src.feature import value\n\n"
        "def test_proposed_value():\n"
        "    assert value == 2\n\n"
        "def test_production_is_hidden():\n"
        "    production = Path(os.environ['ILAIOS_FACTORY_PRODUCTION_PATH'])\n"
        "    assert not (production / 'production-marker').exists()\n",
        encoding="utf-8",
    )
    return (
        IsolatedSoftwareFactory(
            production,
            tmp_path / "workspaces",
            tmp_path / "proposals",
            frozenset({"src", "tests"}),
        ),
        production,
    )


def test_factory_emits_real_tested_content_addressed_review_proposal(
    tmp_path: Path,
) -> None:
    factory, production = _factory(tmp_path)
    proposal = factory.propose("src/feature.py", b"value = 2\n")

    assert proposal.requires_human_approval is True
    assert proposal.production_applied is False
    assert proposal.test_exit_code == 0
    assert proposal.production_snapshot_before == proposal.production_snapshot_after
    assert (production / "src" / "feature.py").read_text() == "value = 1\n"
    patch = Path(proposal.patch_path).read_text()
    assert "-value = 1" in patch
    assert "+value = 2" in patch
    assert "2 passed" in Path(proposal.test_log_path).read_text()
    durable = json.loads(
        (Path(proposal.patch_path).parent / "proposal.json").read_text()
    )
    assert durable["proposal_id"] == proposal.proposal_id
    approval = factory.approve_for_review(proposal.proposal_id, "human-owner")
    assert json.loads(approval.read_text())["decision"] == "approved_for_external_review"

    with pytest.raises(SoftwareFactoryError, match="forbidden"):
        factory.apply_to_production(proposal)


def test_factory_blocks_escape_allowlist_and_symlink_inputs(tmp_path: Path) -> None:
    factory, production = _factory(tmp_path)
    with pytest.raises(SoftwareFactoryError, match="escapes"):
        factory.propose("../secrets", b"x")
    with pytest.raises(SoftwareFactoryError, match="allowlist"):
        factory.propose("infra/prod.yaml", b"x")
    (production / "src" / "escape.py").symlink_to(production / "production-marker")
    with pytest.raises(SoftwareFactoryError, match="regular production file"):
        factory.propose("src/escape.py", b"x")
