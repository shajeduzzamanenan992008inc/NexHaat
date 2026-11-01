---
name: implement-feature-safely
description: "Implement one NexHaat feature as a tested, reviewable vertical slice."
disable-model-invocation: true
---
Implement the requested NexHaat feature as a bounded vertical slice.

Before editing:
- inspect current branch and git status;
- follow repository and path-scoped instructions;
- ask REA to map affected modules when available;
- identify API, UI, database, authorization, observability, and test impact;
- preserve existing 3D branding and design system.

Implementation:
- make the smallest coherent change;
- keep business rules server-authoritative;
- add validation, authorization, error handling, and tests;
- update migrations and docs only when required;
- do not add unrelated refactors or speculative infrastructure.

After editing:
- run relevant tests and builds;
- inspect the full diff and generated files;
- report exact commands and results, remaining risks, and rollback notes;
- do not commit, merge, publish, or deploy without explicit approval.
