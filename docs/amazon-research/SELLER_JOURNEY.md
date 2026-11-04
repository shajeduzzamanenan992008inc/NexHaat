# Seller journey baseline

| Stage | Current NexHaat evidence | Classification / gap |
|---|---|---|
| Apply and activate | `/auth/seller-application`, seller review routes and admin API | Existing server workflow; approval and onboarding need role-based verification |
| Manage account | `/seller/account` and password route | Existing Flask pages; React seller account parity is incomplete/unknown |
| Create and maintain listings | Flask seller catalog, create/edit/archive, variants and inventory routes; `/api/v1/seller/products` family | Backend workflow exists; moderation remains server-owned; client completeness needs route-by-route verification |
| Manage orders and returns | Seller order list, status and return routes; seller order API | Existing seller-scoped backend paths; prove cross-seller denial and duplicate transition behavior before release claims |
| Payouts | Seller payout view and admin payout creation | Backend surface exists; external settlement and payout eligibility/configuration are not proven live |
| Deals | Seller deal list and toggle | Existing route; funding, eligibility and inventory effects remain server policy |
| Analytics and AI assistance | Seller AI workspace, listing suggestion, price and analytics endpoints | Backend/API only or configuration-dependent in clients; suggestions must remain reviewable drafts |
| Advertising/storefront | Store detail and public Amazon seller/ads reference | Store page exists; paid ad campaign, billing, attribution and self-service ad reporting are missing or require separate approved integrations |

Seller isolation and moderation are mandatory acceptance gates. The presence of a page or endpoint is not proof of seller scope correctness. Flask remains the authority; Express/Gemini cannot write marketplace prices, orders, payments, or inventory.
