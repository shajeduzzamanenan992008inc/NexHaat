# Customer journey baseline

This map distinguishes server-rendered Flask journeys, API capability, and the additional React/Android clients. Route presence does not itself prove a complete end-to-end client workflow.

| Stage | Current NexHaat evidence | Classification / gap |
|---|---|---|
| Discover and search | Flask home, menu, category, search, deals and search suggestions; API catalog/search; React home/catalog/deals with preview fallback noted in the local browser | Flask route family exists; React live catalog is configuration-dependent/partially connected |
| Inspect product and reviews | Flask product/store views and review submission/helpful/report routes; catalog/product/review API; React product detail has mixed server and preview capability per existing audit | Backend exists; React detail/review connection remains partial and must be verified per action |
| Save products | Flask wishlist pages/actions and API wishlist; React wishlist view | Existing; client connection and cross-session behavior require journey tests |
| Cart | Flask cart routes; `/api/v1/cart`; React cart state and API adapter; Android cart API client | Backend authoritative; complete browser/device synchronization is not established by source presence |
| Checkout | Flask checkout and `/api/v1/checkout`/preview | Existing server-side workflow; payment continuation remains provider/configuration-dependent |
| Payment | SSLCOMMERZ success/return/IPN and payment status/retry routes; API payment status/retry | Callback and provider configuration are required. A browser redirect is not evidence of payment success |
| Orders | Flask confirmation, order history, cancellation/return; API order detail/list/timeline; React orders/confirmation pages; Android order routes | Backend operations exist; React parity and live deployment behavior need separate verification |
| Delivery | Rider assignment and rider status routes, seller/admin order handling | Existing operational endpoints; external dispatch/tracking integrations are not established |
| Returns/refunds | Customer return and admin review/refund routes | Existing paths; provider refund behavior, edge cases and completion require controlled verification |
| Help and account | Support case pages/replies, customer and role account/auth routes; notification API/pages | Server paths exist; React customer profile/support remain partial according to the current feature audit |

## Trust boundaries

Flask services and persistence own product price, availability, checkout totals, payment state, order transitions, role/ownership checks, returns and payouts. React preview data and Android presentation state are not authoritative. Never claim checkout completion from client state or a payment redirect.
