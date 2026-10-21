"""Structural checks for the current example skill and manually recorded evals."""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExampleSkillEvalTests(unittest.TestCase):
    def test_example_skill_is_discoverable(self):
        skill = (ROOT / ".agents/skills/engineering-workbench/SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertTrue(skill.startswith("---\n"))
        frontmatter, body = skill[4:].split("\n---\n", 1)
        self.assertIn("name: engineering-workbench", frontmatter.splitlines())
        self.assertTrue(
            any(
                line.startswith("description: Use when ")
                for line in frontmatter.splitlines()
            )
        )
        self.assertNotIn("disable-model-invocation: true", frontmatter)
        self.assertTrue(body.strip())

    def test_case_rubrics_and_sample_limits(self):
        cases = json.loads((ROOT / "evals/cases.json").read_text())
        self.assertEqual(cases["schema_version"], 1)
        execution = cases["execution"]
        self.assertEqual(
            execution["isolation"], "one fresh agent conversation per case"
        )
        self.assertEqual(execution["max_agent_turns_per_case"], 2)
        self.assertFalse(execution["external_actions_allowed"])
        ids = [case["id"] for case in cases["cases"]]
        self.assertEqual(len(ids), len(set(ids)))
        for case in cases["cases"]:
            self.assertTrue(case["prompt"])
            self.assertTrue(case["must_do"])
            self.assertTrue(case["must_not_do"])
            if case["id"] in execution["sample_case_ids"]:
                self.assertTrue(case["context"])
        self.assertTrue(set(execution["sample_case_ids"]) <= set(ids))

    def test_rea_routing_and_consent_cases_are_required(self):
        cases = json.loads((ROOT / "evals/cases.json").read_text())
        by_id = {case["id"]: case for case in cases["cases"]}
        required = {
            "rea-source-question",
            "rea-artifact-offer",
            "rea-consent-accepted",
            "rea-consent-declined",
        }
        self.assertTrue(required <= set(cases["execution"]["sample_case_ids"]))
        for identifier in required:
            case = by_id[identifier]
            for field in (
                "workspace_policy",
                "workspace_evidence",
                "availability",
                "approvals",
            ):
                self.assertTrue(case["context"][field].strip())
        for identifier in ("rea-consent-accepted", "rea-consent-declined"):
            interaction = by_id[identifier]["interaction"]
            self.assertEqual(interaction["harness"], "recording-only-skill-stub")
            self.assertTrue(interaction["follow_up"].strip())
            self.assertTrue(interaction["required_observation"].strip())
        self.assertNotIn("interaction", by_id["rea-source-question"])
        self.assertNotIn("interaction", by_id["rea-artifact-offer"])

    def test_slicing_scope_and_follow_up_cases_are_required(self):
        cases = json.loads((ROOT / "evals/cases.json").read_text())
        by_id = {case["id"]: case for case in cases["cases"]}
        required = {
            "logical-pr-slices",
            "pr-frontier-progress",
            "smallest-complete-change",
            "follow-up-capture",
            "follow-up-approved",
            "follow-up-declined",
        }
        self.assertTrue(required <= set(cases["execution"]["sample_case_ids"]))
        for identifier in required:
            for field in (
                "workspace_policy",
                "workspace_evidence",
                "availability",
                "approvals",
            ):
                self.assertTrue(by_id[identifier]["context"][field].strip())
        for identifier in ("follow-up-approved", "follow-up-declined"):
            interaction = by_id[identifier]["interaction"]
            self.assertEqual(interaction["harness"], "recording-only-tracker-stub")
            self.assertTrue(interaction["follow_up"].strip())
            self.assertTrue(interaction["required_observation"].strip())

    def test_historical_results_cover_criteria_and_identify_the_tested_version(self):
        cases = json.loads((ROOT / "evals/cases.json").read_text())
        results = json.loads((ROOT / "evals/results.json").read_text())
        self.assertEqual(results["schema_version"], 1)
        self.assertRegex(results["skill_sha256"], re.compile(r"^[0-9a-f]{64}$"))
        self.assertEqual(
            results["skill_path"], ".agents/skills/engineering-workbench/SKILL.md"
        )
        self.assertEqual(results["execution_target"], "Copilot task-tool subagents")
        self.assertTrue(results["assessment"])
        by_id = {case["id"]: case for case in cases["cases"]}
        executed = [run["case_id"] for run in results["runs"]]
        self.assertEqual(len(executed), len(set(executed)))
        self.assertTrue(set(executed) <= set(by_id))
        self.assertEqual(set(executed) | set(results["not_run"]), set(by_id))
        self.assertFalse(set(executed) & set(results["not_run"]))
        for run in results["runs"]:
            self.assertGreater(run["agent_turns"], 0)
            self.assertLessEqual(
                run["agent_turns"], cases["execution"]["max_agent_turns_per_case"]
            )
            self.assertTrue(run["response"])
            expected = {
                (kind, index)
                for kind in ("must_do", "must_not_do")
                for index in range(len(by_id[run["case_id"]][kind]))
            }
            actual = {(item["kind"], item["index"]) for item in run["criteria"]}
            self.assertEqual(actual, expected)
            self.assertEqual(len(actual), len(run["criteria"]))
            for item in run["criteria"]:
                self.assertIn(item["verdict"], ("pass", "fail", "not_observable"))
                self.assertTrue(item["evidence"])
            expected_status = (
                "fail"
                if any(item["verdict"] == "fail" for item in run["criteria"])
                else "inconclusive"
                if any(item["verdict"] == "not_observable" for item in run["criteria"])
                else "pass"
            )
            self.assertEqual(run["status"], expected_status)
        self.assertTrue(results["limitations"])


if __name__ == "__main__":
    unittest.main()
