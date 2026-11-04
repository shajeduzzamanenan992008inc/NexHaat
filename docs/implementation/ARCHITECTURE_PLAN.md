# OMEGA architecture plan

## Keep the current boundaries

1. Flask application factory, existing blueprints, services, SQLAlchemy models and `/api/v1` remain the marketplace authority.
2. React keeps the current `AppContext`, `flaskAuth`, `marketplaceApi` and current page components; connect actions to existing API contracts rather than creating a competing store or auth system.
3. Android keeps Compose navigation, Hilt, Retrofit DTOs, cookie persistence and CSRF behavior.
4. Express/Gemini remains a separate AI/media/science capability. Its outputs cannot authorize or mutate marketplace transactions.
5. Firebase remains separate until an exact token/account-linking flow is proven.

## Delivery sequence

- Establish evidence and preserve the existing worktree (Phase 0/1).
- Apply the requested Signature Blue design tokens to shared React, Flask and Android themes (Phase 2 foundation).
- Trace each customer and role workflow to an existing backend operation before implementing client controls (Phases 3–15).
- Verify local, sandbox and device behavior with explicit status and failure paths (Phases 16–17).

## Compatibility and safety gates

- No new framework, database, identity provider, queue, paid provider or microservice is proposed.
- No schema migration is needed for the current palette task.
- Do not invent API paths or treat React preview state as persisted success.
- Keep payment provider callbacks verified and idempotent; never infer payment success from a redirect.
- Keep seller/customer/rider ownership and admin policy enforced by Flask.
- External provider configuration, production data, deployment and real funds remain out of scope without a separately approved environment and recovery plan.

The canonical roadmap and its acceptance gates remain `docs/plans/nexhaat-master-plan.md`.
