from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


def load_certification_module() -> ModuleType:
    script_path = Path(__file__).with_name("production-certification.py")
    module_name = "ilaios_production_certification"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load certification module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    # dataclasses and other runtime introspection expect the module to be
    # discoverable in sys.modules while its top-level definitions execute.
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def isolate_pending_navigation_requests(page: Any) -> None:
    """Drain requests from the previous certification navigation.

    Next.js can still have lazy/static chunk requests in flight after the
    certification has finished inspecting a page. Reusing the same Playwright
    page for the next route/viewport aborts those old requests. If the next
    check has already attached its requestfailed listener, Chromium attributes
    that benign cancellation to the new check and creates a false production
    failure. Moving to about:blank before each check isolates the previous
    navigation without weakening same-origin failure handling for the page that
    is actually under certification.
    """

    page.goto("about:blank", wait_until="load", timeout=10_000)
    page.wait_for_timeout(50)


def main() -> int:
    certification = load_certification_module()
    original_check_www_alias = certification.check_www_alias
    original_check_page = certification.check_page

    def check_www_alias_isolated(page: Any) -> dict[str, Any]:
        result = original_check_www_alias(page)
        isolate_pending_navigation_requests(page)
        return result

    def check_page_isolated(page: Any, url: str, width: int, height: int) -> Any:
        # Isolate prior route/viewport work before check_page attaches its
        # requestfailed listener. Failures initiated by the page being checked
        # remain fatal in the underlying certification implementation.
        isolate_pending_navigation_requests(page)
        return original_check_page(page, url, width, height)

    certification.check_www_alias = check_www_alias_isolated
    certification.check_page = check_page_isolated
    return int(certification.main())


if __name__ == "__main__":
    raise SystemExit(main())
