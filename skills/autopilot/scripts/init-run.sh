#!/usr/bin/env bash
set -euo pipefail

project_root() {
  if [ -n "${CODEX_PROJECT_DIR:-}" ]; then
    printf '%s' "$CODEX_PROJECT_DIR"
    return 0
  fi
  printf '%s' "$PWD"
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
skill_dir="$(cd "$script_dir/.." && pwd)"
template_path="$skill_dir/templates/plan.md.template"

workspace_root() {
  printf '%s/.autopilot' "$(project_root)"
}

pointer_token() {
  local raw="${1:-}"
  if [ -z "$raw" ]; then
    return 1
  fi

  raw="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]')"
  raw="$(printf '%s' "$raw" | sed -E 's/[^a-z0-9._-]+/-/g; s/^-+//; s/-+$//; s/-+/-/g')"
  if [ -z "$raw" ]; then
    return 1
  fi

  printf '%s' "$raw"
}

thread_key() {
  local candidate

  candidate="$(pointer_token "${AUTOPILOT_THREAD_KEY:-}" || true)"
  if [ -n "$candidate" ]; then
    printf '%s' "$candidate"
    return 0
  fi

  candidate="$(pointer_token "${CODEX_THREAD_ID:-}" || true)"
  if [ -n "$candidate" ]; then
    printf '%s' "$candidate"
    return 0
  fi

  return 1
}

thread_pointer_path() {
  local key
  key="$(thread_key || true)"
  if [ -z "$key" ]; then
    return 1
  fi

  printf '%s/threads/%s.current' "$(workspace_root)" "$key"
}

slugify() {
  local raw="$1"
  raw="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]')"
  raw="$(printf '%s' "$raw" | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g')"
  if [ -z "$raw" ]; then
    raw="autopilot"
  fi
  printf '%s' "$raw"
}

make_run_dir() {
  local root="$1"
  local slug="$2"
  local timestamp="$3"
  local base candidate suffix

  base="$root/${slug}_${timestamp}"
  candidate="$base"
  suffix=1

  while [ -e "$candidate" ]; do
    candidate="${base}_$(printf '%02d' "$suffix")"
    suffix=$((suffix + 1))
  done

  printf '%s' "$candidate"
}

if [ ! -f "$template_path" ]; then
  printf 'plan template not found: %s\n' "$template_path" >&2
  exit 1
fi

root="$(workspace_root)"
slug="$(slugify "${1:-autopilot}")"
timestamp="$(date '+%Y%m%d_%H%M%S')"
run_dir="$(make_run_dir "$root" "$slug" "$timestamp")"
plan_path="$run_dir/plan.md"
thread_pointer="$(thread_pointer_path || true)"

mkdir -p "$run_dir"
cp "$template_path" "$plan_path"
printf '%s\n' "$plan_path" > "$root/current"

if [ -n "$thread_pointer" ]; then
  mkdir -p "$(dirname "$thread_pointer")"
  printf '%s\n' "$plan_path" > "$thread_pointer"
fi

printf '%s\n' "$plan_path"
