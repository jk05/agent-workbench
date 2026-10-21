# Evals: does the agent follow the skill?

Tests check file handling. Evals check actual AI responses to fictional tasks.
Why: readable instructions are not proof of reliable behavior.

```text
Skill + fictional task -> fresh Copilot session -> response + tool trace
                                                        |
                                    Review EVERY criterion
                                                        |
                           Saved verdicts -> verify -> approved install
```

## Current result

On 21 October, the final twelve-case SDK sample produced **12 passes**,
assessed criterion by criterion by the orchestrating assistant.
Runtime-selected `claude-sonnet-5.5` was confirmed in usage events.

- Planning now covers measurable workload/time; PR tracking includes threads.
- Accepted actions occurred only after confirmation; refusal traces are empty.
- After declining ticket creation, the response retains the proposal, closes
  the publication decision and returns to approved work without re-offering it.

**Verification passes; activation still needs approval.** Previous failures
are retained; no verdict or fingerprint was refreshed without a real run
and assessment.

## Run the sample

Only eval collection needs Python 3.11+ and the official SDK.
The installer remains dependency-free, supporting Python 3.9+.
From this repo, with `uv` and an existing GitHub/Copilot login:

```sh
uv venv --python 3.12 .local/eval-venv
uv pip install --python .local/eval-venv/bin/python -r evals/requirements.txt
.local/eval-venv/bin/python -m copilot download-runtime
.local/eval-venv/bin/python -m evals.run --help
```

Choose a **new private output path**, then explicitly approve model calls:

```sh
.local/eval-venv/bin/python -m evals.run --run \
  --output /absolute/private/path/sample.json
```

`--case ID` selects a smaller sample; `--timeout` bounds each assistant turn.
Existing output is never overwritten. These limits do not cap monetary cost.
The SDK may download its verified runtime into its user cache.
Use the module entry point: direct script startup failed SDK import locally.
The final sample completed using the module entry point.

The runner hides rubrics and later follow-up messages. It disables configuration
discovery, installed skills, file hooks, built-in/MCP tools and host Git
operations. Only recording stubs are exposed; other permissions are denied.
These stubs never contact REA or a tracker. This is not an OS sandbox.

## Assess, then verify

Collection saves **unassessed** responses, ordered tool calls and input hashes.
It does not grade itself or update the installation evidence.

1. Review each case's `must_do` and `must_not_do` against the actual responses.
2. Record evidence for every item: `pass`, `fail`, or `not_observable`.
3. Any failure fails the case; otherwise an unobservable item makes it
   inconclusive. A promise to invoke is not an observed tool call.
4. Preserve the previous result, then export assessed responses and traces to
   [results.json](results.json), with the run's original fingerprints.
5. Recheck current inputs, then verify without installing or calling AI:

   ```sh
   python3 scripts/workbench.py eval-inputs engineering-workbench
   python3 scripts/workbench.py verify engineering-workbench
   ```

All required cases must pass against current inputs. Verification is separate
from activation permission. Status and removal remain available when blocked.

## When must evals be repeated?

| Change | Check before adoption |
| --- | --- |
| Skill instructions/resources, cases/rubrics, policy | Required AI sample |
| Copilot discovery/invocation wiring | Sample + discovery check |
| Helper file mechanics only | Unit tests, lint/types |
| Human-facing prose only | Markdownlint and relevant links |

The gate fingerprints skill files/modes, cases, selected policy and runtime
wiring. Changes invalidate old evidence. If helper changes affect discovery or
invocation, update the wiring contract too. No force/skip flag exists.

## Files and limits

- [cases.json](cases.json): tasks, supplied facts and rubrics. Twelve cases are
  required: planning/PR follow-up, four REA, six slicing/scope/follow-up cases.
  Four interaction cases use two turns and recording-only tools.
- [run.py](run.py): Python SDK collector, not an automatic judge.
- [results.json](results.json): latest assessed responses and tool traces.
- [history/](history/): previous assessed failures, not conversation history
  or gate input.
- [policy.json](policy.json): maps each skill to its cases and results.

Seven optional cases remain unrun. These checks do not prove live Jira/PR/CI
behavior, user-wide discovery, cross-runtime support or repeated reliability.
An approved plan-only trial in a real project is still needed.
