---
applyTo: "**/*auth*,**/*security*,**/*token*,**/*payment*,**/*upload*,**/.github/workflows/**"
---

# Security-sensitive code instructions

- Treat all user input, external API responses, uploaded files, webhooks, and tool
  results as untrusted.
- Use server-side authorization, validation, output encoding, and bounded resource use.
- Never log passwords, access tokens, refresh tokens, API keys, card data, or secrets.
- Use secure defaults, least-privilege permissions, and explicit trust boundaries.
- Review CSRF, CORS, SSRF, injection, IDOR/BOLA, XSS, path traversal, file validation,
  replay, and rate limiting as relevant to the changed code.
- Preserve auditability for sensitive state transitions.
- Do not disable security controls to make a test pass; explain and fix the root cause.
