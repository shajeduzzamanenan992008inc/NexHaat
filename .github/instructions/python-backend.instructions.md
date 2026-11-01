---
applyTo: "**/*.py"
---

# NexHaat Python backend instructions

- Inspect the existing Flask app factory, blueprints/routes, services, models,
  schemas, extensions, migrations, and test fixtures before editing.
- Keep route handlers thin; place reusable business logic in the established service
  or domain layer rather than creating a parallel architecture.
- Validate and authorize every resource access server-side; test denied as well as
  allowed cases, especially for customer, seller, and admin boundaries.
- Use parameterized database operations, safe serialization, and explicit transaction
  boundaries.
- Make checkout, payment callbacks, order creation, inventory, refunds, and settlement
  idempotent and retry-safe.
- Treat money using decimal-safe representations and explicit rounding/currency rules.
- Never trust client-submitted price, role, owner ID, payment status, or inventory value.
- Add migrations for schema changes; never edit deployed schema manually or run a
  production migration without explicit approval.
- Keep secrets in the approved secret store/environment, never in source code or logs.
- Add unit/integration tests for validation, authorization, state transitions,
  error handling, and rollback behavior.
- Preserve the repository's supported Python versions and current style conventions.
