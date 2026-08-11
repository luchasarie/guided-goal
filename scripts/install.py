#!/usr/bin/env python3
"""Install the canonical Guided Goal skill and thin host adapters safely."""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
SKILL_SOURCE = ROOT / "skills" / "guided-goal"
OPENCODE_COMMAND = ROOT / "adapters" / "opencode" / "commands" / "guided-goal.md"
PI_PROMPT = ROOT / "adapters" / "pi" / "prompts" / "guided-goal.md"
HOSTS = ("codex", "claude", "opencode", "pi")


@dataclass(frozen=True)
class Target:
    source: Path
    destination: Path
    label: str


def lexical_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def same_content(source: Path, destination: Path) -> bool:
    if destination.is_symlink():
        try:
            return destination.resolve(strict=False) == source.resolve()
        except OSError:
            return False
    if source.is_file() and destination.is_file():
        return filecmp.cmp(source, destination, shallow=False)
    if source.is_dir() and destination.is_dir():
        source_files = sorted(p.relative_to(source) for p in source.rglob("*") if p.is_file())
        destination_files = sorted(
            p.relative_to(destination) for p in destination.rglob("*") if p.is_file()
        )
        return source_files == destination_files and all(
            filecmp.cmp(source / rel, destination / rel, shallow=False) for rel in source_files
        )
    return False


def user_targets(hosts: set[str], home: Path) -> list[Target]:
    targets: list[Target] = []
    if hosts & {"codex", "opencode", "pi"}:
        targets.append(Target(SKILL_SOURCE, home / ".agents/skills/guided-goal", "shared skill"))
    if "claude" in hosts:
        targets.append(Target(SKILL_SOURCE, home / ".claude/skills/guided-goal", "Claude skill"))
    if "opencode" in hosts:
        targets.append(
            Target(
                OPENCODE_COMMAND,
                home / ".config/opencode/commands/guided-goal.md",
                "OpenCode command",
            )
        )
    if "pi" in hosts:
        targets.append(
            Target(PI_PROMPT, home / ".pi/agent/prompts/guided-goal.md", "Pi prompt template")
        )
    return targets


def project_targets(hosts: set[str], project: Path) -> list[Target]:
    targets: list[Target] = []
    if hosts & {"codex", "opencode", "pi"}:
        targets.append(Target(SKILL_SOURCE, project / ".agents/skills/guided-goal", "shared skill"))
    if "claude" in hosts:
        targets.append(Target(SKILL_SOURCE, project / ".claude/skills/guided-goal", "Claude skill"))
    if "opencode" in hosts:
        targets.append(
            Target(
                OPENCODE_COMMAND,
                project / ".opencode/commands/guided-goal.md",
                "OpenCode command",
            )
        )
    if "pi" in hosts:
        targets.append(Target(PI_PROMPT, project / ".pi/prompts/guided-goal.md", "Pi prompt template"))
    return targets


def create_staging(source: Path, staging: Path, mode: str) -> None:
    if mode == "symlink":
        staging.symlink_to(source.resolve(), target_is_directory=source.is_dir())
    elif source.is_dir():
        shutil.copytree(source, staging)
    else:
        shutil.copy2(source, staging)


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def install(targets: list[Target], *, mode: str, force: bool, dry_run: bool) -> list[Path]:
    pending: list[Target] = []
    for target in targets:
        if same_content(target.source, target.destination):
            print(f"OK   {target.label}: {target.destination}")
            continue
        if lexical_exists(target.destination) and not force:
            raise RuntimeError(
                f"Refusing to replace {target.destination}; rerun with --force to preserve a backup."
            )
        pending.append(target)

    for target in pending:
        action = "replace" if lexical_exists(target.destination) else "install"
        print(f"{action.upper():7} {target.label}: {target.destination} <- {target.source}")
    if dry_run or not pending:
        return []

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    committed: list[tuple[Target, Path | None]] = []
    staging_paths: list[Path] = []
    try:
        for target in pending:
            target.destination.parent.mkdir(parents=True, exist_ok=True)
            staging = target.destination.with_name(f".{target.destination.name}.staging-{uuid4().hex}")
            staging_paths.append(staging)
            create_staging(target.source, staging, mode)

            backup: Path | None = None
            if lexical_exists(target.destination):
                backup = target.destination.with_name(
                    f"{target.destination.name}.backup-{timestamp}-{uuid4().hex[:8]}"
                )
                target.destination.rename(backup)
            try:
                staging.rename(target.destination)
            except Exception:
                if backup is not None and not lexical_exists(target.destination):
                    backup.rename(target.destination)
                raise
            committed.append((target, backup))

        for _target, backup in committed:
            if backup is not None:
                print(f"BACKUP preserved: {backup}")
        return [target.destination for target, _backup in committed]
    except Exception:
        for target, backup in reversed(committed):
            remove_path(target.destination)
            if backup is not None and lexical_exists(backup):
                backup.rename(target.destination)
        raise
    finally:
        for staging in staging_paths:
            remove_path(staging)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host",
        action="append",
        choices=(*HOSTS, "all"),
        required=True,
        help="Target host; repeat or use all",
    )
    parser.add_argument("--project", type=Path, help="Install into this project instead of user scope")
    parser.add_argument("--home", type=Path, help="Override the user home for isolated testing")
    parser.add_argument("--copy", action="store_true", help="Copy files instead of creating symlinks")
    parser.add_argument("--force", action="store_true", help="Replace conflicts and preserve backups")
    parser.add_argument("--dry-run", action="store_true", help="Display mutations without writing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    hosts: set[str] = set(HOSTS) if "all" in args.host else set(args.host)
    mode = "copy" if args.copy else "symlink"
    try:
        if args.project:
            targets = project_targets(hosts, args.project.expanduser().resolve())
        else:
            home = (args.home or Path.home()).expanduser().resolve()
            targets = user_targets(hosts, home)
        install(targets, mode=mode, force=args.force, dry_run=args.dry_run)
    except (OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("Guided Goal installation complete." if not args.dry_run else "Dry run complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
