#!/usr/bin/env bash
set -euo pipefail

# Import only an explicitly approved, pre-extracted ILAIOS brand package.
# This script is intentionally fail-closed: specification boards must never be
# substituted for deployable logo masters, and imports must never push directly
# to master.

SOURCE_DIR="${1:-}"
REPO_ROOT="$(git rev-parse --show-toplevel)"
ASSET_DIR="$REPO_ROOT/brand/assets"
SOURCE_ARCHIVE_DIR="$REPO_ROOT/brand/source"
CURRENT_BRANCH="$(git branch --show-current)"

cd "$REPO_ROOT"

if [[ -z "$SOURCE_DIR" || ! -d "$SOURCE_DIR" ]]; then
  echo "ERROR: usage: $0 /path/to/pre-extracted-approved-brand-package" >&2
  exit 2
fi

if [[ -z "$CURRENT_BRANCH" || "$CURRENT_BRANCH" == "master" ]]; then
  echo "ERROR: brand imports must run on a review branch, never directly on master" >&2
  exit 3
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: worktree is not clean" >&2
  git status --short
  exit 4
fi

mkdir -p "$ASSET_DIR" "$SOURCE_ARCHIVE_DIR"

find_unique() {
  local pattern="$1"
  mapfile -t matches < <(find "$SOURCE_DIR" -type f -name "$pattern" -print | sort)
  if [[ "${#matches[@]}" -ne 1 ]]; then
    echo "ERROR: expected exactly one deployable source matching '$pattern'; found ${#matches[@]}" >&2
    printf '  %s\n' "${matches[@]:-}" >&2
    exit 5
  fi
  printf '%s\n' "${matches[0]}"
}

copy_unique() {
  local pattern="$1"
  local target_name="$2"
  local source
  source="$(find_unique "$pattern")"
  cp -f "$source" "$ASSET_DIR/$target_name"
}

# Dark runtime masters are deliberately stricter than the numbered package
# boards. The final package's 02/03 JPG/PNG/PDF files are specification boards;
# they are not valid runtime replacements. Require explicit deployable masters.
DARK_HORIZONTAL_JPG="$(find_unique '02-ilaios-primary-horizontal-dark-runtime.jpg')"
DARK_SYMBOL_JPG="$(find_unique '03-ilaios-symbol-dark-runtime.jpg')"
DARK_SYMBOL_SVG="$(find_unique 'ilaios-symbol-dark.svg')"

python3 - "$DARK_HORIZONTAL_JPG" "$DARK_SYMBOL_JPG" "$DARK_SYMBOL_SVG" <<'PY'
from pathlib import Path
import sys

horizontal = Path(sys.argv[1])
symbol_jpg = Path(sys.argv[2])
symbol_svg = Path(sys.argv[3])

for path in (horizontal, symbol_jpg, symbol_svg):
    if path.stat().st_size <= 0:
        raise SystemExit(f"ERROR: deployable master is empty: {path}")

svg_head = symbol_svg.read_text(encoding="utf-8", errors="strict").lstrip()[:512].lower()
if "<svg" not in svg_head:
    raise SystemExit(f"ERROR: expected SVG primary master, got non-SVG content: {symbol_svg}")
PY

cp -f "$DARK_HORIZONTAL_JPG" "$ASSET_DIR/02-ilaios-primary-horizontal-dark.jpg"
cp -f "$DARK_SYMBOL_JPG" "$ASSET_DIR/03-ilaios-symbol-dark.jpg"

# Direct deployable/package assets. Existing canonical repo filenames are kept.
copy_unique '01-ilaios-brand-color-system.png' '01-ilaios-brand-color-system.png'
copy_unique '04-ilaios-symbol-light*.jpg' '04-ilaios-symbol-light.jpg'
copy_unique '05-ilaios-app-icon.jpg' '05-ilaios-app-icon.jpg'
copy_unique '06-ilaios-favicon-master.jpg' '06-ilaios-favicon-master.jpg'
copy_unique '07-ilaios-linkedin-company-logo.jpg' '07-ilaios-linkedin-company-logo.jpg'
copy_unique '08-ilaios-linkedin-company-cover-v3-balanced.jpg' '08-ilaios-linkedin-company-cover.jpg'
copy_unique '09-ilaios-linkedin-personal-cover.jpg' '09-ilaios-linkedin-personal-cover.jpg'
copy_unique '10-ilaios-github-social-preview.jpg' '10-ilaios-github-social-preview.jpg'
copy_unique '11-ilaios-website-hero.jpg' '11-ilaios-website-hero.jpg'
copy_unique '12-ilaios-official-brand-board.jpg' '12-ilaios-official-brand-board.jpg'
copy_unique '13-ilaios-primary-horizontal-light-v2*.jpg' '13-ilaios-primary-horizontal-light.jpg'

python3 - "$SOURCE_DIR" "$SOURCE_ARCHIVE_DIR/ilaios-full-logo.zip" <<'PY'
from pathlib import Path
import sys
import zipfile

source = Path(sys.argv[1]).resolve()
target = Path(sys.argv[2]).resolve()
with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(source.rglob("*")):
        if path.is_file():
            archive.write(path, path.relative_to(source.parent))
PY

python3 - "$ASSET_DIR" <<'PY'
from pathlib import Path
import sys

expected = [
    "01-ilaios-brand-color-system.png",
    "02-ilaios-primary-horizontal-dark.jpg",
    "03-ilaios-symbol-dark.jpg",
    "04-ilaios-symbol-light.jpg",
    "05-ilaios-app-icon.jpg",
    "06-ilaios-favicon-master.jpg",
    "07-ilaios-linkedin-company-logo.jpg",
    "08-ilaios-linkedin-company-cover.jpg",
    "09-ilaios-linkedin-personal-cover.jpg",
    "10-ilaios-github-social-preview.jpg",
    "11-ilaios-website-hero.jpg",
    "12-ilaios-official-brand-board.jpg",
    "13-ilaios-primary-horizontal-light.jpg",
]
root = Path(sys.argv[1])
missing = [name for name in expected if not (root / name).is_file()]
empty = [name for name in expected if (root / name).is_file() and (root / name).stat().st_size == 0]
if missing or empty:
    raise SystemExit(f"ERROR: asset validation failed; missing={missing}; empty={empty}")
print(f"validated {len(expected)} canonical raster assets")
PY

sha256sum "$ASSET_DIR"/* "$SOURCE_ARCHIVE_DIR/ilaios-full-logo.zip"

git add brand/assets brand/source
changed="$(git diff --cached --name-only)"
if [[ -z "$changed" ]]; then
  echo "No asset changes staged."
  exit 0
fi
if echo "$changed" | grep -Ev '^(brand/assets/|brand/source/)' >/dev/null; then
  echo "ERROR: staged changes escaped allowed brand paths" >&2
  echo "$changed"
  git reset --quiet
  exit 6
fi

echo "STATUS: STAGED_FOR_REVIEW"
echo "BRANCH: $CURRENT_BRANCH"
echo "DARK_SYMBOL_PRIMARY_MASTER: $DARK_SYMBOL_SVG"
echo "NOTE: no commit or push was performed; review byte hashes before committing"
