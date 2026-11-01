---
name: repository-deep-audit
description: Evidence-first full NexHaat repository audit using REA and specialist agents.
disable-model-invocation: true
---
Perform a read-only, evidence-first NexHaat repository audit.

1. Confirm repository root, branch, working tree, and instruction files.
2. Ask REA to map the actual architecture and features; verify important claims in source.
3. Inventory apps, packages, lockfiles, database models/migrations, APIs, tests,
   workflows, deployment files, security controls, and MCP integrations.
4. Map critical customer, seller, admin, payment, order, and inventory journeys.
5. Identify blockers, security risks, architectural risks, missing tests, and drift.
6. Do not edit files or run destructive commands.

Return a prioritized report with evidence paths, confidence, dependencies, quick wins,
high-risk work, and a phased implementation plan. Separate confirmed facts from gaps.
