# Contributing

Guided Goal is intentionally narrow. Changes should strengthen the interview-to-contract-to-verification path without duplicating behavior across host adapters.

## Setup

```bash
git clone https://github.com/luchasarie/guided-goal.git
cd guided-goal
python -m pip install -r requirements-dev.txt
python -m pytest --rootdir=tests tests -q
python scripts/validate.py
uvx --from skills-ref==0.1.1 agentskills validate skills/guided-goal
```

## Pull requests

1. Keep the skill and Hermes plugin dependency-free at runtime.
2. Preserve explicit user confirmation before activation.
3. Do not let the interview call tools or begin the requested work.
4. Change behavioral policy only in `skills/guided-goal/SKILL.md`; adapters may only forward invocation context.
5. Keep Hermes tool handlers fail-closed and JSON-returning.
6. Add regression coverage for changed host discovery, adapters, installer, parsing, or activation behavior.
7. Run the full test and validation suite and include the result in the pull request.

Use conventional commit subjects such as `fix: reject duplicate contract sections` or `docs: clarify gateway usage`.

## Security reports

Do not open a public issue for a vulnerability. Follow [SECURITY.md](SECURITY.md).
