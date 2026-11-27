#!/usr/bin/env bash
# Idempotently wire a git worktree (or post-merge main checkout) to .venv,
# .secrets.baseline, and .agents/bmad-custom overrides. Never mutates main from a worktree.
set -euo pipefail
shopt -s nullglob

ROOT="$(git rev-parse --show-toplevel)"
GIT_DIR="$(git rev-parse --path-format=absolute --git-dir)"
GIT_COMMON="$(git rev-parse --path-format=absolute --git-common-dir)"
MAIN_ROOT="$(dirname "$GIT_COMMON")"

link_safe() {
  local src="$1" dst="$2"
  if [[ -L "$dst" ]]; then
    ln -sfn "$src" "$dst"
  elif [[ -e "$dst" ]]; then
    echo "warn: skipping existing non-symlink $dst" >&2
  else
    ln -s "$src" "$dst"
  fi
}

if [[ "$GIT_DIR" == "$GIT_COMMON" ]]; then
  # Main checkout mode (post-merge switchover only)
  if [[ ! -d "$ROOT/.agents/bmad-custom" ]]; then
    echo "skip: .agents/bmad-custom not present yet (pre-merge main); no-op."
    exit 0
  fi
  if [[ -d "$ROOT/_bmad/custom" && ! -L "$ROOT/_bmad/custom" ]]; then
    BAK="${ORCIA_BMAD_BACKUP_DIR:-/tmp/orcia-bmad-custom.bak-$(date +%F)}"
    mkdir -p "$(dirname "$BAK")"
    [[ -e "$BAK" ]] || cp -a "$ROOT/_bmad/custom" "$BAK"
    for uf in "$ROOT/_bmad/custom/"*.user.toml; do
      mv "$uf" "$ROOT/.agents/bmad-custom/"
    done
    rm -rf "$ROOT/_bmad/custom"
  fi
  if [[ -d "$ROOT/_bmad" ]]; then
    link_safe "../.agents/bmad-custom" "$ROOT/_bmad/custom"
  fi
  exit 0
fi

# Worktree mode (read-only wrt MAIN_ROOT)
[[ -e "$MAIN_ROOT/.venv" ]] && link_safe "$MAIN_ROOT/.venv" "$ROOT/.venv"
[[ -e "$MAIN_ROOT/.secrets.baseline" ]] && link_safe "$MAIN_ROOT/.secrets.baseline" "$ROOT/.secrets.baseline"

if [[ -d "$MAIN_ROOT/_bmad" ]]; then
  if [[ -L "$ROOT/_bmad" ]]; then
    echo "warn: skipping symlinked $ROOT/_bmad" >&2
    exit 0
  fi
  mkdir -p "$ROOT/_bmad"
  for entry in "$MAIN_ROOT/_bmad/"*; do
    name="$(basename "$entry")"
    [[ "$name" == "custom" ]] && continue
    link_safe "$entry" "$ROOT/_bmad/$name"
  done
  if [[ -d "$ROOT/.agents/bmad-custom" ]]; then
    link_safe "../.agents/bmad-custom" "$ROOT/_bmad/custom"
    for uf in "$MAIN_ROOT/_bmad/custom/"*.user.toml; do
      link_safe "$uf" "$ROOT/.agents/bmad-custom/$(basename "$uf")"
    done
  fi
fi
