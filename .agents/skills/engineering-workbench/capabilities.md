# Choosing tools and delegating

Read this when deciding which tool or evidence source to use, whether to
reverse engineer an artifact, or whether to delegate work.

## Evidence sources

- **Ticket and requirements:** an available issue integration and relevant
  linked docs. Tracker site and project settings belong in private project
  notes, not here.
- **Production behavior:** narrowly scoped logs, traces, or metrics; avoid
  unrelated customer data.
- **Code structure:** source, code search or code intelligence, docs, and tests.
- **UI behavior:** browser inspection and relevant interaction checks.
- **PRs, checks, feedback:** the repository's standard GitHub tooling.
- **Fetch, filter, parse, format, test:** deterministic tools, not an extra
  model call.

Check availability, permissions, and freshness. Optional services are never
mandatory unless workspace policy says so; report what their absence costs.

## Reverse engineering

Offer the mapped reverse-engineering skill only when the evidence must come
from a shipped artifact rather than available source: binaries, packaged or
minified JavaScript, Electron apps, decompilation, or version comparisons.
A dependency or module appearing in source is not a trigger; ordinary source,
dependency API, and architecture questions stay with repository tools.

Explain the target, the evidence gap, and side effects, then wait for consent
before loading it. Consent to load the procedure is separate from permission
to execute the target or attach to a process. Prefer static inspection first.
If the user declines, do not offer it again; continue with alternatives such
as public docs or a user-supplied sample, and state their limits.

## Delegation

The coordinator holds the plan and final verification; the mapped execute-plan
and parallel skills run workers and per-task review. Delegate only useful work,
never every role "just in case":

| Role | Use for | Model | Tools |
| --- | --- | --- | --- |
| explorer | bounded "where is X" questions | fast | read, search |
| researcher | one external fact, e.g. a library API | fast | read, web |
| worker | a fully specified change and tests | strong | read, edit, shell |
| reviewer | independent review of a finished diff | strongest | read, search |

- Skip the explorer when you can open the file in one read; do a few-line
  change yourself.
- Write the worker brief first: files, expected behavior, tests, and the
  verification commands. Run workers in parallel only on disjoint files.
- Keep briefs short and closed-ended; ask for paths with line numbers, diffs,
  and command output, not narratives. Verify claims you have not seen output for.
- Use the reviewer when risk warrants it; it is the most expensive step.
- Launch parallel agents only when delegation is approved. Treat unknown
  quota as unknown.
