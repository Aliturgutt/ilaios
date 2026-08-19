from pathlib import Path
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

# flutter_lints requires explicit blocks for these flow-control statements.
replace_once(
    "apps/desktop/lib/features/create/create_view.dart",
    "if (scope.target != target) scope.onTargetChanged(target);",
    "if (scope.target != target) {\n                  scope.onTargetChanged(target);\n                }",
)
replace_once(
    "apps/desktop/lib/features/deliveries/deliveries_view.dart",
    "if (!_isTr(context)) return value;",
    "if (!_isTr(context)) {\n    return value;\n  }",
)

print("COMBINED_ANALYZER_FIXES_APPLIED")
