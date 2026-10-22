"""Install selected skill folders for VS Code Copilot and Claude Code, plus handoffs."""

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
RUNTIMES = ["copilot", "claude-code"]
RUNTIME_LABEL = "shared"
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


def skills_wiring() -> dict:
    wiring = read_json_object(REPOSITORY_ROOT / "runtimes/skills.json")
    directory = wiring.get("personal_skills_directory")
    if (
        wiring.get("schema_version") != 2
        or wiring.get("runtimes") != RUNTIMES
        or not isinstance(directory, str)
        or not safe_relative(directory)
    ):
        raise WorkbenchError("invalid wiring in runtimes/skills.json")
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
    return home / skills_wiring()["personal_skills_directory"], state_root


def validate_name(name: str) -> None:
    if not SLUG_PATTERN.fullmatch(name):
        raise WorkbenchError("skill name must be a lowercase kebab-case slug")


def manifest_location(state: Path, name: str) -> Path:
    return state / "installations/skills" / f"{name}.json"


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
        or manifest.get("runtime") != RUNTIME_LABEL
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
        manifests = state / "installations/skills"
        reject_symlinks(manifests)
        names = set(sources) | {path.stem for path in manifests.glob("*.json")}
        if not names:
            print("No source skills or managed installations")
        return max(
            (status(home, state_root, item) for item in sorted(names)), default=0
        )
    directory, manifest_path = installation_paths(home, state_root, name)
    manifest = read_manifest(manifest_path, directory)
    prefix = f"Skills / {name}"
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
            "installation requires --activate to confirm user-level file writes"
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
    apply_files(directory, manifest_path, before, after)
    print(f"Skills / {name}: installed at {directory}")


def remove(home: Path, state_root: Path | None, name: str, confirm: bool) -> None:
    if not confirm:
        raise WorkbenchError("removal requires --confirm-removal")
    directory, manifest_path = installation_paths(home, state_root, name)
    manifest = read_manifest(manifest_path, directory)
    if manifest is None:
        raise WorkbenchError(f"no managed installation found for: {name}")
    before = installed_files(directory, manifest)
    apply_files(directory, manifest_path, before, {})
    if directory.exists():
        print(f"preserved user-added files in: {directory}")
    print(f"Skills / {name}: removed managed files")


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
        description="Install skills for VS Code Copilot and Claude Code (one shared folder), and manage private handoffs.",
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
        "skill", nargs="?", help="skill folder name; omit to list all known skills"
    )
    apply_parser = commands.add_parser(
        "install", help="install/update one selected skill folder"
    )
    apply_parser.add_argument("skill", help="folder name under .agents/skills/")
    apply_parser.add_argument(
        "--activate", action="store_true", help="confirm user-level file writes"
    )
    remove_parser = commands.add_parser("remove", help="remove one managed skill")
    remove_parser.add_argument(
        "skill", help="installed skill name (source need not exist)"
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
