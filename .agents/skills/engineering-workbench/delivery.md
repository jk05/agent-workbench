# Delivery: draft PR to green CI

Read this when committing, pushing, opening or updating a PR, watching CI,
handling review feedback, or working on more than one PR.

## Permissions

Commit, push, draft PR creation or update, public replies, and marking ready
are distinct actions. An approved delivery sequence covers the actions it
names; do not ask again for each. Without publication approval, leave the
validated local changes and a draft PR description in the response.

## PR descriptions

Start from the repository template and follow repository requirements.
Where allowed, omit irrelevant optional sections rather than filling them
with empty checklists. Keep Proof focused on a short video or screenshot
when useful, plus a few relevant test results with commands and outcomes.
Keep routine lint/build logs out of Proof; put material failures or
limitations under Considerations. Retain the full validation record in
session evidence, not the PR description.

Before publishing or updating, check the final PR text:

- Use concise bullets in each prose section, grouped under short headings
  or bold labels where helpful, with no blank lines between related bullets.
- Keep only relevant tests and material considerations.
- Write PR review comments as one or two short, plain sentences explaining
  the reasoning, without repeating the code or PR description.

## Visual evidence

- Screenshots: use native macOS capture (Screenshot/Cmd+Shift+4/5 or
  `screencapture`), scoped to the intended window or region.
- Synthetic annotated walkthroughs: reuse a saved local renderer with
  structured inputs; do not generate a new renderer for each task. Label
  these as illustrations, not proof of actual application execution.
- Otherwise, ask the user to record in Loom. Retrieve the recording's
  share URL through the available Atlassian MCP and add it to the PR
  through GitHub MCP. Do not promise MCP desktop recording or visual
  annotation features without verifying them.
- Verify caption/highlight alignment and exclude sensitive content.
  Recording and publication still require the applicable permissions.

## What green means

Discover the project's bar; never write one into its repo. In order: its
`CONSTRAINTS.md` if present, then its CI workflows and check scripts (e.g.
`.github/workflows/`, `package.json` scripts), then its lint, type, and test
configs. Private extras, such as known flaky tests, live in
`~/.agent-workbench/projects/<repo-name>/`.

## The CI-to-green loop

1. Follow workspace branch, base, and title conventions. Check whether a PR
   already exists for the branch; never create a duplicate. Push, then create
   or update the **draft** PR with a concise, evidence-based description.
2. Confirm the PR head matches the intended commit. Associate every check
   result with that SHA; results for an older SHA are not readiness evidence.
   Watch for a bounded time (e.g. `gh pr checks <pr> --watch`), never forever.
3. On failure, read the logs (e.g. `gh run view <run-id> --log-failed`) and
   separate pre-existing or environment failures from regressions.
4. Fix in-scope failures locally, rerun the local checks, push, and watch again.
   Before every push, inspect the diff for anything that weakens the quality
   floor in [SKILL.md](SKILL.md); if present, stop and report.
5. Stop when CI is green, after two failed repairs with the same root cause, or
   when the agreed time budget runs out. Report the PR, head SHA, pending,
   skipped, failed, and unavailable checks, unresolved threads, and next action.

Never mark ready or merge without explicit approval and evidence that meets
workspace readiness rules.

## Review feedback

Judge each comment against the approved scope. Fix in-scope issues with the
same repair bound. Escalate conflicting, consequential, or out-of-scope
requests, and never remove a regression test because a comment asks to.
Post replies only when permitted and under workspace disclosure policy.

## More than one PR

- While a PR waits for review, continue other approved, independent slices in
  isolated branches or worktrees.
- A slice that depends on an unmerged PR needs an agreed base strategy
  (stacked or wait). Do not stack silently or merge to unblock it.
- When a prerequisite changes, recheck dependants; their earlier results are stale.
- Report each PR's base, head, CI, unresolved threads, and dependencies
  separately; mark missing state as unknown.
- If a slice grows, revisit its boundary and seek approval before changing
  scope or base strategy. Waiting is not permission to merge, expand scope,
  or launch parallel agents.
