# Skill Repository Rules

- Installable skills live in `skills/<skill-name>/`.
- Keep one skill per folder and name folders with lowercase letters, digits, and hyphens only.
- Every skill must have `SKILL.md`. `agents/openai.yaml` is recommended and should stay in sync with `SKILL.md`.
- Do not put extra docs inside a skill folder unless they are directly used by the skill, such as `references/`, `scripts/`, or `assets/`.
- Use `python3 scripts/skill_repo.py init ...` to scaffold a new skill instead of hand-rolling the folder structure.
- Use `python3 scripts/skill_repo.py refresh-catalog` after adding or updating skill metadata.
- Use `python3 scripts/skill_repo.py install <skill-name> --mode link` to install a repo-managed skill into `~/.codex/skills`.
- Treat `catalog.json` as generated output. Edit source files under `skills/` and regenerate the catalog instead of editing it directly.
