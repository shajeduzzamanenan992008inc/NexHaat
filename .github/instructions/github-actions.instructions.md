---
applyTo: ".github/workflows/*.yml"
---

# NexHaat GitHub Actions instructions

- Use least-privilege permissions at workflow and job scope.
- Prefer read-only permissions; grant `id-token: write` only to the deployment job
  that needs Azure OIDC.
- Pin third-party actions to verified full-length commit SHAs and keep the release
  version in a comment. Do not invent or copy an unverified SHA.
- Keep actions updated through Dependabot and review breaking changes before merging.
- Do not use `pull_request_target` for untrusted code.
- A `workflow_run` workflow that has secrets or write permissions must never check out
  or execute code from an untrusted PR/fork. Gate by event, branch, conclusion, and
  trusted repository context.
- Set timeouts, concurrency controls, explicit artifact names, short artifact
  retention, and `persist-credentials: false` when checkout credentials are unused.
- Do not expose secrets in logs, artifacts, caches, shell tracing, or job outputs.
- Production deploys must use the exact verified commit/artifact, a protected
  environment, least-privileged OIDC, and a documented rollback path.
- Treat a workflow edit as production-sensitive infrastructure. Review its triggers,
  contexts, permissions, expressions, artifact flows, and secrets access.
