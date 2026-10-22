# How the runtimes find installed skills

**Why:** each runtime must see each skill exactly once.

```text
                         -- install -->  ~/.agents/skills/<name>/  -> VS Code Copilot
.agents/skills/<name>/
                         -- install -->  ~/.claude/skills/<name>/  -> Claude Code
```

## Where each runtime looks

| | VS Code Copilot (Agents window) | Claude Code |
| --- | --- | --- |
| Skills | `~/.agents/skills/` | `~/.claude/skills/` |
| Agents | `~/.copilot/agents/` | `~/.claude/agents/` |
| Plugins | `chat.plugins.marketplaces` setting | `claude plugin` |

The installer copies each skill and agent to both runtimes' folders
([wiring](../runtimes/wiring.json)). One agent file works in both because
Copilot accepts Claude Code's tool names (`Read`, `Grep`, `Glob`) as aliases
([Copilot agent reference](https://docs.github.com/en/copilot/reference/custom-agents-configuration)).
Plugin skills, such as Superpowers, may appear prefixed: `superpowers:<name>`.

## Observed, 22 October 2026

- VS Code's docs list `~/.claude/skills/` as a personal skills folder, but the
  **Agents window (Copilot harness) did not load skills from it**. It did load
  `~/.agents/skills/`. Claude Code loaded `~/.claude/skills/`.
- VS Code's built-in chat (Local harness) reads both folders, so it may list
  each skill twice. This repo targets the Agents window.
- `~/.copilot/agents/` and `~/.claude/agents/` were each picked up.

## Model versus runtime

The runtime (VS Code calls it a harness) controls tools and discovery; the
model only reasons. Choosing a Claude model inside Copilot still runs Copilot.

## Sources

- [VS Code agent skills](https://code.visualstudio.com/docs/copilot/customization/agent-skills)
- [VS Code custom agents](https://code.visualstudio.com/docs/copilot/customization/custom-agents)
- [VS Code harnesses](https://code.visualstudio.com/docs/agents/run/agent-harnesses)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [Claude Code subagents](https://code.claude.com/docs/en/sub-agents)

Recheck these, and what each runtime actually lists, before changing wiring.
