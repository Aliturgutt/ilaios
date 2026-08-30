from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from typing import Any


RUNNER_PATH = Path("apps/website/scripts/production-certification-runner.py")


def _load_runner() -> Any:
    spec = importlib.util.spec_from_file_location("test_website_production_certification_runner", RUNNER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakePage:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        self.calls.append(("goto", url, wait_until, timeout))

    def wait_for_timeout(self, milliseconds: int) -> None:
        self.calls.append(("wait", milliseconds))


def test_isolate_pending_navigation_requests_uses_blank_page_before_next_check() -> None:
    runner = _load_runner()
    page = FakePage()

    runner.isolate_pending_navigation_requests(page)

    assert page.calls == [
        ("goto", "about:blank", "load", 10_000),
        ("wait", 50),
    ]


def test_main_isolates_previous_navigation_before_underlying_check(monkeypatch: Any) -> None:
    runner = _load_runner()
    page = FakePage()
    observed: list[tuple[str, list[tuple[Any, ...]]]] = []

    def original_check_www_alias(current_page: FakePage) -> dict[str, Any]:
        observed.append(("www", list(current_page.calls)))
        current_page.calls.append(("www-check",))
        return {"status": 200}

    def original_check_page(current_page: FakePage, url: str, width: int, height: int) -> str:
        observed.append(("page", list(current_page.calls)))
        return f"{url}:{width}x{height}"

    certification = SimpleNamespace(
        check_www_alias=original_check_www_alias,
        check_page=original_check_page,
    )

    def certification_main() -> int:
        certification.check_www_alias(page)
        result = certification.check_page(page, "https://ilaios.com/", 1440, 900)
        assert result == "https://ilaios.com/:1440x900"
        return 0

    certification.main = certification_main
    monkeypatch.setattr(runner, "load_certification_module", lambda: certification)

    assert runner.main() == 0

    page_observation = next(calls for name, calls in observed if name == "page")
    assert page_observation[-2:] == [
        ("goto", "about:blank", "load", 10_000),
        ("wait", 50),
    ]
