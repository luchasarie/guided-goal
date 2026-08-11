# Changelog

All notable changes to this project are documented here.

## [0.2.0] - 2026-08-11

### Added

- Standards-first `guided-goal` Agent Skill shared by every host.
- Codex CLI and Claude Code native skill installations.
- OpenCode command adapter and Pi prompt-template adapter.
- Transactional user/project installer with symlink and copy modes, conflict backups, broken-symlink protection, and multi-target rollback.
- Portable package validator and cross-host packaging tests.

### Changed

- Rebranded the project from a Hermes-only plugin to a universal Guided Goal package.
- Moved the interview and execution contract into one canonical `SKILL.md`.
- Kept Hermes as the native persisted-goal adapter while other hosts use honest bounded in-session execution.

## [0.1.0] - 2026-08-11

### Added

- `/guided-goal` interview command for Hermes CLI sessions.
- Gateway rewrite support for `/guided-goal` on messaging platforms.
- Five-section completion contracts covering objective, success criteria, verification, boundaries, and stop conditions.
- Explicit confirmation gate before native goal activation.
- Numeric attempt/turn cap validation.
- Protection against replacing active or paused goals.
- Structured, fail-closed activation errors.
- Automated coverage for CLI, gateway, parsing, and activation paths.
