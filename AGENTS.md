# Agent Workbench instructions

This repo holds reusable skills and helpers, not a new runtime.
These instructions protect scope and user-owned files during maintenance.

- Read [README.md](README.md) for entry points and
  [project intent](docs/PROJECT-INTENT.md) for design decisions.
- Skills install once into `~/.claude/skills/`, read by both VS Code Copilot
  and Claude Code. Read [discovery evidence](docs/runtime-discovery.md) before
  changing wiring; verify current primary docs before adding a runtime.
- Skills live in `.agents/skills/`. Engineering Workbench is the first example,
  not a hardcoded installer dependency. Keep complete skill folders reusable.
- Keep the main `SKILL.md` under 120 lines (tested). Skill names belong in
  `skills-map.md`; detail belongs in linked files, read only when needed.
- Write concisely: no repetition across docs, no unnecessary hedging.
- This repo is public: no company code, ticket text, or private repo names.
  Project specifics belong in `~/.agent-workbench/projects/<repo-name>/`.
- Keep project knowledge in its workspace; private task state and credentials
  outside repositories.
- Obtain explicit approval before user-wide installation, live configuration
  changes, publishing, or retirement of existing customizations.
- Preserve unrelated content. Cover ownership, drift, removal, and ordinary
  write-error rollback with deterministic fixture tests.
- Changes need the unit tests and markdownlint below. Report unrun or limited
  checks honestly. See [tests](tests/README.md).
- There are no agent evals for now. Try skill behavior changes on a real task
  and report what was and was not exercised. Add an eval only when a retro
  shows a real failure worth guarding; never spend AI budget silently.
- If installer changes alter discovery or invocation, update
  `runtimes/wiring.json` and the [discovery notes](docs/runtime-discovery.md).
- Lead user-facing docs with why/what/how and short diagrams. Keep the visible
  README concise and detailed reference material collapsible.

Run the local checks with:

```sh
python3 -m unittest discover -s tests -v
npx --yes markdownlint-cli2@0.23.3 "**/*.md"
```
