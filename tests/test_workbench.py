"""Copilot installer and handoff mechanics, using synthetic skills and private fixtures."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/workbench.py"
SPEC = importlib.util.spec_from_file_location("workbench", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"cannot load workbench helper: {SCRIPT}")
workbench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workbench)


class CopilotInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.home = self.root / "home"
        self.state = self.root / "state"
        self.sources = self.root / "sources"
        self.home.mkdir()
        self.sources.mkdir()
        self.addCleanup(patch.stopall)
        patch.object(workbench, "SKILLS_ROOT", self.sources).start()
        patch.object(workbench, "REPOSITORY_ROOT", self.root).start()
        (self.root / "runtimes").mkdir()
        (self.root / "runtimes/copilot.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "runtime": "copilot",
                    "personal_skills_directory": ".agents/skills",
                }
            )
        )
        self.make_skill("example-one")
        self.make_skill("example-two")

    def make_skill(self, name):
        directory = self.sources / name
        directory.mkdir()
        (directory / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: A synthetic test skill.\n---\n\n# Example\n",
            encoding="utf-8",
        )
        resource = directory / "references/example.txt"
        resource.parent.mkdir()
        resource.write_text("supporting resource", encoding="utf-8")
        script = directory / "scripts/check.sh"
        script.parent.mkdir()
        script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        script.chmod(0o755)
        return directory

    def destination(self, name="example-one"):
        return self.home / ".agents/skills" / name

    def manifest(self, name="example-one"):
        return self.state / "agent-workbench/installations/copilot" / f"{name}.json"

    def install(self, name="example-one"):
        workbench.install(self.home, self.state, name, True)

    def remove(self, name="example-one"):
        workbench.remove(self.home, self.state, name, True)

    def test_status_is_read_only_and_install_requires_approval(self):
        self.assertEqual(workbench.status(self.home, self.state, None), 0)
        with self.assertRaisesRegex(workbench.WorkbenchError, "--activate"):
            workbench.install(self.home, self.state, "example-one", False)
        self.assertFalse(self.state.exists())
        self.assertFalse((self.home / ".agents").exists())

    def test_two_skills_full_resources_modes_and_repeat_install(self):
        self.install()
        self.install("example-two")
        self.install()
        for name in ("example-one", "example-two"):
            for source in (self.sources / name).rglob("*"):
                if source.is_file():
                    target = self.destination(name) / source.relative_to(
                        self.sources / name
                    )
                    self.assertEqual(target.read_bytes(), source.read_bytes())
                    self.assertEqual(
                        target.stat().st_mode & 0o777, source.stat().st_mode & 0o777
                    )
        self.remove()
        self.assertFalse(self.destination().exists())
        self.assertTrue(self.destination("example-two").is_dir())
        self.assertTrue(self.manifest("example-two").is_file())

    def test_update_adds_resources_removes_obsolete_owned_files_preserves_user_files(
        self,
    ):
        self.install()
        notes = self.destination() / "references/user.txt"
        notes.write_text("my notes", encoding="utf-8")
        source = self.sources / "example-one"
        (source / "references/example.txt").unlink()
        (source / "references/new.txt").write_text("new", encoding="utf-8")
        (source / "SKILL.md").write_text(
            (source / "SKILL.md").read_text(encoding="utf-8") + "Updated\n",
            encoding="utf-8",
        )
        with patch("builtins.print") as printed:
            self.assertEqual(workbench.status(self.home, self.state, "example-one"), 0)
        self.assertIn("update available", printed.call_args.args[0])
        self.install()
        self.assertFalse((self.destination() / "references/example.txt").exists())
        self.assertEqual((self.destination() / "references/new.txt").read_text(), "new")
        self.assertEqual(notes.read_text(), "my notes")
        self.remove()
        self.assertEqual(notes.read_text(), "my notes")
        self.assertFalse(self.manifest().exists())

    def test_missing_source_does_not_prevent_removal(self):
        self.install()
        (self.sources / "example-one").rename(self.sources / "renamed-away")
        self.assertEqual(workbench.status(self.home, self.state, "example-one"), 0)
        self.remove()
        self.assertFalse(self.destination().exists())

    def test_unmanaged_directory_and_new_resource_collisions_are_preserved(self):
        self.destination().mkdir(parents=True)
        with self.assertRaisesRegex(workbench.WorkbenchError, "unmanaged"):
            self.install()
        self.destination().rmdir()
        self.install()
        target = self.destination() / "user.txt"
        target.write_text("mine")
        (self.sources / "example-one/user.txt").write_text("source")
        with self.assertRaisesRegex(workbench.WorkbenchError, "unmanaged"):
            self.install()
        self.assertEqual(target.read_text(), "mine")

    def test_drift_in_resource_or_mode_blocks_install_status_and_remove(self):
        self.install()
        target = self.destination() / "references/example.txt"
        original = target.read_bytes()
        target.write_text("local edit")
        for action in (
            self.install,
            self.remove,
            lambda: workbench.status(self.home, self.state, "example-one"),
        ):
            with self.assertRaisesRegex(workbench.WorkbenchError, "locally edited"):
                action()
        self.assertEqual(target.read_text(), "local edit")
        target.write_bytes(original)
        (self.destination() / "scripts/check.sh").chmod(0o644)
        with self.assertRaisesRegex(workbench.WorkbenchError, "locally edited"):
            self.remove()

    def test_symlinks_in_sources_and_managed_paths_are_refused(self):
        linked = self.sources / "example-one/references/link"
        linked.symlink_to(self.sources / "example-two/SKILL.md")
        with self.assertRaisesRegex(workbench.WorkbenchError, "symbolic link"):
            self.install()
        linked.unlink()
        self.install()
        target = self.destination() / "references/example.txt"
        target.unlink()
        target.symlink_to(self.sources / "example-two/SKILL.md")
        for action in (self.install, self.remove):
            with self.assertRaisesRegex(workbench.WorkbenchError, "symbolic link"):
                action()

    def test_invalid_names_and_frontmatter_fail_before_writes(self):
        for name in ("../outside", "/absolute", "UPPERCASE"):
            with self.assertRaises(workbench.WorkbenchError):
                self.install(name)
        (self.sources / "example-one/SKILL.md").write_text("# missing frontmatter")
        with self.assertRaisesRegex(workbench.WorkbenchError, "frontmatter"):
            self.install()
        self.assertFalse(self.destination().exists())

    def test_manifest_is_per_skill_and_records_runtime_hashes_and_modes(self):
        self.install()
        manifest = json.loads(self.manifest().read_text())
        self.assertEqual(manifest["version"], 2)
        self.assertEqual(manifest["runtime"], "copilot")
        self.assertEqual(manifest["destination"], str(self.destination()))
        self.assertEqual(
            set(manifest["files"]),
            {"SKILL.md", "references/example.txt", "scripts/check.sh"},
        )
        self.assertEqual(manifest["files"]["scripts/check.sh"]["mode"], 0o755)

    def test_invalid_manifest_traversal_is_rejected(self):
        self.install()
        manifest = json.loads(self.manifest().read_text())
        manifest["files"]["../outside"] = manifest["files"]["SKILL.md"]
        self.manifest().write_text(json.dumps(manifest))
        with self.assertRaisesRegex(workbench.WorkbenchError, "invalid file record"):
            self.remove()
        self.assertTrue((self.destination() / "SKILL.md").exists())

    def test_update_write_failure_restores_files_and_manifest(self):
        self.install()
        original_file = (self.destination() / "SKILL.md").read_bytes()
        original_manifest = self.manifest().read_bytes()
        source = self.sources / "example-one/SKILL.md"
        source.write_text(source.read_text() + "updated")
        (self.sources / "example-one/new.txt").write_text("new")
        real_write = workbench.write_atomic

        def fail_manifest(path, contents):
            if path == self.manifest():
                raise OSError("simulated manifest write failure")
            real_write(path, contents)

        with (
            patch.object(workbench, "write_atomic", side_effect=fail_manifest),
            self.assertRaisesRegex(workbench.WorkbenchError, "managed files restored"),
        ):
            self.install()
        self.assertEqual((self.destination() / "SKILL.md").read_bytes(), original_file)
        self.assertEqual(self.manifest().read_bytes(), original_manifest)
        self.assertFalse((self.destination() / "new.txt").exists())

    def test_first_install_write_failure_cleans_managed_files(self):
        with (
            patch.object(
                workbench, "write_atomic", side_effect=OSError("manifest unavailable")
            ),
            self.assertRaisesRegex(workbench.WorkbenchError, "managed files restored"),
        ):
            self.install()
        self.assertFalse(self.destination().exists())
        self.assertFalse(self.manifest().exists())

    def test_removal_failure_restores_owned_files_and_keeps_manifest(self):
        self.install()
        original_manifest = self.manifest().read_bytes()
        real_unlink = Path.unlink

        def fail_manifest_unlink(path, *args, **kwargs):
            if path == self.manifest():
                raise OSError("simulated removal failure")
            return real_unlink(path, *args, **kwargs)

        with (
            patch.object(Path, "unlink", fail_manifest_unlink),
            self.assertRaisesRegex(workbench.WorkbenchError, "managed files restored"),
        ):
            self.remove()
        self.assertEqual(self.manifest().read_bytes(), original_manifest)
        for source in (self.sources / "example-one").rglob("*"):
            if source.is_file():
                relative = source.relative_to(self.sources / "example-one")
                self.assertEqual(
                    (self.destination() / relative).read_bytes(), source.read_bytes()
                )

    def test_remove_requires_approval(self):
        self.install()
        with self.assertRaisesRegex(workbench.WorkbenchError, "--confirm-removal"):
            workbench.remove(self.home, self.state, "example-one", False)
        self.assertTrue(self.manifest().exists())

    def test_legacy_manifest_is_explicitly_reported_without_modification(self):
        legacy = self.state / "agent-workbench/install.json"
        legacy.parent.mkdir(parents=True)
        legacy.write_text('{"version": 1}')
        with self.assertRaisesRegex(workbench.WorkbenchError, "legacy"):
            self.install()
        self.assertEqual(legacy.read_text(), '{"version": 1}')


class HandoffAndCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.home = self.root / "home"
        self.state = self.root / "state"

    def run_cli(self, *arguments, script=SCRIPT):
        return subprocess.run(
            [
                sys.executable,
                str(script),
                "--home",
                str(self.home),
                "--state-root",
                str(self.state),
                *arguments,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_help_explicitly_limits_installation_to_copilot(self):
        help_text = self.run_cli("--help")
        self.assertEqual(help_text.returncode, 0)
        self.assertIn("Copilot-only", help_text.stdout)
        self.assertIn("not supported yet", help_text.stdout)
        invalid = self.run_cli("--runtime", "claude", "status")
        self.assertNotEqual(invalid.returncode, 0)
        unnamed = self.run_cli("install", "--activate")
        self.assertNotEqual(unnamed.returncode, 0)

    def test_cli_status_has_no_writes(self):
        result = self.run_cli("status", "engineering-workbench")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Copilot / engineering-workbench: not installed", result.stdout)
        self.assertFalse(self.home.exists())
        self.assertFalse(self.state.exists())

    def test_handoff_template_is_private_and_not_overwritten(self):
        result = self.run_cli(
            "handoff", "create", "example-task", "--workspace", str(SCRIPT.parents[1])
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        path = Path(result.stdout.strip())
        self.assertEqual(path.parent, self.state / "agent-workbench/tasks")
        self.assertIn("Approved scope", path.read_text())
        self.assertIn("Relevant processes", path.read_text())
        duplicate = self.run_cli("handoff", "create", "example-task")
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertEqual(
            self.run_cli("handoff", "show", "example-task").stdout, path.read_text()
        )
        self.assertNotEqual(
            self.run_cli("handoff", "create", "../escape").returncode, 0
        )

    def test_xdg_state_base_is_used(self):
        with patch.dict(os.environ, {"XDG_STATE_HOME": str(self.state)}):
            _, state = workbench.paths(self.home, None)
        self.assertEqual(state, self.state / "agent-workbench")


if __name__ == "__main__":
    unittest.main()
