# Marketplace capability matrix

Status describes repository evidence observed for this task, not deployment readiness. “Existing” means a source surface exists; it does not imply a complete customer journey.

| Capability | Status | Evidence and boundary |
|---|---|---|
| Customer shopping | Existing but incomplete | Flask discovery/cart/order routes; React home/catalog/checkout/orders pages; live catalog unavailable in inspected preview |
| Product discovery/search | Existing but incomplete | Flask catalog and search routes plus `/api/v1/search`; React has preview fallback and needs live parity checks |
| Product detail/reviews | Existing but incomplete | Flask product and review operations plus catalog API; React integration has known partial areas |
| Cart | Existing but incomplete | Flask and `/api/v1/cart`; client synchronization and negative cases need workflow verification |
| Checkout | Existing but incomplete | Flask checkout and API; payment continuation depends on provider/configuration |
| Payment | Requires external integration | SSLCOMMERZ callback/status paths exist; live credentials, verified provider callbacks and controlled sandbox evidence are required |
| Order management | Existing but incomplete | Flask customer/seller/admin order routes and API; end-to-end state journeys are not proven for all clients |
| Delivery/rider | Existing but incomplete | Rider assignment/account/status routes; dispatch, maps or live tracking infrastructure is not established |
| Returns/refunds | Existing but incomplete | Customer return and admin refund paths exist; live provider settlement not verified |
| Customer account | Existing but incomplete | Flask auth/account; React profile is backend-only/partial in prior audit |
| Seller onboarding | Existing but incomplete | Application, approval and seller account routes; activation workflow needs verification |
| Seller catalog/inventory | Existing but incomplete | Seller create/edit/archive/variant and stock routes/API |
| Seller analytics | Existing but incomplete | Seller dashboard and AI query endpoints; meaningful source data, permissions and client parity need verification |
| Seller settlement | Requires external integration | Payout surfaces exist, but settlement provider/configuration and live funds are not verified |
| Promotions/coupons | Existing but incomplete | Admin promotions and seller deal routes; broader coupon/stacking policy needs verification |
| Brand storefronts | Existing but incomplete | Store detail routes; storefront customization and moderation scope need verification |
| Seller advertising | Missing | No verified campaign billing, delivery, attribution or advertiser reporting workflow; paid service would need approval/integration |
| Warehouse/fulfillment | Not suitable for current platform as a default assumption | Seller fulfillment routes exist; no evidence of a NexHaat-operated warehouse network |
| Marketplace administration | Existing but incomplete | Flask admin pages/API for moderation, orders, payments, users and categories; React admin completeness is not established |
| Fraud/security | Existing but incomplete | Auth/session/CSRF/rate-limit and payment review surfaces exist; comprehensive production fraud detection is not established |
| AI shopping | Existing but incomplete | Express/Gemini and Flask AI surfaces exist; separate from marketplace authority and configuration-dependent |
| Mobile shopping | Existing but incomplete | Android Compose client has catalog/cart/checkout/orders/auth routes; device-to-live deployment parity is unverified |
| Accessibility | Existing but incomplete | Semantic labels/focus and reduced-motion work exist in source; full keyboard/screen-reader audit is outstanding |
| Performance | Existing but incomplete | Vite build and prior audits show a large client bundle; production telemetry and device budgets remain outstanding |
| Internationalization | Existing but incomplete | Flask locale infrastructure and Bengali support; full customer/seller/admin coverage per client requires audit |

Advertising payments, provider settlement, operational warehouses, live dispatch and production risk controls are integration/operational scope; they cannot be declared ready from local source alone.
