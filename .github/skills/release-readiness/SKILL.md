---
name: release-readiness
description: Run a pre-release readiness review for a NexHaat release.
disable-model-invocation: true
---
Review the requested NexHaat release candidate.

Verify:
- exact commit SHA and clean/understood working tree;
- CI, CodeQL, dependency review, and config-validation results;
- database migration and rollback safety;
- authentication, authorization, tenant isolation, and commerce invariants;
- secrets and environment-file exclusion;
- SBOM/provenance availability and artifact identity;
- production Environment protection and Azure OIDC configuration;
- monitoring, health checks, incident contact, and rollback readiness.

Do not deploy. Return GO / CONDITIONAL GO / NO-GO with evidence, blockers, owners,
and explicit unverified items. Never convert missing evidence into a pass.
