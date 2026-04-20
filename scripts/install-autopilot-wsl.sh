#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$repo_root"

echo "[1/3] Validate autopilot metadata"
node scripts/install-skills.mjs validate autopilot

echo "[2/3] Install autopilot into the WSL Codex home"
node scripts/install-skills.mjs install autopilot --tools codex --copy --force

echo "[3/3] Show the generated WSL hook manifest"
cat "$HOME/.codex/hooks.json"
