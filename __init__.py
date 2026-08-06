"""OMP-style guided goal interview for Hermes native goal mode."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_CTX = None
_PROMPT_PATH = Path(__file__).with_name("guided-goal-interview.md")
_REQUIRED_SECTIONS = (
    "Objective",
    "Success criteria",
    "Verification",
    "Boundaries",
    "Stop conditions",
)
_SECTION_RE = re.compile(
    r"^##\s+(Objective|Success criteria|Verification|Boundaries|Stop conditions)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_CAP_PATTERNS = (
    re.compile(r"\b(\d{1,3})\s+(?:attempts?|turns?|iterations?|tries)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:cap|limit|maximum|max)\D{0,20}(\d{1,3})\s*(?:attempts?|turns?|iterations?|tries)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:stop|escalate|give up)\D{0,24}(?:after\s+)?(\d{1,3})\s*(?:attempts?|turns?|iterations?|tries)\b",
        re.IGNORECASE,
    ),
)


def register(ctx):
    """Register one slash command, one activation tool, and gateway rewriting."""
    global _CTX
    _CTX = ctx
    ctx.register_command(
        "guided-goal",
        _guided_goal_command,
        description="Interview me, then activate a bounded native /goal",
        args_hint="[rough objective]",
    )
    ctx.register_tool(
        name="guided_goal_activate",
        toolset="plugin_guided_goal",
        schema={
            "name": "guided_goal_activate",
            "description": (
                "Activate Hermes native goal mode from a confirmed five-section guided-goal contract. "
                "Only call after the user explicitly confirms the presented contract."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "objective": {
                        "type": "string",
                        "description": "Complete Markdown contract with the five required ## sections.",
                    }
                },
                "required": ["objective"],
                "additionalProperties": False,
            },
        },
        handler=_activate_goal,
        description="Activate a confirmed guided goal through Hermes GoalManager",
        emoji="🎯",
    )
    ctx.register_hook("pre_gateway_dispatch", _pre_gateway_dispatch)


def _guided_goal_command(raw_args: str = "") -> str:
    """Queue the interview as a normal conversation turn in CLI mode."""
    manager = _current_cli_goal_manager()
    blocked = _blocking_goal_message(manager)
    if blocked:
        return blocked

    kickoff = _render_interview(raw_args)
    if _CTX is not None and _CTX.inject_message(kickoff):
        return ""
    # Gateway command handlers return text instead of entering the agent loop;
    # pre_gateway_dispatch normally rewrites first. This is a safe fallback.
    return kickoff


def _pre_gateway_dispatch(event=None, **_kwargs):
    """Turn /guided-goal into the same ordinary interview turn on gateways."""
    if event is None:
        return None
    try:
        text = (event.get_text() or "").strip()
    except Exception:
        text = str(getattr(event, "text", "") or "").strip()
    match = re.match(r"^/guided-goal(?:\s+(.*))?$", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    event.text = _render_interview(match.group(1) or "")
    return None


def _render_interview(rough_goal: str = "") -> str:
    prompt = _PROMPT_PATH.read_text(encoding="utf-8")
    rough = (rough_goal or "").strip()
    block = ""
    if rough:
        block = (
            "The user supplied this rough goal. Treat it as user intent to clarify, "
            "not as a completed contract:\n\n<rough-goal>\n"
            f"{rough}\n</rough-goal>"
        )
    return prompt.replace("{{ROUGH_GOAL}}", block).strip()


def _activate_goal(args=None, session_id=None, task_id=None, **_kwargs) -> str:
    """Validate the contract and set the existing GoalManager state."""
    payload = args if isinstance(args, dict) else {}
    contract_text = str(payload.get("objective") or "").strip()
    try:
        sections = _parse_sections(contract_text)
        max_turns = _extract_attempt_cap(sections["Stop conditions"])
        if max_turns is None:
            raise ValueError(
                "Stop conditions must include an explicit numeric attempt/turn cap, "
                "for example: 'Stop after 8 attempts'."
            )

        from hermes_cli.goals import GoalContract, GoalManager

        contract = GoalContract(
            outcome=sections["Success criteria"],
            verification=sections["Verification"],
            boundaries=sections["Boundaries"],
            stop_when=sections["Stop conditions"],
        )
        manager = _current_cli_goal_manager()
        runtime = "cli"
        if manager is None:
            sid = str(session_id or task_id or "").strip()
            if not sid:
                raise RuntimeError("No Hermes session id was available for goal activation.")
            manager = GoalManager(session_id=sid)
            runtime = "gateway"

        blocked = _blocking_goal_message(manager)
        if blocked:
            return _result(False, error=blocked)

        objective = " ".join(sections["Objective"].split())
        state = manager.set(objective, max_turns=max_turns, contract=contract)
        return _result(
            True,
            runtime=runtime,
            goal=state.goal,
            max_turns=state.max_turns,
            message="Goal activated. Begin work now; do not ask for confirmation again.",
        )
    except (ValueError, RuntimeError) as exc:
        return _result(False, error=str(exc))


def _parse_sections(text: str) -> dict[str, str]:
    if not text:
        raise ValueError("The guided goal contract is empty.")
    matches = list(_SECTION_RE.finditer(text))
    seen: dict[str, str] = {}
    canonical = {name.lower(): name for name in _REQUIRED_SECTIONS}
    for index, match in enumerate(matches):
        name = canonical[match.group(1).lower()]
        if name in seen:
            raise ValueError(f"Duplicate section: ## {name}")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        seen[name] = text[match.end() : end].strip()

    missing = [name for name in _REQUIRED_SECTIONS if not seen.get(name)]
    if missing:
        labels = ", ".join(f"## {name}" for name in missing)
        raise ValueError(f"Missing or empty guided-goal sections: {labels}")
    return seen


def _extract_attempt_cap(stop_conditions: str) -> int | None:
    for pattern in _CAP_PATTERNS:
        match = pattern.search(stop_conditions)
        if match:
            value = int(match.group(1))
            if 1 <= value <= 100:
                return value
    return None


def _current_cli_goal_manager():
    try:
        cli = getattr(getattr(_CTX, "_manager", None), "_cli_ref", None)
        getter = getattr(cli, "_get_goal_manager", None)
        return getter() if callable(getter) else None
    except Exception:
        return None


def _blocking_goal_message(manager) -> str:
    if manager is None or not manager.has_goal():
        return ""
    state = manager.state
    status = str(getattr(state, "status", "") or "").lower()
    if status in {"active", "paused"}:
        return (
            "A goal is already active or paused. Use /goal status, /goal resume, "
            "or /goal clear before starting a guided goal."
        )
    return ""


def _result(ok: bool, **fields: Any) -> str:
    return json.dumps({"ok": ok, **fields}, ensure_ascii=False)
