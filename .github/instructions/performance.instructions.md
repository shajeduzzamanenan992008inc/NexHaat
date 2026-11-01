---
applyTo: "**/*.{py,js,jsx,ts,tsx,css,scss},**/static/**,**/templates/**"
---

# Performance and reliability instructions

- Measure before optimizing and record reproducible baseline and environment.
- Avoid N+1 queries, unbounded result sets, synchronous slow I/O, and unbounded retries.
- Use timeouts and bounded retries with jitter where the integration requires them.
- Keep cache invalidation, inventory consistency, and payment idempotency correct.
- Preserve responsive behavior and reduce unnecessary 3D/GPU/CPU work.
- Do not claim a performance improvement without a comparable measurement.
- Do not introduce infrastructure components without a demonstrated need.
