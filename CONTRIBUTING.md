# Contributing

Guided Goal is intentionally narrow. Changes should strengthen the interview-to-contract path without creating a second goal runtime beside Hermes native `/goal` mode.

## Setup

```bash
git clone https://github.com/luchasarie/hermes-guided-goal.git
cd hermes-guided-goal
python -m pip install -r requirements-dev.txt
python -m pytest --rootdir=tests tests -q
```

## Pull requests

1. Keep the plugin dependency-free at runtime.
2. Preserve explicit user confirmation before activation.
3. Do not let the interview call tools or begin the requested work.
4. Keep tool handlers fail-closed and JSON-returning.
5. Add regression coverage for changed CLI, gateway, parsing, or activation behavior.
6. Run the full test suite and include the result in the pull request.

Use conventional commit subjects such as `fix: reject duplicate contract sections` or `docs: clarify gateway usage`.

## Security reports

Do not open a public issue for a vulnerability. Follow [SECURITY.md](SECURITY.md).
