from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "skill_repo.py"
SPEC = importlib.util.spec_from_file_location("skill_repo", MODULE_PATH)
skill_repo = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = skill_repo
SPEC.loader.exec_module(skill_repo)


class SkillRepoTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._patch_stack = contextlib.ExitStack()

    def tearDown(self) -> None:
        self._patch_stack.close()

    def patch_repo_globals(self, root: Path) -> None:
        originals = {
            "ROOT": skill_repo.ROOT,
            "SKILLS_DIR": skill_repo.SKILLS_DIR,
            "CATALOG_PATH": skill_repo.CATALOG_PATH,
            "DEFAULT_DEST": skill_repo.DEFAULT_DEST,
        }

        root = root.resolve()
        skill_repo.ROOT = root
        skill_repo.SKILLS_DIR = root / "skills"
        skill_repo.CATALOG_PATH = root / "catalog.json"
        skill_repo.DEFAULT_DEST = root / ".codex" / "skills"

        def restore() -> None:
            for key, value in originals.items():
                setattr(skill_repo, key, value)

        self._patch_stack.callback(restore)

    def make_skill(
        self,
        root: Path,
        name: str,
        description: str = "Do useful work.",
    ) -> Path:
        skill_dir = root / "skills" / name
        (skill_dir / "agents").mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            (
                "---\n"
                f"name: {name}\n"
                f"description: {json.dumps(description)}\n"
                "---\n\n"
                f"# {name}\n"
            ),
            encoding="utf-8",
        )
        (skill_dir / "agents" / "openai.yaml").write_text(
            (
                "interface:\n"
                f'  display_name: "{name}"\n'
                f'  short_description: "{description}"\n'
                f'  default_prompt: "Use ${name}."\n'
            ),
            encoding="utf-8",
        )
        return skill_dir

    def test_validate_passes_for_well_formed_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.patch_repo_globals(root)
            self.make_skill(root, "alpha-skill")
            skill_repo.write_catalog()

            result = skill_repo.cmd_validate(SimpleNamespace())

            self.assertEqual(result, 0)

    def test_validate_detects_stale_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.patch_repo_globals(root)
            self.make_skill(root, "alpha-skill")
            skill_repo.write_catalog()
            skill_repo.CATALOG_PATH.write_text(
                json.dumps({"version": 1, "skills_dir": "skills", "skills": []}),
                encoding="utf-8",
            )

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                result = skill_repo.cmd_validate(SimpleNamespace())

            self.assertEqual(result, 1)
            self.assertIn("catalog.json is stale", stderr.getvalue())

    def test_uninstall_removes_installed_skill_directory(self) -> None:
        with tempfile.TemporaryDirectory() as dest_dir:
            installed = Path(dest_dir) / "alpha-skill"
            installed.mkdir()
            (installed / "SKILL.md").write_text("stub", encoding="utf-8")
            args = SimpleNamespace(
                skills=["alpha-skill"],
                dest=dest_dir,
                missing_ok=False,
            )

            result = skill_repo.cmd_uninstall(args)

            self.assertEqual(result, 0)
            self.assertFalse(installed.exists())

    def test_uninstall_missing_skill_can_be_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as dest_dir:
            args = SimpleNamespace(
                skills=["alpha-skill"],
                dest=dest_dir,
                missing_ok=True,
            )

            result = skill_repo.cmd_uninstall(args)

            self.assertEqual(result, 0)

    def test_install_github_installs_selected_skill(self) -> None:
        temp_root = Path(tempfile.mkdtemp(prefix="skill-remote-"))
        self._patch_stack.callback(lambda: shutil.rmtree(temp_root, ignore_errors=True))
        remote_root = temp_root / "my-skills-main"
        self.make_skill(remote_root, "alpha-skill", "Alpha.")
        self.make_skill(remote_root, "beta-skill", "Beta.")

        original_download = skill_repo.download_and_extract_repo
        skill_repo.download_and_extract_repo = lambda repo, ref: remote_root
        self._patch_stack.callback(
            lambda: setattr(skill_repo, "download_and_extract_repo", original_download)
        )

        with tempfile.TemporaryDirectory() as dest_dir:
            args = SimpleNamespace(
                repo="owner/repo",
                ref="main",
                dest=dest_dir,
                skills=["beta-skill"],
                all=False,
                overwrite=False,
            )

            result = skill_repo.cmd_install_github(args)

            self.assertEqual(result, 0)
            self.assertTrue((Path(dest_dir) / "beta-skill" / "SKILL.md").exists())
            self.assertFalse((Path(dest_dir) / "alpha-skill").exists())

    def test_list_github_json_marks_installed_skills(self) -> None:
        temp_root = Path(tempfile.mkdtemp(prefix="skill-remote-"))
        self._patch_stack.callback(lambda: shutil.rmtree(temp_root, ignore_errors=True))
        remote_root = temp_root / "my-skills-main"
        self.make_skill(remote_root, "alpha-skill", "Alpha.")
        self.make_skill(remote_root, "beta-skill", "Beta.")

        original_download = skill_repo.download_and_extract_repo
        skill_repo.download_and_extract_repo = lambda repo, ref: remote_root
        self._patch_stack.callback(
            lambda: setattr(skill_repo, "download_and_extract_repo", original_download)
        )

        with tempfile.TemporaryDirectory() as dest_dir:
            (Path(dest_dir) / "beta-skill").mkdir()
            args = SimpleNamespace(
                repo="owner/repo",
                ref="main",
                dest=dest_dir,
                json=True,
            )
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                result = skill_repo.cmd_list_github(args)

            payload = json.loads(stdout.getvalue())
            installed = {item["name"]: item["installed"] for item in payload}

            self.assertEqual(result, 0)
            self.assertFalse(installed["alpha-skill"])
            self.assertTrue(installed["beta-skill"])

    def test_validate_guard_fails_without_local_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.patch_repo_globals(root)

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit):
                    skill_repo.cmd_validate(SimpleNamespace())

            self.assertIn("requires a local checkout", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
