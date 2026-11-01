# NexHaat Backup and Restore Readiness

This is a planning and verification checklist; it does not create backups by itself.

## Before an incident
- Identify every stateful system and its owner.
- Document backup frequency, retention, encryption, access control, and restore procedure.
- Define recovery point and recovery time objectives from business requirements.
- Ensure backups are isolated from normal application credentials.
- Schedule restore drills with synthetic or approved masked data.
- Verify database, uploaded media, object storage, configuration, and encryption-key recovery.

## During recovery
- Declare incident and assign an authorized incident lead.
- Determine the last known-good backup and consistency boundary.
- Avoid restoring over current production data without an explicit plan.
- Validate schema, row counts, referential integrity, and critical commerce state.
- Reconcile payment provider and order events before reopening checkout.

## Evidence
Record backup ID, timestamp, restore duration, validation results, missing data,
and the approving owner. Never claim restore readiness from backup existence alone.
