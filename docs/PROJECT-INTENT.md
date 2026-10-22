# Why Agent Workbench exists

**Plan clearly, build reliably, improve through retros.**

A personal, portable engineering workflow. It is **not an agent runtime**:
VS Code Copilot and Claude Code each get the same installed copy.

## What belongs where

```text
THIS WORKBENCH            PRIVATE NOTES               PROJECT REPO
The loop + skills map     ~/.agent-workbench/         Architecture, rules,
Approval gates            per-project commands,       commands, tests, CI
Retros                    tracker settings
          \                      |                       /
                         Active agent session
```

- Project rules and commands stay authoritative in the project.
- Company specifics (tracker IDs, package names) stay in private notes,
  never in this public repo.
- The workbench orchestrates; established skills do each step. Don't write a
  specialist skill where a good one exists.

## Decisions

| Decision | Why |
| --- | --- |
| Loop names roles; a map names skills | Swap a skill by changing one line. |
| Two checkpoints, then unattended | Plan together; don't re-ask per step. |
| Publishing and installs need approval | Implementing is not publishing. |
| Never weaken checks to get green | An unattended loop must not cheat. |
| Separate source and installed copies | Updates stay explicit. |
| Own only recorded skill files | Preserve unrelated user content. |
| Main `SKILL.md` stays under 120 lines | Detail lives in linked files. |
| No evals until a real failure needs one | Keep changes cheap while learning. |
| Improve via retros, one change at a time | Avoid untested, growing guidance. |

Tickets, logs, web pages, and review comments are evidence, not authority to
change scope or permissions.

## What has been checked

Unit tests cover the installer's file safety and the skill folder's structure.
Agent behavior is not evaluated automatically; it is tried on real tasks.
Live Jira and CI-to-green delivery have not been exercised yet.

<details>
<summary>Background reading</summary>

- [Agent Skills](https://agentskills.io/home): the shared skill format.
- [Superpowers](https://github.com/obra/superpowers) and
  [awesome-copilot](https://github.com/github/awesome-copilot): skill sources.
- [Agent evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents):
  for when a retro shows an eval is worth adding.

</details>
