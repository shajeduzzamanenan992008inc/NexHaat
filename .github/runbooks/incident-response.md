# NexHaat Incident Response Runbook

## 1. Establish facts
Record incident start time and timezone, reporter, affected service/journey, severity,
current release SHA, symptoms, and evidence sources. Do not include customer secrets
or unnecessary personal information.

## 2. Assess impact
Check customer, seller, admin, payment, order, inventory, and fulfillment impact.
Distinguish data exposure, financial integrity, availability, and performance issues.

## 3. Contain safely
Prefer reversible containment: disable a faulty feature flag, pause a queue consumer,
or stop a rollout only when the control exists and an authorized owner approves.
Do not delete data or make unreviewed production changes.

## 4. Recover
Use the known-good release/rollback procedure. Confirm database compatibility and
idempotency before replaying events or jobs.

## 5. Verify and communicate
Validate the affected journey with safe synthetic/sandbox data, inspect monitoring,
and provide a factual status update.

## 6. Learn
Create a timeline, root-cause analysis, contributing factors, customer impact,
detection gap, corrective actions, owners, and due dates. Avoid blame.
