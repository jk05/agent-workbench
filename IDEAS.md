# Workbench ideas

Why: remember useful approaches without turning every discovery into a rule.
These are candidates, not active instructions or approval to adopt anything.

Save a curated public summary, never a transcript or private project context.
Each entry has a stable ID, source, takeaway, when it might help, and status:
`open`, `adopted`, or `declined`. Keep the reason for a decision; mark adopted
only after the approved change is applied, with a reference to the change.

## native-and-generated-video-proof

- Source: user suggestion.
- Takeaway: use native macOS tools for screenshots. For synthetic annotated
  walkthroughs, reuse a local renderer with structured inputs rather than
  generating a new renderer each time. Otherwise the user records in Loom;
  use the existing Atlassian MCP to retrieve the share URL and GitHub MCP
  to link it in the PR.
- When useful: concise visual evidence or an explanation communicates better
  than command logs.
- Status: adopted in
  [delivery guidance](.agents/skills/engineering-workbench/delivery.md#visual-evidence)
  on `retro/concise-pr-proof`.
- Review note: label synthetic illustrations; they are not execution proof.
  Verify scope, permissions and sensitive content before capture/publication.
  The private renderer accepts structured scene inputs. Loom MCP recording
  and burned-in annotation are not verified capabilities.

## pstack-task-paths

- Source: [pstack](https://github.com/backnotprop/pstack)
- Takeaway: route investigations, small changes, and substantial delivery
  through proportionate paths instead of one mandatory pipeline.
- When useful: a real task repeats interviews, planning, or approval steps
  despite already having a clear, approved scope.
- Status: open.
- Review note: borrow routing ideas, not a second top-level orchestrator.
  First check why the workbench's existing sizing guidance did not suffice.

## ponytail-reuse-first

- Source: [Ponytail](https://github.com/dietrichgebert/ponytail)
- Takeaway: look for existing project code, platform features, and installed
  dependencies before writing new code; prefer the smallest complete change.
- When useful: tasks produce unnecessary wrappers, dependencies, or home-grown
  features despite the existing simplification guidance.
- Status: open.
- Review note: compare against the current simplifier; avoid stacking
  overlapping always-on instructions. Prevention during build may matter more
  than a cleanup pass afterward. Published gains are not measured here.

## no-mistakes-delivery-gate

- Source: [no-mistakes](https://github.com/kunchenguid/no-mistakes)
- Takeaway: a persistent local validation-and-delivery service can track a run
  separately from the chat and work in an isolated checkout.
- When useful: repeated session interruptions lose delivery state, or agents
  repeatedly miss checks before publishing.
- Status: open.
- Review note: the current delivery loop has been used successfully. No need
  to adopt a service without observed friction. If trialled, give delivery one
  owner; review installation, publication, and history-rewrite permissions.
