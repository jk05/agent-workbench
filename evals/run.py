"""Collect isolated Copilot responses; grading remains an explicit review step."""

from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def fingerprints() -> dict[str, str]:
    return json.loads(
        subprocess.check_output(
            [
                sys.executable,
                str(ROOT / "scripts/workbench.py"),
                "eval-inputs",
                "engineering-workbench",
            ],
            text=True,
        )
    )


def candidate_prompt(case: dict[str, Any]) -> str:
    return (
        case["prompt"]
        + "\n\nSupplied fictional context:\n"
        + json.dumps(case["context"], indent=2)
    )


class Recorder:
    def __init__(self) -> None:
        self.turn = 0
        self.trace: list[dict[str, Any]] = []

    def call(self, name: str, arguments: dict[str, Any]) -> str:
        if (
            name == "invoke_skill"
            and arguments.get("skill") == "reverse-engineer-anything"
        ):
            result = "Procedure loaded; no artifact inspected or executed."
        elif name == "create_ticket":
            result = "SIMULATED: DEMO-61 at https://tracker.example.test/DEMO-61"
        elif name == "comment_ticket":
            result = "SIMULATED: comment recorded, not posted to a real tracker."
        else:
            raise ValueError(f"unsupported recording tool or arguments: {name}")
        self.trace.append(
            {"turn": self.turn, "tool": name, "arguments": arguments, "result": result}
        )
        return result


def tool_specs(case: dict[str, Any]) -> dict[str, dict[str, str]]:
    harness = case.get("interaction", {}).get("harness")
    if harness == "recording-only-skill-stub":
        return {"invoke_skill": {"skill": "Installed skill name to load."}}
    if harness == "recording-only-tracker-stub":
        return {
            "create_ticket": {
                "title": "Ticket title.",
                "body": "Ticket description and relevant links.",
                "parent": "Original ticket identifier or URL.",
            },
            "comment_ticket": {
                "issue": "Ticket identifier or URL.",
                "body": "Comment text.",
            },
        }
    if harness is not None:
        raise ValueError(f"unsupported harness: {harness}")
    return {}


def isolated_options(root: Path, names: list[str]) -> dict[str, Any]:
    return {
        "working_directory": str(root),
        "config_directory": str(root / "config"),
        "enable_config_discovery": False,
        "skip_custom_instructions": True,
        "enable_skills": False,
        "enable_file_hooks": False,
        "enable_host_git_operations": False,
        "enable_session_store": False,
        "enable_on_demand_instruction_discovery": False,
        "plugin_directories": [],
        "mcp_servers": {},
        "available_tools": [f"custom:{name}" for name in names],
        "excluded_tools": ["builtin:*", "mcp:*"],
        "custom_agents": [],
        "infinite_sessions": {"enabled": False},
    }


async def collect(args: argparse.Namespace) -> None:
    from copilot import CopilotClient, Tool, ToolInvocation, ToolResult
    from copilot.session import PreToolUseHookInput, PreToolUseHookOutput
    from copilot.session_events import AssistantMessageData

    cases = json.loads((ROOT / "evals/cases.json").read_text())
    required = cases["execution"]["sample_case_ids"]
    selected = args.case or required
    if len(selected) != len(set(selected)) or not set(selected) <= set(required):
        raise ValueError("--case must select unique cases from the required sample")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite: {args.output}")
    inputs = fingerprints()
    skill = (ROOT / ".agents/skills/engineering-workbench/SKILL.md").read_text()
    record: dict[str, Any] = {
        "schema_version": 1,
        "date": date.today().isoformat(),
        "execution_target": "Copilot Python SDK",
        "sdk_version": importlib.metadata.version("github-copilot-sdk"),
        "inputs_sha256": inputs,
        "model": args.model or "runtime default; see model events",
        "assessment": "Unassessed candidate transcripts; not installation evidence.",
        "runs": [],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as output:
        output.write(json.dumps(record, indent=2) + "\n")
    with tempfile.TemporaryDirectory(prefix="workbench-eval-") as temporary:
        base = Path(temporary)
        async with CopilotClient(
            working_directory=temporary, base_directory=temporary
        ) as client:
            auth = await client.get_auth_status()
            if not auth.isAuthenticated:
                raise RuntimeError(
                    "Copilot is not authenticated; sign in with GitHub first"
                )
            for identifier in selected:
                case = next(case for case in cases["cases"] if case["id"] == identifier)
                root = base / identifier
                root.mkdir()
                recorder = Recorder()
                specs = tool_specs(case)

                def handler(
                    invocation: ToolInvocation, recorder: Recorder = recorder
                ) -> ToolResult:
                    if not isinstance(invocation.arguments, dict):
                        raise TypeError("recording tools require object arguments")
                    result = recorder.call(invocation.tool_name, invocation.arguments)
                    return ToolResult(text_result_for_llm=result)

                tools = [
                    Tool(
                        name=name,
                        description="Recording-only fictional evaluation tool; no external effects.",
                        parameters={
                            "type": "object",
                            "properties": {
                                key: {"type": "string", "description": value}
                                for key, value in fields.items()
                            },
                            "required": list(fields),
                            "additionalProperties": False,
                        },
                        handler=handler,
                        skip_permission=True,
                    )
                    for name, fields in specs.items()
                ]
                run: dict[str, Any] = {
                    "case_id": identifier,
                    "status": "unassessed",
                    "turns": [],
                    "tool_trace": recorder.trace,
                    "events": [],
                }
                record["runs"].append(run)

                def pre_tool(
                    event: PreToolUseHookInput,
                    _context: dict[str, str],
                    recorder: Recorder = recorder,
                    specs: dict[str, dict[str, str]] = specs,
                ) -> PreToolUseHookOutput:
                    name = event.get("toolName")
                    allowed = name in specs
                    if not allowed:
                        recorder.trace.append(
                            {"turn": recorder.turn, "denied_tool": name}
                        )
                    return {
                        "permissionDecision": "allow" if allowed else "deny",
                        "permissionDecisionReason": "Only recording stubs are permitted.",
                    }

                async def deny_permission(_request: Any, _context: Any) -> Any:
                    from copilot.generated.rpc import PermissionDecisionReject

                    return PermissionDecisionReject(
                        feedback="Evaluation denies external effects."
                    )

                options = isolated_options(root, list(specs))
                print(f"Running {identifier}", flush=True)
                try:
                    async with await client.create_session(
                        **options,
                        model=args.model,
                        tools=tools,
                        on_permission_request=deny_permission,
                        hooks={"on_pre_tool_use": pre_tool},
                        system_message={
                            "mode": "replace",
                            "content": (
                                "Follow this workflow for the supplied fictional task. "
                                "Respond as the task assistant, not an evaluator. "
                                "Use only supplied facts and exposed recording tools. "
                                "No real tools or workspace access are permitted.\n\n"
                                + skill
                            ),
                        },
                    ) as session:

                        def observe(event: Any, run: dict[str, Any] = run) -> None:
                            if event.type.value in (
                                "session.model_change",
                                "session.error",
                                "assistant.usage",
                            ):
                                run["events"].append(event.to_dict())

                        session.on(observe)
                        prompts = [candidate_prompt(case)]
                        if "interaction" in case:
                            prompts.append(case["interaction"]["follow_up"])
                        for turn, prompt in enumerate(prompts, 1):
                            recorder.turn = turn
                            response = await session.send_and_wait(
                                prompt, timeout=args.timeout
                            )
                            if (
                                response is None
                                or not isinstance(response.data, AssistantMessageData)
                                or not response.data.content
                            ):
                                raise RuntimeError(
                                    f"empty candidate response in {identifier}"
                                )
                            run["turns"].append(
                                {
                                    "turn": turn,
                                    "prompt": prompt,
                                    "response": response.data.content,
                                }
                            )
                    run["status"] = "unassessed"
                except Exception as error:
                    run["status"] = "error"
                    run["error"] = f"{type(error).__name__}: {error}"
                    raise
                finally:
                    args.output.write_text(json.dumps(record, indent=2) + "\n")
                print(
                    f"Collected {identifier}: {len(run['turns'])} turn(s)", flush=True
                )
    if inputs != fingerprints():
        raise RuntimeError("eval inputs changed during the run; transcripts are stale")
    print(f"Saved unassessed transcripts to {args.output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case", action="append")
    parser.add_argument("--model")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--run", action="store_true", help="Approve candidate AI calls")
    args = parser.parse_args()
    if not args.run:
        parser.error("--run is required: this command makes paid model calls")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        asyncio.run(collect(args))
    except (RuntimeError, ValueError, OSError, TimeoutError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()
