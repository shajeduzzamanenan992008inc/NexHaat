# NexHaat capability gaps and implementation order

The canonical delivery roadmap remains `docs/plans/nexhaat-master-plan.md`. This OMEGA task tracker supplements it; it does not change stage status.

| Priority | Gap | Bounded next work | Acceptance evidence |
|---|---|---|---|
| P0 | Shared identity tokens disagree across React, Flask and Android | Apply Signature Blue tokens and theme behavior in existing shared theme files | Browser light/dark, Flask customer/auth views, Android unit/build evidence where available |
| P0 | Preview and backend states can be confused | Keep unavailable/preview notice and distinguish authoritative states | Browser proves warning; API journey proves success/error source |
| P1 | Customer journey parity across web and Android | Trace catalog → product → cart → checkout → order using existing API/services | Authenticated local controlled journey plus invalid/duplicate paths; never live payment |
| P1 | React customer profile/support and seller/admin completeness | Map actions to existing Flask/API contracts before adding UI | Each action has request/response/error/ownership evidence |
| P1 | Payment continuation and returns depend on provider setup | Verify sandbox callback/idempotency paths after confirming configuration | Provider sandbox evidence; no production calls |
| P1 | Seller isolation, admin policy and rider assignment need explicit negative coverage | Add/extend focused tests at service/API boundaries when implementation changes | Own-resource success and cross-owner/role denial evidence |
| P2 | Responsive and accessible consistency across roles | Audit keyboard, labels, errors, reduced motion and narrow widths | Browser automation evidence at desktop/mobile and reduced-motion preference |
| P2 | Performance and operations evidence | Investigate bundle splitting and documented CI/runtime constraints | Build output, budgets, deployment/provider limitations recorded |
| Separate approval | Paid ads, production settlement, warehouse/dispatch providers and production changes | Do not emulate as local success; design integration proposal first | User-approved scope, provider sandbox, security and rollout plan |

## Current state

The source/runtime topology is known, public reference research is bounded, and a partial REA static scan plus existing local browser evidence are recorded. The React catalog API was unavailable in the inspected preview and showed preview-data messaging. No production workflow has been verified. Signature Blue implementation is being applied now; the rest of the roadmap remains open in `docs/implementation/IMPLEMENTATION_TRACKER.md`.
