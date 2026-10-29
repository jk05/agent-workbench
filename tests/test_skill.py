"""Structural checks for the engineering-workbench skill folder."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIRECTORY = ROOT / ".agents/skills/engineering-workbench"
SKILL_LINE_LIMIT = 120


class EngineeringWorkbenchSkillTests(unittest.TestCase):
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
