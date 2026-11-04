# NexHaat Phase 0 — REA and System Audit

**Audit date:** 2026-11-03 (Asia/Dhaka)  
**Repository:** `D:\FTP\NexHaat`  
**Branch / local HEAD at audit start:** `main` / `19d027eb53fec33d0f6e55407d6b3fb8b9c7e0e2`  
**Audit type:** Source and configuration review; no production systems were changed.

## REA capability evidence

| Capability | Status | Evidence and limit |
|---|---|---|
| REA MCP connection | PARTIAL | `inspect_analysis_settings` returned REA runtime admission settings. This proves that this MCP tool responded, not that every REA provider is healthy. |
| REA runtime/provider state | UNKNOWN | Runtime settings reported active values as `not_observed`; no provider was confirmed usable for this repository. |
| Workspace access through REA | NOT TESTED | No successful REA source-analysis result was returned for this workspace. |
| Browser inspection | BLOCKED | `list_browser_targets` against `http://127.0.0.1:9222` reported the endpoint unreachable; no page target was available. |
| Static JavaScript application analysis | BLOCKED | Codex rejected the `analyze_javascript_application` MCP request because the approval policy is `never`; REA did not return analysis evidence. The request was not retried or bypassed. |
| REA CLI | NOT AVAILABLE | `rea` was not found in the local command environment. |
| REA editing, testing, orchestration, independent review | NOT OBSERVED | The available REA tools discovered were artifact/runtime reverse-engineering tools; no verified REA coding-agent or test-run result was available. Codex tools and explicitly requested Codex specialist agents were used for repository work. |
| Provider integration | UNKNOWN | No provider execution or external integration was tested. |

## Confirmed architecture and scope

- Flask, SQLAlchemy, and Alembic remain the authoritative source for identities, permissions, catalog, cart, checkout, orders, payment state, seller operations, and persisted marketplace data.
- React/Vite and Android/Compose are distinct clients with different API coverage. A screen or local demo state is not evidence of an end-to-end Flask integration.
- Express remains the AI/auxiliary boundary. No marketplace authority was moved into it.
- Local state at audit start already contained substantial user changes: 83 tracked paths were changed/deleted and 25 untracked paths existed. These were treated as pre-existing work and preserved. The baseline Git status was clean of staged changes.
- Local `HEAD` was `19d027e`; GitHub's latest CI evidence available to the audit was for a different SHA, `1fc9dccfd6827a3e788c238794034874f97728ea`. Remote CI results below are not results for the current local tree.

## Confirmed integration and security findings

| Area | Finding | Status |
|---|---|---|
| React checkout | Guest/non-Flask checkout waited 700 ms, created an app-local order, and set non-COD payment to `paid`. Flask checkout requires a signed-in customer and is authoritative. | Confirmed high-risk client fallback; removed locally. Checkout now calls Flask for COD and SSLCommerz. No hosted-payment runtime test was run. |
| Android seller portal | API failure was converted into fabricated dashboard values and an empty successful order list. | Confirmed misleading success; local implementation now presents an error with retry. Android build/device behavior is NOT TESTED. |
| Firebase rules | `/test/{docId}` allowed anonymous read and write despite the default-deny catch-all. `/orders` and `/reviews` also allowed client writes that could bypass Flask payment/order and delivered-purchase/moderation rules. | Public `/test` exception removed; client order/review writes are denied while permitted reads remain. Other Firebase rules were not comprehensively reviewed, and no emulator test was available. |
| Web feature parity | Catalog, cart, wishlist, customer order/checkout, and notifications have Flask adapters. Seller/admin/rider flows, reviews, support, and social authentication have local, partial, or unconnected behavior; inspect each journey before claiming parity. | PARTIAL; source audit only. |
| Android feature parity | Android has auth, catalog, cart, checkout, wishlist, notifications, and customer orders. It lacks several web/backend portal and support/review capabilities. | PARTIAL; no device test. |
| Social login | Flask `/api/v1/auth/social-login` deliberately fails closed with `SOCIAL_LOGIN_UNAVAILABLE`; Firebase web sign-in does not establish a Flask marketplace session. | Confirmed configuration/integration boundary; no provider change made. |
| Two-factor authentication | Existing local work adds TOTP and backup-code paths. Initial review found TOTP replay-step check and update were separate operations, and crypto code had a non-AES fallback when `cryptography` was absent. | Atomic replay and backup-code consumption and fail-closed AES-GCM are implemented. Targeted suite: 14 passed; targeted Ruff: passed. No production claim. |
| Support | Flask has database-backed server-rendered support; React ticket confirmation is local/static and there is no verified client API adapter. | PARTIAL. |
| Motion | Web and Android tokens existed but were barely consumed. Web splash showed a simulated secure-session progress message; several animations remained local/hard-coded. | Shared 100–450 ms timings, reduced-motion safeguards, lighter confetti, brief non-blocking splash, and Android product-card token use are implemented. Platform runtime remains NOT TESTED. |

## Remote CI evidence available at audit time

GitHub Actions run `41643034411` for SHA `1fc9dccfd6827a3e788c238794034874f97728ea` failed:

- Python 3.11–3.14 compile/install/dependency/migration/pytest steps passed in that remote run, then `git diff --check` failed on trailing whitespace in the two Azure workflow files.
- Ruff reported 24 errors. The complete diagnostics still need to be reconciled against this local tree before making unrelated lint edits.
- Structure validation failed because `package-lock.json` was absent.
- Web build job failed before install because `actions/setup-node` was configured to cache from the absent `package-lock.json`; build, lint, and Node tests did not run in that job.
- `main_nexhut` Azure login failed with “No subscriptions found”; its deploy step was skipped. Another remote workflow reported a completed deploy action for `main_nexhaat`, but that was not triggered by this task and does not prove application health.

These are historical remote results for another commit. No CI or deployment workflow was triggered by this audit.

## Local verification and data safety

- `git rev-parse HEAD`: `19d027eb53fec33d0f6e55407d6b3fb8b9c7e0e2`.
- `git status --short --branch`: `main...origin/main`, with the pre-existing changes summarized above.
- `python -m flask --app run.py db heads`: one local Alembic head, `20261104_01`; no migration was applied. The revision is dated after the audit date and requires history review before any schema operation.
- `python -m pytest -q` first hit 12 `PermissionError` errors because pytest could not enumerate the pre-existing `%TEMP%\pytest-of-enan9` directory; 323 tests passed. Rerunning with `python -m pytest -q --basetemp=.pytest_cache/nexhaat-full-20261103` passed: **335 passed**. A missing editable-install path warning for `D:\FTP\Telegram-Bot\src` remains an environment warning.
- `python -m ruff check .`: **All checks passed** after fixing the lint findings in the pre-existing untracked APK package script.
- `python -m compileall -q app migrations tests run.py wsgi.py`: passed.
- `npm.cmd run lint`: passed. `npm.cmd run build`: passed and generated the ignored `dist/` output; Vite warned that the main JavaScript chunk is 1,080.8 kB (gzip 289.17 kB), above its 500 kB advisory threshold.
- `npm.cmd test`: NOT RUN to completion. Node v26.13.0 failed before test discovery in `tsx` at `os.userInfo()` with `ERR_SYSTEM_ERROR / uv_os_get_passwd ENOMEM` (0 tests executed). No Node 22 installation was available locally.
- Android `:app:testDebugUnitTest` with Gradle 9.7.1 initially failed because `ANDROID_HOME` and `ANDROID_SDK_ROOT` pointed to missing paths. With process-scoped variables set to the existing SDK, Gradle reached `:app:compileDebugKotlin` but failed on existing source mismatches across AI/auth/deals/checkout/orders/wishlist/portals/settings screens and view models. Unit tests did not start; compile repairs are in progress. No release APK was created; release signing is not configured.
- `python scripts/validate_repository_structure.py --fail-on-review`: failed because the pre-existing untracked `bun.lock` conflicts with this repository's authoritative npm `package-lock.json`. The generated npm lock is present for the existing `npm ci` CI contract; `bun.lock` was preserved.
- `git diff --check`: passed after trimming only the reported trailing whitespace/extra blank lines from already modified files. The two Azure workflow targets/configuration were not changed.
- Android local Gradle cache and `android/local.properties` were already absent/deleted in the worktree; no APK/AAB was present.
- No production database, provider, Firebase project, deployment target, credential, or external service was changed.
- Local test/build results for the present implementation are recorded after the corresponding commands actually run; anything not run remains NOT RUN.

## Phase status

- **Phase 0 — Audit:** PARTIAL. Source, CI, repository state, and REA capability constraints were inspected. Browser/runtime observations and provider checks are BLOCKED/NOT TESTED as described above.
- **Phase 1 — CI/build reliability:** IN PROGRESS. npm lock, TypeScript lint, web build, Python lint/compile, and diff whitespace pass. Node tests are blocked by this local Node/`tsx` runtime error; structure validation flags the preserved `bun.lock`; the web bundle-size advisory remains.
- **Phase 2 — Authentication:** IN PROGRESS. TOTP replay and backup-code use are now atomic; non-AES crypto fallback was removed. Targeted tests passed (14), and the full Python suite passed (335); broader identity-provider and live-session behavior remains untested.
- **Website/Android parity, motion, and release readiness:** PARTIAL. Android Kotlin compilation currently fails on source/API mismatches and device/runtime parity is NOT TESTED. No installable release artifact or production-readiness claim is made.

**Non-goals for this audit:** deploy, restart production, alter provider/cloud/GitHub settings, perform production migrations or data changes, create a guest checkout endpoint, or claim unobserved REA work.

## Verification update — 2026-11-04

This update supersedes the earlier in-progress Android compile result and records the final local checks after checkout, review, and Android source corrections.

- Flask remains the authority for checkout and review eligibility. React checkout requires a Flask customer session; COD and the existing SSLCommerz initiation use Flask. No fake local order or client-set `paid` status remains in the checkout flow. Payment callback/redirect completion was not runtime-tested.
- React review listing/submission and helpful voting now use `/api/v1/products/...` Flask endpoints. Flask enforces delivered-order eligibility and moderation; helpful votes require a session. Verified-purchase badges and viewer helpful state are derived from server fields. Browser runtime and accessibility checks were not run.
- The React HaatAI drawer now displays actual chat/search/maps responses; its fabricated AppContext reply path was removed. The Express chat chooses from server-controlled roles, rejects client `systemInstruction`, caps history at 40 messages, text at 8,000 characters, and model output at 1,024 tokens. Grounding prompts treat retrieved data as untrusted, and displayed grounding links require HTTPS. Provider-backed runtime behavior remains NOT TESTED.
- Android source/API mismatches were repaired; the 2FA challenge refreshes its CSRF token after password login creates the pending session. Final `:app:testDebugUnitTest` run: **67 tests, 0 failures/errors, 0 skipped**. This is a local debug build/test result, not device, instrumentation, or release verification.
- Final review/trust test command: `python -m pytest -q --basetemp=.pytest_cache/nexhaat-review-verification-20261104 tests/test_reviews.py tests/test_review_trust.py` — **20 passed**. Full Python suite earlier passed **335 tests**; it was not rerun after these additive review assertions.
- `python -m ruff check .`, `npm.cmd run lint`, `npm.cmd run build`, and `git diff --check` passed. Vite still warns that the main JavaScript chunk is about **1,080.43 kB** (288.72 kB gzip), above its 500 kB advisory threshold.
- `node --test tests-node/server-security.test.ts` passed **9 tests**, including the new server-controlled AI-role and output-bound checks. The canonical `npm.cmd test` wrapper remains blocked before test discovery by Node v26.13.0 `tsx`/`os.userInfo()` error `uv_os_get_passwd returned ENOMEM`. Repository-structure validation still fails because the preserved untracked `bun.lock` conflicts with the authoritative npm `package-lock.json`.
- One Alembic head (`20261104_01`) is visible locally; no migration was applied. Firebase rules were changed locally, but emulator verification and deployment were not performed. No APK/AAB was created, and release signing is not configured.
- REA capability evidence remains as recorded above: MCP inspection responded, but REA code analysis was rejected by Codex approval policy (`never`); no REA implementation/test result is claimed. Codex specialist agents performed bounded backend, Android, and web work.
- No commit, push, merge, CI dispatch, cloud operation, provider configuration, production migration, or deployment occurred.

## Files touched in this execution

The following paths received implementation, verification, documentation, or targeted whitespace edits during this execution. Several were already modified or untracked at first contact; this list does not imply that every current Git change originated here. Pre-existing deleted screenshots, Playwright snapshots, `.gradle` cache files, and `android/local.properties` were left as found.

### Backend, API, and tests

- `app/api/routes/auth.py`
- `app/api/routes/catalog.py`
- `app/api/serializers.py`
- `app/routes/auth.py`
- `app/services/two_factor.py`
- `app/services/two_factor_crypto.py`
- `tests/test_auth_two_factor.py`
- `tests/test_reviews.py`
- `tests/test_review_trust.py`
- `firestore.rules`

### Website and Node AI

- `src/pages/CheckoutPage.tsx`
- `src/lib/marketplaceApi.ts`
- `src/components/ProductReviewsSection.tsx`
- `src/context/AppContext.tsx`
- `src/types/index.ts`
- `src/components/AIAssistantDrawer.tsx`
- `src/components/ProductCard.tsx`
- `src/lib/motionTokens.ts`
- `src/lib/motionTokens.test.ts`
- `src/index.css`
- `src/components/SplashScreen.tsx`
- `src/services/apkDownloadService.ts`
- `server.ts`
- `serverAI.ts`
- `tests-node/server-security.test.ts`
- `package-lock.json`

### Android

- `android/app/src/main/java/com/nexhaat/app/data/remote/ApiService.kt`
- `android/app/src/main/java/com/nexhaat/app/data/remote/dto/ApiResponse.kt`
- `android/app/src/main/java/com/nexhaat/app/data/remote/dto/AuthDto.kt`
- `android/app/src/main/java/com/nexhaat/app/data/repository/AuthRepository.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/components/EmptyState.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/components/ProductCard.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/components/ProductImage.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/ai/AIAssistantScreen.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/ai/AIAssistantViewModel.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/auth/ForgotPasswordViewModel.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/auth/SignInScreen.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/auth/SignInViewModel.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/auth/SignUpScreen.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/auth/SignUpViewModel.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/auth/VerifyRegistrationViewModel.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/checkout/CheckoutViewModel.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/deals/DealsScreen.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/deals/DealsViewModel.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/home/HomeScreen.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/notifications/NotificationsViewModel.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/orders/OrdersViewModel.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/portals/PortalsScreen.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/portals/PortalsViewModel.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/security/SecuritySettingsViewModel.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/settings/SettingsScreen.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/wishlist/WishlistScreen.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/wishlist/WishlistViewModel.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/theme/MotionTokens.kt`
- `android/app/src/main/res/values/strings.xml`
- `android/app/src/main/res/values-bn/strings.xml`

### Documentation and targeted formatting

- `docs/architecture/ANIMATION_AND_MOTION_STANDARD.md`
- `docs/architecture/NEXHAAT_PHASE0_REA_AND_SYSTEM_AUDIT.md`
- `docs/architecture/WEBSITE_ANDROID_FEATURE_PARITY.md`
- `scripts/generate_apk_package.py`
- Targeted trailing-whitespace cleanup: `.github/workflows/main_nexhaat.yml`, `.github/workflows/main_nexhut.yml`, `src/components/FlaskAuthPanel.tsx`, `src/pages/OrderConfirmationPage.tsx`, `src/pages/ProductDetailPage.tsx`, `app/models/security.py`, `app/api/serializers.py`, `app/api/routes/auth.py`, and `app/routes/auth.py`.

