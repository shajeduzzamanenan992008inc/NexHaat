# NexHaat Database Migration Runbook

1. Identify the database engine, schema version, current migration head, and affected data.
2. Review generated migration code manually; generated output is not automatically safe.
3. Check locks, table size, indexes, constraints, backfill cost, and transaction behavior.
4. Prefer additive expand-migrate-contract steps for high-risk changes.
5. Confirm application compatibility during rolling deployment and rollback windows.
6. Verify a recent backup and a tested restore path before destructive or irreversible work.
7. Test migration from a representative previous schema using synthetic or masked data.
8. Run integrity checks, migration head checks, and affected business workflow tests.
9. Obtain explicit approval before production migration or data correction.
10. Record migration SHA, operator, start/end, result, validation, and recovery decision.

Never run DROP/TRUNCATE, mass deletion, or irreversible data correction autonomously.
