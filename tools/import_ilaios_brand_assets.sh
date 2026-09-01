#!/usr/bin/env bash
set -euo pipefail

EXPECTED_BRANCH="master"
SOURCE_DIR="/mnt/c/Users/USER/OneDrive/Desktop/ilaios full Logo"
REPO_ROOT="$(git rev-parse --show-toplevel)"
ASSET_DIR="$REPO_ROOT/brand/assets"
SOURCE_ARCHIVE_DIR="$REPO_ROOT/brand/source"

cd "$REPO_ROOT"

if [[ "$(git branch --show-current)" != "$EXPECTED_BRANCH" ]]; then
  echo "ERROR: expected branch $EXPECTED_BRANCH" >&2
  exit 2
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: worktree is not clean" >&2
  git status --short
  exit 3
fi

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "ERROR: source directory not found: $SOURCE_DIR" >&2
  exit 4
fi

git pull --ff-only origin master
mkdir -p "$ASSET_DIR" "$SOURCE_ARCHIVE_DIR"

copy_asset() {
  local source_rel="$1"
  local target_name="$2"
  local source="$SOURCE_DIR/$source_rel"
  local target="$ASSET_DIR/$target_name"
  if [[ ! -f "$source" ]]; then
    echo "ERROR: missing source asset: $source" >&2
    exit 5
  fi
  cp -f "$source" "$target"
}

copy_asset "1 — Brand Color System/01-ilaios-brand-color-system.png" "01-ilaios-brand-color-system.png"
copy_asset "02-ilaios-primary-horizontal-dark.svg/02-ilaios-primary-horizontal-dark.jpg" "02-ilaios-primary-horizontal-dark.jpg"
copy_asset "3- Primary Horizontal Light/03-ilaios-symbol-dark.jpg" "03-ilaios-symbol-dark.jpg"
copy_asset "4-Symbol Only  Light/04-ilaios-symbol-light.jpg" "04-ilaios-symbol-light.jpg"
copy_asset "5- ilaioswordmark/05-ilaios-app-icon(1).jpg" "05-ilaios-app-icon.jpg"
copy_asset "06 — ILAIOS Favicon Master/06-ilaios-favicon-master(2).jpg" "06-ilaios-favicon-master.jpg"
copy_asset "07 — ILAIOS LinkedIn Company Logo/07-ilaios-linkedin-company-logo-FIXED.jpg" "07-ilaios-linkedin-company-logo.jpg"
copy_asset "08 — ILAIOS LinkedIn Company Cover/08-ilaios-linkedin-company-cover-v3-balanced.jpg" "08-ilaios-linkedin-company-cover.jpg"
copy_asset "09 — ILAIOS LinkedIn Personal Cover/09-ilaios-linkedin-personal-cover.jpg" "09-ilaios-linkedin-personal-cover.jpg"
copy_asset "10 — ILAIOS GitHub Social Preview/10-ilaios-github-social-preview.jpg" "10-ilaios-github-social-preview.jpg"
copy_asset "11 — ILAIOS Website Hero/11-ilaios-website-hero.jpg" "11-ilaios-website-hero.jpg"
copy_asset "12 — ILAIOS Official Brand Board/12-ilaios-official-brand-board.jpg" "12-ilaios-official-brand-board.jpg"
copy_asset "13 — ILAIOS Primary Horizontal Light/13-ilaios-primary-horizontal-light-v2.jpg" "13-ilaios-primary-horizontal-light.jpg"

python3 - "$SOURCE_DIR" "$SOURCE_ARCHIVE_DIR/ilaios-full-logo.zip" <<'PY'
from pathlib import Path
import sys
import zipfile

source = Path(sys.argv[1])
target = Path(sys.argv[2])
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
    raise SystemExit(f"asset validation failed; missing={missing}; empty={empty}")
print(f"validated {len(expected)} canonical raster assets")
PY

sha256sum "$ASSET_DIR"/* "$SOURCE_ARCHIVE_DIR/ilaios-full-logo.zip"

git add brand/assets brand/source
if git diff --cached --quiet; then
  echo "No asset changes to commit."
  exit 0
fi

changed="$(git diff --cached --name-only)"
if echo "$changed" | grep -Ev '^(brand/assets/|brand/source/)' >/dev/null; then
  echo "ERROR: staged changes escaped allowed brand paths" >&2
  echo "$changed"
  exit 6
fi

git commit -m "chore(brand): import approved ILAIOS brand assets"
git push origin master

git fetch origin master
HEAD_SHA="$(git rev-parse HEAD)"
ORIGIN_SHA="$(git rev-parse origin/master)"
if [[ "$HEAD_SHA" != "$ORIGIN_SHA" ]]; then
  echo "ERROR: HEAD does not equal origin/master" >&2
  exit 7
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: worktree not clean after push" >&2
  git status --short
  exit 8
fi

echo "STATUS: PASS"
echo "COMMIT: $HEAD_SHA"
echo "CANONICAL_ASSETS: 13"
echo "SOURCE_ARCHIVE: brand/source/ilaios-full-logo.zip"
