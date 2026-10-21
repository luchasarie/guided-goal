<div align="center">
  <img src="assets/hero.svg" alt="Guided Goal turns rough intent into a verified completion contract for multiple AI coding agents" width="100%">

  # Guided Goal

  **Turn “make this better” into a goal an agent can actually finish.**

  [![Tests](https://github.com/luchasarie/guided-goal/actions/workflows/test.yml/badge.svg)](https://github.com/luchasarie/guided-goal/actions/workflows/test.yml)
  [![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-8b5cf6.svg)](https://agentskills.io/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-22c55e.svg)](LICENSE)
  [![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776ab.svg)](https://www.python.org/)
</div>

---

Rough prompts are easy to start and hard to finish. Guided Goal conducts a short interview, turns the answers into a deterministic completion contract, asks for explicit confirmation, and then executes under a finite attempt cap.

It uses one standards-first Agent Skill across **Hermes Agent, Codex CLI, Claude Code, OpenCode, and Pi**. The host adapters only handle discovery and invocation; the behavioral contract is not copied into five prompt forks.

```text
/guided-goal improve our flaky test situation

Agent: Which test suite should define success, and what failure rate is acceptable?
You: The API integration suite; zero flakes across 10 consecutive runs.

Agent: [presents Objective, Success criteria, Verification,
        Boundaries, and Stop conditions]
       Activate this goal?
You: Yes.

Agent: Goal activated. Work begins immediately.
```

## See it in 30 seconds

https://github.com/user-attachments/assets/2d00f46a-8172-4d50-b7a6-f9886b1dff75

Can't see the video? [Watch the 30-second demo](https://github.com/user-attachments/assets/2d00f46a-8172-4d50-b7a6-f9886b1dff75).

## What it fixes

Without a contract, an agent can polish forever, stop after a plausible-looking change, or quietly broaden scope. Guided Goal makes five things explicit before work begins:

1. **Objective** — one bounded outcome.
2. **Success criteria** — binary or deterministic completion conditions.
3. **Verification** — exact commands, checks, artifacts, or observable evidence.
4. **Boundaries** — allowed scope and an explicit denylist.
5. **Stop conditions** — a numeric attempt cap plus escalation rules.

## Compatibility

| Host | Invoke | Release evidence | Execution mode |
| --- | --- | --- | --- |
| **Hermes Agent 0.20.0** | `/guided-goal [rough goal]` | Host API + plugin tests | Persisted native `GoalManager` + goal judge |
| **Codex CLI 0.146.1** | `$guided-goal [rough goal]` | Live two-turn mutation smoke passed | Bounded execution in the current session |
| **Claude Code 2.1.44** | `/guided-goal [rough goal]` | Agent Skills package validated; live model smoke pending | Bounded execution in the current session |
| **OpenCode 1.18.11** | `/guided-goal [rough goal]` | Live two-turn mutation smoke passed in Build agent | Bounded execution in the current session |
| **Pi 0.77.0** | `/guided-goal [rough goal]` or `/skill:guided-goal [rough goal]` | Live two-turn mutation smoke passed | Bounded execution in the current session |

Hermes is the only adapter with a native persisted goal loop. The portable adapters never pretend that a host has background persistence or a native goal judge when it does not.

OpenCode must remain in its execution-enabled **Build** agent when the contract is confirmed. The command shim selects `build` for the interview turn; non-interactive continuations must also pass `--agent build`.

See the full [v0.2.0 compatibility evidence](evals/compatibility-v0.2.0.md), including the exact fixture and the honest Claude Code authentication boundary.

## Install

### Hermes Agent

Hermes needs native `/goal` support and the general plugin API. The adapter is tested against Hermes Agent `0.20.0`.

```bash
hermes plugins install luchasarie/guided-goal --enable
```

Start a new session, then run:

```text
/guided-goal ship the parser fix without breaking the public API
```

### Codex, Claude Code, OpenCode, and Pi

Clone once, then install the selected adapters:

```bash
git clone https://github.com/luchasarie/guided-goal.git
cd guided-goal
python3 scripts/install.py --host all
```

Install only selected hosts by repeating `--host`:

```bash
python3 scripts/install.py --host codex --host claude
python3 scripts/install.py --host opencode --host pi
```

The user-scope installer creates symlinks to one canonical skill:

- `~/.agents/skills/guided-goal` for Codex, OpenCode, and Pi;
- `~/.claude/skills/guided-goal` for Claude Code;
- `~/.config/opencode/commands/guided-goal.md` for the OpenCode slash alias;
- `~/.pi/agent/prompts/guided-goal.md` for the Pi slash alias.

Use copies instead of symlinks when needed:

```bash
python3 scripts/install.py --host all --copy
```

Install into a repository instead of your user profile:

```bash
python3 scripts/install.py --host all --project .
```

The installer refuses conflicts by default. `--force` preserves every replaced target as a timestamped sibling backup. All destinations are preflighted and a multi-target failure rolls back already-applied replacements.

## Usage

Start with a rough objective using the invocation syntax for your host. During the interview, answer normally. Guided Goal asks one question at a time and does **not** inspect files, call tools, or begin work before confirmation.

When the contract is ready, the agent shows:

```markdown
## Objective
...

## Success criteria
...

## Verification
...

## Boundaries
...

## Stop conditions
...
```

Then it asks:

```text
Activate this goal?
```

A clear yes activates the presented contract. Changing its scope or proof invalidates the old confirmation and requires the revised contract to be confirmed again.

## One core, thin adapters

```text
skills/guided-goal/SKILL.md          ← canonical behavior
              │
              ├── Hermes plugin      ← slash + gateway + native GoalManager
              ├── Codex              ← native Agent Skill discovery
              ├── Claude Code        ← native Agent Skill discovery
              ├── OpenCode command   ← forwards $ARGUMENTS to the skill
              └── Pi prompt template ← forwards $ARGUMENTS to the skill
```

Repository layout:

```text
.
├── skills/guided-goal/              # standards-first source of truth
├── adapters/opencode/               # slash-command ergonomics only
├── adapters/pi/                     # slash-command ergonomics only
├── scripts/install.py               # transactional multi-host installer
├── scripts/validate.py              # portable package validation
├── __init__.py                      # Hermes adapter
├── plugin.yaml                      # Hermes manifest
└── tests/                           # plugin, portability, and installer coverage
```

Behavioral changes belong in [`skills/guided-goal/SKILL.md`](skills/guided-goal/SKILL.md), never in copied host prompts.

## Safety model

Guided Goal intentionally separates **clarification** from **execution**:

- no tools run during the interview;
- activation requires explicit confirmation;
- material contract changes require fresh confirmation;
- verification and scope boundaries are mandatory;
- every goal has a finite attempt cap from 1 to 100;
- portable adapters respect each host's normal permissions and approvals;
- the installer never reads or modifies memories, sessions, credentials, provider settings, or instruction files;
- no API keys, telemetry, network services, or runtime dependencies are added.

Installed skills and plugins run with the same local trust as their host agent. Review third-party source before installing it.

## Development

```bash
git clone https://github.com/luchasarie/guided-goal.git
cd guided-goal
python -m pip install -r requirements-dev.txt
python -m pytest --rootdir=tests tests -q
python scripts/validate.py
uvx --from skills-ref==0.1.1 agentskills validate skills/guided-goal
```

The test suite covers Hermes CLI and gateway behavior, contract parsing and activation, portable frontmatter, thin-adapter invariants, user/project installs, symlink and copy modes, idempotency, conflict backups, broken symlinks, and multi-target rollback.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow and [the host invocation reference](skills/guided-goal/references/host-invocation.md) for adapter boundaries.

## Project status

`v0.2.1` is the universal release: one completion-contract skill, five host integrations, no duplicated behavioral prompts, and fail-closed installer source preflight.

## License

[MIT](LICENSE) © 2026 Luchas Arie.
