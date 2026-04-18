# my-skills

GitHub-managed Codex skills collection for local installation and reuse.

## Included skills

- `planwork`: talks through a task with the user, creates a dedicated `.workloop` planning folder, and prepares work that can be handed to `workloop`
- `workloop`: creates or updates a same-thread coding heartbeat with `.workloop/work_<timestamp>/` planning folders and explicit completion rules
- `webp`: uses `demoon84/webp-maker` to produce static or animated WebP assets

## Plan with `planwork`, then run `workloop`

Use `planwork` first when the task still needs a short planning conversation. It should clarify the goal, scope, verification, and `Done When`, then create a fresh task folder like `.workloop/work_<timestamp>_<slug>/`.

Once that plan is stable, hand the exact planning files to `workloop` so the same-thread heartbeat keeps moving against the approved plan instead of replanning each wakeup.

Example flow:

```text
Use $planwork to talk through this repository task with me, create a dedicated .workloop planning folder, and make the plan stable enough for $workloop.
```

Then:

```text
Use $workloop to create a 1-minute same-thread coding heartbeat that re-reads .workloop/work_<timestamp>_<slug>/task_plan.md, .workloop/work_<timestamp>_<slug>/findings.md, and .workloop/work_<timestamp>_<slug>/progress.md, keeps changes limited to this repo, verifies relevant checks after code changes, and stops only when the Done When criteria are satisfied or a real blocker requires input.
```

## Optional `Model Strategy`

`planwork` can also record a simple `Model Strategy` section when the user wants guidance on which Codex model fits which subtask.

This repository treats that section as planning metadata only. It is useful for recommendations like "use a deeper model for architecture work and a faster model for narrow cleanup," but it does not turn `planwork` or `workloop` into an automatic routing harness.

Example:

```text
## Model Strategy
- Task: architecture-heavy refactor
  preferred_model: gpt-5.3-codex
  why: deeper reasoning across multiple files

- Task: small focused follow-up
  preferred_model: gpt-5.3-codex-spark
  why: faster narrow iteration
```

## Install from a local clone

```bash
git clone https://github.com/demoon84/my-skills.git
cd my-skills
python3 scripts/skill_repo.py install workloop --mode link
python3 scripts/skill_repo.py install planwork --mode link
python3 scripts/skill_repo.py install webp --mode link
```

Install every skill from the clone:

```bash
python3 scripts/skill_repo.py install --all --mode link
```

Remove an installed skill:

```bash
python3 scripts/skill_repo.py uninstall workloop
```

Print install or uninstall results as JSON:

```bash
python3 scripts/skill_repo.py install workloop --mode link --json
python3 scripts/skill_repo.py uninstall workloop --json
```

## Install directly from GitHub

List what is available from the published repo:

```bash
python3 scripts/skill_repo.py list-github demoon84/my-skills
```

If you already have this repository checked out somewhere, you can use its helper script to install a copy from GitHub:

```bash
python3 scripts/skill_repo.py install-github demoon84/my-skills workloop
python3 scripts/skill_repo.py install-github demoon84/my-skills planwork
python3 scripts/skill_repo.py install-github demoon84/my-skills webp
```

Install every skill from the published repo:

```bash
python3 scripts/skill_repo.py install-github demoon84/my-skills --all
```

Use a different branch or tag:

```bash
python3 scripts/skill_repo.py install-github demoon84/my-skills workloop --ref main
```

Run the helper script directly from GitHub without cloning first:

```bash
curl -fsSL https://raw.githubusercontent.com/demoon84/my-skills/main/scripts/skill_repo.py | python3 - list-github demoon84/my-skills
curl -fsSL https://raw.githubusercontent.com/demoon84/my-skills/main/scripts/skill_repo.py | python3 - install-github demoon84/my-skills workloop
```

## Repository commands

List skills:

```bash
python3 scripts/skill_repo.py list
```

Create a new skill skeleton:

```bash
python3 scripts/skill_repo.py init my-skill --description "Describe the trigger clearly."
```

Refresh the generated catalog:

```bash
python3 scripts/skill_repo.py refresh-catalog
```

Validate the repository metadata:

```bash
python3 scripts/skill_repo.py validate
```

Run the unit tests:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## CI

GitHub Actions runs `python3 scripts/skill_repo.py validate` on pushes to `main` and on pull requests so metadata drift is caught before release.
It also runs `python3 -m unittest discover -s tests -p 'test_*.py'`.
