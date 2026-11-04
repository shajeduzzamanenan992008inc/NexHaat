# NexHaat Phase 1 — Marketplace API Contract Repair

**তারিখ:** 2026-11-04  
**রিপোজিটরি:** `D:\FTP\NexHaat`  
**ব্রাঞ্চ / HEAD:** `main` / `19d027eb53fec33d0f6e55407d6b3fb8b9c7e0e2`

## ফলাফল

Flask marketplace API-র বর্তমান response contract-এর সঙ্গে React adapter-কে সামঞ্জস্য করা হয়েছে। Catalog, review এবং online checkout response এখন যাচাই করা হয়; nullable/optional field অনুমান করে বানানো হয় না। React catalog seed/localStorage fallback বন্ধ করা হয়েছে, যাতে API failure বা empty catalog-এ demo product live listing হিসেবে না দেখা যায়।

এই কাজ আগের uncommitted `marketplaceApi.ts` উদ্ধার করেনি। Recovery audit-এর baseline snapshot অপরিবর্তিত। Baseline ও repaired-source hash আলাদা করে [recovery report](../recovery/MARKETPLACE_API_RECOVERY_REPORT.md)-এ লেখা আছে; byte-for-byte historical parity দাবি করা হচ্ছে না।

## পরিবর্তন

### Checkout contract

- Online checkout result-এ `orders`, nullable `checkout_url`, এবং optional nullable `checkout_group`, `payment_status`, `payment_status_url` আছে।
- Payment status শুধু backend model-এর supported state গ্রহণ করে। Malformed order/status হলে adapter `INVALID_RESPONSE` error দেয়।
- COD checkout `payment_method: 'cod'` পাঠায় এবং order-only result contract রাখে।
- `CheckoutPage`-এর HTTPS gateway allowlist অপরিবর্তিত। কোনো provider request বা real payment চালানো হয়নি।

### Catalog, product metrics ও errors

- Catalog endpoint data array না দিলে malformed response error হয়; server থেকে আসা `[]` বৈধ empty catalog।
- Invalid price-কে zero fallback করা হয় না। Variant price-ও product price দিয়ে প্রতিস্থাপন করা হয় না।
- Backend product serializer rating/review count না দিলে UI-তে metric অনুপস্থিত থাকে; `Product.rating` ও `Product.review_count` optional করা হয়েছে এবং metric consumers guard করা হয়েছে।
- HTTP/API envelope errors `MarketplaceApiError`-এ status ও code-সহ map হয়; network failure-এ নিরাপদ `NETWORK_ERROR` হয় এবং `AbortError` propagate হয়।

### Reviews ও fallback state

- Review list/create/helpful response shape validate হয়। Malformed success response fake empty reviews বা success state হিসেবে ফেরে না।
- `ProductReviewsSection` খালি state দিয়ে শুরু করে, API result এলে সেটি দেখায়, failure হলে error দেখায়।
- `AppContext` catalog products/categories খালি দিয়ে শুরু করে ও Flask response-ই ব্যবহার করে। API ব্যর্থ হলেও কোনো seed/localStorage catalog রাখা হয় না। `nexhaat_products` legacy key মুছে ফেলা হয়নি; code path সেটি আর hydrate বা update করে না.
- Seller/admin preview-তে product mutation-ների সম্পূর্ণ Flask backend integration এই কাজের অংশ ছিল না; local preview mutation-কে server-authoritative capability বলা হচ্ছে না।

## ফাইল

- `src/lib/marketplaceApi.ts` — checkout metadata/type mapping, payload validation, safe error normalization, optional catalog metrics।
- `src/types/index.ts` — backend-optional rating/review count types।
- `src/context/AppContext.tsx`, `src/App.tsx` — authoritative catalog-only state এবং সঠিক loading/error notice।
- `src/lib/priceIntelligence.ts`, `src/components/PriceIntelligenceCard.tsx`, `src/components/AIAssistantDrawer.tsx`, `src/components/CompareModal.tsx`, `src/components/ProductCard.tsx`, `src/pages/HomePage.tsx`, `src/pages/ProductDetailPage.tsx` — অনুপস্থিত review metrics-এর নিরাপদ rendering।
- `tests-node/marketplace-api.test.mjs` — catalog/review/checkout/error adapter regression coverage।
- `tests/test_api_foundation.py` — nullable SSLCOMMERZ provider-link response contract test; provider/payment বাস্তবে চালায় না।
- `docs/recovery/MARKETPLACE_API_RECOVERY_REPORT.md`, `docs/recovery/PROJECT_INTEGRITY_REPORT.md`, `docs/implementation/IMPLEMENTATION_TRACKER.md` — recovery/integrity evidence এবং task status update।

## যাচাই

| Command / workflow | ফল |
|---|---|
| `npm.cmd run lint` | **PASS** (`tsc --noEmit`) |
| `node --import tsx --test tests-node/marketplace-api.test.mjs` | **PASS — 20 passed** |
| Targeted `pytest` catalog, checkout, reviews ও review-trust suite | **PASS — 23 passed in 59.65s** |
| `npm.cmd run build -- --outDir C:\Users\enan9\AppData\Local\Temp\nexhaat-phase1-api-build-20261104-final` | **PASS** — 2,047 modules, 2m25s; main chunk 1,074.18 kB / gzip 285.09 kB; Vite >500 kB warning খোলা |
| Live browser via same-origin Vite proxy to Flask, disposable SQLite | **PASS: empty catalog state, no fake product cards**; zero products থাকায় review UI ও populated product/checkout journey যাচাই করা যায়নি |

Python suite-এ চালানো targeted command:

```text
python -m pytest -q -p no:cacheprovider tests/test_api_foundation.py::test_api_sslcommerz_checkout_returns_nullable_provider_link_and_payment_contract tests/test_api_foundation.py::test_api_catalog_search_filters_and_paginates tests/test_api_foundation.py::test_api_cart_checkout_orders_and_cancel_restore_inventory tests/test_reviews.py tests/test_review_trust.py
```

Python startup-এ `.pth` থেকে `D:\FTP\Telegram-Bot\src` অনুপস্থিত বলে harmless warning এসেছিল; suite তবুও 23 tests pass করেছে।

`python -m pytest -q` full suite **NOT RUN**। SSLCOMMERZ sandbox, real payment/provider callback, populated catalog end-to-end, customer-authenticated review write এবং production environment **NOT RUN**। Browser check-এ direct cross-origin API origin-এর প্রথম setup CORS-এ ব্যর্থ হয়; same-origin dev proxy দিয়ে সফল empty-catalog check করা হয়েছে। REA MCP tools এই session-এ অনুপলব্ধ ছিল; live browser automation CUA দিয়ে করা হয়েছে।

## সীমাবদ্ধতা ও নিরাপত্তা

- Disposable DB-তে products/categories শূন্য; তাই live populated listing ও product-linked review যাচাই অসম্ভব ছিল।
- Original uncommitted source recover হয়নি; reconstructed baseline snapshot অক্ষত, কিন্তু old implementation-এর exact body-level behavior অজানা।
- `dev-dist/` আগেই untracked ছিল এবং Vite PWA plugin পরীক্ষার সময় সেখানে service-worker output লিখেছে। আগের per-file contents সংরক্ষিত না থাকায় byte-level পূর্বাবস্থা নিশ্চিত নয়; বর্তমান output temp backup-এ রাখা হয়েছে। বিস্তারিত [project integrity report](../recovery/PROJECT_INTEGRITY_REPORT.md)-এ।
- API contract repair কোনো migration, production DB operation, external message, provider transaction, commit, push বা deployment করেনি।
- Existing worktree-তে পূর্বের staged/unstaged/untracked পরিবর্তন ছিল। এই কাজ কোনো existing user change restore, reset, clean বা stage করেনি।
