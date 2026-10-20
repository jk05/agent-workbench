# Agent Workbench instructions

This repo holds reusable skills and helpers, not a new runtime.
These instructions protect scope and user-owned files during maintenance.

- Read [README.md](README.md) for entry points and
  [project intent](docs/PROJECT-INTENT.md) for design decisions.
- Installation supports **Copilot only**. Read
  [discovery evidence](docs/copilot-discovery.md) before changing wiring;
  verify current primary docs before supporting another runtime.
- Skills live in `.agents/skills/`. Engineering Workbench is the first example,
  not a hardcoded installer dependency. Keep complete skill folders reusable.
- Keep project knowledge in its workspace; private task state and credentials
  outside repositories.
- Obtain explicit approval before user-wide installation, live configuration
  changes, publishing, or retirement of existing customizations.
- Preserve unrelated content. Cover ownership, drift, removal, and ordinary
  write-error rollback with deterministic fixture tests.
- Separate helper tests from agent evals; report unrun or limited checks
  honestly. See [tests](tests/README.md) and [evals](evals/README.md).
- Before adopting skill/resource, eval-case/rubric, or Copilot-wiring changes,
  run the affected skill's required real AI sample and review every criterion.
  Follow the [rerun policy](evals/README.md#when-must-evals-be-repeated).
  Installer-only/handoff changes need unit tests; prose-only docs need lint.
  If installer changes alter discovery or invocation semantics, update the
  Copilot wiring contract and rerun the affected evals as well.
- Installation/update requires `verify <skill>` to pass saved-evidence checks.
  Keep failed or stale results visible; never refresh fingerprints or change
  verdicts without an actual run and assessment. Do not silently spend AI
  budget, weaken criteria, or bypass the gate to achieve completion.
- Lead user-facing docs with why/what/how and short diagrams. Keep the visible
  README concise and detailed reference material collapsible.

Run the local checks with:

```sh
python3 -m unittest discover -s tests -v
python3 -m json.tool evals/cases.json
python3 -m json.tool evals/results.json
npx --yes markdownlint-cli2@0.23.3 "**/*.md"
```
