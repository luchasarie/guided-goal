from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validator = load_module("guided_goal_validator", ROOT / "scripts" / "validate.py")
installer = load_module("guided_goal_installer", ROOT / "scripts" / "install.py")


def test_portable_package_validation_passes():
    assert validator.validate() == []


def test_canonical_skill_owns_host_neutral_behavior():
    text = (ROOT / "skills/guided-goal/SKILL.md").read_text(encoding="utf-8")
    assert "Hermes native mode" in text
    assert "Portable in-session mode" in text
    assert "exactly one short question" in text
    assert "Activate this goal?" in text
    assert "/home/" not in text


def test_command_adapters_only_forward_to_canonical_skill():
    opencode = (ROOT / "adapters/opencode/commands/guided-goal.md").read_text(
        encoding="utf-8"
    )
    pi = (ROOT / "adapters/pi/prompts/guided-goal.md").read_text(encoding="utf-8")
    for adapter in (opencode, pi):
        assert "Load and follow the `guided-goal` skill" in adapter
        assert "$ARGUMENTS" in adapter
        assert "## Success criteria" not in adapter
    assert "agent: build" in opencode


def test_user_install_all_hosts_is_idempotent(tmp_path: Path):
    targets = installer.user_targets(set(installer.HOSTS), tmp_path)
    written = installer.install(targets, mode="symlink", force=False, dry_run=False)
    assert len(written) == 4
    assert (tmp_path / ".agents/skills/guided-goal/SKILL.md").is_file()
    assert (tmp_path / ".claude/skills/guided-goal/SKILL.md").is_file()
    assert (tmp_path / ".config/opencode/commands/guided-goal.md").is_file()
    assert (tmp_path / ".pi/agent/prompts/guided-goal.md").is_file()
    assert installer.install(targets, mode="symlink", force=False, dry_run=False) == []


def test_project_copy_install_uses_documented_paths(tmp_path: Path):
    targets = installer.project_targets(set(installer.HOSTS), tmp_path)
    installer.install(targets, mode="copy", force=False, dry_run=False)
    assert not (tmp_path / ".agents/skills/guided-goal").is_symlink()
    assert (tmp_path / ".agents/skills/guided-goal/SKILL.md").is_file()
    assert (tmp_path / ".claude/skills/guided-goal/SKILL.md").is_file()
    assert (tmp_path / ".opencode/commands/guided-goal.md").is_file()
    assert (tmp_path / ".pi/prompts/guided-goal.md").is_file()


def test_conflict_requires_force_and_force_preserves_backup(tmp_path: Path):
    destination = tmp_path / ".agents/skills/guided-goal"
    destination.mkdir(parents=True)
    (destination / "old.txt").write_text("old", encoding="utf-8")
    targets = installer.user_targets({"codex"}, tmp_path)

    with pytest.raises(RuntimeError, match="--force"):
        installer.install(targets, mode="copy", force=False, dry_run=False)

    installer.install(targets, mode="copy", force=True, dry_run=False)
    assert (destination / "SKILL.md").is_file()
    backups = list(destination.parent.glob("guided-goal.backup-*"))
    assert len(backups) == 1
    assert (backups[0] / "old.txt").read_text(encoding="utf-8") == "old"


def test_broken_symlink_is_treated_as_a_conflict(tmp_path: Path):
    destination = tmp_path / ".agents/skills/guided-goal"
    destination.parent.mkdir(parents=True)
    destination.symlink_to(tmp_path / "missing")
    targets = installer.user_targets({"codex"}, tmp_path)
    with pytest.raises(RuntimeError, match="--force"):
        installer.install(targets, mode="symlink", force=False, dry_run=False)


def test_multi_target_failure_rolls_back_prior_replacement(tmp_path: Path, monkeypatch):
    source_a = tmp_path / "source-a.txt"
    source_b = tmp_path / "source-b.txt"
    source_a.write_text("new-a", encoding="utf-8")
    source_b.write_text("new-b", encoding="utf-8")
    destination_a = tmp_path / "dest-a.txt"
    destination_b = tmp_path / "dest-b.txt"
    destination_a.write_text("old-a", encoding="utf-8")
    targets = [
        installer.Target(source_a, destination_a, "A"),
        installer.Target(source_b, destination_b, "B"),
    ]

    real_create = installer.create_staging
    calls = 0

    def fail_second(source, staging, mode):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected staging failure")
        real_create(source, staging, mode)

    monkeypatch.setattr(installer, "create_staging", fail_second)
    with pytest.raises(OSError, match="injected"):
        installer.install(targets, mode="copy", force=True, dry_run=False)

    assert destination_a.read_text(encoding="utf-8") == "old-a"
    assert not destination_b.exists()
