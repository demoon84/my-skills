#!/usr/bin/env bash
# autopilot Stop-hook guard.
#
# When the agent tries to stop, this script:
#   1. Locates plan.md (env AUTOPILOT_PLAN_PATH, or common locations).
#   2. Counts unchecked items in ## Done When and ## Todos.
#   3. If any unchecked AND no BLOCKER marker → emit `decision: block` so the
#      agent is forced to continue on the next turn.
#   4. If everything checked → allow the stop, rename plan.md → plan.done.md.
#   5. If a BLOCKER marker is present → allow the stop (user intervention needed).
#
# The hook communicates via JSON on stdout. Empty output means "allow stop".
#
# Works across Claude / Codex / Gemini because all three use the same
# `{"hookSpecificOutput": {"hookEventName": "Stop", "decision": "block", "reason": "..."}}`
# contract for the Stop hook.

set -euo pipefail

# ---------- locate plan.md ----------
find_plan() {
  if [ -n "${AUTOPILOT_PLAN_PATH:-}" ] && [ -f "$AUTOPILOT_PLAN_PATH" ]; then
    printf '%s' "$AUTOPILOT_PLAN_PATH"
    return 0
  fi

  local candidates=(
    "${CLAUDE_PROJECT_DIR:-}/plan.md"
    "${CODEX_PROJECT_DIR:-}/plan.md"
    "${GEMINI_PROJECT_DIR:-}/plan.md"
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
  allow_stop
fi

# Still work to do — tell the agent to keep going.
reason="plan.md에 미완료 항목이 ${unchecked}개 남았습니다. ## Next Action을 보고 다음 unchecked todo를 처리하세요."
emit_block "$reason"
exit 0
