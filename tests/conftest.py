"""Minimal host API shim for standalone unit-test environments."""

from __future__ import annotations

import sys
import importlib
from dataclasses import dataclass
from types import ModuleType

try:
    importlib.import_module("hermes_cli.goals")
except ModuleNotFoundError:
    hermes_cli = ModuleType("hermes_cli")
    hermes_cli.__path__ = []
    goals = ModuleType("hermes_cli.goals")

    @dataclass
    class GoalContract:
        outcome: str = ""
        verification: str = ""
        constraints: str = ""
        boundaries: str = ""
        stop_when: str = ""

    class GoalManager:
        def __init__(self, session_id: str):
            self.session_id = session_id

    setattr(goals, "GoalContract", GoalContract)
    setattr(goals, "GoalManager", GoalManager)
    setattr(hermes_cli, "goals", goals)
    sys.modules["hermes_cli"] = hermes_cli
    sys.modules["hermes_cli.goals"] = goals
