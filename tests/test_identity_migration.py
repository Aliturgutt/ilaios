"""Identity-migration checks for the active ILAIOS package."""

from __future__ import annotations

from pathlib import Path

from src import ilaios


def test_active_package_uses_ilaios_identity() -> None:
    assert ilaios.__version__ == "0.1.0"
    assert Path("src/ilaios/__init__.py").is_file()
    assert not Path("src/hermes/__init__.py").exists()


def test_project_metadata_uses_ilaios_identity() -> None:
    metadata = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "ILAIOS"' in metadata
    assert 'name = "HermesEnterpriseOS"' not in metadata
