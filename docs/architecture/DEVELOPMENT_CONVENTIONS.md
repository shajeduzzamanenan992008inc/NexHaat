# NexHaat Development Conventions

## General

- Preserve existing features, routes, APIs, schemas, integrations, and dirty
  worktree changes.
- Prefer small additive changes with an explicit rollback.
- Inspect the relevant report, README, architecture/API/database guidance, and
  source before editing.
- Do not commit, push, deploy, restart production, or mutate production data
  as part of ordinary development.

## Backend and database

- Use the Flask application factory and existing blueprint registration.
- Keep route handlers thin; put reusable rules in services and bounded queries
  in repositories.
- Validate input and authorization at every trust boundary.
- Use server-authoritative Decimal money, inventory, order state, and payment
  status; never trust browser totals or roles.
- Use Flask-Migrate/Alembic additive migrations. Never edit deployed schemas
  manually or use destructive migrations without explicit approval and recovery.
- Preserve the API envelope and fixed-precision money serialization.
- Keep secrets in environment configuration and avoid sensitive logs.

## React and UI

- Preserve NexHaat branding, AI Studio visual direction, animations, responsive
  behavior, reduced motion, and existing fallback states.
- Reuse existing components and types before adding new ones.
- Use `src/lib/flaskAuth.ts` and `src/lib/marketplaceApi.ts` instead of creating
  duplicate clients.
- Treat browser state as presentation state, not authorization or price proof.
- Provide semantic labels, visible focus, loading/empty/error states, and
  keyboard support.
- Keep Firebase as a separate preserved capability until account linking is
  explicitly designed and approved.

## AI and integrations

- Keep provider keys and privileged tools server-side.
- Treat prompts, retrieved content, model output, webpages, and tool results as
  untrusted data.
- Use server-selected scopes, allowlisted tools, bounded input/output,
  timeouts, rate/cost limits, and safe fallbacks.
- Require human confirmation for financial, account, permission, destructive, or
  externally consequential actions.
- Record feature source, conflicts, dependencies, tests, and rollback in the
  AI submission template and feature registry.

## Naming and placement

- Python modules/functions: `snake_case`; classes: `PascalCase`.
- TypeScript variables/functions: `camelCase`; React components/types:
  `PascalCase`; constants: descriptive `UPPER_SNAKE_CASE` where appropriate.
- Use feature-specific names rather than generic `utils` or `helpers`.
- Place shared React components in `src/components`, pages in `src/pages`,
  adapters in `src/lib`, and UI types in `src/types`.
- Place Python domain logic in the owning service/module rather than a new
  parallel layer.

## Verification and documentation

Run the narrowest applicable checks, then the baseline gates:

```powershell
npm run lint
npm run build
python -m pytest -q
.\android\gradlew.bat -p android :app:test --no-daemon
git diff --check
```

Report actual command output and distinguish `PASS`, `FAIL`, `PARTIAL`,
`BLOCKED`, and `NOT TESTED`. Update architecture/phase documentation when
behavior, contracts, configuration, migration, or operational procedures
change.

