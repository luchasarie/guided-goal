from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

PLUGIN_DIR = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("guided_goal_plugin", PLUGIN_DIR / "__init__.py")
plugin = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(plugin)


CONTRACT = """## Objective
Ship the parser fix without changing the public API.

## Success criteria
- Parser regression test passes.
- Existing test suite passes.

## Verification
Run `pytest tests/test_parser.py` and `pytest` with exit code 0.

## Boundaries
Only parser.py and parser tests. Denylist: deployment, credentials, and public API changes.

## Stop conditions
Stop after 8 attempts. Escalate if the public API must change.
"""


class FakeGoalManager:
    def __init__(self, status="cleared"):
        self.state = SimpleNamespace(status=status) if status else None
        self.set_calls = []

    def has_goal(self):
        return self.state is not None and self.state.status != "cleared"

    def set(self, goal, *, max_turns=None, contract=None):
        self.set_calls.append((goal, max_turns, contract))
        self.state = SimpleNamespace(goal=goal, status="active", max_turns=max_turns, contract=contract)
        return self.state


class FakeContext:
    def __init__(self, manager=None, injection_ok=True):
        cli = SimpleNamespace(_get_goal_manager=lambda: manager) if manager is not None else None
        self._manager = SimpleNamespace(_cli_ref=cli)
        self.injection_ok = injection_ok
        self.injected = []
        self.commands = {}
        self.tools = {}
        self.hooks = {}

    def inject_message(self, content, role="user"):
        self.injected.append((content, role))
        return self.injection_ok

    def register_command(self, name, handler, **kwargs):
        self.commands[name] = (handler, kwargs)

    def register_tool(self, name, handler, **kwargs):
        self.tools[name] = (handler, kwargs)

    def register_hook(self, name, handler):
        self.hooks[name] = handler


@pytest.fixture(autouse=True)
def reset_context():
    plugin._CTX = None
    yield
    plugin._CTX = None


def test_registers_only_command_tool_and_gateway_hook():
    ctx = FakeContext()
    plugin.register(ctx)
    assert set(ctx.commands) == {"guided-goal"}
    assert set(ctx.tools) == {"guided_goal_activate"}
    assert set(ctx.hooks) == {"pre_gateway_dispatch"}


def test_bare_command_injects_interview_without_rough_goal():
    ctx = FakeContext(FakeGoalManager())
    plugin.register(ctx)
    result = plugin._guided_goal_command("")
    assert result == ""
    assert len(ctx.injected) == 1
    kickoff = ctx.injected[0][0]
    assert "Ask exactly one short question" in kickoff
    assert "<rough-goal>" not in kickoff


def test_command_preserves_rough_goal():
    ctx = FakeContext(FakeGoalManager())
    plugin.register(ctx)
    plugin._guided_goal_command("automate flaky test triage")
    kickoff = ctx.injected[0][0]
    assert "<rough-goal>\nautomate flaky test triage\n</rough-goal>" in kickoff


def test_command_blocks_active_or_paused_goal():
    for status in ("active", "paused"):
        ctx = FakeContext(FakeGoalManager(status))
        plugin.register(ctx)
        result = plugin._guided_goal_command("replace it")
        assert "already active or paused" in result
        assert ctx.injected == []


def test_gateway_hook_rewrites_command_to_interview():
    event = SimpleNamespace(text="/guided-goal ship it", get_text=lambda: event.text)
    plugin._pre_gateway_dispatch(event=event)
    assert not event.text.startswith("/")
    assert "<rough-goal>\nship it\n</rough-goal>" in event.text


def test_gateway_hook_ignores_normal_messages():
    event = SimpleNamespace(text="hello", get_text=lambda: event.text)
    plugin._pre_gateway_dispatch(event=event)
    assert event.text == "hello"


def test_activation_maps_contract_and_enforces_cap():
    manager = FakeGoalManager()
    ctx = FakeContext(manager)
    plugin.register(ctx)
    result = json.loads(plugin._activate_goal({"objective": CONTRACT}))
    assert result["ok"] is True
    assert result["runtime"] == "cli"
    assert result["max_turns"] == 8
    goal, cap, contract = manager.set_calls[0]
    assert goal == "Ship the parser fix without changing the public API."
    assert cap == 8
    assert "Parser regression test passes" in contract.outcome
    assert "pytest tests/test_parser.py" in contract.verification
    assert "Denylist" in contract.boundaries
    assert "Stop after 8 attempts" in contract.stop_when


def test_activation_rejects_missing_section_or_attempt_cap():
    missing = CONTRACT.replace("## Verification", "## Checks")
    result = json.loads(plugin._activate_goal({"objective": missing}))
    assert result["ok"] is False
    assert "## Verification" in result["error"]

    no_cap = CONTRACT.replace("Stop after 8 attempts.", "Stop if blocked; file size limit 20 MB.")
    result = json.loads(plugin._activate_goal({"objective": no_cap}))
    assert result["ok"] is False
    assert "numeric attempt/turn cap" in result["error"]


def test_activation_refuses_to_replace_active_goal():
    manager = FakeGoalManager("active")
    ctx = FakeContext(manager)
    plugin.register(ctx)
    result = json.loads(plugin._activate_goal({"objective": CONTRACT}))
    assert result["ok"] is False
    assert manager.set_calls == []


def test_gateway_activation_uses_supplied_session_id(monkeypatch):
    from hermes_cli import goals

    manager = FakeGoalManager()
    seen = {}

    def factory(session_id):
        seen["session_id"] = session_id
        return manager

    monkeypatch.setattr(goals, "GoalManager", factory)
    ctx = FakeContext(manager=None, injection_ok=False)
    plugin.register(ctx)
    result = json.loads(
        plugin._activate_goal({"objective": CONTRACT}, session_id="discord:channel:thread")
    )
    assert result["ok"] is True
    assert result["runtime"] == "gateway"
    assert seen["session_id"] == "discord:channel:thread"
    assert manager.set_calls[0][1] == 8
