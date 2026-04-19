# Gemini CLI setup

## Install skills

```bash
node scripts/install-skills.mjs install --all --tools gemini
```

Creates symlinks at `~/.gemini/skills/<name>` pointing to this package's `skills/<name>`.

Hooks are written to `~/.gemini/hooks.json` in Claude-compatible JSON (Gemini ships `gemini hooks migrate` from Claude Code). The file is marked `"$marker": "myskills"` — do not hand-edit.

If your Gemini CLI version loads hooks from a different location (older builds used `~/.gemini/settings.json` with a `hooks` key), symlink or copy `~/.gemini/hooks.json` into place:

```bash
ln -s ~/.gemini/hooks.json ~/.gemini/settings-hooks.json   # example
```

## Stop hook (autopilot)

`autopilot` registers a `Stop` hook the same way it does for Claude and Codex. When Gemini finishes a turn, the hook reads `plan.md` and blocks the stop if unchecked items remain. Gemini doesn't have a built-in scheduler; the Stop hook is the only mechanism needed.

## Proxy request fields for Gemini

```json
POST /v1/chat/completions
{
  "model": "gemini:auto",
  "messages": [],
  "approval_mode": "auto_edit",
  "add_dir": ["/extra/path"]
}
```

| Field           | Maps to                    | Allowed values                                                   |
|-----------------|----------------------------|------------------------------------------------------------------|
| `approval_mode` | `--approval-mode`          | `default`, `auto_edit`, `yolo`, `plan`                           |
| `add_dir`       | `--include-directories`    | array of absolute paths                                          |

`approval_mode` defaults to `AI_PROXY_GEMINI_APPROVAL_MODE` (default `plan`).

## Verify

```bash
ls -la ~/.gemini/skills
cat ~/.gemini/hooks.json
gemini skills list
```
