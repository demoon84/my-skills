# Skills

This directory is the canonical source for skills distributed to Claude, Codex, and Gemini.

Each subdirectory is one skill. The installer scans `skills/*` and fans out to each CLI's native skill directory via symlink (or copy with `--copy`).

## Adding a new skill

```bash
# Scaffold from _template
node scripts/scaffold-skill.mjs my-skill

# Or manually: copy _template to skills/my-skill and edit SKILL.md
```

After editing:

```bash
node scripts/install-skills.mjs validate my-skill
node scripts/install-skills.mjs install my-skill
```

## SKILL.md format

```yaml
---
name: my-skill                      # required, must match folder name
description: What the skill does.   # required
targets: [claude, codex, gemini]    # optional, default: all three
hooks:                              # optional
  session_start: scripts/init.sh
  stop: scripts/finish.sh
  pre_tool_use: scripts/pre.sh
  post_tool_use: scripts/post.sh
metadata:                           # optional, free-form
  tags: [planning]
---

# Skill body (markdown instructions for the agent)
```

### Required fields
- `name` — folder name in lowercase with hyphens
- `description` — one-line summary used by skill-selection heuristics

### Optional fields
- `targets` — which tools to install this skill for. Default: `[claude, codex, gemini]`.
- `hooks` — lifecycle hooks. Keys must be one of `session_start`, `stop`, `pre_tool_use`, `post_tool_use`. Values are paths (relative to the skill folder) to shell scripts.
- `metadata` — free-form tags, categories, etc.

### Skill folder layout

```
skills/my-skill/
├── SKILL.md           # required
├── scripts/           # optional — hook scripts referenced from SKILL.md
│   └── init.sh
└── templates/         # optional — file templates the skill produces
```

## Install targets

Running `node scripts/install-skills.mjs install my-skill` creates symlinks at:

| Tool   | Global path                       | Project path (`--project`)   |
|--------|-----------------------------------|------------------------------|
| Claude | `~/.claude/skills/my-skill`       | `.claude/skills/my-skill`    |
| Codex  | `~/.codex/skills/my-skill`        | `.agents/skills/my-skill`    |
| Gemini | `~/.gemini/skills/my-skill`       | `.agents/skills/my-skill`    |

Hook bindings are additionally written into each tool's manifest (auto-generated). See `docs/authoring.md` for the AI-assisted creation flow.

## Conventions

- Folder names use `kebab-case`.
- Do not hand-edit the `.claude-plugin/`, `.codex/`, `.gemini/` directories at the repo root — the installer regenerates those files from this directory.
- Directories starting with `_` (like `_template`) or `.` are ignored by the scanner.
