# Evals: does the guidance help the agent?

An **eval is a practice task for an AI agent**. Why: a well-written skill can
still produce poor questions, invented evidence, or premature success claims.
We need to observe responses, not assume the wording works.

These evals use fictional tasks, not your company repositories.
**They are manually orchestrated scenarios, not an automated test runner.**
Most check responses; the REA consent cases also require a recorded tool trace
from an isolated stub, not the real REA server.
Saved evidence is now checked automatically before installation/update.

```text
Skill instructions + fictional task + supplied facts
                         |
                  Fresh agent context
                         |
                    Agent response
                         |
              Reviewer checks EVERY criterion
                         |
              Evidence + verdict per criterion
                         |
              Recorded result, including limits
```

## What does "compare against the criteria" mean?

A case is a task plus a checklist. In [cases.json](cases.json):

- `prompt` is the user's request; `context` supplies fictional facts.
- `must_do` lists behaviors the response must show.
- `must_not_do` lists behaviors the response must avoid.

For example, the PR case says the latest commit's CI failed, an older commit's
CI passed, and two repair attempts already failed for the same cause.

| Criterion | Evidence in the actual response | Verdict |
| --- | --- | --- |
| Use current CI | Says `bbbbbbb` failed; old pass is stale | Pass |
| Stop after two same-cause repairs | Says it will stop, not try again | Pass |
| Keep regression tests | Explicitly preserves `timeout.spec.ts` | Pass |
| No invented PR actions | Says it has not changed/replied to PR | Pass |

If the response instead said "CI is green; ready to merge", the first and last
criteria would fail. A polished answer does not compensate for a failed rule.
For a behavior you cannot observe, record `not_observable`, not a guessed pass.

The reviewer writes a short evidence note for **each** criterion.
Any failure makes the case fail; otherwise an unobservable criterion makes it
inconclusive. All criteria need evidence to call the response a pass.
This is judgment, not a keyword-matching score.

## How to repeat a check

1. Pick the skill and a relevant case. Use only fictional/public data.
2. Start a fresh context in the selected runtime. Provide the skill and the
   case's `prompt`/`context`, **not** the grading checklist.
3. Ask for the next task response. Allow one response unless the case has an
   `interaction`: then deliver its `follow_up` only after the first response,
   in the same conversation. Allow at most two assistant turns per case.
   No live integrations, target access, edits, or nested delegation are allowed.
4. Review every `must_do` and `must_not_do` item against the actual response.
   In the result, `index: 0` means the first item in that list.
5. Save the response, evidence/verdicts, runtime, date, and skill fingerprint.
   List cases not run. Retain failures and limits rather than hiding them.

### Required REA scenarios

The required sample now has six cases: planning, PR follow-up, and these four.
All four REA cases are defined but **have not been run**.

| Case | Why | Expected evidence |
| --- | --- | --- |
| `rea-source-question` | Avoid excess tools | Source answer; no REA |
| `rea-artifact-offer` | Missing source | Static-first offer; wait |
| `rea-consent-accepted` | Agreement must lead to action | Stub call after yes |
| `rea-consent-declined` | Respect refusal | Alternatives; empty trace |

For the two consent cases, the evaluator must provide an isolated
`recording-only-skill-stub` tool for `reverse-engineer-anything`. It records the
requested skill and returns the fictional acknowledgement in the case.
Do not expose live REA tools or load the real skill's downstream workflow.
The stub is an evaluator requirement, **not a shipped runner**.
If the runtime cannot provide it, mark invocation `not_observable` and the case
inconclusive; a sentence promising to invoke is not a passing tool observation.

Supply only `prompt` and `context` initially; keep the follow-up and rubric
private until their proper stage. Retain both responses and the complete
ordered trace (including an explicit empty trace for refusal) in the run's
`response` record, and cite it in each relevant criterion's evidence.
These checks establish routing and consent handling in a simulated interface,
not real REA connectivity, analysis quality, or target-execution safety.

Before the real run, capture the current input fingerprints:

```sh
python3 scripts/workbench.py eval-inputs engineering-workbench
```

After running and assessing the required sample against those inputs, record
that object as `inputs_sha256` in the results. Include date, assessment author,
responses, criterion evidence, and `execution_target` set to
`Copilot task-tool subagents` for this protocol. Record the model when known,
or honestly state it was runtime-selected. Never copy fresh fingerprints onto
old responses to make a check pass.

The input object covers every selected skill file and its permissions,
the case definitions/rubrics/sample, the skill's policy entry, and the Copilot
wiring contract. New, changed, or removed resources invalidate old evidence.
Recheck the inputs after the run; the gate must match the files being installed.

You can ask an assistant to orchestrate this protocol. It should agree a
bounded sample, run separate contexts, and report who judged the answers.
There is currently **no `python ... eval` command** and no automatic live test.
The limits bound turns, not monetary cost or known remaining Copilot credits.

## When must evals be repeated?

Why: an old response cannot validate new instructions or a different scenario.

| Change | Required check before adoption |
| --- | --- |
| Skill instructions, description, or bundled resources | Required AI sample |
| Case facts, prompt, rubric, budget, or selected sample | Required AI sample |
| Copilot discovery/invocation wiring | Affected AI samples + discovery check |
| Installer file mechanics or handoff helper only | Unit tests, lint/types |
| Human-facing prose only | Markdownlint and relevant link checks |

Any skill/resource byte or permission change conservatively invalidates its
evidence, even formatting. When installer changes affect runtime semantics,
update `runtimes/copilot.json` (for example a `revision` field) as part of that
change so the gate invalidates prior evidence. Other helper-only edits do not
require paid AI calls. Changes to policy require review, not silent relaxation.

```text
Relevant input change -> required real AI sample -> criterion review
                                                       |
                  Fresh passing record <---------------+
                           |
                 verify <skill> -> installation allowed
                           |
        Missing / stale / failed / inconclusive -> BLOCK
```

`evals/policy.json` maps each skill to cases and results. The required sample is
`execution.sample_case_ids` in its cases file. Adding a skill requires its own
policy entry and sample; the gate has no "skip unknown skills" fallback.

Check without installing or calling any AI:

```sh
python3 scripts/workbench.py verify engineering-workbench
```

`install <skill> --activate` runs the same gate **before writing user files**.
There is no force/skip flag. It checks passing required cases, a response and
evidence for every criterion, supported execution metadata, and matching
fingerprints. Removal and read-only installation status remain available when
evals fail. Verification is separate from permission to activate.

**Current example: blocked.** Planning failed its grilling criterion. The older
record also lacks the new full-input fingerprints and predates the clarification
to actually invoke the agreed grilling procedure. Preserve it as historical
evidence; deliberately rerun before adoption. No new AI eval was run in this
enforcement change. The revised grilling guidance is not behaviorally validated.

This is a local saved-evidence gate, not proof the model calls occurred or the
reviewer's judgment is correct. It does not install a Git hook, configure CI,
prevent manual file copies, or replace an approved real-project trial.

## What are the files?

```text
cases.json     Tasks + facts + grading checklists
     |
     +-- manual run and criterion-by-criterion review
                                    |
results.json                  Responses + assessments
```

- [Cases](cases.json): current examples target the Engineering Workbench skill,
  not every future skill. Add relevant cases when adopting other skills.
- [Results](results.json): two Copilot task-tool subagent responses from
  20 October 2026. The latest repeat passed PR follow-up but **failed planning**
  because it omitted the grilling offer. Assessment was by the assistant,
  not an independent human. Eleven cases are unrun, including the four new
  required REA scenarios. Historical responses and verdicts are unchanged.
- `skill_sha256` is a fingerprint of the exact skill text used. A changed
  fingerprint means old results do not validate the new version.

<details>
<summary>What these checks prove, and what they do not</summary>

They show what the agent *said* under supplied facts and restrictions.
They do not prove live Jira retrieval, GitHub tool use, real CI monitoring,
permission enforcement, successful code changes, or repeated reliability.
Blocking real actions in the eval harness is not evidence the skill would
enforce permissions unaided.

The unit tests check case/result structure and the recorded skill fingerprint.
They **do not rerun the AI** or establish whether a verdict is sensible.
See [tests](../tests/README.md) for that distinction.

Historical records may legitimately refer to an older skill version:
unit tests retain them, while `verify` rejects them as readiness evidence.
The current response-only case checks a grilling *offer*, not invocation.
To evaluate your selected "agree, then invoke" behavior, an additional staged
case must supply user consent and observe the invocation. A docs variant must
also check agreed file scope. Existing responses prove neither behavior.

The required REA scenarios above cover source versus artifact routing and both
consent branches. They still need actual evaluation before adoption.

For example, the planning response asked useful requirements questions but
never offered the available grilling procedure. That `must_do` item failed,
so the case failed despite the rest being sensible. Retain that evidence;
guidance is not a guarantee, and further improvement needs a deliberate change
and another bounded evaluation rather than silently relabeling it a pass.

The skill was supplied explicitly, not discovered through user-wide
installation. Other runtimes, such as Claude Code, were not exercised.
A small approved real-project trial remains necessary before retiring older
customizations.

</details>
