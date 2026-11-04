# Existing feature inventory

Inventory is based on source and route inspection on 2026-11-04. A route means an implementation surface exists; integration and failure-path behavior still need workflow evidence.

| Area | Flask / API | React | Android | Current classification |
|---|---|---|---|---|
| Authentication and sessions | Login/register/verify/2FA/password/account/invitation/logout; API auth and CSRF | Shared context and sign-in flows | Sign-in/up/verification/2FA/settings | Existing; preserve session, CSRF and revocation contracts |
| Catalog and search | Home/menu/category/product/search/deals, catalog/search API | Home/catalog/deals/product detail; preview fallback present | Home/categories/products/search/detail | Existing but live client parity incomplete |
| Reviews and stores | Review submit/helpful/report, store pages, catalog API | Product review surface is partially connected per prior audit | Product detail review surface requires device verification | Backend exists; UI connection varies |
| Cart and checkout | Cart and checkout routes/API; server validates totals | Cart/checkout pages and adapters; payment continuation partial | Cart/checkout route and Retrofit layer | Backend-owned; no client total is authoritative |
| Orders and payment | Orders, status, cancel, return, payment status/retry, SSLCOMMERZ callbacks | Orders and confirmation pages | Orders/confirmation | Existing; provider-dependent and not live-verified |
| Seller operations | Apply/account/catalog/products/variants/stock/orders/returns/deals/payouts/AI | Seller portal surfaces; parity incomplete | Portal surface exists | Backend exists; verify seller ownership and client integration |
| Rider | Account/dashboard/delivery status | Portal surface | Portal route | Existing route; external dispatch not established |
| Admin | Moderation, users, orders, categories, promotions, payment/refund, seller review/payout, support | Admin portal surface; completeness unknown | Portal surface | Backend exists; enforce role checks/audit; React completeness not proven |
| Support and notifications | Customer cases, staff queue/reply, notification read routes/API | Support and notifications pages; support integration partial | Notification/support-related surfaces | Existing but client parity incomplete |
| AI/media/science | Flask AI scope plus separate Express/Gemini service | AI interactions through existing adapters | AI assistant route | Configuration-dependent; cannot perform commerce authority actions |
| Internationalization | Flask locales and localized pages | Shared language context | UI locale support | Existing but coverage needs per-screen verification |
| Security and accessibility | CSRF, session/auth controls, role checks, rate limits and safe media/security modules | labels, focus and reduced-motion tokens in source | Compose semantics/theme | Partial audit; no global completion claim |

Existing detailed security, connectivity and stage audits remain in `docs/architecture/`. Their dates and scope should be checked before relying on old test outcomes.
