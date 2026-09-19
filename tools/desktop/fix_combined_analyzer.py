from pathlib import Path
import subprocess
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


def replace_once_or_verify(rel: str, old: str, new: str) -> None:
    """Apply one lint-equivalent rewrite or verify it is already present exactly once."""
    path = root / rel
    text = path.read_text(encoding="utf-8")
    old_count = text.count(old)
    new_count = text.count(new)
    if old_count == 1 and new_count == 0:
        path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
        return
    if old_count == 0 and new_count == 1:
        print(f"ANALYZER_FIX_ALREADY_APPLIED {rel}: {old!r}")
        return
    raise SystemExit(
        f"ANALYZER_FIX_EQUIVALENCE_MISMATCH {rel}: old={old_count}, new={new_count}: {old!r}"
    )


def brace_simple_statement_ifs(rel: str) -> None:
    """Brace simple one-line statement ifs without touching collection-if syntax."""
    path = root / rel
    lines = path.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    count = 0

    for line in lines:
        stripped = line.lstrip(" \t")
        indent = line[: len(line) - len(stripped)]
        if not stripped.startswith("if ("):
            output.append(line)
            continue

        open_index = stripped.find("(")
        depth = 0
        close_index = -1
        quote: str | None = None
        escaped = False
        for index in range(open_index, len(stripped)):
            char = stripped[index]
            if quote is not None:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                continue
            if char in {"'", '"'}:
                quote = char
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    close_index = index
                    break

        if close_index < 0:
            output.append(line)
            continue

        body = stripped[close_index + 1 :].strip()
        condition = stripped[open_index + 1 : close_index]
        if not body or body.startswith("{") or not body.endswith(";"):
            output.append(line)
            continue

        output.extend(
            [
                f"{indent}if ({condition}) {{",
                f"{indent}  {body}",
                f"{indent}}}",
            ]
        )
        count += 1

    if count == 0:
        raise SystemExit(f"NO_SIMPLE_STATEMENT_IFS_TO_BRACE {rel}")
    path.write_text("\n".join(output) + "\n", encoding="utf-8", newline="\n")
    print(f"BRACED_SIMPLE_STATEMENT_IFS {rel}={count}")


# Normalize protected-shell typography after the aggressive candidate patch.
normalizer = root / "tools/desktop/normalize_combined_typography.py"
if not normalizer.is_file():
    raise SystemExit(f"NORMALIZER_MISSING {normalizer}")
subprocess.run([sys.executable, str(normalizer), str(root)], check=True)

# Shared helper function must not be shadowed by a local variable of the same name.
replace_once_or_verify(
    "apps/desktop/lib/app/desktop_app.dart",
    "final referenceFactoryCount = referenceFactoryCount(objective);",
    "final referenceTargetCount = referenceFactoryCount(objective);",
)
replace_once_or_verify(
    "apps/desktop/lib/app/desktop_app.dart",
    "if (hasReferences && referenceFactoryCount == 0)",
    "if (hasReferences && referenceTargetCount == 0)",
)
replace_once_or_verify(
    "apps/desktop/lib/app/desktop_app.dart",
    "if (hasReferences && referenceFactoryCount != 1)",
    "if (hasReferences && referenceTargetCount != 1)",
)
replace_once_or_verify(
    "apps/desktop/lib/app/desktop_app.dart",
    "if ((hasReferences && referenceFactoryCount == 1) || hasSourceVideo)",
    "if ((hasReferences && referenceTargetCount == 1) || hasSourceVideo)",
)

# The generated compact attachment callback contains one-line ifs. Brace those
# exact anchors first, then safely brace remaining simple statement ifs in the
# existing Create view so flutter_lints remains clean after line shifts.
replace_once_or_verify(
    "apps/desktop/lib/features/create/create_view.dart",
    "if (scope.target != target) scope.onTargetChanged(target);",
    "if (scope.target != target) {\n                  scope.onTargetChanged(target);\n                }",
)
replace_once_or_verify(
    "apps/desktop/lib/features/create/create_view.dart",
    "if (!scope.open) scope.onToggle();",
    "if (!scope.open) {\n                  scope.onToggle();\n                }",
)
brace_simple_statement_ifs(
    "apps/desktop/lib/features/create/create_view.dart",
)

# Equivalent lint cleanup in Deliveries. Newer source may already carry the
# same braces; accept only the exact unbraced or exact braced form, never an
# ambiguous/missing anchor.
replace_once_or_verify(
    "apps/desktop/lib/features/deliveries/deliveries_view.dart",
    "if (value.endsWith(suffix)) value = value.substring(0, value.length - suffix.length);",
    "if (value.endsWith(suffix)) {\n    value = value.substring(0, value.length - suffix.length);\n  }",
)
replace_once_or_verify(
    "apps/desktop/lib/features/deliveries/deliveries_view.dart",
    "if (value.isEmpty) return record.executionId;",
    "if (value.isEmpty) {\n    return record.executionId;\n  }",
)
replace_once_or_verify(
    "apps/desktop/lib/features/deliveries/deliveries_view.dart",
    "if (!_isTr(context)) return value;",
    "if (!_isTr(context)) {\n    return value;\n  }",
)

print("COMBINED_ANALYZER_FIXES_APPLIED")
