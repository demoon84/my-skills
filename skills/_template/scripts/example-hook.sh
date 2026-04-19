#!/usr/bin/env bash
# Example lifecycle hook.
# Delete this file or rename it to match an event declared in SKILL.md `hooks`.
#
# Events available:
#   session_start   — run once when a session starts
#   stop            — run when the agent stops
#   pre_tool_use    — run before a tool is invoked
#   post_tool_use   — run after a tool is invoked
#
# Env available to hooks (tool-dependent):
#   CLAUDE_PROJECT_DIR, CODEX_PROJECT_DIR, GEMINI_PROJECT_DIR
set -euo pipefail

echo "[__SKILL_NAME__] example hook invoked"
