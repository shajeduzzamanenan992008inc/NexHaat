---
applyTo: "**/tests/**,**/*test*.py,**/*spec*.{js,jsx,ts,tsx}"
---

# Testing instructions

- Discover actual test framework, fixtures, commands, and environment setup first.
- Test business invariants, not only implementation details.
- Include positive, negative, boundary, authorization, concurrency, and failure cases.
- Prioritize checkout, payment, order lifecycle, inventory, refunds, seller settlement,
  tenant isolation, authentication, and role separation.
- Tests must be deterministic, isolated, and safe to run repeatedly.
- Never use real payment providers, customer data, production databases, or live
  external APIs in automated tests unless explicitly authorized and sandboxed.
- Do not claim a test passed unless its command completed successfully.
