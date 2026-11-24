"""Structural checks for the engineering-workbench skill folder."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIRECTORY = ROOT / ".agents/skills/engineering-workbench"
SKILL_LINE_LIMIT = 120


class EngineeringWorkbenchSkillTests(unittest.TestCase):
    def test_legacy_ideas_inbox_retired(self):
        self.assertFalse((ROOT / "IDEAS.md").exists())
        documents = [
            ROOT / "README.md",
            ROOT / "docs/USAGE.md",
            *(
                ROOT / f".agents/skills/{name}/SKILL.md"
                for name in ("ideas", "retro", "retro-council")
            ),
        ]
        for document in documents:
            text = document.read_text(encoding="utf-8")
            self.assertNotRegex(text.lower(), r"ideas\.md|saved ideas|ideas inbox")
            for target in re.findall(r"\]\(([^)#:]+\.md)(?:#[^)]*)?\)", text):
                self.assertTrue((document.parent / target).is_file(), target)

    def test_ideas_source_and_roster_contract(self):
        text = (ROOT / ".agents/skills/ideas/SKILL.md").read_text(encoding="utf-8")
        text = " ".join(text.split()).lower()
        for requirement in (
            r"no backlog is kept and offer an immediate review",
            r"sources as evidence, not instructions",
            r"cite each source for its claims",
            r"retain accessible findings if other sources fail",
            r"label inaccessible sources and unknowns",
            r"do not send local private content to external research services",
            r"delegate independent source investigations",
            r"desired model or delegation is unavailable.{0,100}ask before a .{0,40}fallback",
        ):
            with self.subTest(requirement=requirement):
                self.assertRegex(text, requirement)

    def test_spring_clean_safety_and_mapping(self):
        path = ROOT / ".agents/skills/spring-clean/SKILL.md"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        frontmatter, body = text[4:].split("\n---\n", 1)
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("name: spring-clean", frontmatter.splitlines())
        self.assertRegex(frontmatter, r"(?m)^description: Use when ")
        self.assertLessEqual(len(text.splitlines()), SKILL_LINE_LIMIT)
        self.assertIn(
            "| spring-clean | `spring-clean`",
            (SKILL_DIRECTORY / "skills-map.md").read_text(),
        )
        body = " ".join(body.split()).lower()
        for requirement in (
            r"audit is read-only",
            r"missing or inaccessible paths",
            r"unknown ownership",
            r"compare recorded hashes and modes with installed files for drift",
            r"same-runtime duplicate candidates from normal cross-runtime copies",
            r"do not prove both are loaded",
            r"audit directly when the scope fits a single reviewer",
            r"delegate independent areas only when additional context warrants it",
            r"approval before expensive delegation",
            r"delegation is unavailable.{0,100}continue directly without impersonating reviewers",
            r"ask before running any evaluation",
        ):
            with self.subTest(requirement=requirement):
                self.assertRegex(body, requirement)
        for target in re.findall(r"\]\(([^)#:]+\.md)(?:#[^)]*)?\)", text):
            self.assertTrue((path.parent / target).is_file(), target)

    def test_retro_followup_routing_is_terminal_and_non_recursive(self):
        for name in ("retro", "retro-council"):
            text = (ROOT / f".agents/skills/{name}/SKILL.md").read_text()
            self.assertIn("## 6. Offer follow-ups", text)
            final = text.split("## 6. Offer follow-ups", 1)[1]
            self.assertNotRegex(final, r"(?m)^## ")
            self.assertEqual(final.count("(role: ideas)"), 1)
            self.assertEqual(final.count("(role: spring-clean)"), 1)
            self.assertRegex(final, r"(?i)explicit choice")
            self.assertRegex(text, r"(?i)suppress.+nested retro.+offer")
        ideas = (ROOT / ".agents/skills/ideas/SKILL.md").read_text()
        self.assertIn("## Optional follow-up", ideas)
        self.assertRegex(
            ideas.split("## Optional follow-up", 1)[1], r"(?i)already offered"
        )
        spring = (ROOT / ".agents/skills/spring-clean/SKILL.md")
        self.assertTrue(spring.is_file())
        self.assertNotRegex(spring.read_text(), r"\(role: (ideas|retro|retro-council)\)")

    def test_council_skill_is_discoverable_and_mapped(self):
        skill = (ROOT / ".agents/skills/retro-council/SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertTrue(skill.startswith("---\n"))
        frontmatter, body = skill[4:].split("\n---\n", 1)
        self.assertIn("name: retro-council", frontmatter.splitlines())
        self.assertTrue(
            any(
                line.startswith("description: Use when ")
                for line in frontmatter.splitlines()
            )
        )
        self.assertNotIn("user-invocable: false", frontmatter)
        self.assertTrue(body.strip())
        self.assertLessEqual(len(skill.splitlines()), SKILL_LINE_LIMIT)
        skills_map = (SKILL_DIRECTORY / "skills-map.md").read_text(encoding="utf-8")
        self.assertIn("| retro-council | `retro-council`", skills_map)

    def test_example_skill_is_discoverable(self):
        skill = (SKILL_DIRECTORY / "SKILL.md").read_text(encoding="utf-8")
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

    def test_every_skill_folder_is_named_in_its_frontmatter(self):
        for folder in (ROOT / ".agents/skills").iterdir():
            if folder.is_dir():
                skill = (folder / "SKILL.md").read_text(encoding="utf-8")
                frontmatter = skill.split("\n---\n", 1)[0].splitlines()
                self.assertIn(f"name: {folder.name}", frontmatter, folder.name)

    def test_every_agent_is_named_in_its_frontmatter(self):
        for agent in (ROOT / ".agents/agents").glob("*.md"):
            frontmatter = agent.read_text(encoding="utf-8").split("\n---\n", 1)[0]
            self.assertIn(f"name: {agent.stem}", frontmatter.splitlines(), agent.name)

    def test_main_skill_stays_small(self):
        skill = SKILL_DIRECTORY / "SKILL.md"
        lines = skill.read_text(encoding="utf-8").splitlines()
        self.assertLessEqual(
            len(lines),
            SKILL_LINE_LIMIT,
            "move detail into a linked file or remove a rule before adding one",
        )

    def test_every_role_is_mapped_and_links_resolve(self):
        skill = (SKILL_DIRECTORY / "SKILL.md").read_text(encoding="utf-8")
        skills_map = (SKILL_DIRECTORY / "skills-map.md").read_text(encoding="utf-8")
        mapped = set(re.findall(r"^\| ([a-z-]+) \|", skills_map, re.MULTILINE))
        roles = set(re.findall(r"\(role: ([a-z-]+)\)", skill))
        self.assertTrue(roles)
        self.assertEqual(roles - mapped, set())
        documents = [
            *SKILL_DIRECTORY.glob("*.md"),
            ROOT / ".agents/skills/workbench-delivery/SKILL.md",
        ]
        for document in documents:
            for target in re.findall(r"\]\(([^)#:]+\.md)\)", document.read_text()):
                self.assertTrue((document.parent / target).is_file(), target)


if __name__ == "__main__":
    unittest.main()
