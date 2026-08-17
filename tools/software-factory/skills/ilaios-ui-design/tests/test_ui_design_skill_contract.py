from __future__ import annotations

from collections.abc import Mapping

import pytest

from services.ui_design_skill import UIDesignSkillError, is_ui_design_intent, resolve_ui_design


def test_ui_skill_resolves_drawer_without_authority() -> None:
    output = resolve_ui_design({"intent": "sagdan acilan ayarlar paneli olustur"})
    layout = output["layout"]
    authority = output["authority"]
    assert isinstance(layout, Mapping)
    assert isinstance(authority, Mapping)
    assert output["component"] == "drawer"
    assert layout["placement"] == "right"
    assert dict(authority) == {"shell": False, "network": False, "secrets": False, "deploy": False}


def test_diagram_only_intent_is_not_claimed_by_ui_skill() -> None:
    assert is_ui_design_intent("system architecture diagram olustur") is False
    with pytest.raises(UIDesignSkillError, match="ilaios-diagram-design"):
        resolve_ui_design({"intent": "system architecture diagram olustur"})
