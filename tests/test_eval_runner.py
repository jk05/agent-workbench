"""Deterministic evaluation isolation and recording checks; no SDK or model calls."""

import importlib.util
import json
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "evals/run.py"
SPEC = importlib.util.spec_from_file_location("eval_runner", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"cannot load eval runner: {SCRIPT}")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class EvalRunnerTests(unittest.TestCase):
    def test_consent_branches_have_identical_blind_initial_inputs(self):
        cases = json.loads((SCRIPT.parent / "cases.json").read_text())
        by_id = {case["id"]: case for case in cases["cases"]}
        for accepted, declined in (
            ("rea-consent-accepted", "rea-consent-declined"),
            ("follow-up-approved", "follow-up-declined"),
        ):
            initial = runner.candidate_prompt(by_id[accepted])
            self.assertEqual(initial, runner.candidate_prompt(by_id[declined]))
            self.assertNotIn("follow-up grants", initial)
            self.assertNotIn("follow-up refuses", initial)
            self.assertNotIn("DEMO-61", initial)
            self.assertNotEqual(
                by_id[accepted]["interaction"]["follow_up"],
                by_id[declined]["interaction"]["follow_up"],
            )

    def test_prompt_does_not_leak_rubric_or_later_decision(self):
        prompt = runner.candidate_prompt(
            {
                "prompt": "Plan only",
                "context": {"evidence": "supplied fact"},
                "must_do": ["PRIVATE RUBRIC"],
                "interaction": {"follow_up": "PRIVATE DECISION"},
            }
        )
        self.assertIn("supplied fact", prompt)
        self.assertNotIn("PRIVATE", prompt)

    def test_only_custom_stubs_and_no_discovery(self):
        options = runner.isolated_options(Path("/tmp/synthetic"), ["invoke_skill"])
        self.assertEqual(options["available_tools"], ["custom:invoke_skill"])
        self.assertEqual(options["excluded_tools"], ["builtin:*", "mcp:*"])
        for setting in (
            "enable_config_discovery",
            "enable_skills",
            "enable_file_hooks",
            "enable_host_git_operations",
            "enable_session_store",
            "enable_on_demand_instruction_discovery",
        ):
            self.assertFalse(options[setting])
        self.assertTrue(options["skip_custom_instructions"])
        self.assertEqual(options["mcp_servers"], {})
        self.assertEqual(options["plugin_directories"], [])

    def test_recorder_retains_turn_order_and_simulated_results(self):
        recorder = runner.Recorder()
        self.assertEqual(recorder.trace, [])
        recorder.turn = 2
        recorder.call(
            "create_ticket", {"title": "help", "body": "text", "parent": "DEMO-51"}
        )
        recorder.call("comment_ticket", {"issue": "DEMO-51", "body": "DEMO-61"})
        self.assertEqual(
            [call["tool"] for call in recorder.trace],
            ["create_ticket", "comment_ticket"],
        )
        self.assertTrue(all(call["turn"] == 2 for call in recorder.trace))
        self.assertTrue(all("SIMULATED" in call["result"] for call in recorder.trace))
        with self.assertRaises(ValueError):
            recorder.call("bash", {"command": "anything"})

    def test_tools_are_limited_to_each_harness(self):
        self.assertEqual(runner.tool_specs({}), {})
        for harness, expected in (
            ("recording-only-skill-stub", {"invoke_skill"}),
            ("recording-only-tracker-stub", {"create_ticket", "comment_ticket"}),
        ):
            self.assertEqual(
                set(runner.tool_specs({"interaction": {"harness": harness}})), expected
            )
        with self.assertRaises(ValueError):
            runner.tool_specs({"interaction": {"harness": "live-tracker"}})


if __name__ == "__main__":
    unittest.main()
