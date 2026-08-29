from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "apps" / "website" / "scripts" / "production-certification.py"


def _load_module():
    playwright = types.ModuleType("playwright")
    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.Page = object
    sync_api.Response = object
    sync_api.sync_playwright = lambda: None
    playwright.sync_api = sync_api
    sys.modules["playwright"] = playwright
    sys.modules["playwright.sync_api"] = sync_api
    spec = importlib.util.spec_from_file_location("website_production_certification_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _Page:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _Context:
    def __init__(self) -> None:
        self.page = _Page()

    def new_page(self) -> _Page:
        return self.page


def test_alias_probe_uses_and_closes_isolated_page(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    context = _Context()
    monkeypatch.setattr(module, "check_www_alias", lambda page: {"status": 200})

    assert module.check_www_alias_isolated(context) == {"status": 200}
    assert context.page.closed is True


def test_alias_probe_error_remains_blocking_and_page_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    context = _Context()

    def fail(_page):
        raise RuntimeError("www alias failed")

    monkeypatch.setattr(module, "check_www_alias", fail)
    with pytest.raises(RuntimeError, match="www alias failed"):
        module.check_www_alias_isolated(context)
    assert context.page.closed is True
