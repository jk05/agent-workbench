# Use and maintain skills

**Why:** edit skills here, then reuse the approved version in every project.

```text
.agents/skills/<name>/   -- install (approved) -->   ~/.claude/skills/<name>/
                                  |
                       private ownership record
                       (hashes + file permissions)
```

The helper only copies files. It never runs an AI, configures MCP, or touches
your projects.

## Install, update, remove

```sh
python3 scripts/workbench.py status                       # read-only
python3 scripts/workbench.py install engineering-workbench --activate
python3 scripts/workbench.py remove engineering-workbench --confirm-removal
```

- **Agents:** `.agents/agents/<name>.md` installs the same way, copied to
  `~/.claude/agents/` and `~/.copilot/agents/`.
- **Update:** edit the source, run the tests, install again.
- **Safety:** the helper only touches files it installed. It refuses to
  overwrite edits you made to the installed copy or unmanaged files, keeps
  files you added, and restores changed files if a write fails.
- **Not provided:** automatic sync, skill downloads, or version history.
  Roll back by installing an earlier source version.

## Use the workflow

Ask in a fresh Copilot Agents or Claude Code session, or type
`/engineering-workbench`:

> Use engineering-workbench to investigate PE-1234. Plan only for now.

After you agree the plan, approve delivery in one go, for example:

> Approved, go all the way to a green draft PR. Don't mark ready or merge.

Each phase names a role, and the
[skills map](../.agents/skills/engineering-workbench/skills-map.md) says which
skill fills it. If a mapped skill is missing, the workflow says so and uses a
short built-in fallback.

## Private project notes

Project-specific commands, tracker settings, and known flaky tests live
outside every repository:

```text
~/.agent-workbench/projects/<repo-name>/
```

The workflow reads that folder when it exists. Never commit it.

## Retro

Say "retro" at the end of a task. It proposes **one** change to this repo and
applies it only after you approve the diff: on a `retro/` branch in your clone
(path from `~/.agent-workbench/config`), with checks run, asking before any
push. Each retro is logged in `~/.agent-workbench/retros.md`.

## Handoffs

Ask the agent to pause; it saves a private Markdown handoff. In a new chat,
point it at the handoff; it rechecks Git, checks, and PR state before acting.

```sh
python3 scripts/workbench.py handoff create ticket-name --workspace /path/to/repo
python3 scripts/workbench.py handoff show ticket-name
```

State lives in `$XDG_STATE_HOME/agent-workbench/` or
`~/.local/state/agent-workbench/`. Override with `--state-root <dir>` before the
subcommand. No secrets, automatic deletion, or backups.

## Add another skill

Create `.agents/skills/<kebab-name>/SKILL.md` with `name` and `description`
frontmatter, keep its resources inside the folder, try it on a real task, then
install it. Check a third-party skill's source, license, and side effects first.
