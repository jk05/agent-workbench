"""Copilot installer and handoff mechanics, using synthetic skills and private fixtures."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import TypedDict
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/workbench.py"
SPEC = importlib.util.spec_from_file_location("workbench", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"cannot load workbench helper: {SCRIPT}")
workbench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workbench)


class FixturePolicy(TypedDict):
    schema_version: int
    skills: dict[str, dict[str, str]]


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
        (self.root / "evals").mkdir()
        self.policy: FixturePolicy = {"schema_version": 1, "skills": {}}
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
        self.policy["skills"][name] = {
            "cases": f"evals/{name}-cases.json",
            "results": f"evals/{name}-results.json",
        }
        (self.root / "evals/policy.json").write_text(json.dumps(self.policy))
        cases = {
            "schema_version": 1,
            "execution": {
                "sample_case_ids": ["fixture"],
                "max_agent_turns_per_case": 2,
            },
            "cases": [
                {
                    "id": "fixture",
                    "must_do": ["Show the synthetic expected behavior."],
                    "must_not_do": [
                        "Claim a real AI run took place in this unit test."
                    ],
                }
            ],
        }
        (self.root / f"evals/{name}-cases.json").write_text(json.dumps(cases))
        self.record_fixture_eval(name)
        return directory

    def result_path(self, name="example-one"):
        return self.root / f"evals/{name}-results.json"

    def record_fixture_eval(self, name="example-one"):
        """Fabricated unit-test data, not real behavioral evidence."""
        result = {
            "schema_version": 1,
            "date": "unit-test fixture",
            "execution_target": "Copilot task-tool subagents",
            "assessment": "Synthetic record testing gate mechanics only; no AI was called.",
            "inputs_sha256": workbench.eval_inputs(name, workbench.source_files(name)),
            "runs": [
                {
                    "case_id": "fixture",
                    "status": "pass",
                    "agent_turns": 1,
                    "response": "Synthetic response fixture, not AI output.",
                    "criteria": [
                        {
                            "kind": kind,
                            "index": 0,
                            "verdict": "pass",
                            "evidence": "Synthetic fixture evidence.",
                        }
                        for kind in ("must_do", "must_not_do")
                    ],
                }
            ],
        }
        self.result_path(name).write_text(json.dumps(result))

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
        self.record_fixture_eval()
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
        self.record_fixture_eval()
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

    def test_missing_policy_and_results_block_before_install_writes(self):
        self.policy["skills"].pop("example-one")
        (self.root / "evals/policy.json").write_text(json.dumps(self.policy))
        with self.assertRaisesRegex(workbench.WorkbenchError, "no eval policy"):
            self.install()
        self.assertFalse(self.destination().exists())
        self.assertFalse(self.state.exists())
        self.policy["skills"]["example-one"] = {
            "cases": "evals/example-one-cases.json",
            "results": "evals/example-one-results.json",
        }
        (self.root / "evals/policy.json").write_text(json.dumps(self.policy))
        self.result_path().unlink()
        with self.assertRaisesRegex(
            workbench.WorkbenchError, "cannot read JSON record"
        ):
            self.install()
        self.assertFalse(self.destination().exists())

    def test_failed_inconclusive_or_missing_required_run_blocks_install(self):
        original = self.result_path().read_text()
        for verdict in ("fail", "inconclusive", None):
            result = json.loads(original)
            if verdict is None:
                result["runs"] = []
            else:
                result["runs"][0]["status"] = verdict
            self.result_path().write_text(json.dumps(result))
            with self.assertRaisesRegex(workbench.WorkbenchError, "required eval"):
                self.install()
            self.assertFalse(self.destination().exists())
            self.assertFalse(self.state.exists())

    def test_stale_skill_resource_mode_cases_wiring_and_policy_block_update(self):
        self.install()
        installed = (self.destination() / "SKILL.md").read_bytes()
        changes = [
            self.sources / "example-one/SKILL.md",
            self.sources / "example-one/references/example.txt",
            self.root / "evals/example-one-cases.json",
            self.root / "runtimes/copilot.json",
        ]
        for path in changes:
            original = path.read_bytes()
            path.write_bytes(original + b"\n")
            with self.assertRaisesRegex(workbench.WorkbenchError, "stale or missing"):
                self.install()
            self.assertEqual((self.destination() / "SKILL.md").read_bytes(), installed)
            path.write_bytes(original)
        script = self.sources / "example-one/scripts/check.sh"
        script.chmod(0o644)
        with self.assertRaisesRegex(workbench.WorkbenchError, "stale or missing"):
            self.install()
        script.chmod(0o755)
        self.policy["skills"]["example-one"]["purpose"] = "policy change"
        (self.root / "evals/policy.json").write_text(json.dumps(self.policy))
        with self.assertRaisesRegex(workbench.WorkbenchError, "stale or missing"):
            self.install()

    def test_new_or_removed_resources_invalidate_evidence(self):
        extra = self.sources / "example-one/extra.md"
        extra.write_text("new resource")
        with self.assertRaisesRegex(workbench.WorkbenchError, "stale or missing"):
            self.install()
        extra.unlink()
        (self.sources / "example-one/references/example.txt").unlink()
        with self.assertRaisesRegex(workbench.WorkbenchError, "stale or missing"):
            self.install()

    def test_claimed_pass_with_bad_criteria_is_rejected(self):
        original = self.result_path().read_text()
        for change in ("failure", "inconclusive", "missing", "duplicate", "evidence"):
            result = json.loads(original)
            criteria = result["runs"][0]["criteria"]
            if change == "failure":
                criteria[0]["verdict"] = "fail"
            elif change == "inconclusive":
                criteria[0]["verdict"] = "not_observable"
            elif change == "missing":
                criteria.pop()
            elif change == "duplicate":
                criteria.append(criteria[0].copy())
            else:
                criteria[0]["evidence"] = ""
            self.result_path().write_text(json.dumps(result))
            with self.assertRaises(workbench.WorkbenchError):
                self.install()
            self.assertFalse(self.destination().exists())

    def test_verification_does_not_call_ai_or_write_files(self):
        with patch.object(
            subprocess, "run", side_effect=AssertionError("no AI/tool calls")
        ):
            workbench.verify_evals("example-one")
        self.assertFalse(self.state.exists())
        self.assertFalse(self.destination().exists())

    def test_human_docs_and_other_skill_policy_do_not_invalidate_evidence(self):
        (self.root / "README.md").write_text("Human-facing prose change")
        self.policy["skills"]["example-two"]["purpose"] = "other skill change"
        (self.root / "evals/policy.json").write_text(json.dumps(self.policy))
        workbench.verify_evals("example-one")
        self.assertFalse(self.state.exists())

    def test_missing_assessment_wrong_runtime_and_duplicate_runs_are_rejected(self):
        original = self.result_path().read_text()
        for change in ("assessment", "runtime", "duplicate", "budget", "fingerprint"):
            result = json.loads(original)
            if change == "assessment":
                result["assessment"] = ""
            elif change == "runtime":
                result["execution_target"] = "another runtime"
            elif change == "duplicate":
                result["runs"].append(result["runs"][0].copy())
            elif change == "budget":
                result["runs"][0]["agent_turns"] = 3
            else:
                result.pop("inputs_sha256")
            self.result_path().write_text(json.dumps(result))
            with self.assertRaises(workbench.WorkbenchError):
                self.install()
            self.assertFalse(self.destination().exists())
            self.assertFalse(self.state.exists())

    def test_removal_and_status_still_work_with_failing_eval(self):
        self.install()
        result = json.loads(self.result_path().read_text())
        result["runs"][0]["status"] = "fail"
        self.result_path().write_text(json.dumps(result))
        self.assertEqual(workbench.status(self.home, self.state, "example-one"), 0)
        self.remove()
        self.assertFalse(self.destination().exists())


class HandoffAndCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.home = self.root / "home"
        self.state = self.root / "state"

    def run_cli(self, *arguments):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
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

    def test_cli_blocks_current_failed_example_without_writes(self):
        result = self.run_cli("install", "engineering-workbench", "--activate")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ticket-planning: fail", result.stderr)
        self.assertFalse(self.home.exists())
        self.assertFalse(self.state.exists())
        verify = self.run_cli("verify", "engineering-workbench")
        self.assertNotEqual(verify.returncode, 0)
        self.assertIn("ticket-planning: fail", verify.stderr)
        fingerprints = self.run_cli("eval-inputs", "engineering-workbench")
        self.assertEqual(fingerprints.returncode, 0, fingerprints.stderr)
        self.assertEqual(
            set(json.loads(fingerprints.stdout)),
            {"skill_tree", "cases", "policy", "copilot_wiring"},
        )

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
