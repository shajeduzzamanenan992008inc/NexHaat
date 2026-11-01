---
name: threat-model-change
description: Threat-model a NexHaat feature or pull request before implementation.
disable-model-invocation: true
---
Create a focused threat model for the specified NexHaat change.

Identify assets, actors, trust boundaries, entry points, data flows, privileged
operations, abuse cases, and security assumptions. Cover relevant STRIDE-style
threat categories, tenant isolation, sensitive data exposure, payment/order integrity,
webhook replay, prompt injection, and MCP/tool misuse where applicable.

For each finding provide severity, confidence, evidence path, exploit preconditions,
impact, and smallest safe mitigation. Add negative tests and residual risks.
Do not claim exploitability without evidence and do not modify code in a review-only task.
