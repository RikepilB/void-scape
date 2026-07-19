#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(dirname "$SCRIPT_DIR")}"
VOIDSCAPE_SOURCE="$REPO_ROOT/skill"
LEGACY_SOURCE="$REPO_ROOT/compat/read-video"
CODEX_SKILLS_ROOT="${CODEX_SKILLS_ROOT:-$HOME/.agents/skills}"

install_to() {
  local name="$1" source="$2" dest="$CODEX_SKILLS_ROOT/$name"
  if [ ! -d "$source" ]; then
    echo "RESULT codex $name copy FAILED missing source"
    return 1
  fi
  if ! mkdir -p "$dest"; then
    echo "RESULT codex $name copy FAILED mkdir $dest"
    return 1
  fi
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --exclude workspace.json --exclude .env "$source"/ "$dest"/
  else
    find "$source" -mindepth 1 -maxdepth 1 ! -name workspace.json ! -name .env \
      -exec cp -r {} "$dest"/ \;
  fi
  echo "RESULT codex $name copy OK"
}

verify_frontmatter() {
  local name="$1" dest="$2" skill_md="$2/SKILL.md"
  if [ -f "$skill_md" ] && grep -q '^name:' "$skill_md" && grep -q '^description:' "$skill_md"; then
    echo "RESULT codex $name verify:frontmatter OK"
    return 0
  fi
  echo "RESULT codex $name verify:frontmatter FAILED"
  return 1
}

verify_cli() {
  local name="$1" dest="$2"
  if command -v python >/dev/null 2>&1 && python "$dest/scripts/video.py" probe --help >/dev/null 2>&1; then
    echo "RESULT codex $name verify:cli OK"
    return 0
  fi
  echo "RESULT codex $name verify:cli FAILED"
  return 1
}

any_ok=0
for spec in "voidscape $VOIDSCAPE_SOURCE" "read-video $LEGACY_SOURCE"; do
  name="${spec%% *}"
  source="${spec#* }"
  dest="$CODEX_SKILLS_ROOT/$name"
  if install_to "$name" "$source"; then
    any_ok=1
    verify_frontmatter "$name" "$dest" || true
    verify_cli "$name" "$dest" || true
  fi
done

if [ "$any_ok" -eq 0 ]; then
  echo "SUMMARY all targets FAILED"
  exit 1
fi
echo "SUMMARY install complete: Voidscape primary, read-video compatibility retained"
