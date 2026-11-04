# `marketplaceApi.ts` রিকভারি রিপোর্ট

**তারিখ:** 2026-11-04  
**রিপোজিটরি:** `D:\FTP\NexHaat`  
**ব্রাঞ্চ / HEAD:** `main` / `19d027eb53fec33d0f6e55407d6b3fb8b9c7e0e2`

## সিদ্ধান্ত

আগের uncommitted `src/lib/marketplaceApi.ts`-এর হুবহু কপি পাওয়া যায়নি। আগের ফাইলের pre-overwrite SHA-256 বা সংরক্ষিত byte copy নেই, তাই byte-for-byte recovery প্রমাণ করা সম্ভব নয়। বর্তমান reconstructed ফাইল অক্ষত রাখা হয়েছে; কোনো restoration বা source overwrite করা হয়নি।

বর্তমান ফাইলের আলাদা snapshot:

- কপি: `docs/recovery/marketplaceApi.reconstructed-20261104.ts.txt`
- snapshot আকার: 16,850 bytes; recovery audit-এর সময় source ও snapshot একই ছিল এবং hash ছিল `5135A17587A366FE57548D3F7AA1C5D12FC4D0089BB1E150C7D663E439B8C16E`।
- Phase 1 API contract repair-এর পরে বর্তমান source 24,999 bytes; SHA-256 `572CEA4D087F2D18BDECFD815620B5E5E44F62A26F1F40A650B35ECC8C1EF0F4`।
- baseline snapshot অপরিবর্তিত আছে; বর্তমান source hash-কে pre-overwrite বা recovered historical source-এর hash হিসেবে গণ্য করা যাবে না।

## Recovery উৎস পরীক্ষা

| উৎস | পর্যবেক্ষণ | ফল |
|---|---|---|
| VS Code `User\History` / Timeline backing files | 880টি file ও 161টি `entries.json` পাওয়া গেছে; কোনো entry-তে `marketplaceApi.ts` নেই | আগের ফাইলের কপি পাওয়া যায়নি |
| VS Code `Backups` | directory-তে 0টি file | কপি নেই |
| VS Code workspace storage | `state.vscdb`-তে `agentSessions.sessionChanges` key পাওয়া গেছে; সংশ্লিষ্ট value-তে `marketplaceApi.ts` বা review/checkout function text নেই | কপি নেই |
| VS Code global storage | Local History snapshot রাখে এমন extension directory নেই | সম্ভাব্য extension backup নেই |
| Workspace, `%TEMP%`, sibling repository | repo-র `src/lib` ছাড়া অন্য `marketplaceApi.ts` কপি পাওয়া যায়নি; `%TEMP%`-এ filename match নেই | কপি পাওয়া যায়নি |
| Git history | `git log --all --follow`-এ 4টি tracked version; `git stash list` ফাঁকা; 1টি worktree | committed version-গুলো uncommitted সংস্করণ নয় |
| Git unreachable objects | 1,278টি unreachable blob; 10–26 KB সীমার 201টি blob-এ target catalog/review/checkout signature পাওয়া যায়নি | সম্ভাব্য কপি পাওয়া যায়নি |
| Filesystem snapshots | `Win32_ShadowCopy` কোনো snapshot ফেরত দেয়নি | snapshot recovery source নেই |
| Build artifacts | বর্তমান bundle `dist/assets/index-CjlE3IFQ.js` reconstructed source build-এর; `.map` ফাইল নেই। আগের `index-kLF5RpBy.js` asset আর নেই | bundle থেকে মূল TypeScript ফেরত আনা যায় না |

REA MCP tools এই audit session-এ উপলভ্য ছিল না; তাই REA evidence store থেকে আলাদা recovery scan করা যায়নি।

## ফাংশন ও API সামঞ্জস্য

নিচের তুলনাটি বর্তমান ফাইল, `HEAD`, বর্তমান callers, Flask route/serializer এবং আগের tool output-এ ধরা function নামের ভিত্তিতে। আগের পূর্ণ source না থাকায় body-level সমতা যাচাই করা যায়নি।

| ক্ষেত্র | `HEAD`-এ | বর্তমান reconstructed ফাইল | Caller / server contract | যাচাই ও সীমা |
|---|---|---|---|---|
| `requestApi` | আছে | আছে; cookie credentials, state-changing request-এ CSRF token, envelope/error parsing | Flask `/api/v1` envelope | TypeScript lint/build পাস; prior body-এর exact আচরণ অজানা |
| Catalog mapping ও initial fetch | আছে | আছে; response shape যাচাই, invalid product price fail-closed, rating/review count optional; seed/localStorage fallback বন্ধ | `/api/v1/categories`, `/api/v1/products` | API adapter test, live empty-catalog browser check, lint/build পাস; populated catalog runtime অযাচাইকৃত |
| `fetchMarketplaceCatalogPage` | নেই | আছে; query, category slug, price, rating, stock, discount, sort ও pagination পাঠায় | Catalog page; `/products` ও `/categories/<slug>` | এটি NUL incident-এর পর যোগ করা বর্তমান implementation, আগের uncommitted source-এর অংশ ছিল না |
| Cart, wishlist, order, timeline, notification adapters | অধিকাংশ আছে | আছে | `AppContext`, cart, orders ও notification views | COD checkout/cart backend test-সহ targeted tests পাস; exact আগের body যাচাই অসম্ভব |
| Review mapping, list ও submit | নেই | আছে: `mapReview`, `fetchMarketplaceProductReviews`, `submitMarketplaceProductReview`; malformed success payload-এ `INVALID_RESPONSE`, fake empty review list নয় | `AppContext`, `ProductReviewsSection`; `/products/<id>/reviews`; serializer `review_to_dict` | Node adapter tests ও backend review tests পাস; live product/review browser journey সম্ভব হয়নি, disposable DB-তে product নেই |
| Helpful vote | নেই | আছে: `toggleMarketplaceReviewHelpful`; response fields যাচাই করে | `ProductReviewsSection`; `/reviews/<review_id>/helpful` | Node adapter tests ও backend review tests পাস; original adapter-এর response handling অজানা |
| COD checkout | আছে | আছে: `submitMarketplaceCheckout` | `/api/v1/checkout`, `payment_method: cod` | cart/checkout/order route test পাস |
| SSLCOMMERZ checkout | নেই | `createMarketplaceCheckout` orders, nullable `checkout_url`, এবং nullable optional `checkout_group`, `payment_status`, `payment_status_url` ফেরায়; COD order-only | `CheckoutPage`; `/api/v1/checkout` | Node tests ও Flask nullable-provider-link contract test পাস; sandbox/real provider payment চালানো হয়নি। আগের source-এ metadata map করা হত কি না অজানা |
| Error/CSRF boundary | `requestApi`-তে আছে | envelope, HTTP status/code, normalized network error, CSRF wrapper error map হয়; `AbortError` propagate হয় | Flask CSRF এবং API error envelope | Node error tests, type check ও build পাস; live provider/payment error path অযাচাইকৃত |

আগের source-এর `rg` output-এ review helper/list/submit এবং `createMarketplaceCheckout` নামগুলো দেখা গিয়েছিল। বর্তমান reconstruction-এ ওই নামগুলো আছে, তবে আগের output-এ function-গুলোর ক্রম বর্তমান ফাইলের ক্রমের থেকে আলাদা ছিল। নামের মিল byte বা behavior সমতা প্রমাণ করে না।

## Phase 1 API contract repair follow-up — 2026-11-04

- `MarketplaceCheckoutResult` এখন server contract-এর online-payment metadata বহন করে। `checkout_url` null হলে null-ই থাকে; অনুপস্থিত optional metadata বানিয়ে যোগ করা হয় না। COD response order-only রয়ে গেছে।
- Catalog ও review adapter malformed success response-কে `MarketplaceApiError` হিসেবে reject করে। Invalid price-কে শূন্যে নামানো হয় না; backend না দিলে rating/review count-ও কৃত্রিমভাবে তৈরি হয় না। Product metric type optional করা হয়েছে এবং সংশ্লিষ্ট UI checks যোগ হয়েছে।
- `AppContext` product/category state খালি দিয়ে শুরু হয়, `INITIAL_PRODUCTS`, `INITIAL_CATEGORIES` বা `nexhaat_products` থেকে catalog hydrate করে না, এবং API error হলে খালি রাখে। পুরোনো localStorage entry মোছা হয়নি। `ProductReviewsSection`-ও খালি review list দিয়ে শুরু করে এবং load error আলাদা দেখায়।
- Verification: `node --import tsx --test tests-node/marketplace-api.test.mjs` — 20 passed; targeted Python catalog/checkout/review suites — 23 passed; `npm.cmd run lint` — pass; production build — pass (2,047 modules)। Build-এর main chunk 1,074.18 kB, gzip 285.09 kB; >500 kB warning রয়ে গেছে। Full Python suite, provider sandbox এবং real payment **NOT RUN**।
- Disposable SQLite catalog-এ product/category row শূন্য ছিল। Same-origin Vite proxy দিয়ে বর্তমান app-এ live empty state দেখা গেছে; কোনো fake product card দেখা যায়নি। Product না থাকায় review UI-তে যাওয়া যায়নি; review fallback আচরণ adapter tests ও source path দিয়ে যাচাই হয়েছে, live review journey দিয়ে নয়। Populated catalog থেকে product detail/review/checkout browser workflow চালানো যায়নি। REA MCP tool উপলভ্য ছিল না; browser check CUA দিয়ে করা হয়েছে।
- আগের uncommitted সংস্করণের recovery সীমাবদ্ধতা অপরিবর্তিত: exact historical parity নিশ্চিত নয়। Phase 1-এর বিস্তারিত [API Contract Repair Report](../implementation/PHASE_1_API_CONTRACT_REPAIR_REPORT.md)-এ।

## রিকভারি সিদ্ধান্ত ও নিরাপদ পরবর্তী পদক্ষেপ

1. বর্তমান source ও আলাদা snapshot সংরক্ষিত থাকবে; কোনো Git restore বা overwrite করা হয়নি।
2. পাওয়া যায়নি এমন আগের body বা metadata কল্পনা করে যোগ করা হয়নি।
3. ভবিষ্যতে কোনো পুরনো candidate পাওয়া গেলে আগে আলাদা ফাইলে রাখতে হবে, SHA-256 ও diff তুলতে হবে, তারপর caller/API/test যাচাই করতে হবে। বর্তমান source বদলানোর আগে review approval নিতে হবে।
4. আগের source-এর byte-level recovery অসম্ভব বলে recovery ঝুঁকি খোলা থাকছে; review/online checkout adapter-এর আচরণ current API contract-এর সঙ্গে মেলে, কিন্তু আগের uncommitted আচরণের পূর্ণতা নিশ্চিত নয়।

