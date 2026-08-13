# Security Policy

## Supported Versions

Security fixes are published on the current `main` branch and included in the
next release tag. Client deployments should upgrade to the latest compatible
release after reviewing migration and deployment notes.

## Reporting A Vulnerability

Do not open a public issue for a suspected vulnerability, secret exposure,
workspace isolation failure, authorization bypass, or remote code execution.

Use GitHub's private vulnerability reporting for this repository when it is
enabled. Repository maintainers must enable that GitHub setting before public
release. If private reporting is unavailable, contact the repository owner
through a private channel.

Include the affected version or commit, reproduction steps, impact, and any
safe proof of concept. Never include production credentials, tokens, personal
data, or customer data in the report.

## Response Expectations

Maintainers will acknowledge valid reports privately, assess impact, prepare a
fix and regression test, then publish an advisory after a patch is available.
Critical issues involving tenancy, authorization, or secrets take priority over
ordinary feature work.
