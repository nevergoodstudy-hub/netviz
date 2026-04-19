# Security Policy

This repository ships the NetViz application from [`netviz/`](netviz).

## Supported Scope

Security fixes are currently focused on the actively maintained NetViz app under `netviz/`.

## Reporting a Vulnerability

Please do not open public issues for security reports.

Use one of these channels instead:

1. GitHub Security Advisories for this repository
2. Direct maintainer contact listed on GitHub

When possible, include:

- a clear description of the issue
- reproduction steps or a proof of concept
- impact assessment
- suggested mitigations if you have them

## Operational Notes

- Sensitive API keys stored through the NetViz admin settings are encrypted at rest.
- A dedicated `SETTINGS_ENCRYPTION_KEY` may be supplied through the environment.
- If that variable is not set, NetViz generates a per-install key file under the app data directory instead of falling back to a shared default secret.

## Response Targets

- Initial acknowledgement within 48 hours
- Triage update within 7 days
- Coordinated fix or mitigation target within 30 days when the report is confirmed
