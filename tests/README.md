# Tests: is the helper safe to use?

Why: an installer must preserve your files even when a source changes,
a collision occurs, or a write fails. These are ordinary automated Python
tests, not conversations with an AI.

```text
Temporary fake home + synthetic skill folders
                       |
                Run helper operations
                       |
           Assert expected files and errors
                       |
             Discard temporary fixtures
```

Run from the repo with Python 3.9+:

```sh
python3 -m unittest discover -s tests -v
```

For the same lint/type checks used during development:

```sh
uvx ty@0.0.89 check scripts tests --python-version 3.9
uvx ruff@0.17.1 check scripts tests --target-version py39
uvx ruff@0.17.1 format --check scripts tests --target-version py39
npx --yes markdownlint-cli2@0.23.3 "**/*.md"
```

`uvx` and `npx` may download these developer tools; they are not runtime
dependencies. Markdown lint uses standard rules, with only `details` and
`summary` allowed as HTML so the docs can keep reference material collapsible.

## What is tested?

| File | Purpose |
| --- | --- |
| [test_workbench.py](test_workbench.py) | Copilot installer and handoff mechanics |
| [test_skill_evals.py](test_skill_evals.py) | Example skill and eval record structure |

Installer tests use **two fictional skills**, each with supporting resources.
They check selection, repeat installs, updates, removal, file permissions,
drift, collisions, symlinks, invalid input, and write-error rollback.
They also check private handoff templates and Copilot-only CLI help.
Your actual home and live configuration are not installation targets.

Gate tests use fabricated passing records **only inside temporary fixtures**;
no real AI is called. They prove missing/stale/failed evidence blocks writes,
including changed resources, case definitions, policy, and Copilot wiring.
They also reject incomplete evidence or a claimed pass with failed criteria.
The real example's recorded failure is tested as a blocked installation.

The skill/eval checks verify metadata, case coverage, per-criterion verdict
records, and the recorded fingerprint's shape. Historical results can remain
valid records of an older version; `verify` separately rejects stale evidence
for installation. If the skill changes, rerun the relevant eval sample rather
than merely replacing its fingerprint.
Structural checks also require the four REA scenarios in the installation
sample and follow-up/observation definitions for both consent branches.
They likewise require slicing, in-review progress, minimal-scope, and follow-up
capture cases, including tracker consent and refusal observation definitions.
They do not execute a stub or prove the AI handles those branches correctly.

The suite can be green while a faithfully recorded AI eval is red. That means
the software correctly recorded and blocked a failure, not that the skill is
ready for adoption. `verify <skill>` is the separate readiness check.

**A green suite proves neither that Copilot follows a skill nor that it can
deliver a real PR.** [Evals](../evals/README.md) observe agent responses;
an approved real-project trial checks integration behavior.
