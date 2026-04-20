# Skill Repository Rules

- Installable skills live in `skills/<skill-name>/`.
- Keep one skill per folder and name folders with lowercase letters, digits, and hyphens only.
- Every skill must have `SKILL.md`. `agents/openai.yaml` is recommended and should stay in sync with `SKILL.md`.
- Do not put extra docs inside a skill folder unless they are directly used by the skill, such as `references/`, `scripts/`, or `assets/`.
- Use `node scripts/scaffold-skill.mjs <name>` to scaffold a new skill from `skills/_template` instead of hand-rolling the folder structure.
- Use `node scripts/install-skills.mjs validate` after adding or updating skill metadata.
- Use `node scripts/install-skills.mjs install <skill-name>` to symlink a repo-managed skill into `~/.codex/skills`.
- Keep `catalog.json` in sync with `skills/` when the skill set changes (add/remove entries, update descriptions). It is a hand-maintained public manifest.
