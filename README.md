# my-skills

GitHub-managed Codex skills collection for local installation and reuse.

## Included skills

- `workloop`: creates or updates a same-thread coding heartbeat with `.workloop/work_<timestamp>/` planning folders and explicit completion rules
- `webp`: uses `demoon84/webp-maker` to produce static or animated WebP assets

## Install from a local clone

```bash
git clone https://github.com/demoon84/my-skills.git
cd my-skills
python3 scripts/skill_repo.py install workloop --mode link
python3 scripts/skill_repo.py install webp --mode link
```

Install every skill from the clone:

```bash
python3 scripts/skill_repo.py install --all --mode link
```

## Install directly from GitHub

If you already have this repository checked out somewhere, you can use its helper script to install a copy from GitHub:

```bash
python3 scripts/skill_repo.py install-github demoon84/my-skills workloop
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
