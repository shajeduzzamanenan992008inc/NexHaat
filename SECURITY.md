# Security Policy

## Reporting a vulnerability

Please do not disclose suspected vulnerabilities in public issues, discussions,
screenshots, or social posts.

Use GitHub's **Private vulnerability reporting** feature on the NexHaat repository
when it is enabled. If it is unavailable, contact the repository maintainers privately
through a verified private channel shown on the repository owner's GitHub profile.

Include, where safe:
- Affected version/commit and component.
- Preconditions and a concise reproduction procedure.
- Expected versus observed behavior.
- Potential impact and affected data boundary.
- A suggested mitigation, if known.

Do not include real customer data, payment details, credentials, access tokens, or
other people's private information.

## Safe-harbor expectations

Security testing must be authorized and non-destructive. Do not access or modify
another user's data, disrupt service, perform denial-of-service testing, or run
automated scans against production without explicit permission.

## Response and remediation

The maintainers will assess reports, validate impact, prioritize remediation, and
coordinate disclosure. No response-time or remediation-time SLA is promised by this
file. Security fixes should be tested and released through the repository's review
and deployment process.

Operational guidance: see [the security incident runbook](.github/runbooks/security-incident.md) and [hardening guide](.github/SECURITY-HARDENING-GUIDE.md).
