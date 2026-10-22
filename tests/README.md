# Tests: do the helpers behave correctly?

Why: file handling and the skill folder's structure should be checked without
AI calls or changes to your real home/configuration.

```text
Temporary fixtures -> helper operations -> assertions -> discard fixtures
```

Run from this repo with Python 3.9+:

```sh
python3 -m unittest discover -s tests -v
```

| File | Checks |
| --- | --- |
| [test_workbench.py](test_workbench.py) | Install/update/remove, drift, rollback |
| [test_skill.py](test_skill.py) | Frontmatter, line limit, mapped roles, links |

Installer tests use fictional skills and temporary homes.
**Green unit tests do not mean the agent follows the skill.** Try behavior
changes on a real task.

## Lint and types

```sh
uvx ty@0.0.89 check scripts tests --python-version 3.9
uvx ruff@0.17.1 check scripts tests --target-version py39
uvx ruff@0.17.1 format --check scripts tests --target-version py39
npx --yes markdownlint-cli2@0.23.3 "**/*.md"
```

`uvx`/`npx` may download developer tools; no Node runtime dependency or
package manifest is required.
