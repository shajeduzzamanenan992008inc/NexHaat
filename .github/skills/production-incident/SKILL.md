---
name: production-incident
description: Triage a NexHaat production incident safely and preserve evidence.
disable-model-invocation: true
---
Triage the supplied NexHaat incident.

First establish impact, affected journeys, time window, current deployment SHA,
recent changes, observed symptoms, and available logs/metrics. Separate customer
impact from technical symptoms. Protect customer data and credentials.

Recommend containment before speculative repair. Do not run destructive commands,
change production settings, rotate credentials, restore backups, or deploy fixes
without explicit authorization. Preserve evidence and provide a rollback decision
tree, communication update, owner, and verification checklist.
