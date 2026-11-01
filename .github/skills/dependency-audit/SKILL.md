---
name: dependency-audit
description: Full evidence-based dependency and software supply-chain audit.
disable-model-invocation: true
---
Use Dependency Guardian for a read-only NexHaat dependency audit.

Inventory actual manifests and lockfiles, direct/transitive dependencies, action
references, container files when present, license data, advisories, release health,
and update compatibility. Evaluate exploitability and the business-critical paths
affected. Do not invent CVEs or versions.

Return a prioritized dependency report, safe target versions supported by evidence,
test plan, rollback plan, and a list of unverified manifests. Do not merge or deploy.
