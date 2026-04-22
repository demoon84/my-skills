#!/usr/bin/env bash
# autopilot Stop-hook guard.
#
# When the agent tries to stop, this script:
#   1. Resolves the active plan from AUTOPILOT_PLAN_PATH,
#      ./.autopilot/threads/<thread-key>.current, ./.autopilot/current,
#      or compatibility fallbacks.
#   2. Counts unchecked items in ## Done When and ## Todos.
#   3. If any unchecked AND no BLOCKER marker → emit `decision: block` so the
#      agent is forced to continue on the next turn.
#   4. If everything checked → allow the stop, rename plan.md → plan.done.md,
#      and clear the current pointer if it still points at that run.
#   5. If a BLOCKER marker is present → allow the stop (user intervention needed).
#
# The hook communicates via JSON on stdout. Empty output means "allow stop".
#
# This skill is installed for Codex only. The hook emits the Codex-compatible
# Stop-hook block payload on stdout when work remains.

set -euo pipefail

project_root() {
  if [ -n "${CODEX_PROJECT_DIR:-}" ]; then
    printf '%s' "$CODEX_PROJECT_DIR"
    return 0
  fi
  printf '%s' "$PWD"
}

current_pointer_path() {
  printf '%s/.autopilot/current' "$(project_root)"
}

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

resolve_pointer_file() {
  local pointer="$1"
  local recorded

  if [ ! -f "$pointer" ]; then
    return 1
  fi

  recorded="$(tr -d '\r' < "$pointer" | head -n 1)"
  if [ -z "$recorded" ]; then
    return 1
  fi

  if [ -f "$recorded" ]; then
    printf '%s' "$recorded"
    return 0
  fi

  if [ -d "$recorded" ] && [ -f "$recorded/plan.md" ]; then
    printf '%s' "$recorded/plan.md"
    return 0
  fi

  return 1
}

resolve_thread_pointer() {
  local pointer
  pointer="$(thread_pointer_path || true)"
  if [ -z "$pointer" ]; then
    return 1
  fi

  resolve_pointer_file "$pointer"
}

resolve_current_pointer() {
  local pointer
  pointer="$(current_pointer_path)"
  resolve_pointer_file "$pointer"
}

latest_autopilot_plan() {
  local root latest
  root="$(workspace_root)"
  latest=$(ls -t "$root"/*/plan.md 2>/dev/null | head -n 1 || true)
  if [ -n "$latest" ]; then
    printf '%s' "$latest"
    return 0
  fi

  return 1
}

find_plan() {
  if [ -n "${AUTOPILOT_PLAN_PATH:-}" ] && [ -f "$AUTOPILOT_PLAN_PATH" ]; then
    printf '%s' "$AUTOPILOT_PLAN_PATH"
    return 0
  fi

  local thread_plan
  thread_plan="$(resolve_thread_pointer || true)"
  if [ -n "$thread_plan" ]; then
    printf '%s' "$thread_plan"
    return 0
  fi

  local current
  current="$(resolve_current_pointer || true)"
  if [ -n "$current" ]; then
    printf '%s' "$current"
    return 0
  fi

  local latest_autopilot
  latest_autopilot="$(latest_autopilot_plan || true)"
  if [ -n "$latest_autopilot" ]; then
    printf '%s' "$latest_autopilot"
    return 0
  fi

  local candidates=(
    "${CODEX_PROJECT_DIR:-}/plan.md"
    "$PWD/plan.md"
  )
  for c in "${candidates[@]}"; do
    if [ -n "$c" ] && [ -f "$c" ]; then
      printf '%s' "$c"
      return 0
    fi
  done

  # Fall back to scanning .workloop/work_*/plan.md (most recent)
  local latest
  latest=$(ls -t "$PWD"/.workloop/work_*/plan.md 2>/dev/null | head -n 1 || true)
  if [ -n "$latest" ]; then
    printf '%s' "$latest"
    return 0
  fi

  return 1
}

clear_pointer_if_plan() {
  local pointer="$1"
  local plan_file="$2"
  local plan_dir recorded

  if [ ! -f "$pointer" ]; then
    return 0
  fi

  recorded="$(tr -d '\r' < "$pointer" | head -n 1)"
  plan_dir="$(dirname "$plan_file")"

  if [ "$recorded" = "$plan_file" ] || [ "$recorded" = "$plan_dir" ]; then
    rm -f "$pointer"
  fi
}

clear_thread_pointer_if_plan() {
  local plan_file="$1"
  local pointer

  pointer="$(thread_pointer_path || true)"
  if [ -z "$pointer" ]; then
    return 0
  fi

  clear_pointer_if_plan "$pointer" "$plan_file"
}

clear_current_pointer_if_plan() {
  local plan_file="$1"
  clear_pointer_if_plan "$(current_pointer_path)" "$plan_file"
}

# ---------- emit a block decision ----------
emit_block() {
  local reason="$1"
  # Escape double-quotes and backslashes for JSON safety
  reason="${reason//\\/\\\\}"
  reason="${reason//\"/\\\"}"
  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "Stop",
    "decision": "block",
    "reason": "$reason"
  }
}
EOF
}

# ---------- allow the stop ----------
allow_stop() {
  # no stdout → the CLI proceeds to actually stop
  exit 0
}

# ---------- main ----------
plan_file=$(find_plan || true)

if [ -z "$plan_file" ]; then
  # No plan.md found; nothing to guard. Let the agent stop normally.
  allow_stop
fi

# If user marked a blocker explicitly, respect it and allow stop.
if grep -qE '^BLOCKER:\s*true' "$plan_file"; then
  allow_stop
fi

# Extract the ## Done When and ## Todos sections, count unchecked checkboxes.
unchecked=$(awk '
  /^## Done When/    { in_target=1; next }
  /^## Todos/        { in_target=1; next }
  /^## /             { in_target=0 }
  in_target && /^[[:space:]]*- \[ \]/ { count++ }
  END                { print count+0 }
' "$plan_file")

if [ "${unchecked}" -eq 0 ]; then
  # All checkboxes ticked → archive the plan and allow stop.
  done_file="${plan_file%.md}.done.md"
  if [ ! -f "$done_file" ]; then
    mv "$plan_file" "$done_file" 2>/dev/null || true
  fi
  clear_thread_pointer_if_plan "$plan_file"
  clear_current_pointer_if_plan "$plan_file"
  allow_stop
fi

# Still work to do — tell the agent to keep going.
reason="plan.md에 미완료 항목이 ${unchecked}개 남았습니다. ## Next Action을 보고 다음 unchecked todo를 처리하세요."
emit_block "$reason"
exit 0
