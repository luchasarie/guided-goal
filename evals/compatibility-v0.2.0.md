# Compatibility evidence — v0.2.0

Date: 2026-08-11

The release candidate was installed into one disposable Git repository with project-scoped adapters. Each live behavioral smoke used a separate empty subdirectory and this contract:

- create one host-specific proof file with exact bytes `guided-goal-ok\n`;
- create no other file in the working directory;
- verify exact bytes with Python;
- deny network, Git, configuration, and out-of-directory writes;
- stop after two attempts.

The first turn had to present all five contract sections, ask `Activate this goal?`, and leave the proof file absent. A second explicit confirmation had to create only the proof file and report successful verification.

| Host | Version | Discovery / command receipt | First-turn gate | Confirmed mutation | Result |
| --- | --- | --- | --- | --- | --- |
| Hermes Agent | 0.20.0 | Plugin command, tool, and gateway hook loaded in a fresh host process | Covered by plugin tests | Native `GoalManager` activation covered against the pinned host API | Tested |
| Codex CLI | 0.146.1 | `$guided-goal` loaded the project Agent Skill | Five sections, confirmation question, no mutation | Exact proof file; verification exited 0 on attempt 1 | Tested live |
| Claude Code | 2.1.44 | Package paths and skill structure validated against Claude's documented Agent Skills surface | Live turn unavailable because the installed CLI's OAuth credential was expired | Not run | Supported by standard; live smoke pending |
| OpenCode | 1.18.11 | `opencode debug skill` found one canonical skill; `/guided-goal` loaded it through the command shim | Five sections, confirmation question, no mutation | Exact proof file; verification exited 0 on attempt 1 in Build agent | Tested live |
| Pi | 0.77.0 | `/guided-goal` expanded the prompt shim and loaded the canonical skill | Five sections, confirmation question, no tool calls | Exact proof file; verification exited 0 on attempt 1 | Tested live |

Additional deterministic gates:

- 19 Python tests for Hermes behavior, portability, and transactional installation;
- `scripts/validate.py` passed;
- `agentskills validate skills/guided-goal` passed with `skills-ref==0.1.1`;
- isolated user and project installs covered symlink mode, copy mode, idempotency, backup preservation, broken symlinks, and injected multi-target rollback.

A loader receipt is not treated as a behavioral pass. Claude Code remains explicitly below the live-tested tier until a valid authenticated model turn completes the same two-turn fixture.
