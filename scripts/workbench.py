"""Manage selected skill folders for Copilot only; other runtimes are not supported."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPOSITORY_ROOT / ".agents/skills"
MANIFEST_VERSION = 2
SLUG_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?\Z")


class WorkbenchError(Exception):
    """An expected, user-actionable workbench error."""


def digest(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def reject_symlinks(path: Path) -> None:
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise WorkbenchError(f"refusing to follow symbolic link: {candidate}")


def read_json_object(path: Path) -> dict:
    reject_symlinks(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WorkbenchError(f"cannot read JSON record {path}: {error}") from error
    if not isinstance(value, dict):
        raise WorkbenchError(f"expected JSON object: {path}")
    return value


def copilot_wiring() -> dict:
    wiring = read_json_object(REPOSITORY_ROOT / "runtimes/copilot.json")
    directory = wiring.get("personal_skills_directory")
    if (
        wiring.get("schema_version") != 1
        or wiring.get("runtime") != "copilot"
        or not isinstance(directory, str)
        or not safe_relative(directory)
    ):
        raise WorkbenchError("invalid Copilot wiring in runtimes/copilot.json")
    return wiring


def paths(home: Path, state_root: Path | None) -> tuple[Path, Path]:
    home = home.expanduser().resolve()
    if state_root is None:
        configured_state = os.environ.get("XDG_STATE_HOME")
        state_root = (
            Path(configured_state).expanduser()
            if configured_state
            else home / ".local/state"
        )
    state_root = state_root.expanduser().resolve() / "agent-workbench"
    return home / copilot_wiring()["personal_skills_directory"], state_root


def validate_name(name: str) -> None:
    if not SLUG_PATTERN.fullmatch(name):
        raise WorkbenchError("skill name must be a lowercase kebab-case slug")


def manifest_location(state: Path, name: str) -> Path:
    return state / "installations/copilot" / f"{name}.json"


def safe_relative(value: str) -> bool:
    return (
        bool(value)
        and "\\" not in value
        and not value.startswith("/")
        and all(part not in ("", ".", "..") for part in value.split("/"))
    )


def read_manifest(manifest_path: Path, skill_directory: Path) -> dict | None:
    reject_symlinks(manifest_path)
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WorkbenchError(
            f"cannot read install manifest {manifest_path}: {error}"
        ) from error
    if (
        not isinstance(manifest, dict)
        or manifest.get("version") != MANIFEST_VERSION
        or manifest.get("destination") != str(skill_directory)
        or manifest.get("runtime") != "copilot"
        or not isinstance(manifest.get("files"), dict)
        or "SKILL.md" not in manifest["files"]
    ):
        raise WorkbenchError(f"unrecognized install manifest: {manifest_path}")
    for name, metadata in manifest["files"].items():
        if (
            not safe_relative(name)
            or not isinstance(metadata, dict)
            or not isinstance(metadata.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", metadata["sha256"]) is None
            or type(metadata.get("mode")) is not int
            or not 0 <= metadata["mode"] <= 0o777
        ):
            raise WorkbenchError(f"invalid file record in: {manifest_path}")
    return manifest


def write_atomic(path: Path, contents: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".workbench-", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(contents)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_path, path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise


def write_new(path: Path, contents: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".workbench-", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(contents)
            output.flush()
            os.fsync(output.fileno())
        os.link(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def snapshot_file(path: Path) -> tuple[bytes, int] | None:
    reject_symlinks(path)
    if not path.exists():
        return None
    if not path.is_file():
        raise WorkbenchError(f"expected regular file: {path}")
    return path.read_bytes(), path.stat().st_mode & 0o777


def file_record(snapshot: tuple[bytes, int]) -> dict:
    contents, mode = snapshot
    return {"sha256": digest(contents), "mode": mode}


def source_files(name: str) -> dict[str, tuple[bytes, int]]:
    validate_name(name)
    directory = SKILLS_ROOT / name
    reject_symlinks(directory)
    if not directory.is_dir():
        raise WorkbenchError(f"skill source not found: {directory}")
    files = {}
    for path in sorted(directory.rglob("*")):
        reject_symlinks(path)
        if not path.is_dir():
            snapshot = snapshot_file(path)
            if snapshot is not None:
                files[path.relative_to(directory).as_posix()] = snapshot
    if "SKILL.md" not in files:
        raise WorkbenchError(f"missing SKILL.md: {directory}")
    text = files["SKILL.md"][0].decode("utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise WorkbenchError(f"missing YAML frontmatter: {directory / 'SKILL.md'}")
    frontmatter = text[4:].split("\n---\n", 1)[0].splitlines()
    if not any(
        line.strip() in (f"name: {name}", f'name: "{name}"', f"name: '{name}'")
        for line in frontmatter
    ):
        raise WorkbenchError(f"skill name must match source folder: {name}")
    if not any(
        line.startswith("description:") and line.partition(":")[2].strip()
        for line in frontmatter
    ):
        raise WorkbenchError(f"skill description required: {name}")
    return files


def eval_setup(name: str) -> tuple[dict, Path, Path]:
    validate_name(name)
    policy = read_json_object(REPOSITORY_ROOT / "evals/policy.json")
    skills = policy.get("skills")
    if policy.get("schema_version") != 1 or not isinstance(skills, dict):
        raise WorkbenchError("invalid eval policy")
    selection = skills.get(name)
    if not isinstance(selection, dict):
        raise WorkbenchError(
            f"no eval policy for {name}; add cases and results before installation"
        )
    for key in ("cases", "results"):
        value = selection.get(key)
        if not isinstance(value, str) or not safe_relative(value):
            raise WorkbenchError(f"invalid {key} path in eval policy for {name}")
    return (
        selection,
        REPOSITORY_ROOT / selection["cases"],
        REPOSITORY_ROOT / selection["results"],
    )


def eval_inputs(name: str, files: dict[str, tuple[bytes, int]]) -> dict[str, str]:
    selection, cases_path, _ = eval_setup(name)
    reject_symlinks(cases_path)
    copilot_wiring()
    records = {relative: file_record(value) for relative, value in files.items()}
    return {
        "skill_tree": digest(json.dumps(records, sort_keys=True).encode()),
        "cases": digest(cases_path.read_bytes()),
        "copilot_wiring": digest(
            (REPOSITORY_ROOT / "runtimes/copilot.json").read_bytes()
        ),
        "policy": digest(json.dumps(selection, sort_keys=True).encode()),
    }


def verify_evals(name: str, files: dict[str, tuple[bytes, int]] | None = None) -> None:
    _, cases_path, results_path = eval_setup(name)
    cases = read_json_object(cases_path)
    results = read_json_object(results_path)
    execution = cases.get("execution")
    if cases.get("schema_version") != 1 or not isinstance(execution, dict):
        raise WorkbenchError(f"invalid eval cases: {cases_path}")
    required = execution.get("sample_case_ids")
    definitions = cases.get("cases")
    max_turns = execution.get("max_agent_turns_per_case")
    if (
        not isinstance(required, list)
        or not required
        or not all(isinstance(item, str) and item for item in required)
        or len(required) != len(set(required))
        or not isinstance(definitions, list)
        or type(max_turns) is not int
        or max_turns < 1
    ):
        raise WorkbenchError(f"invalid required eval sample in: {cases_path}")
    by_id = {}
    for case in definitions:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str):
            raise WorkbenchError(f"invalid case definition in: {cases_path}")
        if case["id"] in by_id:
            raise WorkbenchError(f"duplicate case ID in: {cases_path}")
        for kind in ("must_do", "must_not_do"):
            criteria = case.get(kind)
            if (
                not isinstance(criteria, list)
                or not criteria
                or not all(isinstance(item, str) and item.strip() for item in criteria)
            ):
                raise WorkbenchError(f"invalid {kind} criteria for: {case['id']}")
        by_id[case["id"]] = case
    if not set(required) <= by_id.keys():
        raise WorkbenchError("required eval case definition is missing")
    runs = results.get("runs")
    if (
        results.get("schema_version") != 1
        or not isinstance(runs, list)
        or not isinstance(results.get("assessment"), str)
        or not results["assessment"].strip()
        or not isinstance(results.get("date"), str)
        or not results["date"].strip()
        or results.get("execution_target")
        not in ("Copilot task-tool subagents", "Copilot Python SDK")
    ):
        raise WorkbenchError(
            f"missing or invalid Copilot eval assessment in: {results_path}"
        )
    by_run = {}
    for run in runs:
        if not isinstance(run, dict) or not isinstance(run.get("case_id"), str):
            raise WorkbenchError(f"invalid eval run in: {results_path}")
        if run["case_id"] in by_run:
            raise WorkbenchError(f"duplicate eval run: {run['case_id']}")
        by_run[run["case_id"]] = run
    for identifier in required:
        run = by_run.get(identifier)
        if run is None:
            raise WorkbenchError(f"required eval not run: {identifier}")
        if run.get("status") != "pass":
            raise WorkbenchError(
                f"required eval {identifier}: {run.get('status', 'missing verdict')}; "
                "installation blocked, address and rerun the eval"
            )
        if (
            not isinstance(run.get("response"), str)
            or not run["response"].strip()
            or type(run.get("agent_turns")) is not int
            or not 1 <= run["agent_turns"] <= max_turns
            or not isinstance(run.get("criteria"), list)
        ):
            raise WorkbenchError(f"invalid response or turn budget for: {identifier}")
        expected = {
            (kind, index)
            for kind in ("must_do", "must_not_do")
            for index in range(len(by_id[identifier][kind]))
        }
        observed = set()
        for criterion in run["criteria"]:
            if (
                not isinstance(criterion, dict)
                or not isinstance(criterion.get("kind"), str)
                or type(criterion.get("index")) is not int
                or criterion.get("verdict") != "pass"
                or not isinstance(criterion.get("evidence"), str)
                or not criterion["evidence"].strip()
            ):
                raise WorkbenchError(
                    f"non-passing or invalid criterion in: {identifier}"
                )
            key = (criterion["kind"], criterion["index"])
            if key in observed:
                raise WorkbenchError(f"duplicate criterion in: {identifier}")
            observed.add(key)
        if observed != expected:
            raise WorkbenchError(f"incomplete criterion assessment for: {identifier}")
    current = eval_inputs(name, source_files(name) if files is None else files)
    if results.get("inputs_sha256") != current:
        raise WorkbenchError(
            f"stale or missing eval input fingerprints for {name}; rerun the required "
            "sample against current skill/resources, cases, policy and Copilot wiring"
        )


def installed_files(directory: Path, manifest: dict) -> dict[str, tuple[bytes, int]]:
    files = {}
    for name, expected in manifest["files"].items():
        snapshot = snapshot_file(directory / name)
        if snapshot is None or file_record(snapshot) != expected:
            raise WorkbenchError(
                f"missing or locally edited managed file: {directory / name}"
            )
        files[name] = snapshot
    return files


def clean_empty_parents(path: Path, boundary: Path) -> None:
    while path == boundary or boundary in path.parents:
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
        path = path.parent


def apply_files(
    directory: Path,
    manifest_path: Path,
    before: dict[str, tuple[bytes, int]],
    after: dict[str, tuple[bytes, int]],
) -> None:
    touched = []
    try:
        for name in sorted(before.keys() | after.keys()):
            if before.get(name) == after.get(name):
                continue
            target = directory / name
            reject_symlinks(target)
            if name in after:
                contents, mode = after[name]
                if name in before:
                    write_atomic(target, contents)
                else:
                    write_new(target, contents)
                touched.append(name)
                target.chmod(mode)
            else:
                target.unlink()
                touched.append(name)
        if after:
            manifest = {
                "version": MANIFEST_VERSION,
                "runtime": "copilot",
                "destination": str(directory),
                "files": {name: file_record(value) for name, value in after.items()},
            }
            write_atomic(
                manifest_path,
                (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(),
            )
        else:
            manifest_path.unlink()
    except OSError as error:
        try:
            for name in reversed(touched):
                target = directory / name
                if name in before:
                    contents, mode = before[name]
                    write_atomic(target, contents)
                    target.chmod(mode)
                else:
                    target.unlink()
                    clean_empty_parents(target.parent, directory)
        except OSError as rollback_error:
            raise WorkbenchError(
                f"operation failed: {error}; rollback also failed: {rollback_error}"
            ) from rollback_error
        raise WorkbenchError(
            f"operation failed; managed files restored: {error}"
        ) from error
    for name in before.keys() - after.keys():
        clean_empty_parents((directory / name).parent, directory)


def installation_paths(
    home: Path, state_root: Path | None, name: str
) -> tuple[Path, Path]:
    validate_name(name)
    skills, state = paths(home, state_root)
    legacy = state / "install.json"
    if legacy.exists() or legacy.is_symlink():
        raise WorkbenchError(
            f"legacy single-skill manifest found: {legacy}; remove using the previous helper before switching"
        )
    destination = skills / name
    reject_symlinks(destination)
    return destination, manifest_location(state, name)


def status(home: Path, state_root: Path | None, name: str | None) -> int:
    if name is None:
        _, state = paths(home, state_root)
        sources = [path.name for path in SKILLS_ROOT.iterdir() if path.is_dir()]
        manifests = state / "installations/copilot"
        reject_symlinks(manifests)
        names = set(sources) | {path.stem for path in manifests.glob("*.json")}
        if not names:
            print("Copilot: no source skills or managed installations")
        return max(
            (status(home, state_root, item) for item in sorted(names)), default=0
        )
    directory, manifest_path = installation_paths(home, state_root, name)
    manifest = read_manifest(manifest_path, directory)
    prefix = f"Copilot / {name}"
    if manifest is None:
        if directory.exists():
            raise WorkbenchError(f"unmanaged path exists: {directory}")
        print(f"{prefix}: not installed")
        return 0
    current = installed_files(directory, manifest)
    if not (SKILLS_ROOT / name).exists():
        print(f"{prefix}: installed; source missing (removal still available)")
    elif current != source_files(name):
        print(f"{prefix}: update available")
    else:
        print(f"{prefix}: installed and in sync")
    return 0


def install(home: Path, state_root: Path | None, name: str, activate: bool) -> None:
    if not activate:
        raise WorkbenchError(
            "Copilot installation requires --activate to confirm user-level file writes"
        )
    after = source_files(name)
    directory, manifest_path = installation_paths(home, state_root, name)
    manifest = read_manifest(manifest_path, directory)
    if manifest is None and directory.exists():
        raise WorkbenchError(f"refusing to overwrite unmanaged path: {directory}")
    before = installed_files(directory, manifest) if manifest else {}
    for relative in after.keys() - before.keys():
        target = directory / relative
        reject_symlinks(target)
        if target.exists():
            raise WorkbenchError(f"refusing to overwrite unmanaged path: {target}")
        for parent in target.parents:
            if parent.exists() and not parent.is_dir():
                raise WorkbenchError(f"file blocks destination folder: {parent}")
    verify_evals(name, after)
    apply_files(directory, manifest_path, before, after)
    print(f"Copilot / {name}: installed at {directory}")


def remove(home: Path, state_root: Path | None, name: str, confirm: bool) -> None:
    if not confirm:
        raise WorkbenchError("Copilot removal requires --confirm-removal")
    directory, manifest_path = installation_paths(home, state_root, name)
    manifest = read_manifest(manifest_path, directory)
    if manifest is None:
        raise WorkbenchError(f"no managed Copilot installation found for: {name}")
    before = installed_files(directory, manifest)
    apply_files(directory, manifest_path, before, {})
    if directory.exists():
        print(f"preserved user-added files in: {directory}")
    print(f"Copilot / {name}: removed managed files")


def git_value(workspace: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(workspace), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def create_handoff(
    home: Path, state_root: Path | None, name: str, workspace: Path
) -> None:
    if not SLUG_PATTERN.fullmatch(name):
        raise WorkbenchError("handoff name must be a lowercase kebab-case slug")

    _, state = paths(home, state_root)
    handoff_directory = state / "tasks"
    handoff_path = handoff_directory / f"{name}.md"
    if handoff_path.exists():
        raise WorkbenchError(f"handoff already exists: {handoff_path}")

    workspace = workspace.expanduser().resolve()
    branch = git_value(workspace, "branch", "--show-current") or "detached"
    commit = git_value(workspace, "rev-parse", "HEAD")
    changes = git_value(workspace, "status", "--short")
    worktree = (
        "clean" if changes == "" else "unknown" if changes == "unavailable" else "dirty"
    )
    handoff = f"""# Task handoff: {name}

## Reconcile before acting

- Workspace: `{workspace}`
- Branch: `{branch}`
- Commit: `{commit}`
- Worktree at handoff creation: {worktree}
- Relevant processes at handoff creation: not recorded; check before resuming
- External actions already taken: not recorded; fill this in before resuming

## Approved scope

<!-- Record the user's approved outcome and boundaries. -->

## Completed work and evidence

<!-- Record changes, checks, and their results. -->

## Blockers and external actions

<!-- Record blockers and any PR, push, deployment, or other external action. -->

## Next step

<!-- Reconcile the current workspace and continue from here. -->
"""
    handoff_directory.mkdir(parents=True, exist_ok=True)
    try:
        with handoff_path.open("x", encoding="utf-8") as output:
            output.write(handoff)
    except FileExistsError as error:
        raise WorkbenchError(f"handoff already exists: {handoff_path}") from error
    print(handoff_path)


def show_handoff(home: Path, state_root: Path | None, name: str) -> None:
    if not SLUG_PATTERN.fullmatch(name):
        raise WorkbenchError("handoff name must be a lowercase kebab-case slug")
    _, state = paths(home, state_root)
    handoff_path = state / "tasks" / f"{name}.md"
    if handoff_path.is_symlink():
        raise WorkbenchError(f"refusing to follow symbolic link: {handoff_path}")
    try:
        print(handoff_path.read_text(encoding="utf-8"), end="")
    except OSError as error:
        raise WorkbenchError(f"cannot read handoff {handoff_path}: {error}") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Copilot-only skill installer and private handoff helpers. Other runtimes (e.g. Claude Code) are not supported yet.",
    )
    parser.add_argument(
        "--home", type=Path, default=Path.home(), help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--state-root",
        type=Path,
        help="private state base (agent-workbench/ is appended)",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    status_parser = commands.add_parser(
        "status", help="report Copilot installations without writes"
    )
    status_parser.add_argument(
        "skill", nargs="?", help="skill folder name; omit to list all known skills"
    )
    apply_parser = commands.add_parser(
        "install", help="install/update one selected skill folder for Copilot"
    )
    apply_parser.add_argument("skill", help="folder name under .agents/skills/")
    apply_parser.add_argument(
        "--activate", action="store_true", help="confirm user-level file writes"
    )
    remove_parser = commands.add_parser(
        "remove", help="remove one managed Copilot skill"
    )
    remove_parser.add_argument(
        "skill", help="installed skill name (source need not exist)"
    )
    remove_parser.add_argument("--confirm-removal", action="store_true")

    verify_parser = commands.add_parser(
        "verify",
        help="check saved Copilot eval evidence without installing or calling AI",
    )
    verify_parser.add_argument("skill")
    inputs_parser = commands.add_parser(
        "eval-inputs",
        help="print current fingerprints for recording a real eval; not approval",
    )
    inputs_parser.add_argument("skill")

    handoffs = commands.add_parser("handoff", help="manage private task handoffs")
    handoff_commands = handoffs.add_subparsers(dest="handoff_command", required=True)
    create_parser = handoff_commands.add_parser(
        "create", help="create a private handoff template"
    )
    create_parser.add_argument("name")
    create_parser.add_argument("--workspace", type=Path, default=Path.cwd())
    show_parser = handoff_commands.add_parser("show", help="display a private handoff")
    show_parser.add_argument("name")
    return parser


def main() -> int:
    parser = build_parser()
    arguments = parser.parse_args()
    try:
        if arguments.command == "status":
            return status(arguments.home, arguments.state_root, arguments.skill)
        if arguments.command == "install":
            install(
                arguments.home,
                arguments.state_root,
                arguments.skill,
                arguments.activate,
            )
            return 0
        if arguments.command == "remove":
            remove(
                arguments.home,
                arguments.state_root,
                arguments.skill,
                arguments.confirm_removal,
            )
            return 0
        if arguments.command == "verify":
            verify_evals(arguments.skill)
            print(
                f"Copilot / {arguments.skill}: required eval evidence is current and passing"
            )
            return 0
        if arguments.command == "eval-inputs":
            print(
                json.dumps(
                    eval_inputs(arguments.skill, source_files(arguments.skill)),
                    indent=2,
                )
            )
            return 0
        if arguments.command == "handoff":
            if arguments.handoff_command == "create":
                create_handoff(
                    arguments.home,
                    arguments.state_root,
                    arguments.name,
                    arguments.workspace,
                )
            else:
                show_handoff(arguments.home, arguments.state_root, arguments.name)
            return 0
    except (WorkbenchError, OSError, UnicodeDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
