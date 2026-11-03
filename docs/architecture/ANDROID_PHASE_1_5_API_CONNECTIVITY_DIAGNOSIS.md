# Android Phase 1.5 API Connectivity Diagnosis

**Overall status: PARTIAL**

## Executive summary

The physical-device build used the Android-emulator-only `10.0.2.2:5000` default, while the repository's `run.py` invokes Flask's development server without a host override. This confirms a configuration mismatch for direct physical-device access to a PC-hosted API. No approved endpoint override was present, so no HTTP request was sent.

The observed Categories and Cart spinners are consistent with API calls remaining in flight without a reachable endpoint, but their exact HTTP result and runtime timeout were not captured. Categories also has a defensive `NetworkResult.Loading` branch that does not terminate loading; the current repository implementation never returns that variant, so it is not established as the observed runtime cause. Cart's route requires a customer session.

## Exact source evidence

### A. Android debug API configuration

- `android/app/build.gradle.kts` — `envOrLocalProperty()` reads environment/local properties; `debugBaseUrlValue` selects `NEXHAAT_DEBUG_BASE_URL` or defaults to `http://10.0.2.2:5000/`. The `debug` build type assigns that value to `BuildConfig.BASE_URL`.
- The `release` build type separately assigns `BuildConfig.BASE_URL` from `NEXHAAT_RELEASE_BASE_URL` (or its release placeholder); the debug URL is not the release URL.
- `android/app/src/main/java/com/nexhaat/app/di/NetworkModule.kt` — `provideRetrofit()` uses `BuildConfig.BASE_URL`; `provideOkHttpClient()` configures connect/read/write timeouts of 30 seconds.
- `android/app/src/main/AndroidManifest.xml` — declares Internet permission and references `@xml/network_security_config`.
- `android/app/src/main/res/xml/network_security_config.xml` — denies cleartext in the base config and allows it only for `10.0.2.2`, `localhost`, and `127.0.0.1`.
- No `NEXHAAT_DEBUG_BASE_URL` environment variable or matching entry in `android/local.properties` was present during this audit. The file contents and any unrelated values were not printed. **No approved physical-device endpoint override exists in the inspected configuration.**

### B. Flask backend binding

- `run.py` — module entry point creates the app and calls `app.run()` without a host or port argument when executed directly.
- Flask's development server defaults to `127.0.0.1:5000`; no repository-owned development host/port override was found in that entry point or the inspected app configuration. No server was started for this diagnostic.
- `app/api/__init__.py` — `api_bp` is mounted under `/api/v1`.
- `app/api/routes/catalog.py`, `list_categories()` — implements public `GET /api/v1/categories`.
- `app/api/routes/commerce.py`, `_customer()` and `get_cart()` — `GET /api/v1/cart` requires an authenticated customer; unauthenticated requests are rejected with 401.
- No Flask CORS setup was found in inspected initialization/API source. Native Android OkHttp is not subject to browser CORS enforcement; CORS is not the confirmed connectivity blocker here.

### C. Categories flow

- `android/app/src/main/java/com/nexhaat/app/data/remote/ApiService.kt`, `getCategories()` — returns `ApiResponse<List<CategoryDto>>` from `GET api/v1/categories`.
- `android/app/src/main/java/com/nexhaat/app/data/repository/CatalogRepository.kt`, `getCategories()` — executes on `Dispatchers.IO`; produces `NetworkResult.Success` when the response is successful with non-null data, otherwise `NetworkResult.Error`; caught exceptions also map to Error. This implementation does not return `NetworkResult.Loading`.
- `android/app/src/main/java/com/nexhaat/app/ui/screens/catalog/CategoriesViewModel.kt`, `loadCategories()` — sets `isLoading=true`; Success and Error both clear it. The `NetworkResult.Loading -> {}` branch leaves it true.
- `android/app/src/main/java/com/nexhaat/app/ui/screens/catalog/CategoriesScreen.kt` — displays `LoadingState` while loading with no categories, then error or empty UI after a terminal state.

**Classification:** emulator endpoint mismatch is a **confirmed configuration blocker**. The empty `NetworkResult.Loading` state branch is a **confirmed defensive code defect**, but is **not the confirmed runtime root cause** because the current `CatalogRepository.getCategories()` does not return Loading. The observed screen's exact request result is **not reproducible / insufficient evidence** without HTTP telemetry.

### D. Cart flow

- `android/app/src/main/java/com/nexhaat/app/data/remote/ApiService.kt`, `getCart()` — calls `GET api/v1/cart`.
- `android/app/src/main/java/com/nexhaat/app/data/repository/CartRepository.kt`, `getCart()` and private `request()` — calls the API; maps successful data to Success, API/HTTP errors to Error, and other exceptions to a generic connectivity Error. HTTP 401 and 403 have customer-specific messages.
- `android/app/src/main/java/com/nexhaat/app/ui/screens/cart/CartScreen.kt` — invokes `viewModel.loadCart()` on entry; shows a spinner while loading and no cart, then error/sign-in/retry UI or cart/empty-cart UI.
- `android/app/src/main/java/com/nexhaat/app/ui/screens/cart/CartViewModel.kt`, `runCartRequest()` — sets loading before request and clears it on Success, Error, or Loading.
- `app/api/routes/commerce.py`, `_customer()` and `get_cart()` — requires an authenticated customer; there is no guest-cart response for this API path.

**Classification:** emulator endpoint mismatch is a **confirmed configuration blocker**. The runtime spinner is consistent with an unresolved/unreachable request but its exact timeout/status is **not reproducible / insufficient evidence**. No separate Cart loading-state defect was proven by the source or runtime evidence available in Phase 1.5.

## Debug endpoint availability and safety

No approved physical-device-accessible debug endpoint was configured. No HTTP request or network probe was sent. Production endpoints were not considered as substitutes.

A safe follow-up can use the existing debug-only endpoint override only with an owner-approved non-production endpoint. If using a local network server, it must be intentionally development-only and limited to a trusted private network; the current Android cleartext allowlist does not include arbitrary LAN addresses. Do not expose the Flask development server publicly or broaden firewall/network-security policy without separate approval.

## Root-cause classification

| Observation | Classification | Evidence / limits |
|---|---|---|
| Phone cannot use emulator loopback as the PC's host endpoint | **Confirmed configuration blocker** | Debug default is `10.0.2.2:5000`; that alias is specific to the Android emulator. |
| Flask direct-run host binding | **Confirmed configuration blocker for LAN access** | `run.py` uses `app.run()` with no host override; Flask defaults to loopback. |
| Categories spinner may remain for a still-pending request | **Conditional issue** | API call has 30-second client timeouts; no HTTP timing/status trace was captured. |
| Categories `NetworkResult.Loading` branch does not clear loading | **Confirmed code defect, not established runtime cause** | Branch is empty, but current `CatalogRepository.getCategories()` only returns Success/Error. |
| Cart API requires a customer session | **Confirmed behavior** | Flask `_customer()` rejects unauthenticated calls with 401. |
| Exact device HTTP status, latency, parsing, or timeout | **Not reproducible / insufficient evidence** | No approved reachable endpoint; no request made. |

## Security implications

The current cleartext exception is narrowly limited to loopback/emulator hosts. Adding an arbitrary LAN cleartext exception would broaden the trust boundary and was not done. Cart authorization must remain server-enforced; client navigation or a guest UI cannot replace `_customer()`. No secrets or environment values were displayed.

## Recommended next actions

1. Provide an owner-approved non-production endpoint reachable from the authorized phone, or authorize a local-only USB reverse-port-forward development setup.
2. Keep the Flask server bound to loopback when using a USB reverse tunnel; use an isolated development/test database, not production data.
3. Configure the endpoint only for a Debug build and verify release BuildConfig remains independent.
4. Once reachable, capture sanitized status/latency for Categories and unauthenticated Cart, and verify visible empty/error/retry behavior.
5. In a separately authorized implementation phase, terminate the Categories ViewModel's unexpected Loading state and add focused tests.

## Tests and checks performed

- Read-only source review of the exact paths above: **PASS**.
- Verified the debug endpoint environment/local-property override was absent without printing property-file contents.
- Verified the authorized V2111 was detected as Android 12 / SDK 31.
- Compared phone/PC private-network subnet presence without printing IP values; the devices appeared on the same subnet, but network trust was **not inferable** from that fact. No LAN endpoint was used.
- `git diff --check`: **PASS**.
- Android unit tests: **NOT RUN**.
- Runtime API checks, HTTP status/timing/parsing, and retry behavior: **NOT TESTED**; no API request was sent.

## Git status and final status

No application/backend source changed during Phase 1.5 finalization; only this report was created/updated. Existing Phase 1/1.1 Android changes and the Phase 1.4 report were preserved. No dependencies, endpoint settings, firewall, device settings, commits, pushes, deployments, or transactions were changed/performed.

**Overall status: PARTIAL** — source diagnosis is documented; physical-device HTTP verification remains blocked by the lack of an approved endpoint.

