from pathlib import Path
import re
import sys

root = Path(sys.argv[1])


def replace_once(rel: str, old: str, new: str) -> None:
    path = root / rel
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"ANALYZER_FIX_ANCHOR_MISMATCH {rel}: expected 1, actual {count}: {old!r}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def brace_simple_statement_ifs(rel: str) -> None:
    """Brace one-line statement ifs, never collection-if entries.

    The matcher is deliberately line-bounded and requires a semicolon at the
    end, so Dart collection-if entries ending in commas remain untouched.
    """
    path = root / rel
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"(?m)^(?P<indent>[ \t]*)if \((?P<condition>.+)\) "
        r"(?P<body>(?!\{).+;)$"
    )

    def repl(match: re.Match[str]) -> str:
        indent = match.group("indent")
        condition = match.group("condition")
        body = match.group("body")
        return (
            f"{indent}if ({condition}) {{\n"
            f"{indent}  {body}\n"
            f"{indent}}}"
        )

    updated, count = pattern.subn(repl, text)
    if count == 0:
        raise SystemExit(f"NO_SIMPLE_STATEMENT_IFS_TO_BRACE {rel}")
    path.write_text(updated, encoding="utf-8", newline="\n")
    print(f"BRACED_SIMPLE_STATEMENT_IFS {rel}={count}")


# Shared helper function must not be shadowed by a local variable of the same name.
replace_once(
    "apps/desktop/lib/app/desktop_app.dart",
    "final referenceFactoryCount = referenceFactoryCount(objective);",
    "final factoryCount = referenceFactoryCount(objective);",
)
replace_once(
    "apps/desktop/lib/app/desktop_app.dart",
    "if (hasReferences && referenceFactoryCount == 0)",
    "if (hasReferences && factoryCount == 0)",
)
replace_once(
    "apps/desktop/lib/app/desktop_app.dart",
    "if (hasReferences && referenceFactoryCount != 1)",
    "if (hasReferences && factoryCount != 1)",
)
replace_once(
    "apps/desktop/lib/app/desktop_app.dart",
    "if ((hasReferences && referenceFactoryCount == 1) || hasSourceVideo)",
    "if ((hasReferences && factoryCount == 1) || hasSourceVideo)",
)

# The generated compact attachment callback contains one-line ifs. Brace those
# exact anchors first, then brace any remaining simple statement ifs in the
# existing Create view so flutter_lints stays clean after line shifts/formatting.
replace_once(
    "apps/desktop/lib/features/create/create_view.dart",
    "if (scope.target != target) scope.onTargetChanged(target);",
    "if (scope.target != target) {\n                  scope.onTargetChanged(target);\n                }",
)
replace_once(
    "apps/desktop/lib/features/create/create_view.dart",
    "if (!scope.open) scope.onToggle();",
    "if (!scope.open) {\n                  scope.onToggle();\n                }",
)
brace_simple_statement_ifs(
    "apps/desktop/lib/features/create/create_view.dart",
)

# Equivalent lint cleanup in Deliveries; behavior is unchanged.
replace_once(
    "apps/desktop/lib/features/deliveries/deliveries_view.dart",
    "if (value.endsWith(suffix)) value = value.substring(0, value.length - suffix.length);",
    "if (value.endsWith(suffix)) {\n    value = value.substring(0, value.length - suffix.length);\n  }",
)
replace_once(
    "apps/desktop/lib/features/deliveries/deliveries_view.dart",
    "if (value.isEmpty) return record.executionId;",
    "if (value.isEmpty) {\n    return record.executionId;\n  }",
)
replace_once(
    "apps/desktop/lib/features/deliveries/deliveries_view.dart",
    "if (!_isTr(context)) return value;",
    "if (!_isTr(context)) {\n    return value;\n  }",
)

print("COMBINED_ANALYZER_FIXES_APPLIED")
