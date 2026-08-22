from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from scripts.validate_fast_closure_v2_state import validate


STATE_PATH = Path(".github/automation/fast-closure-v2-state.json")


def load_state() -> dict[str, Any]:
    raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return cast(dict[str, Any], raw)


def test_repository_fast_closure_state_is_valid() -> None:
    validate(load_state())


def test_available_token_must_not_have_owner() -> None:
    state = load_state()
    state["merge_token"]["state"] = "AVAILABLE"
    state["merge_token"]["owner"] = "desktop"

    with pytest.raises(ValueError, match="must not retain an owner"):
        validate(state)


def test_external_blocker_requires_reason() -> None:
    state = load_state()
    state["workstreams"]["website_v2"]["lifecycle"] = "BLOCKED_EXTERNAL"
    state["workstreams"]["website_v2"]["blocked_reason"] = None

    with pytest.raises(ValueError, match="requires blocked_reason"):
        validate(state)


def test_merge_token_owner_must_be_in_merge_lifecycle() -> None:
    state = load_state()
    state["merge_token"].update(
        {
            "state": "RESERVED",
            "owner": "desktop",
            "freeze_active": True,
        }
    )
    state["workstreams"]["desktop"]["lifecycle"] = "DEVELOPING"

    with pytest.raises(ValueError, match="must be merge-related"):
        validate(state)
