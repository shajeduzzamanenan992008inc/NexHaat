# NexHaat deployment architecture

## Scope

NexHaat currently contains two preserved application surfaces:

- The Flask marketplace and versioned `/api/v1` backend used by the Android client.
- The React/Vite frontend and Express AI/science/WebSocket server.

Neither surface is removed or treated as a replacement for the other.

## Deployment boundary

The supported target is two independently built deployment artifacts:

1. **Marketplace service** — Flask, Gunicorn, SQLAlchemy/Flask-Migrate, and the
   existing database and integration configuration.
2. **Web and AI service** — Node.js, the React/Vite build, and the existing
   Express routes in `server.ts`.

The Android client continues to use the Flask `/api/v1` contract. The React
application must use an explicitly configured marketplace API origin before it
is connected to production marketplace data; its current local/Firebase data
path remains preserved until that contract is verified.

## Required contracts

- Flask liveness: `GET /health/live`
- Flask readiness: `GET /health/ready`
- Marketplace API: `/api/v1`
- Express AI/science routes: `/api/gemini/*` and `/api/science/*`
- Express WebSocket upgrade: `/`
- Media URLs must be produced by the marketplace service or its configured
  object-storage/CDN origin; clients must not infer private storage paths.

## Current Azure limitation

The existing Azure workflow is named and configured for a Python application,
while the committed `main` tree also contains a Node/React application. The
workflow must not silently deploy one runtime as the other. Before changing
the production App Service target, verify the App Service stack, startup
command, deployment history, and health logs in Azure. This document does not
authorize a restart, redeploy, production configuration change, or database
operation.

## Verification gates

Before any production rollout:

1. Build and test the Flask artifact, including migrations against a disposable
   database.
2. Run `npm ci` and `npm run build` for the Node artifact.
3. Verify Android debug tests against a disposable Flask environment.
4. Validate authentication, CORS/CSRF, API versioning, media URLs, and health
   checks in staging.
5. Promote only an identified artifact after owner approval and retain the
   previous known-good artifact for rollback.
