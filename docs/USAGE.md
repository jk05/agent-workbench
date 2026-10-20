# Use and maintain skills

The helper installs selected skill folders for **Copilot only**.
Why: edit skills here, then reuse approved versions across projects without
copying instructions by hand.

```text
.agents/skills/<name>/       Python helper       ~/.agents/skills/<name>/
  SKILL.md                  -- explicit copy -->   SKILL.md
  references/, scripts/...                        same supporting files
                                  |
                          Private ownership record
                          hashes + file permissions
```

The script does not run an AI, configure MCP, launch CI, or create PRs.
Those actions belong to the agent reading the installed skill.

## Install, update, or remove one skill

Requirements: Python 3.9+; Git for handoff snapshots. Run from this repo:

```sh
# Read-only: all known source skills and managed Copilot installations
python3 scripts/workbench.py status
python3 scripts/workbench.py status engineering-workbench

# Read-only evidence gate; does not run an AI
python3 scripts/workbench.py verify engineering-workbench

# Writes user-level files: only after approval
python3 scripts/workbench.py install engineering-workbench --activate

# Removal: only after approval
python3 scripts/workbench.py remove engineering-workbench --confirm-removal
```

`engineering-workbench` is an example selection, not a hardcoded installer
dependency. Future reviewed skills can have their own folders and names.
Installation includes regular supporting files and preserves executable bits.
Empty source directories are not installed; symlinks are refused.

Installation/update also requires fresh, passing eval evidence for the selected
skill. **The current example is blocked by its recorded planning failure.**
See [when to repeat evals](../evals/README.md#when-must-evals-be-repeated).
Activation approval cannot turn a failed eval into a pass.

For updates: edit the source, test it, then explicitly re-run installation.
The helper checks owned files before writing, refuses direct installed edits
and unmanaged collisions, and removes obsolete owned files. Removal preserves
user-added files and other installed skills; it works without the source folder.

An ordinary write failure triggers restoration of the skill's changed files.
Restoration failures are reported. This is not crash-proof transaction storage
or protection against another process changing files during an operation.
Run one maintenance command at a time.

There is no automatic sync, fetch, push, skill download, or version archive.
To roll back content, restore a reviewed source version and explicitly install
it. If an older single-skill `install.json` is detected, the helper refuses to
guess ownership: remove that installation with the earlier helper first.
No such installation has been performed during this build.

## Use the example workflow in your project

Start a fresh Copilot session and explicitly ask:

> Use engineering-workbench to investigate PE-1234. Plan only for now.

Or invoke `/engineering-workbench`. Copilot may also select it from its
description, but automatic selection is not guaranteed.

It should investigate, clarify acceptance criteria, and agree a scoped plan.
It uses tools already available and permitted, such as Atlassian MCP, and
checks for useful procedures or installed skills at meaningful transitions.
It explains the relevant suggestion; you can accept or decline. Agreement
leads to invocation where supported, not just another mention. It respects
declines and does not force irrelevant procedures or install dependencies.

For significant design trade-offs it should suggest `grill-me` (interview)
or `grill-with-docs` (interview plus decision/glossary documentation), then
invoke the available chosen procedure once you agree. The docs variant needs
an agreed document scope. These procedures are optional external skills,
not installed by this workbench.

When ready, you can approve a delivery sequence:

> Implement the agreed scope, validate, commit, push, create a draft PR,
> and follow CI and comments. Don't mark ready, merge, or deploy.

Without publication permission, work stays local with a PR description in chat.
Conflicting existing instructions need resolving before external actions.
PR follow-up is bounded; pending feedback can be handed off, not watched forever.

## Add another skill

```text
.agents/skills/
  engineering-workbench/     First working example
  another-reviewed-skill/    Future skill, not currently shipped
    SKILL.md
    references/             Optional
    scripts/                Optional
```

Use a lowercase kebab-case folder name. Include YAML frontmatter with a matching
`name` and meaningful `description`. Keep any referenced resources inside the
folder so installation remains self-contained.

Review provenance, version, license, side effects, invocation rules, and
Copilot compatibility before adoption. Test mechanics and relevant behavior,
register cases/results in `evals/policy.json`, then verify and explicitly install
the named skill. The installer checks basic
frontmatter presence, not full YAML syntax or behavioral compatibility.

## Private handoffs

Why: retain enough task context to resume without repeating actions.

```text
Ask agent to pause -> populated private Markdown handoff
                               |
New chat + handoff -> reconcile Git/checks/PR state -> continue
```

The helper only creates or displays a template; the agent must populate scope,
approvals, evidence, PR/CI state, processes, blockers, and next step.

```sh
python3 scripts/workbench.py handoff create ticket-name --workspace /path/to/repo
python3 scripts/workbench.py handoff show ticket-name
```

State lives under `$XDG_STATE_HOME/agent-workbench/`, or
`~/.local/state/agent-workbench/`. `tasks/` holds handoffs;
`installations/copilot/<skill>.json` holds ownership records.
Use `--state-root /private/state-base` **before** the subcommand to override
the base; `agent-workbench/` is appended. Use the same base on later commands.
Keep it outside source repositories. No secrets, automatic deletion, or backups.

<details>
<summary>Capability selection and runtime limits</summary>

- **Owned example:** Engineering Workbench, local source, untagged. Explicit
  workspace invocation observed; user-wide use not exercised.
- **Optional procedures:** grilling, TDD, diagnosis, and review. Existing
  workspace/runtime skills or reviewed upstream sources such as
  [Matt Pocock's skills](https://github.com/mattpocock/skills) may supply these.
  They are not pinned, copied, or installed by this repo. Check their actual
  version and invocation policy; suggest explicit-only workflows with consent.
- **Evidence/actions:** Jira/Confluence, observability, GitHub, browser, and
  code intelligence come from configured MCP, CLI, or native tools. Check
  availability and permissions in each session.

Claude Code is a possible future target, not a supported option. Reusing the
Markdown format alone would not verify its discovery, tools, or permissions.
See [Copilot discovery](copilot-discovery.md) and
[project intent](PROJECT-INTENT.md) for the current boundaries.

</details>
