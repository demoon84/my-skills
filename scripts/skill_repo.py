#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
CATALOG_PATH = ROOT / "catalog.json"
DEFAULT_DEST = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "skills"
NAME_RE = re.compile(r"^[a-z0-9-]+$")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


@dataclass
class Skill:
    name: str
    description: str
    path: Path
    display_name: str | None = None
    short_description: str | None = None
    default_prompt: str | None = None

    def to_catalog_dict(self, *, base: Path = ROOT) -> dict[str, object]:
        try:
            path_value = str(self.path.relative_to(base))
        except ValueError:
            path_value = str(self.path)
        return {
            "name": self.name,
            "description": self.description,
            "path": path_value,
            "display_name": self.display_name,
            "short_description": self.short_description,
            "default_prompt": self.default_prompt,
        }


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def normalize_name(value: str) -> str:
    normalized = value.strip().lower().replace("_", "-").replace(" ", "-")
    normalized = re.sub(r"-{2,}", "-", normalized)
    if not normalized or not NAME_RE.fullmatch(normalized):
        fail("skill names must use lowercase letters, digits, and hyphens only")
    return normalized


def parse_top_level_yaml(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        data[key] = strip_quotes(value.strip())
    return data


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.search(text)
    if not match:
        fail(f"{path} is missing YAML frontmatter")
    return parse_top_level_yaml(match.group(1))


def parse_openai_yaml(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    interface: dict[str, str] = {}
    in_interface = False

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if raw_line.strip() == "interface:":
            in_interface = True
            continue
        if not in_interface:
            continue
        if raw_line and not raw_line.startswith("  "):
            break
        match = re.match(r"^\s{2}([A-Za-z0-9_-]+):\s*(.*)$", raw_line)
        if not match:
            continue
        key, value = match.groups()
        interface[key] = strip_quotes(value.strip())

    return interface


def strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def yaml_scalar(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def prompt_fragment(text: str) -> str:
    normalized = text.strip().rstrip(".")
    if not normalized:
        return "do the requested work"
    return normalized[:1].lower() + normalized[1:]


def load_skill(skill_dir: Path) -> Skill:
    metadata = parse_frontmatter(skill_dir / "SKILL.md")
    interface = parse_openai_yaml(skill_dir / "agents" / "openai.yaml")

    name = metadata.get("name")
    description = metadata.get("description")
    if not name or not description:
        fail(f"{skill_dir / 'SKILL.md'} must define name and description")

    return Skill(
        name=name,
        description=description,
        path=skill_dir,
        display_name=interface.get("display_name"),
        short_description=interface.get("short_description"),
        default_prompt=interface.get("default_prompt"),
    )


def load_skills() -> list[Skill]:
    if not SKILLS_DIR.exists():
        return []

    skills: list[Skill] = []
    for skill_dir in sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir()):
        if not (skill_dir / "SKILL.md").exists():
            continue
        skills.append(load_skill(skill_dir))
    return skills


def load_skills_from_root(root: Path) -> list[Skill]:
    skills_dir = root / "skills"
    if not skills_dir.exists():
        fail(f"{root} does not contain a skills directory")

    skills: list[Skill] = []
    for skill_dir in sorted(path for path in skills_dir.iterdir() if path.is_dir()):
        if not (skill_dir / "SKILL.md").exists():
            continue
        skills.append(load_skill(skill_dir))
    return skills


def installed_skill_names(dest_root: Path) -> set[str]:
    if not dest_root.exists():
        return set()
    return {
        path.name
        for path in dest_root.glob("*")
        if path.is_dir() or path.is_symlink()
    }


def build_catalog(skills: list[Skill]) -> dict[str, object]:
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "skills_dir": "skills",
        "skills": [skill.to_catalog_dict() for skill in skills],
    }


def write_catalog() -> list[Skill]:
    skills = load_skills()
    CATALOG_PATH.write_text(
        json.dumps(build_catalog(skills), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return skills


def titleize(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


def ensure_skill_dir(name: str) -> Path:
    skill_dir = SKILLS_DIR / name
    if skill_dir.exists():
        fail(f"{skill_dir} already exists")
    skill_dir.mkdir(parents=True, exist_ok=False)
    (skill_dir / "agents").mkdir()
    return skill_dir


def cmd_init(args: argparse.Namespace) -> int:
    name = normalize_name(args.name)
    description = args.description.strip()
    if not description:
        fail("description is required")

    display_name = args.display_name or name
    short_description = args.short_description or description
    default_prompt = args.default_prompt or f"Use ${name} to {prompt_fragment(description)}."

    skill_dir = ensure_skill_dir(name)
    title = titleize(name)
    skill_body = (
        f"---\n"
        f"name: {name}\n"
        f"description: {yaml_scalar(description)}\n"
        f"---\n\n"
        f"# {title}\n\n"
        f"Describe the reusable workflow here.\n\n"
        f"## When to use\n\n"
        f"- Trigger this skill when the user asks for {description.rstrip('.').lower()}.\n\n"
        f"## Workflow\n\n"
        f"- Replace this starter text with the actual process.\n"
    )
    openai_yaml = (
        "interface:\n"
        f"  display_name: {yaml_scalar(display_name)}\n"
        f"  short_description: {yaml_scalar(short_description)}\n"
        f"  default_prompt: {yaml_scalar(default_prompt)}\n"
    )

    (skill_dir / "SKILL.md").write_text(skill_body, encoding="utf-8")
    (skill_dir / "agents" / "openai.yaml").write_text(openai_yaml, encoding="utf-8")
    write_catalog()

    print(f"created {skill_dir.relative_to(ROOT)}")
    return 0


def remove_existing_target(target: Path) -> None:
    if target.is_symlink() or target.is_file():
        target.unlink()
        return
    if target.is_dir():
        shutil.rmtree(target)
        return


def install_one(skill: Skill, dest_root: Path, mode: str, overwrite: bool) -> None:
    dest_root.mkdir(parents=True, exist_ok=True)
    target = dest_root / skill.name

    if target.exists() or target.is_symlink():
        if target.is_symlink() and target.resolve() == skill.path.resolve():
            print(f"{skill.name}: already installed")
            return
        if not overwrite:
            fail(f"{target} already exists (pass --overwrite to replace it)")
        remove_existing_target(target)

    if mode == "link":
        target.symlink_to(skill.path.resolve())
    else:
        shutil.copytree(skill.path, target, symlinks=True)

    print(f"{skill.name}: installed to {target}")


def selected_skills(args: argparse.Namespace) -> list[Skill]:
    return select_skills(load_skills(), args.skills, args.all)


def select_skills(skills: list[Skill], names: list[str], all_skills: bool) -> list[Skill]:
    by_name = {skill.name: skill for skill in skills}

    if all_skills:
        return skills

    names = [normalize_name(name) for name in names]
    missing = [name for name in names if name not in by_name]
    if missing:
        fail(f"unknown skill(s): {', '.join(missing)}")
    return [by_name[name] for name in names]


def cmd_install(args: argparse.Namespace) -> int:
    if not args.all and not args.skills:
        fail("provide one or more skills, or use --all")

    dest = Path(args.dest).expanduser()
    for skill in selected_skills(args):
        install_one(skill, dest, args.mode, args.overwrite)
    return 0


def normalize_repo(value: str) -> str:
    candidate = value.strip()
    if candidate.startswith("https://github.com/"):
        candidate = candidate.removeprefix("https://github.com/")
    candidate = candidate.removesuffix(".git").strip("/")

    parts = candidate.split("/")
    if len(parts) >= 2:
        candidate = f"{parts[0]}/{parts[1]}"

    if not REPO_RE.fullmatch(candidate):
        fail("repo must look like owner/name or https://github.com/owner/name")
    return candidate


def github_archive_url(repo: str, ref: str) -> str:
    return f"https://codeload.github.com/{repo}/tar.gz/{ref}"


def download_and_extract_repo(repo: str, ref: str) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="skill-repo-"))
    archive_path = temp_dir / "repo.tar.gz"
    urllib.request.urlretrieve(github_archive_url(repo, ref), archive_path)

    with tarfile.open(archive_path, "r:gz") as archive:
        archive.extractall(temp_dir)

    roots = [path for path in temp_dir.iterdir() if path.is_dir()]
    if not roots:
        fail(f"downloaded archive for {repo}@{ref} did not extract correctly")
    return roots[0]


def cmd_install_github(args: argparse.Namespace) -> int:
    if not args.all and not args.skills:
        fail("provide one or more skills, or use --all")

    repo = normalize_repo(args.repo)
    dest = Path(args.dest).expanduser()
    extracted_root = download_and_extract_repo(repo, args.ref)

    try:
        remote_skills = load_skills_from_root(extracted_root)
        for skill in select_skills(remote_skills, args.skills, args.all):
            install_one(skill, dest, "copy", args.overwrite)
    finally:
        shutil.rmtree(extracted_root.parent, ignore_errors=True)

    return 0


def cmd_list_github(args: argparse.Namespace) -> int:
    repo = normalize_repo(args.repo)
    dest = Path(args.dest).expanduser()
    extracted_root = download_and_extract_repo(repo, args.ref)

    try:
        remote_skills = load_skills_from_root(extracted_root)
        installed_names = installed_skill_names(dest)

        if args.json:
            payload = []
            for skill in remote_skills:
                item = skill.to_catalog_dict(base=extracted_root)
                item["installed"] = skill.name in installed_names
                payload.append(item)
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0

        print(f"Skills from {repo}@{args.ref}:")
        for skill in remote_skills:
            suffix = " (installed)" if skill.name in installed_names else ""
            print(f"{skill.name}{suffix}: {skill.description}")
        return 0
    finally:
        shutil.rmtree(extracted_root.parent, ignore_errors=True)


def cmd_list(args: argparse.Namespace) -> int:
    skills = load_skills()
    installed_names = installed_skill_names(DEFAULT_DEST)

    if args.json:
        payload = []
        for skill in skills:
            item = skill.to_catalog_dict()
            item["installed"] = skill.name in installed_names
            payload.append(item)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    for skill in skills:
        suffix = " (installed)" if skill.name in installed_names else ""
        print(f"{skill.name}{suffix}: {skill.description}")
    return 0


def cmd_refresh_catalog(_: argparse.Namespace) -> int:
    skills = write_catalog()
    print(f"catalog refreshed with {len(skills)} skill(s)")
    return 0


def cmd_validate(_: argparse.Namespace) -> int:
    errors: list[str] = []

    if not SKILLS_DIR.exists():
        errors.append("skills directory is missing")
    else:
        skill_dirs = sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir())
        if not skill_dirs:
            errors.append("skills directory is empty")

        for skill_dir in skill_dirs:
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                errors.append(f"{skill_dir.relative_to(ROOT)} is missing SKILL.md")
                continue

            metadata = parse_frontmatter(skill_md)
            expected_name = skill_dir.name
            actual_name = metadata.get("name", "")
            description = metadata.get("description", "")

            if actual_name != expected_name:
                errors.append(
                    f"{skill_md.relative_to(ROOT)} has name '{actual_name}' but folder is '{expected_name}'"
                )
            if not description:
                errors.append(f"{skill_md.relative_to(ROOT)} is missing a description")

            openai_yaml = skill_dir / "agents" / "openai.yaml"
            if openai_yaml.exists():
                interface = parse_openai_yaml(openai_yaml)
                for key in ("display_name", "short_description", "default_prompt"):
                    if not interface.get(key):
                        errors.append(f"{openai_yaml.relative_to(ROOT)} is missing interface.{key}")

    current_skills = load_skills() if SKILLS_DIR.exists() else []
    expected_catalog = build_catalog(current_skills)

    if not CATALOG_PATH.exists():
        errors.append("catalog.json is missing; run refresh-catalog")
    else:
        actual_catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        comparable_actual = {
            "version": actual_catalog.get("version"),
            "skills_dir": actual_catalog.get("skills_dir"),
            "skills": actual_catalog.get("skills"),
        }
        comparable_expected = {
            "version": expected_catalog.get("version"),
            "skills_dir": expected_catalog.get("skills_dir"),
            "skills": expected_catalog.get("skills"),
        }
        if comparable_actual != comparable_expected:
            errors.append("catalog.json is stale; run refresh-catalog")

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"validated {len(current_skills)} skill(s)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage repo-local Codex skills.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List skills in this repository")
    list_parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    list_parser.set_defaults(func=cmd_list)

    init_parser = subparsers.add_parser("init", help="Create a new skill skeleton")
    init_parser.add_argument("name", help="Skill folder name")
    init_parser.add_argument("--description", required=True, help="Trigger description for the skill")
    init_parser.add_argument("--display-name", help="UI display name")
    init_parser.add_argument("--short-description", help="UI short description")
    init_parser.add_argument("--default-prompt", help="UI default prompt")
    init_parser.set_defaults(func=cmd_init)

    install_parser = subparsers.add_parser("install", help="Install one or more skills locally")
    install_parser.add_argument("skills", nargs="*", help="Skill names to install")
    install_parser.add_argument("--all", action="store_true", help="Install every skill in this repo")
    install_parser.add_argument(
        "--mode",
        choices=("link", "copy"),
        default="link",
        help="Install as a symlink or copied directory",
    )
    install_parser.add_argument(
        "--dest",
        default=str(DEFAULT_DEST),
        help="Destination skills directory (default: ~/.codex/skills)",
    )
    install_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing destination if needed",
    )
    install_parser.set_defaults(func=cmd_install)

    install_github_parser = subparsers.add_parser(
        "install-github",
        help="Install skills from a GitHub repository into ~/.codex/skills",
    )
    install_github_parser.add_argument("repo", help="GitHub repo like owner/name or a GitHub URL")
    install_github_parser.add_argument("skills", nargs="*", help="Skill names to install")
    install_github_parser.add_argument("--all", action="store_true", help="Install every skill in the remote repo")
    install_github_parser.add_argument(
        "--ref",
        default="main",
        help="Git ref to download from GitHub (default: main)",
    )
    install_github_parser.add_argument(
        "--dest",
        default=str(DEFAULT_DEST),
        help="Destination skills directory (default: ~/.codex/skills)",
    )
    install_github_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing destination if needed",
    )
    install_github_parser.set_defaults(func=cmd_install_github)

    list_github_parser = subparsers.add_parser(
        "list-github",
        help="List skills available in a GitHub repository",
    )
    list_github_parser.add_argument("repo", help="GitHub repo like owner/name or a GitHub URL")
    list_github_parser.add_argument(
        "--ref",
        default="main",
        help="Git ref to download from GitHub (default: main)",
    )
    list_github_parser.add_argument(
        "--dest",
        default=str(DEFAULT_DEST),
        help="Installed skills directory used to annotate installed items",
    )
    list_github_parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    list_github_parser.set_defaults(func=cmd_list_github)

    refresh_parser = subparsers.add_parser(
        "refresh-catalog",
        help="Regenerate catalog.json from the skills directory",
    )
    refresh_parser.set_defaults(func=cmd_refresh_catalog)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate skill metadata, agent metadata, and catalog.json",
    )
    validate_parser.set_defaults(func=cmd_validate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
