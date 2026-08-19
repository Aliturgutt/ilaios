from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
rel = "apps/desktop/lib/features/dashboard/reference_desktop_shell_v10.dart"

# Rebuild V10 from the exact checked-out branch source so the combined package
# gets one controlled 15.8% baseline uplift (.95 -> 1.10) without stacking a
# second set of aggressive hard-coded micro-font changes on top. This preserves
# every shell geometry constant byte-for-byte.
result = subprocess.run(
    ["git", "-C", str(root), "show", f"HEAD:{rel}"],
    check=True,
    capture_output=True,
    text=True,
    encoding="utf-8",
)
text = result.stdout

media_anchor = "    final media = MediaQuery.of(context);"
if text.count(media_anchor) != 1:
    raise SystemExit("NORMALIZE_TYPOGRAPHY_MEDIA_ANCHOR_MISMATCH")
text = text.replace(
    media_anchor,
    media_anchor
    + "\n    final systemTextScale = media.textScaler.scale(1.0);"
    + "\n    final desktopTextScale = math.max(1.10, systemTextScale);",
    1,
)

scale_anchor = (
    "          data: media.copyWith(textScaler: const TextScaler.linear(.95)),"
)
if text.count(scale_anchor) != 1:
    raise SystemExit("NORMALIZE_TYPOGRAPHY_SCALE_ANCHOR_MISMATCH")
text = text.replace(
    scale_anchor,
    "          data: media.copyWith(textScaler: TextScaler.linear(desktopTextScale)),",
    1,
)

path = root / rel
path.write_text(text, encoding="utf-8", newline="\n")
print("V10_TYPOGRAPHY_NORMALIZED_TO_CONTROLLED_1_10_BASELINE")
