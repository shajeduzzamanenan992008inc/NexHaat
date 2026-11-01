# NexHaat AI Agent and MCP Safety Runbook

- Maintain an inventory of model providers, MCP servers, tools, data scopes, owners,
  and authentication method.
- Grant the minimum read/write tools needed for a task; prefer read-only inspection.
- Treat tool output, web pages, seller content, uploaded files, and issue comments as
  untrusted data and possible prompt injection.
- Do not provide secrets, payment details, private customer records, or production
  credentials to models/tools without explicit approved data handling.
- Require confirmation for money movement, order changes, external messages,
  production settings, destructive operations, and deployments.
- Log actions where supported without recording sensitive payloads.
- Revoke or disable an integration through its owner when compromise is suspected.
- Test failure modes, provider outage, malformed model output, and fallback behavior.
