"""Install skills and agents for VS Code Copilot and Claude Code, plus handoffs."""

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
from typing import NamedTuple

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPOSITORY_ROOT / ".agents/skills"
AGENTS_ROOT = REPOSITORY_ROOT / ".agents/agents"
MANIFEST_VERSION = 2
RUNTIMES = ["copilot", "claude-code"]
RUNTIME_LABEL = "shared"
SLUG_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?\Z")


class WorkbenchError(Exception):
    """An expected, user-actionable workbench error."""


class Target(NamedTuple):
    label: str
    directory: Path
    manifest: Path
    required: str
    # Agent folders also hold files the workbench does not own.
    shared: bool


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


def wiring() -> dict:
    wiring = read_json_object(REPOSITORY_ROOT / "runtimes/wiring.json")
    if wiring.get("schema_version") != 4 or wiring.get("runtimes") != RUNTIMES:
        raise WorkbenchError("invalid wiring in runtimes/wiring.json")
    for key in ("personal_skills_directories", "personal_agents_directories"):
        directories = wiring.get(key)
        if (
            not isinstance(directories, dict)
            or sorted(directories) != sorted(RUNTIMES)
            or not all(
                isinstance(value, str) and safe_relative(value)
                for value in directories.values()
            )
        ):
            raise WorkbenchError(f"invalid {key} in runtimes/wiring.json")
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
    return home, state_root.expanduser().resolve() / "agent-workbench"


def validate_name(name: str) -> None:
    if not SLUG_PATTERN.fullmatch(name):
        raise WorkbenchError("name must be a lowercase kebab-case slug")


def safe_relative(value: str) -> bool:
    return (
        bool(value)
        and "\\" not in value
        and not value.startswith("/")
        and all(part not in ("", ".", "..") for part in value.split("/"))
    )


def read_manifest(target: Target) -> dict | None:
    manifest_path, skill_directory = target.manifest, target.directory
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
        or manifest.get("runtime") != RUNTIME_LABEL
        or not isinstance(manifest.get("files"), dict)
        or target.required not in manifest["files"]
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
    check_frontmatter(files["SKILL.md"][0], name, directory / "SKILL.md")
    return files


def agent_files(name: str) -> dict[str, tuple[bytes, int]]:
    validate_name(name)
    path = AGENTS_ROOT / f"{name}.md"
    snapshot = snapshot_file(path)
    if snapshot is None:
        raise WorkbenchError(f"agent source not found: {path}")
    check_frontmatter(snapshot[0], name, path)
    return {f"{name}.md": snapshot}


def check_frontmatter(contents: bytes, name: str, path: Path) -> None:
    text = contents.decode("utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise WorkbenchError(f"missing YAML frontmatter: {path}")
    frontmatter = text[4:].split("\n---\n", 1)[0].splitlines()
    if not any(
        line.strip() in (f"name: {name}", f'name: "{name}"', f"name: '{name}'")
        for line in frontmatter
    ):
        raise WorkbenchError(f"name must match source: {name}")
    if not any(
        line.startswith("description:") and line.partition(":")[2].strip()
        for line in frontmatter
    ):
        raise WorkbenchError(f"description required: {name}")


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
    item: Target,
    before: dict[str, tuple[bytes, int]],
    after: dict[str, tuple[bytes, int]],
) -> None:
    directory, manifest_path, shared = item.directory, item.manifest, item.shared
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
                "runtime": RUNTIME_LABEL,
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
                    if not shared:
                        clean_empty_parents(target.parent, directory)
        except OSError as rollback_error:
            raise WorkbenchError(
                f"operation failed: {error}; rollback also failed: {rollback_error}"
            ) from rollback_error
        raise WorkbenchError(
            f"operation failed; managed files restored: {error}"
        ) from error
    for name in before.keys() - after.keys():
        if not shared:
            clean_empty_parents((directory / name).parent, directory)


def is_agent(name: str, state: Path) -> bool:
    agent = (AGENTS_ROOT / f"{name}.md").is_file() or any(
        (state / "installations/agents").glob(f"*/{name}.json")
    )
    skill = (SKILLS_ROOT / name).is_dir() or any(
        (state / "installations/skills").glob(f"*/{name}.json")
    )
    if agent and skill:
        raise WorkbenchError(f"name is used by both a skill and an agent: {name}")
    return agent


def targets(home: Path, state_root: Path | None, name: str) -> list[Target]:
    validate_name(name)
    home, state = paths(home, state_root)
    legacy = state / "install.json"
    if legacy.exists() or legacy.is_symlink():
        raise WorkbenchError(
            f"legacy single-skill manifest found: {legacy}; remove using the previous helper before switching"
        )
    config = wiring()
    agent = is_agent(name, state)
    found = []
    for runtime in RUNTIMES:
        if agent:
            directory = home / config["personal_agents_directories"][runtime]
            manifest = state / "installations/agents" / runtime / f"{name}.json"
            label = f"Agent / {name} ({runtime})"
            item = Target(label, directory, manifest, f"{name}.md", True)
        else:
            directory = home / config["personal_skills_directories"][runtime] / name
            manifest = state / "installations/skills" / runtime / f"{name}.json"
            label = f"Skill / {name} ({runtime})"
            item = Target(label, directory, manifest, "SKILL.md", False)
        reject_symlinks(directory)
        found.append(item)
    return found


def source_for(item: Target, name: str) -> dict[str, tuple[bytes, int]]:
    return agent_files(name) if item.shared else source_files(name)


def source_exists(item: Target, name: str) -> bool:
    return (AGENTS_ROOT / f"{name}.md" if item.shared else SKILLS_ROOT / name).exists()


def unmanaged(item: Target) -> bool:
    path = item.directory / item.required if item.shared else item.directory
    return path.exists() or path.is_symlink()


def known_names(state: Path) -> set[str]:
    names = {path.name for path in SKILLS_ROOT.iterdir() if path.is_dir()}
    if AGENTS_ROOT.is_dir():
        names |= {path.stem for path in AGENTS_ROOT.glob("*.md")}
    for pattern in ("installations/skills/*/*.json", "installations/agents/*/*.json"):
        reject_symlinks(state / pattern.split("/*")[0])
        names |= {path.stem for path in state.glob(pattern)}
    return names


def status(home: Path, state_root: Path | None, name: str | None) -> int:
    if name is None:
        names = known_names(paths(home, state_root)[1])
        if not names:
            print("No source skills, agents, or managed installations")
        return max(
            (status(home, state_root, item) for item in sorted(names)), default=0
        )
    for item in targets(home, state_root, name):
        manifest = read_manifest(item)
        if manifest is None:
            if unmanaged(item):
                raise WorkbenchError(f"unmanaged path exists: {item.directory}")
            print(f"{item.label}: not installed")
            continue
        current = installed_files(item.directory, manifest)
        if not source_exists(item, name):
            print(f"{item.label}: installed; source missing (removal still available)")
        elif current != source_for(item, name):
            print(f"{item.label}: update available")
        else:
            print(f"{item.label}: installed and in sync")
    return 0


def install(home: Path, state_root: Path | None, name: str, activate: bool) -> None:
    if not activate:
        raise WorkbenchError(
            "installation requires --activate to confirm user-level file writes"
        )
    planned = []
    for item in targets(home, state_root, name):
        after = source_for(item, name)
        manifest = read_manifest(item)
        if manifest is None and unmanaged(item):
            raise WorkbenchError(
                f"refusing to overwrite unmanaged path: {item.directory}"
            )
        before = installed_files(item.directory, manifest) if manifest else {}
        for relative in after.keys() - before.keys():
            target = item.directory / relative
            reject_symlinks(target)
            if target.exists():
                raise WorkbenchError(f"refusing to overwrite unmanaged path: {target}")
            for parent in target.parents:
                if parent.exists() and not parent.is_dir():
                    raise WorkbenchError(f"file blocks destination folder: {parent}")
        planned.append((item, before, after))
    for item, before, after in planned:
        apply_files(item, before, after)
        print(f"{item.label}: installed at {item.directory}")


def remove(home: Path, state_root: Path | None, name: str, confirm: bool) -> None:
    if not confirm:
        raise WorkbenchError("removal requires --confirm-removal")
    planned = []
    for item in targets(home, state_root, name):
        manifest = read_manifest(item)
        if manifest is not None:
            planned.append((item, installed_files(item.directory, manifest)))
    if not planned:
        raise WorkbenchError(f"no managed installation found for: {name}")
    for item, before in planned:
        apply_files(item, before, {})
        if not item.shared and item.directory.exists():
            print(f"preserved user-added files in: {item.directory}")
        print(f"{item.label}: removed managed files")


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
        description="Install skills and agents for VS Code Copilot and Claude Code, and manage private handoffs.",
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
        "status", help="report installations without writes"
    )
    status_parser.add_argument(
        "skill", nargs="?", help="skill or agent name; omit to list everything known"
    )
    apply_parser = commands.add_parser(
        "install", help="install/update one skill folder or agent"
    )
    apply_parser.add_argument(
        "skill", help="name under .agents/skills/ or .agents/agents/"
    )
    apply_parser.add_argument(
        "--activate", action="store_true", help="confirm user-level file writes"
    )
    remove_parser = commands.add_parser(
        "remove", help="remove one managed skill or agent"
    )
    remove_parser.add_argument(
        "skill", help="installed skill or agent name (source need not exist)"
    )
    remove_parser.add_argument("--confirm-removal", action="store_true")

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
