# Security policy

## Supported version

The latest tagged release is supported.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting for this repository. Please include the affected version, reproduction steps, impact, and any proposed mitigation.

Do not include credentials, private conversation content, or real user goal contracts in a report.

## Trust boundary

Agent Skills and Hermes plugins execute with the same local trust as their host agent. Guided Goal makes no network requests. Hermes stores goal state through its native `GoalManager`; portable hosts execute only in the current session. The installer changes only documented skill and command locations, refuses conflicts by default, and preserves backups when forced. Users should still review source before installing any third-party package.
