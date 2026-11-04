# NexHaat project integrity report

**তারিখ:** 2026-11-04  
**রিপোজিটরি:** `D:\FTP\NexHaat`  
**ব্রাঞ্চ / HEAD:** `main` / `19d027eb53fec33d0f6e55407d6b3fb8b9c7e0e2`

## বর্তমান Git অবস্থা

- Recovery শুরুর সময় branch `main`, `origin/main`-এর সঙ্গে ahead/behind `0/0` ছিল।
- Staged পরিবর্তন ছিল **0**।
- পূর্ণ `git status --porcelain=v2 --branch` snapshot: [GIT_STATUS_20261104.txt](GIT_STATUS_20261104.txt)।
- Snapshot নেওয়ার সময় 114টি modified, 38টি deleted এবং 35টি untracked status entry ছিল। এগুলোতে OMEGA-র আগের source, documentation, user artifacts ও cache status আছে; তদন্তে এগুলো restore, clean বা stage করা হয়নি।
- Snapshot-এর পরে যোগ করা recovery backup ও এই report-গুলো recovery নথি; এগুলোও stage বা commit করা হয়নি।
- `git worktree list`: একটি worktree—এই repository। `git stash list`: খালি।

## `marketplaceApi.ts` সংরক্ষণ

- `src/lib/marketplaceApi.ts` এই audit-এ overwrite করা হয়নি।
- Snapshot path: `docs/recovery/marketplaceApi.reconstructed-20261104.ts.txt`।
- Source ও snapshot: 16,850 bytes; SHA-256 `5135A17587A366FE57548D3F7AA1C5D12FC4D0089BB1E150C7D663E439B8C16E`—পরীক্ষার সময় hash মিলেছে।
- আগের pre-overwrite file hash অনুপস্থিত; বর্তমান hash-কে আগের source-এর hash হিসেবে গণ্য করা যাবে না। বিস্তারিত তুলনা [MARKETPLACE_API_RECOVERY_REPORT.md](MARKETPLACE_API_RECOVERY_REPORT.md)-এ।

## Android Gradle cache

নিচের পাঁচটি tracked cache file বর্তমানে modified। পূর্বের Android compile run-এ এগুলো মুছে থাকা অবস্থা থেকে তৈরি/পরিবর্তিত হয়েছিল; recovery audit-এ এগুলো সরানো হয়নি:

- `android/.gradle/9.7.1/executionHistory/executionHistory.bin`
- `android/.gradle/9.7.1/fileHashes/fileHashes.bin`
- `android/.gradle/9.7.1/fileHashes/resourceHashesCache.bin`
- `android/.gradle/buildOutputCleanup/cache.properties`
- `android/.gradle/buildOutputCleanup/outputFiles.bin`

`android/.gradle/8.11.1`-এর সাতটি cache file এবং `android/.gradle/9.7.1/checksums/sha1-checksums.bin` এখনও deleted status-এ আছে। `android/local.properties`-ও deleted। এগুলোর কোনোটিই ফিরিয়ে আনা বা সরানো হয়নি।

## লোকাল সার্ভার ও database

- Port **3000**: PID `8544`, `node.exe`, `server.ts` marker ও `D:\FTP\NexHaat` path match করেছে। এটি পূর্বে চালু করা Vite/Node development server।
- Port **5100**: PID `2732`, `python.exe`, Flask `run.py` server marker; PID `1916`-এর `flask.exe` parent। এটি পূর্বে চালু করা local Flask test server। কোনো process terminate করা হয়নি।
- Flask server-এর `DATABASE_URL` process-scoped disposable SQLite file-এ ছিল; production database নয়। Read-only যাচাইয়ে Alembic revision `20261104_01`, 56টি table এবং `products` table-এ 0 row পাওয়া গেছে। Database `%TEMP%`-এ রয়ে গেছে; এটি মুছে ফেলা হয়নি।
- এই audit-এ production DB, production migration, external provider বা payment transaction ব্যবহার করা হয়নি।

## Verification

| যাচাই | ফল |
|---|---|
| Targeted Python tests: catalog search/pagination, COD checkout/order/cancel, review ও review-trust suites | **22 passed** (`123.91s`) |
| `npm.cmd run lint` / `tsc --noEmit` | **PASS** |
| Production Vite build | এই recovery audit-এ পুনরায় চালানো হয়নি। একই source hash-এ আগের run **PASS**; `dist/assets/index-CjlE3IFQ.js` 1,090,208 bytes, gzip 291.11 kB; Vite main-chunk size warning ছিল |
| Full Python suite | **NOT RUN** এই audit-এ |
| SSLCOMMERZ sandbox / real provider | **NOT RUN**; কোনো payment করা হয়নি |
| Live UI/browser flow | Read-only browser check-এ `http://127.0.0.1:3000/`-এ NexHaat page লোড হয়েছে। UI বলেছে live catalog unavailable এবং product/promotion preview data দেখাচ্ছে। Catalog/review/checkout-এর end-to-end browser flow যাচাই হয়নি। REA MCP tool এই session-এ অনুপস্থিত |
| `git diff --check` targeted recovery files | error ছিল না; CRLF/LF warning ছিল |

আগের broad `git diff --check`-এ `src/pages/ProductDetailPage.tsx:10`-এর trailing whitespace ধরা পড়েছিল; সেটি এই audit-এ পরিবর্তন করা হয়নি।

## Phase 1 API contract repair integrity update — 2026-11-04

- Recovery baseline snapshot `marketplaceApi.reconstructed-20261104.ts.txt` অপরিবর্তিত: 16,850 bytes, SHA-256 `5135A17587A366FE57548D3F7AA1C5D12FC4D0089BB1E150C7D663E439B8C16E`। Phase 1-এ সংশোধিত `src/lib/marketplaceApi.ts`: 24,999 bytes, SHA-256 `572CEA4D087F2D18BDECFD815620B5E5E44F62A26F1F40A650B35ECC8C1EF0F4`।
- Phase 1-এর targeted Python suite 23 passed (`59.65s`); Node marketplace adapter suite 20 passed; `npm.cmd run lint` passed; production build passed (2,047 modules, main chunk 1,074.18 kB, gzip 285.09 kB)। Full Python suite **NOT RUN**। Build temporary output-এ হয়েছে; repository `dist/` প্রতিস্থাপন করা হয়নি।
- Python startup-এ `.pth` warning ছিল যে `D:\FTP\Telegram-Bot\src` path অনুপস্থিত; targeted suite warning সত্ত্বেও সফল হয়েছে।
- Browser check-এ direct cross-origin API origin-এর কারণে প্রথম চেষ্টা CORS-এ ব্যর্থ হয়েছিল। Same-origin Vite proxy (`127.0.0.1:3001` → Flask `127.0.0.1:5000`) দিয়ে পুনরায় চালালে disposable SQLite থেকে empty catalog এসেছে এবং UI empty state দেখিয়েছে; কোনো fake product card দেখা যায়নি। Product না থাকায় review UI খোলা যায়নি।
- Phase 1-এর পরীক্ষার জন্য চালু করা Vite `3001` ও Flask `5000` process বন্ধ করা হয়েছে। Port `5100`-এর PID `2732`/parent `1916`-কে task-এর disposable-DB Flask run হিসেবে যাচাই করে বন্ধ করা হয়েছে; এখন port `5100` free। Port `3000`-এর existing `node.exe` PID `8544` এই কাজের বাইরে ছিল এবং untouched। Disposable SQLite file রাখা হয়েছে; কোনো production DB বা migration স্পর্শ করা হয়নি।
- **Generated-output integrity limitation:** `dev-dist/` Phase 1-এর আগে untracked ছিল, কিন্তু dev server চালুর আগে এর per-file snapshot নেওয়া হয়নি। Vite PWA plugin বর্তমান run-এ `registerSW.js`, `sw.js` ও `workbox-afac4cd2.js` লিখেছে/আপডেট করেছে। আগের contents byte-for-byte recover বা unchanged ছিল প্রমাণ করা যাচ্ছে না। বর্তমান output-এর backup `C:\Users\enan9\AppData\Local\Temp\nexhaat-dev-dist-post-phase1-20261104-files`-এ রাখা হয়েছে; production `dist/`-এর `workbox-835c8c05.js` আলাদা artifact, তাই সেটিকে replacement হিসেবে ব্যবহার করা হয়নি। কোনো `dev-dist/` file মুছে ফেলা হয়নি।
- Adapter repair-এ user work stage/commit করা হয়নি; no reset/clean/restore, push, deployment, provider transaction বা production data change হয়েছে। `nexhaat_products` legacy localStorage entry মুছে ফেলা হয়নি; React catalog সেটি আর পড়ে না।

## কার্যক্রম ও খোলা ঝুঁকি

- কোনো commit, push, merge, deployment বা source restoration হয়নি।
- কোনো user change, unrelated generated file বা deleted `.gradle`/`local.properties` file restore/remove করা হয়নি।
- Marketplace adapter-এর আগের uncommitted body উদ্ধার করা যায়নি; recovery limitation খোলা আছে।
- Phase status বদলানো হয়নি; tracker-এ recovery addendum যোগ করা হয়েছে।

