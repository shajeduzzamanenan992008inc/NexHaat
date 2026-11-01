---
applyTo: "**/*{model,schema,migration,repository,database,db}*.py,**/migrations/**"
---

# Database and migration instructions

- Inspect the actual database engine, ORM conventions, migration history, and tests.
- Use database constraints for invariants that must hold under concurrency.
- Review tenant ownership, uniqueness, indexes, foreign keys, cascades, and nullability.
- Prefer additive expand-migrate-contract changes for high-risk schema evolution.
- Never edit an applied migration casually; create a new migration after checking
  repository conventions.
- Do not run destructive migrations, truncate tables, or mutate production data
  without explicit approval and verified recovery steps.
- Test migration from the current schema and, where feasible, rollback/forward paths.
- Use real query plans before claiming an index or query optimization is beneficial.
