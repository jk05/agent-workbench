# Agent Workbench

![Agent Workbench: reusable skills for AI coding agents](docs/images/agent-workbench.png)

**Why:** one personal engineering workflow, the same in every project, instead
of repeating preferences in each chat.

**What:** the `engineering-workbench` skill runs the loop; established skills
do each step. The [skills map](.agents/skills/engineering-workbench/skills-map.md)
names them. Sources for now: [Superpowers](https://github.com/obra/superpowers),
[awesome-copilot](https://github.com/github/awesome-copilot), and Addy Osmani's
`code-simplification`.

```text
1. Plan together    investigate -> interview -> plan -> you approve plan + delivery
2. Run unattended   build -> simplify -> review -> checks -> draft PR -> CI green
3. Retro            you say "retro" -> one small improvement to this repo
```

Merging, deploying, ticket writes, and installs always come back to you.

## How

Requires Python 3.9+. Installation supports **Copilot in VS Code** today;
Claude Code support is next.

```sh
git clone https://github.com/jk05/agent-workbench.git
cd agent-workbench
python3 scripts/workbench.py install engineering-workbench --activate
```

Then, in a fresh Copilot Agents session in your project:

> Use engineering-workbench to investigate PE-1234. Plan only for now.

The helper only copies skill files to `~/.agents/skills/`; Copilot does the
work. Install the mapped skills too: see the
[skills map](.agents/skills/engineering-workbench/skills-map.md).

<details>
<summary>More</summary>

- [Usage](docs/USAGE.md): install, update, remove, handoffs, project notes.
- [Why this design](docs/PROJECT-INTENT.md): decisions and boundaries.
- [Copilot discovery](docs/copilot-discovery.md): why this install path works.
- [Tests](tests/README.md): helper and skill-structure checks.

```sh
python3 -m unittest discover -s tests -v
npx --yes markdownlint-cli2@0.23.3 "**/*.md"
```

</details>
