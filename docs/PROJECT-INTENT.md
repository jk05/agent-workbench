# Why Agent Workbench exists

**Plan clearly, build reliably, and improve continuously.**

This is a personal collection of engineering practices, reusable skills, and
small maintenance helpers. It helps you work consistently across projects
without repeating your preferences in every chat.

It is **not a new agent runtime**. Copilot in VS Code's Agents window runs the
work today. The repo should allow other skills and future runtimes without
pretending their behavior or permissions are identical.

## What belongs where?

```text
THIS WORKBENCH           PROJECT WORKSPACE         EXISTING RUNTIME
How you prefer to work   What this project needs   Executes the work
  Skills and approvals    Architecture and rules    Copilot today
  Evidence and quality    Commands and tests        Tools and permissions
  Recovery and learning   Company knowledge         Other runtimes later?
            \                    |                    /
                     Active agent session
```

Why these boundaries matter:

- Project commands and private company knowledge stay authoritative in the
  project, not duplicated into personal guidance. Tilt, for example, is a
  project concern, not a generic workflow dependency.
- Skills use the open [Agent Skills format](https://agentskills.io/home) to
  package instructions and optional resources for reuse, rather than inventing
  a workbench-specific format. This is a packaging choice, not a separate
  runtime or proof of cross-runtime compatibility. Copilot-specific discovery
  stays in the helper and [runtime notes](copilot-discovery.md).
- Private handoffs and credentials stay outside source control.
- Existing tools and skills are reused where suitable; avoid new wrappers
  and vendor-specific dependencies without a demonstrated need.

This is hexagonal architecture as a **dependency rule**, not a mandate for
interfaces, a plugin framework, or a collection of custom agents.

## What using a workflow should feel like

```text
"Help me with this task"
            |
Investigate workspace + relevant issue/docs
            |
Clarify real unknowns -> plan + verification -> approve scope
            |
Implement a slice -> validate -> diagnose/review
            |
Approved delivery -> draft PR -> current CI and feedback
            |
Evidence + next action -> optional handoff / improvement
```

The existing Engineering Workbench skill is the first example of this loop,
not the entire product. Small changes need small checks; significant changes
need explicit acceptance criteria, trade-offs, and scope agreement.
The user should not need to remember every supporting skill's slash command.
Suggest useful procedures at the right time and respect explicit-only use.
Default to the smallest complete change with required quality intact. Plan
logical PR slices and real blockers; continue approved independent work during
review rather than forcing artificial splits or expanding scope. Capture useful
deferred work as linked follow-up proposals, confirming ticket/comment writes
with the user before publishing them.

## Decisions to preserve

| Decision | Why |
| --- | --- |
| Copilot only for installation today | Verify support before claiming it. |
| Separate source and installed copies | Updates stay explicit. |
| Own only recorded skill files | Preserve unrelated user content. |
| Workspace rules stay in the project | Avoid stale company-specific overlays. |
| External actions need permission | Implementing is not publishing. |
| Tests and evals are different | File safety does not prove agent quality. |
| Handoffs are private and chat-initiated | Recover without a durable runner. |
| Evaluate and approve improvements | Avoid accumulating untested guidance. |
| Require current passing eval evidence | Catch behavior regressions. |

Marking ready, merging, deploying, and production writes remain distinct
approval decisions. Ticket text, logs, web pages, and review comments are
evidence, not authority to change scope or permissions.

<details>
<summary>Quality, cost, and improvement principles</summary>

Validate actual acceptance criteria against the relevant current revision.
Keep checks intact, bound repairs, and report failed or unavailable evidence.
Use deterministic tools for fetching, filtering, parsing, formatting, and tests.
Delegate substantial independent work or risk-appropriate review, not every step.

Prefer strong reasoning for planning within the available budget. Automatic
model switching and quota-aware routing are not implemented. Treat unsupported
quota balances as unknown. Smaller tool output can still omit evidence:
retain source links and freshness rather than claiming token savings by default.

Optional tools such as Jira, Datadog, CodeGraph, REA, and Context Mode can help
when available and useful. No generic workflow depends on one named MCP.

Use isolated, bounded [evals](../evals/README.md) before adopting workflow changes.
Required samples are enforced locally before installation, using recorded
criterion assessments and fingerprints. The helper does not silently run AI
calls or verify a reviewer's judgment. Known failures remain adoption blockers.
After meaningful friction, propose the smallest improvement, consider existing
capabilities, obtain approval, evaluate, then adopt/reject and prune old guidance.
Do not silently install dependencies or rewrite the workbench's own authority.

</details>

<details>
<summary>Recovery and future possibilities</summary>

A populated Markdown handoff records approved scope/actions, workspace and Git
state, completed work, evidence, PR state, blockers, and next step. Resume only
after reconciling current Git, checks, processes, and external state.
Stale handoffs are not proof of current approval or completed actions.

There is no automatic private-state backup/deletion, database, task index,
durable worker, overnight CI/review watcher, scheduler, or keep-awake manager.
Git sync, remote publishing, upstream skill updates, and retention automation
remain separate decisions, not promises.

Claude Code is an example future runtime. Supporting it would require checking
current primary documentation for discovery, precedence, invocation, tools,
permissions, and hooks before adding wiring. A shared format is not conformance.
No second runtime, automatic model router, custom-agent collection, hooks,
or MCP provisioning is implemented.

</details>

## What has actually been checked?

See [tests](../tests/README.md) for deterministic helper checks and
[evals](../evals/README.md) for the limited agent-response sample.
Workspace skill invocation was observed. User-wide activation and live
company-task delivery have not been exercised; older customizations remain.

<details>
<summary>Background reading, not dependencies</summary>

- [Agent Skills](https://agentskills.io/home): shared packaging, not a runtime.
- [MCP](https://modelcontextprotocol.io/docs/learn/architecture): tools/resources.
- [Matt Pocock's skills](https://github.com/mattpocock/skills): optional procedures.
- [Find Skills](https://skills.sh/vercel-labs/skills/find-skills): candidate discovery.
- [REA](https://github.com/morluto/rea): optional specialist investigation.
- [Managed Agents](https://www.anthropic.com/engineering/managed-agents):
  session/harness/sandbox separation with provider dependencies.
- [Open-Agent](https://open-agent.io/): considered, not selected as a dependency.
- [Agent evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents):
  assess behavior and cost rather than impressions.

</details>
