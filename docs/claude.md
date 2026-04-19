# Claude Code setup

## Install skills

```bash
node scripts/install-skills.mjs install --all --tools claude
```

This creates symlinks at `~/.claude/skills/<name>` pointing to this package's `skills/<name>` directory.

Hooks declared in `SKILL.md` frontmatter are written to `~/.claude/plugins/myskills/plugin.json` by the installer. The file is marked `"$marker": "myskills"` — do not hand-edit.

## Stop hook (autopilot)

When the `autopilot` skill is installed, its `Stop` hook is registered automatically. Every time Claude finishes a turn, the hook runs `check-completion.sh`, reads `plan.md`, and either:

- allows the stop (all `Done When` + Todos are `[x]`, or `BLOCKER: true` is present), or
- returns `{ "decision": "block", "reason": "..." }` to make Claude continue the next turn.

No scheduler, no routines, no cron. The loop is driven purely by Claude's natural stop points.

## Proxy request fields for Claude

```json
POST /v1/chat/completions
{
  "model": "claude:sonnet",
  "messages": [],
  "permission_mode": "acceptEdits",
  "add_dir": ["/extra/path"]
}
```

| Field             | Maps to              | Allowed values                                                              |
|-------------------|----------------------|-----------------------------------------------------------------------------|
| `permission_mode` | `--permission-mode`  | `default`, `plan`, `acceptEdits`, `bypassPermissions`, `dontAsk`, `delegate`|
| `add_dir`         | `--add-dir`          | array of absolute paths                                                     |

If `permission_mode` is omitted, the env default (`AI_PROXY_CLAUDE_PERMISSION_MODE`, default `plan`) is used. Skills that need Edit/Write must use `acceptEdits` or similar.

## Verify

```bash
ls -la ~/.claude/skills
cat ~/.claude/plugins/myskills/plugin.json
```
