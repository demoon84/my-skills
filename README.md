# my-skills

Canonical Codex skill hub for agent-skills format repositories.

The Node installer scans `skills/*`, links each skill into Codex's skill directory, and writes the Codex hook manifest so lifecycle hooks declared in `SKILL.md` frontmatter are picked up automatically.

## Included skills

- `autopilot` (Codex only): talks through a task into `plan.md` (goal, scope, done-when, detailed todos), then uses a platform-specific `Stop` hook (`scripts/check-completion.sh` on macOS/Linux, `scripts/check-completion.ps1` on Windows) to re-engage the agent every time it tries to stop while unchecked items remain. Single skill, two modes (Plan / Autopilot).
- `webp`: wraps `demoon84/webp-maker` to produce static or animated WebP assets.

## Quick start

```bash
git clone https://github.com/demoon84/my-skills.git
cd my-skills

# List discovered skills
node scripts/install-skills.mjs list

# Validate frontmatter + referenced hook scripts
node scripts/install-skills.mjs validate

# Install every discovered skill into the Codex skill directory
# and write the Codex hook manifest
node scripts/install-skills.mjs install --all
```

Equivalent npm scripts are declared in `package.json` (`npm run list`, `npm run validate`, `npm run install-all`).

## Using `autopilot`

`autopilot` is the Codex-only planning + execution skill in this repo. It replaces the earlier `planwork` / `work-loop` pair by collapsing them into one skill plus a Stop hook.

- **Plan mode** — conversation → `plan.md` at the repo root (or `.workloop/work_<ts>_<slug>/plan.md` for isolation).
- **Autopilot mode** — whenever the agent tries to end a turn, the installed `check-completion` hook script reads `plan.md`; if any item in `## Done When` or `## Todos` is still `[ ]`, it emits `{"decision": "block"}` so the agent is forced to continue. When everything is `[x]`, the hook renames `plan.md` → `plan.done.md` and allows the stop.

For readability on Codex desktop, plan review should be a dedicated stopping point: show the full plan, ask for the numbered choice, then end the turn immediately. After the user approves and the plan is saved, execution should begin only on the next explicit `진행` / `continue` message so the review content does not collapse before they read it.

Example prompts:

```text
$autopilot: 로그인 에러 메시지 개선. 계획부터 잡자.   # Plan mode
$autopilot: 진행해                                       # Autopilot loop until done
$autopilot: status                                       # Report progress from plan.md
$autopilot: stop                                         # Disable the hook, keep plan.md
```

See [skills/autopilot/SKILL.md](skills/autopilot/SKILL.md) for the full behavior spec, `plan.md` template, and guardrails. On Windows, the installer writes a PowerShell hook command; on macOS/Linux, it writes the shell-script command.

## Optional `Model Strategy`

`plan.md` has an optional `## Model Strategy` section for recording which model fits which subtask. It is planning metadata only; `autopilot` does not turn it into an automatic routing harness.

```markdown
## Model Strategy
- Task: architecture-heavy refactor
  preferred_model: gpt-5.3-codex
  why: deeper reasoning across multiple files

- Task: small focused follow-up
  preferred_model: gpt-5.3-codex-spark
  why: faster narrow iteration
```

## Installer commands

```bash
# List skills discovered under skills/
node scripts/install-skills.mjs list

# Show current install state
node scripts/install-skills.mjs status
node scripts/install-skills.mjs status autopilot

# Validate a single skill or all
node scripts/install-skills.mjs validate
node scripts/install-skills.mjs validate autopilot

# Install one skill or everything (symlink by default)
node scripts/install-skills.mjs install autopilot
node scripts/install-skills.mjs install --all

# Copy instead of symlink
node scripts/install-skills.mjs install --all --copy

# Install into project scope (.agents/skills) instead of ~/
node scripts/install-skills.mjs install --all --project

# Preview without writing
node scripts/install-skills.mjs install --all --dry-run

# Limit explicitly to the supported tool
node scripts/install-skills.mjs install --all --tools codex

# Remove symlinks for a skill
node scripts/install-skills.mjs uninstall autopilot
```

## Authoring a new skill

```bash
# Scaffold from skills/_template
node scripts/scaffold-skill.mjs my-skill

# Edit skills/my-skill/SKILL.md, then validate + install
node scripts/install-skills.mjs validate my-skill
node scripts/install-skills.mjs install my-skill
```

`skills/_template/SKILL.md` shows the full frontmatter (name / description / targets / hooks / metadata). See [docs/authoring.md](docs/authoring.md) for the AI-assisted authoring flow and [skills/README.md](skills/README.md) for folder conventions.

## CI

`.github/workflows/validate.yml` runs `node scripts/install-skills.mjs validate` and `npm run check` on pushes to `main` and pull requests so metadata drift and syntax errors are caught before release.

## Setup notes

- Codex: [docs/codex.md](docs/codex.md)
