# Why Copilot finds the installed skills

**Purpose:** record the evidence behind our installation location.
You do not need to read this to use a skill; start with [usage](USAGE.md).

Official VS Code documentation was checked on **20 October 2026**.
The supported target here is **Copilot in the Agents window**, not every chat
experience in VS Code.

```text
Source repo anywhere         Copilot-supported personal location
Not globally discovered  --> ~/.agents/skills/<name>/SKILL.md
                          explicit install
                                        |
                            Fresh Copilot project session
                                        |
                            Invoke selected skill
```

## Evidence and chosen wiring

The official [skills documentation][skills] lists:

| Scope | Supported skill folders |
| --- | --- |
| Workspace | `.github/skills/`, `.claude/skills/`, `.agents/skills/` |
| Personal | `~/.copilot/skills/`, `~/.claude/skills/`, `~/.agents/skills/` |

We use `.agents/skills/` for source and `~/.agents/skills/` for Copilot
installation. This avoids settings edits and leaves other skills alone.
The helper reads [the wiring contract](../runtimes/copilot.json); changing it
invalidates saved eval evidence before installation is allowed.
Workspace slash invocation was observed in this repository. Personal
installation and real-project behavior have not been exercised.

Discovery makes a skill available; it does not guarantee model invocation.
Explicit `/engineering-workbench` invocation worked for the current example.
Supporting scripts/resources can travel with a skill, but execution still
depends on the runtime's tools and permissions.

## Important distinction: model versus runtime

A **runtime** (called a harness in VS Code docs) controls tools, discovery,
and session behavior. A model is the reasoning engine inside that runtime.
Choosing a Claude model inside Copilot does not select Claude Code.

The [harness guide][harnesses] explains how to identify the current runtime.
Copilot, Local, and Claude sessions can load different customizations.
**Our helper supports Copilot only.** Claude Code is a future example, not
verified by installing a folder that happens to share a format.

<details>
<summary>Other customization types: reference, not installed here</summary>

| Type | Copilot workspace | Copilot personal |
| --- | --- | --- |
| Custom agents | `.github/agents/` | `~/.copilot/agents/` |
| Targeted instructions | `.github/instructions/` | `~/.copilot/instructions/` |
| Skills | `.github/skills/` or `.agents/skills/` | See table above |

Sources: [agents][agents], [instructions][instructions], and
[migration guidance][migration].

Project-wide Copilot guidance also includes `.github/copilot-instructions.md`
and `AGENTS.md`. The instruction docs describe additional formats and gates;
do not assume universal precedence from file names alone.

The [prompt-file page][prompts] describes **Local** harness locations.
The migration page explicitly says Copilot harness sessions do not load
`*.prompt.md`: convert reusable workflows to skills instead. This cross-page
distinction is why this repo did not choose prompt-file wiring.

Local user-profile customizations and settings such as
`chat.agentSkillsLocations`, `chat.instructionsFilesLocations`,
`chat.agentFilesLocations`, `chat.modeFilesLocations`, and
`chat.promptFilesLocations` are not Copilot installation mechanisms.
The docs label these extra-location settings deprecated and Local-only.
Do not edit generated VS Code storage to compensate.

VS Code and the CLI share documented Copilot locations. The CLI additionally
has `COPILOT_CUSTOM_INSTRUCTIONS_DIRS`; its mention is not proof of VS Code
support. No CLI-specific integration is implemented here.

</details>

<details>
<summary>Freshness and research limits</summary>

The original research found experimental features including nested `AGENTS.md`,
forked skill context, user-customization migration, and Codex integration.
None is required by our installer. A missing preview label is not itself
proof of stable behavior.

The full custom-agent reference link returned 404 during research. Concrete
Local profile-storage paths and introduction versions were not established.
Hooks were outside the discovery investigation; no hooks are installed here.

Recheck primary documentation before changing wiring or adding a runtime.
Documentation research establishes a supported location, not successful
end-to-end operation of every customization type.

</details>

[skills]: https://code.visualstudio.com/docs/copilot/customization/agent-skills
[agents]: https://code.visualstudio.com/docs/copilot/customization/custom-agents
[instructions]: https://code.visualstudio.com/docs/copilot/customization/custom-instructions
[prompts]: https://code.visualstudio.com/docs/copilot/customization/prompt-files
[migration]: https://code.visualstudio.com/docs/agent-customization/migrate-customizations
[harnesses]: https://code.visualstudio.com/docs/agents/run/agent-harnesses
