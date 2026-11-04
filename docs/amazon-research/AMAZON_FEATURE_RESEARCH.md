# Public marketplace reference research

**Observed:** 2026-11-04 · **Scope:** public web surfaces only

## Method and limits

The review used live browser navigation for Amazon.com search results and one product detail, the public Sell on Amazon page, and the public Amazon Ads page. No account was signed in and no transaction was attempted. Amazon customer service redirected to a human-check page, so it was not bypassed. Seller Central could not be inspected as an authenticated seller. This is a public-interface and published-capability review, not access to Amazon systems, private documentation, or source code.

## Observed patterns

| Area | Public evidence | Marketplace pattern to adapt |
|---|---|---|
| Customer discovery | Amazon home, global department search, destination, account, orders and cart entry points | Keep search prominent; expose delivery context and account/order/cart actions consistently |
| Search and results | Query results, sort options, brand/price/rating/deal facets, ratings, delivery details, variants, sponsored labels and quick cart actions | Make filters, sorting, stock/delivery context and product comparisons legible; label paid placement clearly if NexHaat later has an approved ads product |
| Product detail | Product title and brand, ratings, price/savings, media, variants, seller/fulfillment, delivery/import context, stock, quantity, purchase actions and returns | Present authoritative price, variant, availability, seller and delivery facts before a purchase action |
| Seller offering | Public Sell on Amazon pages describe onboarding, listing, fulfillment choices, pricing, seller education, brand tools and analytics | Separate seller education from operational seller controls; keep listing publication moderated |
| Advertising | Amazon Ads describes self-service sponsored ads and brand stores with reporting | Advertising is a separately funded product; do not simulate billing or ad delivery |

## Areas not verified live

Cart persistence, checkout, provider payment, orders, shipment tracking, returns/refunds, customer support, personalization, private Seller Central, seller payouts, warehouse operations, fraud tooling, authenticated mobile behavior, and logged-in accessibility states were not observed. They are not marked as verified Amazon workflows in this report. Public advertising and seller pages are capability descriptions, not proof that NexHaat has equivalent integrations.

## Public references

- [Amazon.com](https://www.amazon.com/) — public customer storefront.
- [Sell on Amazon](https://sell.amazon.com/) — public seller education and capability pages.
- [Amazon Seller Central](https://sellercentral.amazon.com/) — sign-in boundary; no private content accessed.
- [Amazon Ads](https://advertising.amazon.com/) — public advertising information.
- [About Amazon](https://www.aboutamazon.com/) — broad public company/product context; no proprietary implementation claims are made here.

## NexHaat application

Use marketplace conventions as a checklist, not a visual clone. Keep NexHaat name, original logo, Bangladesh-localized delivery and currency decisions, the Flask commerce authority, and the permanent Signature Blue identity. Do not borrow protected assets or present a feature as connected solely because a reference marketplace offers it.
