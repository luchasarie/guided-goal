#!/usr/bin/env python3
"""Static validation for the portable Guided Goal package."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "guided-goal"
SKILL = SKILL_DIR / "SKILL.md"
REQUIRED = {"name", "description"}
ALLOWED = {"name", "description", "license", "compatibility", "metadata"}


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    try:
        frontmatter = text.split("---\n", 2)[1]
    except IndexError as exc:
        raise ValueError("SKILL.md frontmatter is not closed") from exc
    fields: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if not line or line.startswith(" "):
            continue
        if ":" not in line:
            raise ValueError(f"Invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def validate() -> list[str]:
    errors: list[str] = []
    text = SKILL.read_text(encoding="utf-8")
    try:
        fields = parse_frontmatter(text)
    except ValueError as exc:
        return [str(exc)]

    missing = REQUIRED - fields.keys()
    unknown = fields.keys() - ALLOWED
    if missing:
        errors.append(f"missing frontmatter fields: {', '.join(sorted(missing))}")
    if unknown:
        errors.append(f"non-portable frontmatter fields: {', '.join(sorted(unknown))}")

    name = fields.get("name", "").strip('"\'')
    description = fields.get("description", "").strip('"\'')
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        errors.append("skill name does not match the Agent Skills name grammar")
    if name != SKILL_DIR.name:
        errors.append("skill name must match its directory")
    if not 1 <= len(description) <= 1024:
        errors.append("description must contain 1-1024 characters")

    required_phrases = (
        "## Objective",
        "## Success criteria",
        "## Verification",
        "## Boundaries",
        "## Stop conditions",
        "Activate this goal?",
        "guided_goal_activate",
        "Portable in-session mode",
    )
    for phrase in required_phrases:
        if phrase not in text:
            errors.append(f"canonical behavior missing: {phrase}")

    for match in re.finditer(r"\[[^\]]+\]\((?!https?://|#)([^)]+)\)", text):
        target = (SKILL_DIR / match.group(1)).resolve()
        if not target.exists():
            errors.append(f"broken relative reference: {match.group(1)}")

    committed_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in ROOT.rglob("*")
        if path.is_file()
        and not {".git", ".pytest_cache", "__pycache__", ".ci-hermes"}.intersection(path.parts)
    )
    markers = (
        "/home/" + "luchasarie",
        "Luchas Arie" + " - The Magma Knight",
        "FAKE_TOKEN_CANARY" + "_DO_NOT_ECHO",
    )
    for marker in markers:
        if marker in committed_text:
            errors.append(f"private or secret-bearing marker found: {marker}")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Portable package validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
