#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(dirname "$SCRIPT_DIR")}"
VOIDSCAPE_SOURCE="$REPO_ROOT/skill"
LEGACY_SOURCE="$REPO_ROOT/compat/read-video"
CODEX_SKILLS_ROOT="${CODEX_SKILLS_ROOT:-$HOME/.codex/skills}"
AGENTS_SKILLS_ROOT="${AGENTS_SKILLS_ROOT:-$HOME/.agents/skills}"

install_to() {
  local harness="$1" root="$2" name="$3" source="$4" dest="$2/$3"
  if [ ! -d "$source" ]; then
    echo "RESULT $harness $name copy FAILED missing source"
    return 1
  fi
  if ! mkdir -p "$dest"; then
    echo "RESULT $harness $name copy FAILED mkdir $dest"
    return 1
  fi
  if command -v rsync >/dev/null 2>&1; then
    if ! rsync -a --exclude workspace.json --exclude .env --exclude load-env.ps1 \
      "$source"/ "$dest"/; then
      echo "RESULT $harness $name copy FAILED rsync $dest"
      return 1
    fi
  else
    if ! find "$source" -mindepth 1 -maxdepth 1 ! -name workspace.json ! -name .env \
      ! -name load-env.ps1 -exec cp -r {} "$dest"/ \;; then
      echo "RESULT $harness $name copy FAILED cp $dest"
      return 1
    fi
  fi
  echo "RESULT $harness $name copy OK"
}

verify_frontmatter() {
  local harness="$1" name="$2" dest="$3" skill_md="$3/SKILL.md"
  if [ -f "$skill_md" ] && grep -q '^name:' "$skill_md" && grep -q '^description:' "$skill_md"; then
    echo "RESULT $harness $name verify:frontmatter OK"
    return 0
  fi
  echo "RESULT $harness $name verify:frontmatter FAILED"
  return 1
}

verify_cli() {
  local harness="$1" name="$2" dest="$3" python_cmd=""
  if command -v python >/dev/null 2>&1; then
    python_cmd="python"
  elif command -v python3 >/dev/null 2>&1; then
    python_cmd="python3"
  fi
  if [ -n "$python_cmd" ] && "$python_cmd" "$dest/scripts/video.py" probe --help >/dev/null 2>&1; then
    echo "RESULT $harness $name verify:cli OK"
    return 0
  fi
  echo "RESULT $harness $name verify:cli FAILED"
  return 1
}

all_ok=1
for target in "codex $CODEX_SKILLS_ROOT" "agents $AGENTS_SKILLS_ROOT"; do
  harness="${target%% *}"
  root="${target#* }"
  for spec in "voidscape $VOIDSCAPE_SOURCE" "read-video $LEGACY_SOURCE"; do
    name="${spec%% *}"
    source="${spec#* }"
    dest="$root/$name"
    if ! install_to "$harness" "$root" "$name" "$source"; then
      all_ok=0
      continue
    fi
    verify_frontmatter "$harness" "$name" "$dest" || all_ok=0
    verify_cli "$harness" "$name" "$dest" || all_ok=0
  done
done

if [ "$all_ok" -eq 0 ]; then
  echo "SUMMARY install FAILED: one or more copies or verification checks failed"
  exit 1
fi
echo "SUMMARY install complete: Voidscape primary, read-video compatibility retained"
