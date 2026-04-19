# Codex CLI setup

## Install skills

```bash
node scripts/install-skills.mjs install --all --tools codex
```

Creates symlinks at `~/.codex/skills/<name>` pointing to this package's `skills/<name>`.

Hooks are written to `~/.codex/hooks.json` in Claude-compatible JSON (Codex adopted the Claude hook contract). The file is marked `"$marker": "myskills"` — do not hand-edit.

## Stop hook (autopilot)

When the `autopilot` skill is installed, its `Stop` hook is registered automatically. Every time Codex finishes a turn, the hook runs `check-completion.sh` against `plan.md`. If unchecked items remain, the hook returns a block response and Codex continues the next turn with an automatically generated follow-up.

No Codex automations needed. The loop is driven by Codex's Stop hook.

## Proxy request fields for Codex

```json
POST /v1/chat/completions
{
  "model": "codex:default",
  "messages": [],
  "sandbox": "workspace-write",
  "add_dir": ["/extra/path"]
}
```

| Field     | Maps to       | Allowed values                                        |
|-----------|---------------|-------------------------------------------------------|
| `sandbox` | `-s`          | `read-only`, `workspace-write`, `danger-full-access`  |
| `add_dir` | `--add-dir`   | array of absolute paths                               |

`sandbox` defaults to `AI_PROXY_CODEX_SANDBOX` (default `read-only`). Skills that write files need `workspace-write` or higher.

## Verify

```bash
ls -la ~/.codex/skills
cat ~/.codex/hooks.json
```

## Notes on `--ephemeral`

The proxy invokes `codex exec --ephemeral ...`. If a hook or skill doesn't activate, try removing `--ephemeral` via a local patch and re-test.
