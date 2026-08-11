# Security policy

## Supported version

The latest tagged release is supported.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting for this repository. Please include the affected version, reproduction steps, impact, and any proposed mitigation.

Do not include credentials, private conversation content, or real user goal contracts in a report.

## Trust boundary

Hermes plugins execute with the same local trust as Hermes Agent. Guided Goal itself makes no network requests and stores goal state only through Hermes native `GoalManager`, but users should still review source code before enabling any third-party plugin.
