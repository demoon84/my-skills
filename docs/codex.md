# Codex CLI setup

## Install skills

```bash
node scripts/install-skills.mjs install --all --tools codex
```

Creates symlinks at `~/.codex/skills/<name>` pointing to this package's `skills/<name>`.

Hooks are written to `~/.codex/hooks.json`. The file is marked `"$marker": "myskills"` — do not hand-edit.

## Stop hook (autopilot)

When the `autopilot` skill is installed, its `Stop` hook is registered automatically. Every time Codex finishes a turn, the hook runs the platform-appropriate `check-completion` script against `plan.md`:

- macOS / Linux: `check-completion.sh`
- Windows: `check-completion.ps1`

If unchecked items remain, the hook returns a block response and Codex continues the next turn with an automatically generated follow-up.

No Codex automations needed. The loop is driven by Codex's Stop hook.

On current Codex releases, Windows hook support may still lag behind macOS/Linux. When native Windows hooks are unavailable, the recommended fallback is to run Codex inside WSL2 while keeping the same `autopilot` skill.

## Windows: native vs WSL2

Use the same skill, but choose the runner by platform:

- Native Windows Codex: installer writes a PowerShell hook command that runs `check-completion.ps1`
- macOS / Linux Codex: installer writes the shell-script hook command that runs `check-completion.sh`
- Windows + WSL2 Codex: treat WSL2 like Linux and install the skill from inside the distro so Codex writes the shell-script hook there

Recommended WSL2 flow when native Windows hooks do not fire:

1. Open an elevated Windows terminal and install WSL2 plus a distro.
2. Reboot if Windows requests it.
3. Open the distro shell and move into the repo, for example `/mnt/d/lab/my-skills`.
4. Run `bash scripts/install-autopilot-wsl.sh` inside WSL.
5. Verify `~/.codex/hooks.json` inside WSL points to `check-completion.sh`.
6. Run Codex from the WSL shell for the task that needs `autopilot`.

Notes:

- Enabling `Microsoft-Windows-Subsystem-Linux` / `VirtualMachinePlatform` requires an elevated Windows session.
- Native Windows Codex and WSL Codex keep separate homes, so verify the manifest inside WSL at `~/.codex/hooks.json`.

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
