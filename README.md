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

Merging, deploying, ticket writes, and new installs come back to you.
Approved workbench `main` updates include refreshing existing installations.

## How

Requires Python 3.9+. Works in **VS Code Copilot** and **Claude Code**.

1. Install Superpowers as a plugin in each runtime: see the
   [skills map](.agents/skills/engineering-workbench/skills-map.md).
2. Install this repo's skills and the `workbench-reviewer` agent; each is
   copied into both runtimes' folders:

   ```sh
   git clone https://github.com/jk05/agent-workbench.git
   cd agent-workbench
   for name in engineering-workbench workbench-delivery retro ideas \
       lean-comments code-simplification workbench-reviewer; do
     python3 scripts/workbench.py install "$name" --activate
   done
   ```

3. Tell `retro` and `ideas` where your clone is:

   ```sh
   mkdir -p ~/.agent-workbench
   echo "repo: $PWD" > ~/.agent-workbench/config
   ```

4. In a fresh session in your project, ask:

   > Use engineering-workbench to investigate PE-1234. Plan only for now.

<details>
<summary>More</summary>

- [Usage](docs/USAGE.md): install, update, remove, handoffs, project notes.
- [Ideas](IDEAS.md): saved candidates for future workbench improvements.
- [Why this design](docs/PROJECT-INTENT.md): decisions and boundaries.
- [Runtime discovery](docs/runtime-discovery.md): why one install serves both.
- [Tests](tests/README.md): helper and skill-structure checks.

```sh
python3 -m unittest discover -s tests -v
npx --yes markdownlint-cli2@0.23.3 "**/*.md"
```

</details>
