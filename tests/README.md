# Tests: do the helpers behave correctly?

Why: file handling and eval bookkeeping should be checked without AI calls
or changes to your real home/configuration.

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
| [test_skill_evals.py](test_skill_evals.py) | Case/result structure and coverage |
| [test_eval_runner.py](test_eval_runner.py) | Hidden rubric, tool filters, stubs |

Installer tests use fictional skills and temporary homes. Passing eval records
inside those fixtures are fabricated test inputs, not evidence about an AI.
Runner tests exercise stubs directly; they do not establish runtime enforcement.

**Green unit tests do not mean the skill passes its behavioral evals.**
Actual AI collection and assessment are separate: see [evals](../evals/README.md).

## Lint and types

After creating the optional eval environment described in the eval guide:

```sh
uvx ty@0.0.89 check scripts tests --python-version 3.9
uvx ty@0.0.89 check evals/run.py
uvx ruff@0.17.1 check scripts tests evals/run.py --target-version py39
uvx ruff@0.17.1 format --check scripts tests evals/run.py --target-version py39
npx --yes markdownlint-cli2@0.23.3 "**/*.md"
```

[ty.toml](../ty.toml) resolves the optional SDK from `.local/eval-venv`;
it does not change system Python. Markdownlint excludes that generated
environment. `uvx`/`npx` may download developer tools; no Node runtime
dependency or package manifest is required.
