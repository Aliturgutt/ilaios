from __future__ import annotations

import copy
import json

import pytest

from scripts.validate_product_surface_contract import CONTRACT, ContractError, validate_contract


def _load() -> dict[str, object]:
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_product_surface_contract_is_valid() -> None:
    validate_contract(_load())


def test_missing_canonical_source_fails() -> None:
    data = copy.deepcopy(_load())
    features = data["features"]
    assert isinstance(features, list)
    feature = features[0]
    assert isinstance(feature, dict)
    feature["canonical_source"] = "does/not/exist"
    with pytest.raises(ContractError, match="stale or missing canonical_source"):
        validate_contract(data)


def test_manual_maturity_fails() -> None:
    data = copy.deepcopy(_load())
    features = data["features"]
    assert isinstance(features, list)
    feature = features[0]
    assert isinstance(feature, dict)
    feature["maturity"] = "VERIFIED"
    with pytest.raises(ContractError, match="must be derived"):
        validate_contract(data)


def test_surface_authority_override_fails() -> None:
    data = copy.deepcopy(_load())
    authority = data["authority_model"]
    assert isinstance(authority, dict)
    authority["surface_authority"] = True
    with pytest.raises(ContractError, match="must not become runtime authority"):
        validate_contract(data)


def test_unknown_desktop_projection_fails() -> None:
    data = copy.deepcopy(_load())
    features = data["features"]
    assert isinstance(features, list)
    feature = features[0]
    assert isinstance(feature, dict)
    feature["desktop_projection"] = "available"
    with pytest.raises(ContractError, match="invalid desktop projection"):
        validate_contract(data)


def test_locale_parity_is_required() -> None:
    data = copy.deepcopy(_load())
    features = data["features"]
    assert isinstance(features, list)
    feature = features[0]
    assert isinstance(feature, dict)
    feature["locale_requirements"] = ["en"]
    with pytest.raises(ContractError, match="locale parity violation"):
        validate_contract(data)
