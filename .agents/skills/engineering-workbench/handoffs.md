# Pause, resume, and fresh-session review

Read this when the user asks to pause or resume, or when independent review
needs a fresh session because no subagent is available.

## Pause

Save a compact Markdown handoff in the user's private state root, outside the
workbench and project repositories. The workbench helper
(`scripts/workbench.py handoff`) creates a template if available; otherwise
agree a private location. Populate:

- approved scope and permitted actions
- workspace, branch, commit, and dirty state
- completed work, checks run, and the revision they ran on
- relevant running processes
- PR, head SHA, CI, and unresolved comments
- blockers and the next step.

Exclude secrets and report the saved path.

## Resume

Read the handoff, then reconcile the actual Git state, checks, processes, and
external PR or issue state before acting. A stale handoff is not proof of
current approval or completed actions: do not recreate a PR, repeat an
external action, or reuse old check results because it says so.

## Fresh-session review

When no reviewer subagent exists, pause with a handoff that names the plan,
acceptance criteria, and the diff or commit range to review. The new session
reviews only that diff and reports findings by severity with file and line.
