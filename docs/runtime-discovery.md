# How the runtimes find installed skills

**Why:** one install should work in both runtimes without duplicates.
Checked against the VS Code and Claude Code docs on **22 October 2026**.

```text
.agents/skills/<name>/  -- install -->  ~/.claude/skills/<name>/
                                            |               |
                                   VS Code Copilot    Claude Code
```

## Where each runtime looks

| | VS Code Copilot | Claude Code |
| --- | --- | --- |
| Skills | `~/.claude/skills/` (+ `.copilot`, `.agents`) | `~/.claude/skills/` |
| Agents | `~/.copilot/agents/` | `~/.claude/agents/` |
| Plugins | `chat.plugins.marketplaces` setting | `claude plugin` |

`~/.claude/skills/` is the only personal folder both read, so the installer
uses it ([wiring](../runtimes/skills.json)). Installing into two folders would
make Copilot list each skill twice.

**Observed 22 October 2026:** after one install there, each skill appeared
exactly once in both a new Copilot (Agents window) chat and Claude Code.

Plugin skills, such as Superpowers, may appear with a prefix
(`superpowers:brainstorming`) in both runtimes.

## Model versus runtime

The runtime (VS Code calls it a harness) controls tools and discovery; the
model only reasons. Choosing a Claude model inside Copilot still runs Copilot.
VS Code's Copilot, Local, and Claude harnesses can each load different
customizations; this repo targets the **Copilot** harness.

## Sources

- [VS Code agent skills](https://code.visualstudio.com/docs/copilot/customization/agent-skills)
- [VS Code custom agents](https://code.visualstudio.com/docs/copilot/customization/custom-agents)
- [VS Code harnesses](https://code.visualstudio.com/docs/agents/run/agent-harnesses)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [Claude Code subagents](https://code.claude.com/docs/en/sub-agents)

Recheck these before changing the wiring.
