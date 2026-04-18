#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import os
import shlex
import subprocess
import sys
from pathlib import Path


DEFAULT_REPO_URL = "https://github.com/demoon84/webp-maker.git"
DEFAULT_REF = "master"
DEFAULT_REPO_DIR = (
    Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "codex" / "webp-maker"
)


def log(message: str) -> None:
    print(message, file=sys.stderr)


def fail(message: str) -> None:
    log(f"error: {message}")
    raise SystemExit(1)


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    log(f"$ {shlex.join(command)}")
    result = subprocess.run(command, cwd=cwd, text=True)
    if check and result.returncode != 0:
        raise SystemExit(result.returncode)
    return result


def stamp_value(repo_dir: Path) -> str:
    package_lock = repo_dir / "package-lock.json"
    if not package_lock.exists():
        return "no-lockfile"
    return hashlib.sha256(package_lock.read_bytes()).hexdigest()


def ensure_repo(repo_dir: Path, repo_url: str, ref: str, update: bool) -> None:
    if not repo_dir.exists():
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--depth", "1", "--branch", ref, repo_url, str(repo_dir)])
        return

    if not (repo_dir / ".git").exists():
        if any(repo_dir.iterdir()):
            fail(f"{repo_dir} exists but is not a git repository")
        run(["git", "clone", "--depth", "1", "--branch", ref, repo_url, str(repo_dir)])
        return

    if not update:
        return

    run(["git", "fetch", "origin"], cwd=repo_dir)
    run(["git", "checkout", ref], cwd=repo_dir)
    pull_result = run(["git", "pull", "--ff-only", "origin", ref], cwd=repo_dir, check=False)
    if pull_result.returncode != 0:
        fail(f"failed to update {repo_dir} to {ref}")


def ensure_dependencies(repo_dir: Path, force_install: bool) -> None:
    node_modules = repo_dir / "node_modules"
    stamp_path = node_modules / ".codex-webp-maker-stamp"
    desired_stamp = stamp_value(repo_dir)

    if not force_install and node_modules.exists() and stamp_path.exists():
        if stamp_path.read_text(encoding="utf-8").strip() == desired_stamp:
            return

    package_lock = repo_dir / "package-lock.json"
    install_command = ["npm", "ci"] if package_lock.exists() else ["npm", "install"]
    run(install_command, cwd=repo_dir)
    node_modules.mkdir(exist_ok=True)
    stamp_path.write_text(desired_stamp + "\n", encoding="utf-8")


def ensure_tooling(args: argparse.Namespace) -> Path:
    repo_dir = Path(args.repo_dir).expanduser().resolve()
    ensure_repo(repo_dir=repo_dir, repo_url=args.repo_url, ref=args.ref, update=args.update)
    ensure_dependencies(repo_dir=repo_dir, force_install=args.update)
    return repo_dir


def cmd_bootstrap(args: argparse.Namespace) -> int:
    repo_dir = ensure_tooling(args)
    print(repo_dir)
    return 0


def cmd_run(args: argparse.Namespace, cli_args: list[str]) -> int:
    repo_dir = ensure_tooling(args)
    if args.command_name:
        cli_args.insert(0, args.command_name)
    run(["node", str(repo_dir / "bin" / "webp-maker.js"), *cli_args], cwd=repo_dir)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Wrapper for the demoon84/webp-maker GitHub CLI."
    )
    parser.add_argument(
        "subcommand",
        choices=("bootstrap", "cwebp", "awebp", "pipeline", "help"),
        help="Wrapper action or upstream webp-maker command",
    )
    parser.add_argument(
        "--repo-dir",
        default=str(DEFAULT_REPO_DIR),
        help="Local checkout path for demoon84/webp-maker",
    )
    parser.add_argument(
        "--repo-url",
        default=DEFAULT_REPO_URL,
        help="Git clone URL for demoon84/webp-maker",
    )
    parser.add_argument(
        "--ref",
        default=DEFAULT_REF,
        help="Git ref to clone or update",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Fetch the latest git changes and reinstall dependencies before running",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args, cli_args = parser.parse_known_args()

    if args.subcommand == "bootstrap":
        if cli_args:
            fail(f"bootstrap does not accept upstream CLI arguments: {' '.join(cli_args)}")
        return cmd_bootstrap(args)

    args.command_name = args.subcommand
    if args.command_name == "help":
        args.command_name = None
        cli_args = ["--help", *cli_args]

    return cmd_run(args, cli_args)


if __name__ == "__main__":
    raise SystemExit(main())
