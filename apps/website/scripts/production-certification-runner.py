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


def main() -> int:
    certification = load_certification_module()
    original_check_www_alias = certification.check_www_alias

    def check_www_alias_isolated(page: Any) -> dict[str, Any]:
        result = original_check_www_alias(page)
        # The alias probe may still have _next requests in flight when the next
        # apex navigation starts. Abort those requests before check_page attaches
        # its requestfailed listener so alias cleanup is not misclassified as a
        # failure belonging to the next page under test.
        page.goto("about:blank", wait_until="load", timeout=10_000)
        page.wait_for_timeout(50)
        return result

    certification.check_www_alias = check_www_alias_isolated
    return int(certification.main())


if __name__ == "__main__":
    raise SystemExit(main())
