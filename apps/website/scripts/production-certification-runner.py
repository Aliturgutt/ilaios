from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

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
    return int(certification.main())


if __name__ == "__main__":
    raise SystemExit(main())
