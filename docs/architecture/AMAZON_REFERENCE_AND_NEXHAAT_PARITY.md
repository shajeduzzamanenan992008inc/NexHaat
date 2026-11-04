# Amazon Shopping Reference ও NexHaat parity audit

**তারিখ:** ৪ নভেম্বর ২০২৬  
**পরিধি:** Amazon-এর public website ও Android app feature evidence, NexHaat-এর বর্তমান source status, এবং web visual refresh।  
**সীমা:** Amazon account, private session, checkout, purchase, live provider, বা production system-এ কোনো action করা হয়নি।

## প্রমাণ

### Amazon website

- REA `capture_browser_scenario` দিয়ে public `amazon.com`-এ একটি isolated Chromium session চালানো হয়। Homepage search field দৃশ্যমান ছিল; একটি সাধারণ পণ্য অনুসন্ধান submit হয়। Product detail locator timeout হওয়ায় product details, checkout, এবং order flow browser-এ যাচাই হয়নি। Search capture-এ কিছু 403/network failure ও Playwright service-worker noise ছিল; capture incomplete, তাই এটি Amazon-এর সব UI/behavior-এর প্রমাণ নয়।
- Amazon-এর নিজস্ব Alexa for Shopping তথ্য অনুযায়ী web/app-এ conversational product research, comparisons, deal discovery, price-history, price alerts, shopping guides, এবং list/cart actions আছে. [Alexa for Shopping](https://www.aboutamazon.com/news/retail/how-to-use-amazon-shopping-ai-assistant), [Price history](https://www.aboutamazon.com/news/retail/how-to-check-amazon-price-history), [100+ shopping actions](https://www.aboutamazon.com/news/retail/alexa-for-shopping-new-capabilities)
- Amazon-এর নিজস্ব organization feature-এ Buy Again, Lists, Amazon Lens, Shop by Interest, এবং Saved for Later বর্ণিত. [Amazon shopping organization features](https://www.aboutamazon.com/news/retail/amazon-shopping-features-rufus-lens)

### Amazon Android app

- এই environment-এ Amazon Android APK/app install বা launch করে REA runtime inspection করা হয়নি। Native UI/animation সম্পর্কে runtime claim করা হচ্ছে না।
- Google Play-তে Amazon Mobile LLC-র official listing-এ delivery tracking/notifications, 360° product view, “View in your room”, Lists/price-drop notifications, support chat, এবং camera-based product/barcode scan বর্ণিত. [Amazon Shopping on Google Play](https://play.google.com/store/apps/details?id=com.amazon.mShop.android.shopping)

## NexHaat feature parity

| Shopping pattern | NexHaat source evidence | Status |
|---|---|---|
| Search, category browse, result filtering/sort | `src/components/Navbar.tsx`, `src/pages/CatalogPage.tsx`, `app/services/catalog.py`, `app/api/routes/catalog.py` | Search UI + local filtering আছে; server catalogue adapter আছে। Browser journey-এর end-to-end search ফলাফল এই pass-এ পুনরায় যাচাই হয়নি। |
| Merchandising shelves, category directories, deals | `src/pages/HomePage.tsx`, `src/pages/DealsPage.tsx` | বিদ্যমান UI ও product shelves; live inventory/offer truth backend contract-নির্ভর। |
| Product detail, comparison, reviews/Q&A, bundles | `src/pages/ProductDetailPage.tsx`, `src/components/CompareModal.tsx`, `src/components/ProductReviewsSection.tsx` | UI আছে; প্রতিটি interaction-এর persistence/ownership path এই visual pass-এ যাচাই হয়নি। |
| Lists / saved items | `src/pages/WishlistPage.tsx`, `src/lib/marketplaceApi.ts`, `app/api/routes/catalog.py` | Signed-in customer wishlist API adapter আছে; guest/local behavior আলাদা। |
| Buy again | `src/pages/MyOrdersPage.tsx` | আগের order-এর product ID বর্তমান catalog-এ মিললে cart-এ যোগ করে; missing/unavailable products বাদ পড়ে। |
| Price alerts/history | `src/pages/ProductDetailPage.tsx`, `src/context/AppContext.tsx`, `src/lib/priceTrend.ts` | UI/কিছু browser-local utility আছে; server-backed historical pricing বা guaranteed notifications হিসেবে গণ্য নয়। |
| AI shopping assistant | `src/components/AIAssistantDrawer.tsx`, `server.ts` | Express Gemini route আছে; provider configuration-dependent; এটি Flask catalog/price/order authority নয়। |
| Voice search | `src/components/Navbar.tsx` | আগের আচরণ fixed demo transcript ছিল; এই pass-এ supported browser-এর Web Speech API দিয়ে transcript-ভিত্তিক search করা হয়েছে। Permission/browser support না থাকলে user-facing fallback দেখায়; audio NexHaat backend-এ পাঠানো হয় না, তবে browser-এর speech implementation কীভাবে process করে তা browser/provider-নির্ভর। |
| Photo/Lens search, AR/360° | `src/components/Navbar.tsx`, `serverVisualSearch.ts`, `server.ts` | Exact local barcode/SKU match হলে ছবি upload হয় না। অন্যথায় consent dialog-এর পর browser image-কে 1600px-এর মধ্যে JPEG করে Gemini-তে পাঠায়; Express size/type/rate/concurrency check করে কেবল sanitized search phrase ফেরায়, যা NexHaat catalog-এ খোঁজা হয়। Provider configuration-dependent; image persistence নেই। 3D/AR assets নেই/unknown. |
| Order tracking/notifications | `src/pages/MyOrdersPage.tsx`, `src/lib/marketplaceApi.ts`, Flask order API | UI/API adapters আছে; real delivery provider/tracking availability configuration-dependent। |

## এই pass-এ করা visual implementation

- Global marketplace palette ও surface/shadow tokens আপডেট করা হয়েছে; NexHaat branding ও bilingual copy রাখা হয়েছে।
- Shared web content width 1600px করা হয়েছে এবং sticky marketplace header/search focus treatment উন্নত হয়েছে।
- Home hero, product tiles, catalog, product detail-এর existing hierarchy ও controls বজায় রেখে subtle entrance/hover motion যোগ হয়েছে।
- Product-card cart action-এ desktop-এ “Add” label দেখায়; mobile-এ compact icon action থাকে।
- Navbar-এর পুরনো fixed “Mango found” demo-এর পরিবর্তে image search যোগ হয়েছে; 10 MB input limit, JPG/PNG/WebP allowlist, 40MP pixel cap, local exact barcode/SKU shortcut, এবং 1600px JPEG re-encode আছে। ছবি পাঠানোর আগে বাংলা/ইংরেজিতে Google Gemini-তে image processing-এর disclosure ও continue action লাগে।
- `/api/gemini/visual-search` route সর্বোচ্চ 8 MiB decoded image, actual MIME signature, JSON object, bn/en language, 5 requests/minute, 4 concurrent provider calls, এবং 80 output tokens সীমাবদ্ধ করে। Provider key server-side; response-এ শুধু sanitized one-line catalog query থাকে। Route request image save/log/return করে না। Gemini-র query বাস্তব listing/price/stock নয়; সেগুলো NexHaat catalog ফলাফল থেকে আসে।
- Voice search এখন supported browser-এর Web Speech API ব্যবহার করে; microphone permission ও browser support না থাকলে fallback message দেয়।
- Motion CSS-এ বিদ্যমান `prefers-reduced-motion: reduce` override প্রযোজ্য থাকে।
- Android Material 3 palette, surface colors, এবং native product-card shape/image treatment web refresh-এর সঙ্গে মিলেছে; আগে থেকে থাকা Compose press animation রাখা হয়েছে।
- Flask, database, checkout/payment rules, Android API/navigation/business logic, dependencies, এবং external integrations পরিবর্তন করা হয়নি। Express-এ শুধু additive visual-search route যোগ হয়েছে; Gemini provider call live verification-এ চালানো হয়নি।

## NexHaat local runtime evidence

- REA Chromium 156 scenario-তে নতুন build local `http://127.0.0.2:3000/` থেকে খোলা হয়। 1280×720-এ home heading → image-search disclosure → cancel/close → reopen সফল; screenshot-এ modal viewport-এর মাঝখানে দেখা গেছে। 390×844-এ hamburger → “Search by image” → consent dialog সফল; mobile screenshot-এ layout/controls viewport-এর মধ্যে আছে। পূর্বের 1440×960 capture-এ Browse Catalog → catalog heading → first product → product detail heading সফল হয়েছিল।
- Captured page-level JavaScript errors ছিল না। Dev middleware-এ Vite HMR WebSocket port `24678` অন্য listener-এ ব্যবহৃত হওয়ায় HMR socket handshake fail করে; page rendering ও interactions কাজ করেছে। Flask `:5000` listener অনুপস্থিত থাকায় session check warning ছিল; PWA install-prompt informational log-ও দেখা গেছে। Express visual-search malformed `{}` request `400` দিয়েছে (Vite fallback `404` নয়). Gemini credentials উপলভ্য না থাকায় provider request চালানো হয়নি।
- Local app একটি Firebase/Firestore listener request করেছিল; capture-এ request/response body বা headers রাখা হয়নি এবং কোনো write/action করা হয়নি। এই কারণে Firebase production/development configuration-এর health এই evidence থেকে প্রমাণিত নয়।
- CSS `prefers-reduced-motion: reduce` override source-এ আছে; REA launch-context default reduced-motion setting-এ modal/navigation UI capture হয়েছে। `no-preference` animation timeline-এ frame-by-frame motion comparison করা হয়নি। Android runtime/emulator QA ও screenshot capture-ও করা হয়নি।
- `npm run build` PASS (large JS chunk warning: main bundle 1,093.79 kB minified)। `npm test` PASS (12/12 Node security/API tests; Gemini mock adapter ব্যবহৃত)। `git diff --check` PASS; existing workflow files-এর CRLF/LF warning এসেছে।
- Local production-mode Express startup NOT PASS: existing `app.get('*')` catch-all বর্তমান installed `path-to-regexp`-এ `Missing parameter name at index 1: *` দেয়। এই user-modified route এই task-এ বদলানো হয়নি; development preview runtime আলাদাভাবে কাজ করেছে।
- Android build/unit test NOT RUN: বর্তমান shell-এ Java 8.0.511, কিন্তু repo wrapper Gradle 9.7.1; Gradle 9-এর build daemon-এ Java 17+ প্রয়োজন. [Gradle Java compatibility](https://docs.gradle.org/9.7.1/userguide/compatibility.html)

## সীমাবদ্ধতা ও পরবর্তী প্রয়োজন

- Amazon-এর সম্পূর্ণ catalog, recommender, fulfilment, loyalty, AR assets বা private account flows public web capture থেকে জানা বা পুনর্নির্মাণ করা হয়নি।
- NexHaat source-এ UI থাকা মানেই feature-এর end-to-end persistence বা live provider availability নয়। Checkout/order/payment-এর authoritative path Flask-এর মাধ্যমে আলাদা করে যাচাই করতে হবে।
- Amazon app-এর visual hierarchy/animation native runtime-এ পরীক্ষা হয়নি; NexHaat Android theme source-এ aligned, কিন্তু emulator/device runtime evidence নেই।
- Photo search-এর external data transfer-এ user explicit approval দিয়েছেন। UI per-search disclosure দেখায়; image browser-এ resize/re-encode হয় এবং NexHaat route-এ persistence নেই। Automated route tests provider credentials ছাড়াই চলে; live Gemini response/provider retention policy এই local verification-এ পরীক্ষা করা হয়নি।
