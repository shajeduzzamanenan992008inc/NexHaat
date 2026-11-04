# Route and navigation map

**Discovery command:** `python -m flask --app run.py routes --all-methods` (executed 2026-11-04). Flask's route map is the source for exact methods, endpoints and converters. This document groups the active rules by product domain and points to client navigation separately; it is not a promise that every route is reachable from every client.

## Flask server-rendered domains

| Domain | Route families |
|---|---|
| Main/customer discovery | `/`, `/menu`, `/category/<slug>`, `/food/<slug>`, `/store/<slug>`, `/search`, `/deals`, `/api/search-suggestions`, `/language`, `/health*` |
| Auth/account | `/auth/*`, `/admin/login`, `/admin/verify-admin-login`, including registration verification, login 2FA, password reset, account, staff invitation, phone verification and Telegram link actions |
| Customer | `/customer/dashboard`, `/cart*`, `/checkout`, `/orders/<order_number>*`, `/my-orders`, `/payments/*`, `/wishlist*`, `/notifications*`, `/support*` |
| Seller | `/seller/account*`, `/seller/dashboard`, `/seller/catalog`, `/seller/products*`, `/seller/orders*`, `/seller/deals*`, `/seller/payouts`, `/seller/ai*` |
| Rider | `/rider/account*`, `/rider/dashboard`, `/rider/deliveries/<order_id>/status` |
| Admin | `/admin`, `/admin/orders*`, `/admin/products*`, `/admin/categories*`, `/admin/customers*`, `/admin/accounts*`, `/admin/payments*`, `/admin/promotions*`, `/admin/settings`, `/admin/sellers*`, `/admin/support*` |
| Shared utility | `/ai/*`, `/telegram/*/webhook`, `/static/<path>` |

## Flask JSON API

All marketplace API paths are versioned under `/api/v1` and return the repository's existing envelope.

| Prefix / family | Current resource paths |
|---|---|
| Health | `/health` |
| Auth | `/auth/csrf`, `/auth/me`, `/auth/login`, `/auth/logout`, `/auth/register`, `/auth/register/verify`, `/auth/forgot-password`, `/auth/reset-password`, `/auth/social-login`, `/auth/admin/code`, `/auth/admin/verify`, `/auth/2fa/{status,setup,challenge,verify,confirm,disable,regenerate-backup-codes}` |
| Catalog | `/categories`, `/categories/<slug>`, `/deals`, `/products`, `/products/<id>`, `/products/<id>/recommendations`, `/products/<id>/reviews`, `/products/<id>/reviews/<review_id>/{report,helpful}`, `/search`, `/stores/<slug>`, `/banners` |
| Cart / checkout | `/cart`, `/cart/items`, `/cart/items/<cart_key>`, `/checkout`, `/checkout/preview` |
| Orders / payment | `/orders`, `/orders/<order_number>`, `/orders/<order_number>/{cancel,return,timeline}`, `/payments/<checkout_group>`, `/payments/<checkout_group>/retry` |
| Seller | `/seller/dashboard`, `/seller/orders`, `/seller/orders/<id>`, `/seller/orders/<id>/timeline`, `/seller/products`, `/seller/products/<id>` |
| Admin | `/admin/dashboard`, `/admin/{users,sellers,products,orders,payments,reviews,categories}`, resource moderation/update paths and seller payout/refund paths |
| Wishlist / notifications | `/wishlist`, `/wishlist/items`, `/wishlist/items/<product_id>`, `/notifications`, `/notifications/read-all`, `/notifications/<id>/read` |

## React client navigation

`src/App.tsx` switches among `home`, `catalog`, `deals`, `product-detail`, `checkout`, `order-confirmation`, `my-orders`, `wishlist`, `notifications`, `seller-portal`, `rider-portal`, `admin-portal`, and `support`. This is view-state navigation, not a URL router.

## Android navigation

`NavRoutes.kt` defines `home`, `categories`, `products`, `search`, `product_detail/{productId}`, `cart`, `sign_in`, `settings`, `deals`, `wishlist`, `notifications`, `orders`, `checkout`, `order_confirmation/{orderNumber}`, `portals`, `sign_up`, `verify_registration/{email}`, `forgot_password`, `ai_assistant`, and `security_center`.

## Separate Express service

`server.ts` hosts Gemini chat/search/maps/transcribe/image/video/music operations, PubChem/product science operations, and APK metadata/download paths. It is not a marketplace identity, catalog price, order, payment, or inventory API. Exact route handlers and request guards remain in `server.ts` and `serverSecurity.ts`.

## Exact Flask URL map (captured 2026-11-04)

Implicit `HEAD` and `OPTIONS` methods are included as reported by Flask. This table is the current Flask rule inventory; it does not prove auth, ownership or client integration.

| Endpoint | Methods | Rule |
|---|---|---|
| `--------------------------------------------` | `------------------------` | `------------------------------------------------------------------` |
| `admin.ai_query` | `OPTIONS, POST` | `/admin/ai/query` |
| `admin.ai_workspace` | `GET, HEAD, OPTIONS` | `/admin/ai` |
| `admin.dashboard` | `GET, HEAD, OPTIONS` | `/admin` |
| `ai.chat` | `OPTIONS, POST` | `/ai/chat` |
| `ai.confirm_cart_change` | `OPTIONS, POST` | `/ai/cart/confirm` |
| `ai.create_cart_proposal` | `OPTIONS, POST` | `/ai/cart/proposal` |
| `ai.image_search` | `OPTIONS, POST` | `/ai/image-search` |
| `ai.index` | `GET, HEAD, OPTIONS` | `/ai/` |
| `ai.preferences` | `GET, HEAD, OPTIONS, POST` | `/ai/preferences` |
| `ai.review_summary` | `GET, HEAD, OPTIONS` | `/ai/review-summary/<slug>` |
| `ai.voice_search` | `OPTIONS, POST` | `/ai/voice-search` |
| `api.api_admin.approve_payment_risk` | `OPTIONS, POST` | `/api/v1/admin/payments/<int:payment_id>/approve-risk` |
| `api.api_admin.categories` | `GET, HEAD, OPTIONS` | `/api/v1/admin/categories` |
| `api.api_admin.create_category` | `OPTIONS, POST` | `/api/v1/admin/categories` |
| `api.api_admin.create_seller_payout` | `OPTIONS, POST` | `/api/v1/admin/sellers/<int:seller_id>/payouts` |
| `api.api_admin.dashboard` | `GET, HEAD, OPTIONS` | `/api/v1/admin/dashboard` |
| `api.api_admin.deactivate_category` | `DELETE, OPTIONS` | `/api/v1/admin/categories/<int:category_id>` |
| `api.api_admin.moderate_product` | `OPTIONS, PATCH` | `/api/v1/admin/products/<int:product_id>` |
| `api.api_admin.moderate_review` | `OPTIONS, PATCH` | `/api/v1/admin/reviews/<int:review_id>` |
| `api.api_admin.orders` | `GET, HEAD, OPTIONS` | `/api/v1/admin/orders` |
| `api.api_admin.payments` | `GET, HEAD, OPTIONS` | `/api/v1/admin/payments` |
| `api.api_admin.products` | `GET, HEAD, OPTIONS` | `/api/v1/admin/products` |
| `api.api_admin.refresh_payment_refund` | `OPTIONS, POST` | `/api/v1/admin/refunds/<int:refund_id>/refresh` |
| `api.api_admin.review_seller` | `OPTIONS, PATCH` | `/api/v1/admin/sellers/<int:profile_id>` |
| `api.api_admin.reviews` | `GET, HEAD, OPTIONS` | `/api/v1/admin/reviews` |
| `api.api_admin.sellers` | `GET, HEAD, OPTIONS` | `/api/v1/admin/sellers` |
| `api.api_admin.update_category` | `OPTIONS, PATCH` | `/api/v1/admin/categories/<int:category_id>` |
| `api.api_admin.update_order` | `OPTIONS, PATCH` | `/api/v1/admin/orders/<int:order_id>` |
| `api.api_admin.update_user` | `OPTIONS, PATCH` | `/api/v1/admin/users/<int:user_id>` |
| `api.api_admin.users` | `GET, HEAD, OPTIONS` | `/api/v1/admin/users` |
| `api.api_auth.challenge_2fa` | `OPTIONS, POST` | `/api/v1/auth/2fa/challenge` |
| `api.api_auth.confirm_2fa` | `OPTIONS, POST` | `/api/v1/auth/2fa/verify` |
| `api.api_auth.confirm_2fa` | `OPTIONS, POST` | `/api/v1/auth/2fa/confirm` |
| `api.api_auth.csrf_token` | `GET, HEAD, OPTIONS` | `/api/v1/auth/csrf` |
| `api.api_auth.disable_2fa` | `OPTIONS, POST` | `/api/v1/auth/2fa/disable` |
| `api.api_auth.forgot_password` | `OPTIONS, POST` | `/api/v1/auth/forgot-password` |
| `api.api_auth.login` | `OPTIONS, POST` | `/api/v1/auth/login` |
| `api.api_auth.logout` | `OPTIONS, POST` | `/api/v1/auth/logout` |
| `api.api_auth.me` | `GET, HEAD, OPTIONS` | `/api/v1/auth/me` |
| `api.api_auth.regenerate_backup_codes` | `OPTIONS, POST` | `/api/v1/auth/2fa/regenerate-backup-codes` |
| `api.api_auth.register` | `OPTIONS, POST` | `/api/v1/auth/register` |
| `api.api_auth.request_admin_code` | `OPTIONS, POST` | `/api/v1/auth/admin/code` |
| `api.api_auth.reset_password` | `OPTIONS, POST` | `/api/v1/auth/reset-password` |
| `api.api_auth.setup_2fa` | `OPTIONS, POST` | `/api/v1/auth/2fa/setup` |
| `api.api_auth.social_login` | `OPTIONS, POST` | `/api/v1/auth/social-login` |
| `api.api_auth.two_factor_status` | `GET, HEAD, OPTIONS` | `/api/v1/auth/2fa/status` |
| `api.api_auth.verify_admin_code` | `OPTIONS, POST` | `/api/v1/auth/admin/verify` |
| `api.api_auth.verify_registration` | `OPTIONS, POST` | `/api/v1/auth/register/verify` |
| `api.api_banners.list_banners` | `GET, HEAD, OPTIONS` | `/api/v1/banners` |
| `api.api_catalog.category_products` | `GET, HEAD, OPTIONS` | `/api/v1/categories/<slug>` |
| `api.api_catalog.list_categories` | `GET, HEAD, OPTIONS` | `/api/v1/categories` |
| `api.api_catalog.list_deals` | `GET, HEAD, OPTIONS` | `/api/v1/deals` |
| `api.api_catalog.list_product_reviews` | `GET, HEAD, OPTIONS` | `/api/v1/products/<int:product_id>/reviews` |
| `api.api_catalog.list_products` | `GET, HEAD, OPTIONS` | `/api/v1/products` |
| `api.api_catalog.product_detail` | `GET, HEAD, OPTIONS` | `/api/v1/products/<int:product_id>` |
| `api.api_catalog.product_recommendation_shelf` | `GET, HEAD, OPTIONS` | `/api/v1/products/<int:product_id>/recommendations` |
| `api.api_catalog.report_product_review` | `OPTIONS, POST` | `/api/v1/products/<int:product_id>/reviews/<int:review_id>/report` |
| `api.api_catalog.search_products` | `GET, HEAD, OPTIONS` | `/api/v1/search` |
| `api.api_catalog.store_detail` | `GET, HEAD, OPTIONS` | `/api/v1/stores/<slug>` |
| `api.api_catalog.submit_product_review` | `OPTIONS, POST` | `/api/v1/products/<int:product_id>/reviews` |
| `api.api_catalog.vote_review_helpful` | `OPTIONS, POST` | `/api/v1/products/<int:product_id>/reviews/<int:review_id>/helpful` |
| `api.api_commerce.add_cart_item` | `OPTIONS, POST` | `/api/v1/cart/items` |
| `api.api_commerce.cancel_customer_order` | `OPTIONS, POST` | `/api/v1/orders/<order_number>/cancel` |
| `api.api_commerce.checkout` | `OPTIONS, POST` | `/api/v1/checkout` |
| `api.api_commerce.checkout_preview` | `OPTIONS, POST` | `/api/v1/checkout/preview` |
| `api.api_commerce.clear_cart` | `DELETE, OPTIONS` | `/api/v1/cart` |
| `api.api_commerce.create_seller_product` | `OPTIONS, POST` | `/api/v1/seller/products` |
| `api.api_commerce.customer_order_detail` | `GET, HEAD, OPTIONS` | `/api/v1/orders/<order_number>` |
| `api.api_commerce.customer_order_return` | `OPTIONS, POST` | `/api/v1/orders/<order_number>/return` |
| `api.api_commerce.customer_order_timeline` | `GET, HEAD, OPTIONS` | `/api/v1/orders/<order_number>/timeline` |
| `api.api_commerce.customer_orders` | `GET, HEAD, OPTIONS` | `/api/v1/orders` |
| `api.api_commerce.customer_payment_status` | `GET, HEAD, OPTIONS` | `/api/v1/payments/<checkout_group>` |
| `api.api_commerce.deactivate_seller_product` | `DELETE, OPTIONS` | `/api/v1/seller/products/<int:product_id>` |
| `api.api_commerce.get_cart` | `GET, HEAD, OPTIONS` | `/api/v1/cart` |
| `api.api_commerce.remove_cart_item` | `DELETE, OPTIONS` | `/api/v1/cart/items/<path:cart_key>` |
| `api.api_commerce.retry_customer_payment` | `OPTIONS, POST` | `/api/v1/payments/<checkout_group>/retry` |
| `api.api_commerce.seller_dashboard` | `GET, HEAD, OPTIONS` | `/api/v1/seller/dashboard` |
| `api.api_commerce.seller_order_timeline` | `GET, HEAD, OPTIONS` | `/api/v1/seller/orders/<int:order_id>/timeline` |
| `api.api_commerce.seller_orders` | `GET, HEAD, OPTIONS` | `/api/v1/seller/orders` |
| `api.api_commerce.seller_products` | `GET, HEAD, OPTIONS` | `/api/v1/seller/products` |
| `api.api_commerce.update_cart_item` | `OPTIONS, PATCH` | `/api/v1/cart/items/<path:cart_key>` |
| `api.api_commerce.update_seller_order` | `OPTIONS, PATCH` | `/api/v1/seller/orders/<int:order_id>` |
| `api.api_commerce.update_seller_product` | `OPTIONS, PATCH` | `/api/v1/seller/products/<int:product_id>` |
| `api.api_health.health` | `GET, HEAD, OPTIONS` | `/api/v1/health` |
| `api.api_notifications.list_notifications` | `GET, HEAD, OPTIONS` | `/api/v1/notifications` |
| `api.api_notifications.read_all_notifications` | `OPTIONS, POST` | `/api/v1/notifications/read-all` |
| `api.api_notifications.read_notification` | `OPTIONS, POST` | `/api/v1/notifications/<int:notification_id>/read` |
| `api.api_wishlist.add_wishlist_item` | `OPTIONS, POST` | `/api/v1/wishlist/items` |
| `api.api_wishlist.list_wishlist` | `GET, HEAD, OPTIONS` | `/api/v1/wishlist` |
| `api.api_wishlist.remove_wishlist_item` | `DELETE, OPTIONS` | `/api/v1/wishlist/items/<int:product_id>` |
| `auth.accept_invitation` | `GET, HEAD, OPTIONS, POST` | `/auth/invitation/<token>` |
| `auth.account` | `GET, HEAD, OPTIONS, POST` | `/auth/account` |
| `auth.admin_account` | `GET, HEAD, OPTIONS, POST` | `/auth/admin-account` |
| `auth.admin_login` | `GET, HEAD, OPTIONS, POST` | `/admin/login` |
| `auth.change_password` | `OPTIONS, POST` | `/auth/account/password` |
| `auth.confirm_phone_verification` | `OPTIONS, POST` | `/auth/account/phone/verify/confirm` |
| `auth.create_staff_invitation` | `OPTIONS, POST` | `/auth/admin/invitations` |
| `auth.delete_account` | `OPTIONS, POST` | `/auth/account/delete` |
| `auth.forgot_password` | `GET, HEAD, OPTIONS, POST` | `/auth/forgot-password` |
| `auth.link_telegram_account` | `OPTIONS, POST` | `/auth/account/telegram/link` |
| `auth.login` | `GET, HEAD, OPTIONS, POST` | `/auth/login` |
| `auth.logout` | `OPTIONS, POST` | `/auth/logout` |
| `auth.portal` | `GET, HEAD, OPTIONS` | `/auth/portal` |
| `auth.register` | `GET, HEAD, OPTIONS, POST` | `/auth/register` |
| `auth.request_phone_verification` | `OPTIONS, POST` | `/auth/account/phone/verify/request` |
| `auth.resend_admin_login_code` | `OPTIONS, POST` | `/auth/resend-admin-login-code` |
| `auth.resend_registration_code` | `OPTIONS, POST` | `/auth/resend-registration-code` |
| `auth.resend_staff_invitation` | `OPTIONS, POST` | `/auth/admin/invitations/<int:invitation_id>/resend` |
| `auth.reset_password` | `GET, HEAD, OPTIONS, POST` | `/auth/reset-password` |
| `auth.revoke_staff_invitation` | `OPTIONS, POST` | `/auth/admin/invitations/<int:invitation_id>/revoke` |
| `auth.seller_application` | `GET, HEAD, OPTIONS, POST` | `/auth/seller-application` |
| `auth.two_factor_login_challenge` | `GET, HEAD, OPTIONS, POST` | `/auth/login/2fa` |
| `auth.unlink_telegram_account` | `OPTIONS, POST` | `/auth/account/telegram/unlink` |
| `auth.verify_admin_login` | `GET, HEAD, OPTIONS, POST` | `/auth/verify-admin-login` |
| `auth.verify_registration` | `GET, HEAD, OPTIONS, POST` | `/auth/verify-registration` |
| `auth.verify_reset_code` | `GET, HEAD, OPTIONS, POST` | `/auth/verify-reset-code` |
| `customer.dashboard` | `GET, HEAD, OPTIONS` | `/customer/dashboard` |
| `main.category` | `GET, HEAD, OPTIONS` | `/category/<slug>` |
| `main.deals` | `GET, HEAD, OPTIONS` | `/deals` |
| `main.food` | `GET, HEAD, OPTIONS` | `/food/<slug>` |
| `main.health` | `GET, HEAD, OPTIONS` | `/health/ready` |
| `main.health` | `GET, HEAD, OPTIONS` | `/health/db` |
| `main.health` | `GET, HEAD, OPTIONS` | `/health` |
| `main.health_live` | `GET, HEAD, OPTIONS` | `/health/live` |
| `main.index` | `GET, HEAD, OPTIONS` | `/` |
| `main.menu` | `GET, HEAD, OPTIONS` | `/menu` |
| `main.report_review_route` | `OPTIONS, POST` | `/food/<slug>/reviews/<int:review_id>/report` |
| `main.search` | `GET, HEAD, OPTIONS` | `/search` |
| `main.search_suggestions_api` | `GET, HEAD, OPTIONS` | `/api/search-suggestions` |
| `main.set_language` | `OPTIONS, POST` | `/language` |
| `main.store` | `GET, HEAD, OPTIONS` | `/store/<slug>` |
| `main.submit_review` | `OPTIONS, POST` | `/food/<slug>/reviews` |
| `main.toggle_review_helpful` | `OPTIONS, POST` | `/food/<slug>/reviews/<int:review_id>/helpful` |
| `notifications.index` | `GET, HEAD, OPTIONS` | `/notifications` |
| `notifications.read_all` | `OPTIONS, POST` | `/notifications/read-all` |
| `notifications.read_one` | `OPTIONS, POST` | `/notifications/<int:notification_id>/read` |
| `orders.add_to_cart` | `OPTIONS, POST` | `/cart/add/<int:product_id>` |
| `orders.admin_account_remove` | `OPTIONS, POST` | `/admin/accounts/<int:user_id>/remove` |
| `orders.admin_assign_rider` | `OPTIONS, POST` | `/admin/orders/<int:order_id>/assign` |
| `orders.admin_category_delete` | `OPTIONS, POST` | `/admin/categories/<int:category_id>/delete` |
| `orders.admin_category_edit` | `GET, HEAD, OPTIONS, POST` | `/admin/categories/<int:category_id>/edit` |
| `orders.admin_category_new` | `GET, HEAD, OPTIONS, POST` | `/admin/categories/new` |
| `orders.admin_customer_activate` | `OPTIONS, POST` | `/admin/customers/<int:user_id>/activate` |
| `orders.admin_customer_deactivate` | `OPTIONS, POST` | `/admin/customers/<int:user_id>/deactivate` |
| `orders.admin_customer_new` | `GET, HEAD, OPTIONS, POST` | `/admin/customers/new` |
| `orders.admin_customer_remove` | `OPTIONS, POST` | `/admin/customers/<int:user_id>/remove` |
| `orders.admin_customer_toggle_active` | `OPTIONS, POST` | `/admin/customers/<int:user_id>/toggle-active` |
| `orders.admin_manual_return_refund` | `OPTIONS, POST` | `/admin/orders/<int:return_id>/manual-return-refund` |
| `orders.admin_moderate_review` | `OPTIONS, POST` | `/admin/reviews/<int:review_id>/moderate` |
| `orders.admin_order_confirm` | `OPTIONS, POST` | `/admin/orders/<int:order_id>/confirm` |
| `orders.admin_order_confirm_all` | `OPTIONS, POST` | `/admin/orders/confirm-all` |
| `orders.admin_order_decline` | `OPTIONS, POST` | `/admin/orders/<int:order_id>/decline` |
| `orders.admin_order_decline_all` | `OPTIONS, POST` | `/admin/orders/decline-all` |
| `orders.admin_order_detail` | `GET, HEAD, OPTIONS` | `/admin/orders/<int:order_id>` |
| `orders.admin_order_remove` | `OPTIONS, POST` | `/admin/orders/<int:order_id>/remove` |
| `orders.admin_order_status` | `OPTIONS, POST` | `/admin/orders/<int:order_id>/status` |
| `orders.admin_payment_approve_review` | `OPTIONS, POST` | `/admin/payments/<int:payment_id>/approve-review` |
| `orders.admin_payment_refund_order` | `OPTIONS, POST` | `/admin/payments/<int:payment_id>/orders/<int:order_id>/refund` |
| `orders.admin_payments` | `GET, HEAD, OPTIONS` | `/admin/payments` |
| `orders.admin_product_delete` | `OPTIONS, POST` | `/admin/products/<int:product_id>/delete` |
| `orders.admin_product_edit` | `GET, HEAD, OPTIONS, POST` | `/admin/products/<int:product_id>/edit` |
| `orders.admin_product_new` | `GET, HEAD, OPTIONS, POST` | `/admin/products/new` |
| `orders.admin_promotion_toggle` | `OPTIONS, POST` | `/admin/promotions/<int:promotion_id>/toggle` |
| `orders.admin_promotions` | `GET, HEAD, OPTIONS, POST` | `/admin/promotions` |
| `orders.admin_refund_refresh` | `OPTIONS, POST` | `/admin/refunds/<int:refund_id>/refresh` |
| `orders.admin_resolve_review_report` | `OPTIONS, POST` | `/admin/review-reports/<int:report_id>/resolve` |
| `orders.admin_return_received` | `OPTIONS, POST` | `/admin/orders/<int:return_id>/return-received` |
| `orders.admin_return_refund` | `OPTIONS, POST` | `/admin/orders/<int:return_id>/return-refund` |
| `orders.admin_review_order_return` | `OPTIONS, POST` | `/admin/orders/<int:return_id>/return-review` |
| `orders.admin_review_product` | `OPTIONS, POST` | `/admin/products/<int:product_id>/review` |
| `orders.admin_review_seller` | `OPTIONS, POST` | `/admin/sellers/<int:profile_id>/review` |
| `orders.admin_seller_payout` | `OPTIONS, POST` | `/admin/sellers/<int:seller_id>/payouts` |
| `orders.admin_settings` | `GET, HEAD, OPTIONS, POST` | `/admin/settings` |
| `orders.buy_again` | `OPTIONS, POST` | `/orders/<order_number>/buy-again` |
| `orders.cart` | `GET, HEAD, OPTIONS` | `/cart` |
| `orders.checkout` | `GET, HEAD, OPTIONS, POST` | `/checkout` |
| `orders.confirmation` | `GET, HEAD, OPTIONS` | `/orders/<order_number>` |
| `orders.customer_order_cancel` | `OPTIONS, POST` | `/orders/<order_number>/cancel` |
| `orders.customer_order_return` | `OPTIONS, POST` | `/orders/<order_number>/return` |
| `orders.my_orders` | `GET, HEAD, OPTIONS` | `/my-orders` |
| `orders.payment_retry` | `OPTIONS, POST` | `/payments/<checkout_group>/retry` |
| `orders.payment_status` | `GET, HEAD, OPTIONS` | `/payments/<checkout_group>` |
| `orders.remove_from_cart` | `OPTIONS, POST` | `/cart/remove/<int:product_id>` |
| `orders.sslcommerz_ipn` | `OPTIONS, POST` | `/payments/sslcommerz/ipn` |
| `orders.sslcommerz_return` | `GET, HEAD, OPTIONS, POST` | `/payments/sslcommerz/return` |
| `orders.sslcommerz_success` | `GET, HEAD, OPTIONS, POST` | `/payments/sslcommerz/success` |
| `orders.update_cart` | `OPTIONS, POST` | `/cart/update` |
| `rider.account` | `GET, HEAD, OPTIONS, POST` | `/rider/account` |
| `rider.change_password` | `OPTIONS, POST` | `/rider/account/password` |
| `rider.dashboard` | `GET, HEAD, OPTIONS` | `/rider/dashboard` |
| `rider.update_delivery` | `OPTIONS, POST` | `/rider/deliveries/<int:order_id>/status` |
| `seller.account` | `GET, HEAD, OPTIONS, POST` | `/seller/account` |
| `seller.ai_analytics_query` | `OPTIONS, POST` | `/seller/ai/query` |
| `seller.ai_listing_suggest` | `OPTIONS, POST` | `/seller/ai/suggest` |
| `seller.ai_price_suggestion` | `OPTIONS, POST` | `/seller/ai/price` |
| `seller.ai_workspace` | `GET, HEAD, OPTIONS` | `/seller/ai` |
| `seller.catalog` | `GET, HEAD, OPTIONS` | `/seller/catalog` |
| `seller.change_password` | `OPTIONS, POST` | `/seller/account/password` |
| `seller.dashboard` | `GET, HEAD, OPTIONS` | `/seller/dashboard` |
| `seller.deal_toggle` | `OPTIONS, POST` | `/seller/deals/<int:deal_id>/toggle` |
| `seller.deals` | `GET, HEAD, OPTIONS, POST` | `/seller/deals` |
| `seller.orders` | `GET, HEAD, OPTIONS` | `/seller/orders` |
| `seller.payouts` | `GET, HEAD, OPTIONS` | `/seller/payouts` |
| `seller.product_archive` | `OPTIONS, POST` | `/seller/products/<int:product_id>/archive` |
| `seller.product_edit` | `GET, HEAD, OPTIONS, POST` | `/seller/products/<int:product_id>/edit` |
| `seller.product_new` | `GET, HEAD, OPTIONS, POST` | `/seller/products/new` |
| `seller.product_variant_delete` | `OPTIONS, POST` | `/seller/products/<int:product_id>/variants/<int:variant_id>/toggle` |
| `seller.product_variant_stock` | `OPTIONS, POST` | `/seller/products/<int:product_id>/variants/<int:variant_id>/stock` |
| `seller.product_variants` | `GET, HEAD, OPTIONS, POST` | `/seller/products/<int:product_id>/variants` |
| `seller.update_order_status` | `OPTIONS, POST` | `/seller/orders/<int:order_id>/status` |
| `seller.update_return` | `OPTIONS, POST` | `/seller/orders/<int:order_id>/returns/<int:return_id>` |
| `static` | `GET, HEAD, OPTIONS` | `/static/<path:filename>` |
| `support.customer_case` | `GET, HEAD, OPTIONS` | `/support/<int:case_id>` |
| `support.customer_cases` | `GET, HEAD, OPTIONS, POST` | `/support` |
| `support.reply` | `OPTIONS, POST` | `/support/<int:case_id>/reply` |
| `support.staff_case` | `GET, HEAD, OPTIONS` | `/admin/support/<int:case_id>` |
| `support.staff_queue` | `GET, HEAD, OPTIONS` | `/admin/support` |
| `telegram_customer.webhook` | `OPTIONS, POST` | `/telegram/customer/webhook` |
| `telegram_security.webhook` | `OPTIONS, POST` | `/telegram/security/webhook` |
| `wishlist.add_item` | `OPTIONS, POST` | `/wishlist/add/<int:product_id>` |
| `wishlist.index` | `GET, HEAD, OPTIONS` | `/wishlist` |
| `wishlist.remove_item` | `OPTIONS, POST` | `/wishlist/remove/<int:product_id>` |
