# Skills map

Each role in [SKILL.md](SKILL.md) is filled by the skill named here. To swap a
skill, change one row. If a skill is not installed, the loop uses its fallback.

**Sources for now:** [obra/superpowers](https://github.com/obra/superpowers),
[github/awesome-copilot](https://github.com/github/awesome-copilot), and one
skill from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills).

| Role | Skill | Source |
| --- | --- | --- |
| plan-interview | `brainstorming` | Superpowers |
| plan | `writing-plans` | Superpowers |
| execute-plan | `subagent-driven-development`/`executing-plans` | Superpowers |
| parallel | `dispatching-parallel-agents` | Superpowers |
| build | `test-driven-development` | Superpowers |
| debug | `systematic-debugging` | Superpowers |
| comments | `lean-comments` | awesome-copilot |
| simplify | `code-simplification` | Addy Osmani |
| review | `requesting-code-review` | Superpowers |
| receive-review | `receiving-code-review` | Superpowers |
| verify | `verification-before-completion` | Superpowers |
| deliver, CI to green | this workbench: [delivery.md](delivery.md) | workbench |
| follow-ups, tickets | this workbench: [follow-ups.md](follow-ups.md) | workbench |
| pause, resume | this workbench: [handoffs.md](handoffs.md) | workbench |
| reverse-engineer | `reverse-engineer-anything` (optional, consent) | user |
| retro | fallback in [SKILL.md](SKILL.md) until a retro skill exists | workbench |

## Install notes

- **Superpowers** installs as a plugin in both Claude Code and VS Code Copilot,
  from `obra/superpowers-marketplace`. Its skills may appear as
  `superpowers:<name>`.
- **`lean-comments` and `code-simplification`** are single skill folders, not
  plugins. Until the workbench installer copies them, they may be absent; the
  loop then uses its fallback.
- Install only the mapped `test-driven-development` (Superpowers). Addy's pack
  ships one with the same name; installing the whole pack makes them compete.
