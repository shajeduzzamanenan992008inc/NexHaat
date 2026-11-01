---
applyTo: "**/*route*.py,**/*api*.py,**/*auth*.py,**/*permission*.py,**/*schema*.py,**/routes/**,**/api/**"
---

# API and identity instructions

- Enforce authentication and authorization on the server for every protected action.
- Check object ownership and tenant boundaries after resolving the target resource.
- Default-deny access; do not infer authorization from hidden UI controls.
- Validate request schemas, payload size, pagination, sorting, filtering, and uploads.
- Protect sessions, cookies, CSRF, CORS, password reset, webhook signatures, and replay.
- Use consistent non-leaking error responses and avoid exposing private record existence.
- Keep API contract changes documented and backwards-compatible where required.
- Add negative authorization tests for customer, seller, admin, and cross-tenant access.
