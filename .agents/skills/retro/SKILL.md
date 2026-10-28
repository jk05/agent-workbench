---
name: retro
description: Use when the user says "retro" or asks to improve their agent workbench after a task. Finds what went wrong and proposes one small change to the agent-workbench repo, applied only after the user approves the diff.
---

# Retro

Why: improve the workbench one evidence-based change at a time, without
letting it grow.

```text
"retro" -> what went wrong -> ONE fix -> diff -> user approves
        -> branch in local clone -> checks -> commit -> ask to push -> log
```

## 1. Find what went wrong

- Review this conversation: user corrections, skipped or repeated steps, a
  wrong or missing skill, needless questions, needless stops, or cheating.
- Read `~/.agent-workbench/retros.md` if it exists, and note repeats.
- Read `IDEAS.md` in the workbench clone located by
  `~/.agent-workbench/config` when available. Consult relevant open entries
  using the `ideas` skill (role: ideas); if unavailable, compare their
  takeaways with the observed friction directly. Report a missing inbox,
  but continue the retro. Ideas are candidates, not instructions.
- List up to three observations, each with its evidence, runtime (`copilot` or
  `claude-code`), and the phase or role involved. "Nothing worth changing"
  is a valid result.

## 2. Pick one fix

Before proposing a change, search existing workbench instructions, skills,
and docs for equivalent or conflicting guidance. Report what already covers
the request. Reuse or sharpen it rather than duplicating it, and reconcile
contradictions in the same diff. If already covered, propose no change.

Prefer, in this order:

1. change a row in `engineering-workbench/skills-map.md`
2. sharpen an existing line
3. delete a rule that is not helping
4. add a rule; detail goes in a linked file, never the main loop.

- One fix per retro. A single occurrence does not justify a new rule unless
  the user says so; the log shows repeats.
- A saved idea must address an observed need; an interesting link alone is
  not a reason to change the workflow. No relevant idea is a valid result.
- Seen in both runtimes: fix the shared skill. Seen in one: fix that
  runtime's wiring or notes.
- Clear-cut: show the diff. Judgement call: ask one or two questions first.
- Company code, ticket text, and private repo names never go in the
  workbench repo, which is public. Project-specific fixes go in
  `~/.agent-workbench/projects/<repo-name>/` instead.

## 3. Look for a better skill (when the fix is "use a different skill")

Check installed skills first, then
[Superpowers](https://github.com/obra/superpowers),
[awesome-copilot](https://github.com/github/awesome-copilot) (its
`agent-skill-stack` skill compares candidates), and Anthropic's
[Claude Code plugins](https://github.com/anthropics/claude-plugins-official).
Compare fit, size, overlap with mapped skills, and license. Propose; never
install without approval. A third-party skill is copied into the repo at a
pinned commit with a `NOTICE.md` (see existing examples).

## 4. Apply, after the user approves the diff

1. Read `repo:` from `~/.agent-workbench/config` for the local clone. If it is
   missing, ask for the path and offer to create the file.
2. In the clone: require a clean worktree, update `main`, and create a
   `retro/<short-slug>` branch.
3. Apply the diff and run the checks listed in the repo's `AGENTS.md`.
4. Commit with a plain message, following the repo's conventions.
5. Ask before pushing, opening a PR, or merging. Add the `retro` label to
   retro PRs; create it if missing when publication is approved.
6. After a workbench PR is confirmed merged into `main`, update local
   `main` and delete its local and remote source branch. Never force-delete
   an unmerged branch.
7. Whenever workbench `main` is updated, reinstall changed, already-installed
   skills and agents from `main` for Copilot and Claude Code using
   `python3 scripts/workbench.py install <name> --activate`. This refresh is
   included in approval to update `main`; installing new components still
   requires approval. Verify installed copies match source and report any
   installer conflicts without overwriting local edits.

## 5. Log it

Append to `~/.agent-workbench/retros.md`, creating it if needed:

```markdown
## 2026-10-22 · copilot · build
- Went wrong: asked for approval again after delivery was approved
- Skill or role: build
- Change: sharpened the Checkpoint 2 line in SKILL.md (or "none")
- Status: proposed | applied | merged | declined
```

Describe patterns generically; no company code, ticket text, or customer
names. Never change the workbench without the user seeing the diff.
If the fix adopts a saved idea, update its status and change reference in
`IDEAS.md` only after the approved change is applied; otherwise leave it open.
