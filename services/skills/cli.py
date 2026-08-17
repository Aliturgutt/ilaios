"""CLI entrypoint for invoking ILAIOS-native skills."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from services.skills.ilaios_ui_design import build_default_skill_runtime


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Invoke an ILAIOS-native skill")
    parser.add_argument("prompt", help="Natural-language skill request")
    parser.add_argument(
        "--skill",
        dest="skill_id",
        default=None,
        help="Optional explicit skill id; otherwise deterministic routing is used",
    )
    parser.add_argument(
        "--product",
        default=None,
        help="Optional target product name used only as bounded design context",
    )
    args = parser.parse_args(argv)

    context: dict[str, object] = {}
    if args.product is not None:
        context["product"] = args.product

    invocation = build_default_skill_runtime().invoke(
        args.prompt,
        skill_id=args.skill_id,
        context=context,
    )
    print(json.dumps(invocation.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
