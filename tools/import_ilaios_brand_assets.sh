#!/usr/bin/env bash
set -euo pipefail

# Import only the explicitly approved final ILAIOS brand package.
# This script is intentionally fail-closed:
# - imports never run directly on master,
# - 02/03 are preserved as reference boards, never runtime masters,
# - 05 is the canonical Dark runtime owner,
# - 13 is the canonical Light horizontal runtime owner,
# - the original final ZIP is copied byte-for-byte rather than re-zipped,
# - every staged binary must match the locked SHA-256 authority.

SOURCE_DIR="${1:-}"
SOURCE_ARCHIVE="${2:-}"
REPO_ROOT="$(git rev-parse --show-toplevel)"
ASSET_DIR="$REPO_ROOT/brand/assets"
SOURCE_ARCHIVE_DIR="$REPO_ROOT/brand/source"
CHECKSUM_FILE="$REPO_ROOT/.brand-hydration/expected.sha256"
CURRENT_BRANCH="$(git branch --show-current)"

cd "$REPO_ROOT"

if [[ -z "$SOURCE_DIR" || ! -d "$SOURCE_DIR" ]]; then
  echo "ERROR: usage: $0 /path/to/pre-extracted-final-brand-package /path/to/original-final.zip" >&2
  exit 2
fi

if [[ -z "$SOURCE_ARCHIVE" || ! -f "$SOURCE_ARCHIVE" ]]; then
  echo "ERROR: original final ZIP is required as argument 2" >&2
  exit 2
fi

if [[ ! -f "$CHECKSUM_FILE" ]]; then
  echo "ERROR: checksum authority missing: $CHECKSUM_FILE" >&2
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
    echo "ERROR: expected exactly one approved source matching '$pattern'; found ${#matches[@]}" >&2
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

# Final-package assets. 02/03 are specification/reference boards and are copied
# only as reference assets. Runtime code must not depend on them.
copy_unique '01-ilaios-brand-color-system.png' '01-ilaios-brand-color-system.png'
copy_unique '02-ilaios-primary-horizontal-dark.jpg' '02-ilaios-primary-horizontal-dark.jpg'
copy_unique '03-ilaios-symbol-dark.jpg' '03-ilaios-symbol-dark.jpg'
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

# Preserve the exact approved source archive bytes. Never recreate/recompress it.
cp -f "$SOURCE_ARCHIVE" "$SOURCE_ARCHIVE_DIR/ilaios-full-logo.zip"

python3 - "$ASSET_DIR" "$SOURCE_ARCHIVE_DIR/ilaios-full-logo.zip" "$CHECKSUM_FILE" <<'PY'
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import sys

asset_dir = Path(sys.argv[1])
archive = Path(sys.argv[2])
checksum_file = Path(sys.argv[3])

expected_names = [
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

locked: dict[str, str] = {}
for raw in checksum_file.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    digest, name = line.split(maxsplit=1)
    locked[name] = digest.lower()

required_locks = expected_names + ["ilaios-full-logo.zip"]
missing_locks = [name for name in required_locks if name not in locked]
if missing_locks:
    raise SystemExit(f"ERROR: checksum authority incomplete: {missing_locks}")

paths = {name: asset_dir / name for name in expected_names}
paths["ilaios-full-logo.zip"] = archive

missing = [name for name, path in paths.items() if not path.is_file()]
empty = [name for name, path in paths.items() if path.is_file() and path.stat().st_size == 0]
if missing or empty:
    raise SystemExit(f"ERROR: asset validation failed; missing={missing}; empty={empty}")

mismatches: list[str] = []
for name, path in paths.items():
    actual = sha256(path.read_bytes()).hexdigest()
    expected = locked[name]
    if actual != expected:
        mismatches.append(f"{name}: expected={expected} actual={actual}")

if mismatches:
    raise SystemExit("ERROR: final-package checksum mismatch:\n" + "\n".join(mismatches))

print("ILAIOS_FINAL_BRAND_SHA256_VALIDATION=PASS")
print("DARK_RUNTIME_OWNER=05-ilaios-app-icon.jpg")
print("LIGHT_RUNTIME_OWNER=13-ilaios-primary-horizontal-light.jpg")
print("REFERENCE_ONLY=02-ilaios-primary-horizontal-dark.jpg,03-ilaios-symbol-dark.jpg")
PY

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
echo "DARK_RUNTIME_OWNER: brand/assets/05-ilaios-app-icon.jpg"
echo "LIGHT_RUNTIME_OWNER: brand/assets/13-ilaios-primary-horizontal-light.jpg"
echo "REFERENCE_ONLY: brand/assets/02-ilaios-primary-horizontal-dark.jpg, brand/assets/03-ilaios-symbol-dark.jpg"
echo "SOURCE_ARCHIVE: brand/source/ilaios-full-logo.zip (byte-exact copy)"
echo "NOTE: no commit or push was performed; review staged bytes before committing"
