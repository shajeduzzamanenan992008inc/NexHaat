# Android Phase 1.8 — UI Responsiveness & Adaptive Layout Remediation

**Phase:** 1.8 (follows `ANDROID_PHASE_1_7_RESPONSIVENESS_AUDIT.md`)
**Date:** 2026-11-02
**Device:** V2111 (`98743727330002N`), Android 12 / SDK 31, 720x1600 @ 300 dpi (~384x853 dp), 3-button navigation
**Overall status: PARTIAL**

Phase 1.8 fixes every defect the Phase 1.7 audit verified in source and validates
them on the authorized physical device. It is **PARTIAL** rather than PASS because
three items remain unverified on hardware (Sign In IME behaviour, populated Cart,
pagination error path) and the Phase 1.6 offline-retry blocker is still open. No
performance improvement is claimed because no profiler or frame-timing measurement
was performed.

---

## 1. Phase 1.7 findings reviewed against current code

Every Phase 1.7 finding was re-checked in the working tree before any change. Two
of them had already been partially addressed by uncommitted work in this phase;
the remainder were verified and completed.

| # | Phase 1.7 finding | Phase 1.8 verification and outcome |
|---|---|---|
| 1 | **Medium** — shared top bar drawn under the status bar with edge-to-edge | Confirmed from `MainActivity.kt` (`enableEdgeToEdge`) plus the Phase 1.7 screenshot. Fixed: the bar now consumes safe-drawing top **and horizontal** insets once. |
| 2 | **Medium** — Sign In form has no scroll / IME accommodation | Confirmed (`Column` centered, non-scrollable, no `imePadding`). Fixed: scroll container + `imePadding` + `adjustResize`. |
| 3 | **Medium** — Products / Product Detail can leave loading active on an unexpected `Loading` result | Confirmed: `NetworkResult.Loading` branches did not clear `isLoading`. Fixed in both ViewModels (plus Categories, Cart, Search). |
| 4 | **Medium** — Search can show stale results for the newest query and suppress errors | Confirmed in `SearchViewModel.search()` (retained previous products) and the screen's error branch. Fixed. |
| 5 | **Medium** — 30 s OkHttp timeouts can make an unavailable endpoint feel stalled | **Not changed.** This is a configured upper bound; changing it was not justified without latency measurement. Documented as a remaining issue. |
| 6 | **Low** — Category cards fixed at 152 dp with a 48 dp label region | Confirmed. Fixed: `fillWidth` mode for grids; fixed label height and fixed image width removed. |
| 7 | **Low** — Product cards use the light-only `NexHaatColors` palette | Confirmed. Fixed: cards now use `MaterialTheme.colorScheme`. |
| 8 | **Low** — Home reload lacked an active-job guard | Confirmed. Fixed with a job guard (no duplicate concurrent loads). |
| 9 | Audit note — `collectAsState()` instead of lifecycle-aware collection | Confirmed on all eight screens. Replaced with `collectAsStateWithLifecycle()`. |
| 10 | Audit note — no same-axis nested scrolling found | Re-verified. No change made (no defect). |
| 11 | Audit note — Cart line places price, quantity and Remove in one row | Confirmed as an overflow risk under large font scale. Restructured (price on its own line, controls right-aligned). |
| 12 | Audit note — Product Detail hero fixed at 310 dp | Confirmed as landscape/short-window pressure. Fixed with a clamped fraction of window height. |

Newly found during Phase 1.8 device testing (not in the Phase 1.7 audit):

| # | Finding | Outcome |
|---|---|---|
| 13 | In landscape the top bar's trailing actions were drawn beneath the **side** navigation bar, because only `statusBarsPadding()` was applied | Fixed by using safe-drawing top + horizontal insets. Verified in landscape on-device. |
| 14 | Centered `EmptyState`/`ErrorState` content is non-scrollable and can clip in landscape or at large font scale | Fixed: both state views now centre when they fit and scroll when they do not. |
| 15 | Cart quantity `IconButton`s expose only the glyphs "−"/"+" to accessibility services | Fixed with localized `contentDescription` (EN + BN). |

---

## 2. Verified fixes and technical explanation

### 2.1 Status bar / top bar (`ui/components/MarketplaceTopBar.kt`)

```kotlin
.fillMaxWidth()
.windowInsetsPadding(
    WindowInsets.safeDrawing.only(WindowInsetsSides.Top + WindowInsetsSides.Horizontal)
)
.padding(horizontal = 16.dp, vertical = 10.dp)
```

- Replaces the previous `statusBarsPadding()`, which only handled the status bar
  and left landscape side bars unhandled.
- Insets are applied **once**, on the bar's content row, inside the bar's `Surface`.
  The Surface therefore still paints behind the system bar (intended
  edge-to-edge look) while all interactive content stays clear of it.
- `Scaffold` subtracts the consumed insets before padding screen content, so no
  double padding is introduced.
- No status-bar height is hardcoded anywhere.
- App name and tagline are single-line with `TextOverflow.Ellipsis` so the bar
  keeps a stable, readable height at narrow widths and large font scales instead
  of growing into two/three lines.

### 2.2 Sign In keyboard and short windows (`ui/screens/auth/SignInScreen.kt`, `AndroidManifest.xml`)

- Content is now `BoxWithConstraints` → `Column(heightIn(min = maxHeight) + verticalScroll(rememberScrollState()) + imePadding())`.
  When the IME or a short landscape window reduces the available height, the form
  scrolls instead of clipping the fields or the submit button; when there is room
  the form still centres vertically as before.
- `android:windowSoftInputMode="adjustResize"` added to `MainActivity` so IME
  insets are delivered reliably with `enableEdgeToEdge()`.
- No visible field, label, or action was removed or reduced in size.

### 2.3 Category cards (`ui/components/CategoryCard.kt`)

- New `fillWidth: Boolean = false` parameter. Grids pass `fillWidth = true`
  (Categories screen); the Home horizontal row keeps the 152 dp card width.
- Removed `Modifier.width(152.dp)` on the image and the fixed `height(48.dp)` on
  the label block, replacing the latter with symmetric `vertical` padding. Long
  category names now wrap inside the card instead of being forced into a fixed
  label band.

### 2.4 Product cards (`ui/components/ProductCard.kt`)

- Colours come from `MaterialTheme.colorScheme` (surface, surfaceVariant, error,
  onError, onSurface, onSurfaceVariant) — dark-mode inconsistency resolved.
- Name stays at two lines with `TextOverflow.Ellipsis`.
- Price row is `fillMaxWidth()` with the current price `weight(1f)`, `maxLines = 1`,
  ellipsis; the struck-through previous price is `maxLines = 1`. A long price can
  no longer push the row past the card edge.
- Press feedback is driven by `animateFloatAsState` + `graphicsLayer` on the card,
  with a remembered `MutableInteractionSource` (no per-frame recomposition of
  children).

### 2.5 Product Detail (`ui/screens/product/ProductDetailScreen.kt`)

- Hero height is `35% of window height`, clamped to `120.dp..310.dp`, replacing the
  fixed `310.dp`. In portrait it stays close to the previous look; in landscape it
  no longer consumes most of the viewport.
- Error/retry and loading branches unchanged in structure, but now also render when
  the ViewModel reports an unexpected terminal result.

### 2.6 Empty and error states (`ui/components/EmptyState.kt`, `ErrorState.kt`)

- Both are `Box(fillMaxSize()) { Column(align(Center) + verticalScroll(...) + padding(16.dp)) }`.
  Content centres when it fits and scrolls when a 360 dp-tall landscape window or a
  large font scale makes it taller than the screen.

### 2.7 Loading-state termination (all ViewModels)

Affected: `HomeViewModel`, `CategoriesViewModel`, `ProductsViewModel`,
`SearchViewModel`, `ProductDetailViewModel`, `CartViewModel`.

- Every state has an explicit terminal mapping:

```kotlin
NetworkResult.Loading -> copy(isLoading = false, hasUnexpectedResult = true)
```

- Screens render `hasUnexpectedResult` with the same recoverable error/retry UI as
  a network error (Products, Product Detail, Categories, Cart, Search).
- `try / catch (CancellationException) { throw it } / catch (Exception) / finally`
  ensures `isLoading` cannot survive an unexpected exception or cancellation; the
  `finally` guard only flips loading off if it is still set, so a superseding
  request is not overwritten.
- Active-job guards prevent duplicate requests: Home, Categories, Cart, Products
  (non-refresh path), Product Detail (same product), Search (cancel + debounce).
- Cart is unchanged in behaviour for `401`/`403`: the Sign In action is shown only
  for those codes; other failures show Retry. Authentication is not bypassed.

### 2.8 Search result/query consistency (`SearchViewModel.kt`, `SearchScreen.kt`)

- A new query immediately resets to `SearchUiState(query = new, isLoading = true)`,
  so the previous query's products can never be shown under the new query.
- Errors clear results and are therefore visible; the IME Search action performs an
  immediate (non-debounced) search.

### 2.9 Products pagination error (`ProductsScreen.kt`)

- With products already present, a load-more failure now renders an inline error
  item with Retry instead of silently leaving the old list and a "Load more"
  button. The error item and the "Load more" button are mutually exclusive.

### 2.10 Lifecycle-aware collection

All eight screens now use `collectAsStateWithLifecycle()`; collection stops while
the destination is not started. No new library or dependency was added — the
dependency was already declared (`lifecycle-runtime-compose`).

### 2.11 Accessibility touch points

- Cart quantity controls expose `decrease_quantity` / `increase_quantity` string
  resources in English and Bangla; all are existing 48 dp `IconButton`s.
- Existing content descriptions (top-bar actions, navigation items, images,
  banner pages, buttons) were preserved; no label was removed.
- Font scale 1.3 was exercised on-device (see §6); no text was clipped.

---

## 3. Changed files

### 3.1 Phase 1.8 UI change set (uncommitted working tree)

| File | Change |
|---|---|
| `android/app/src/main/java/com/nexhaat/app/ui/components/MarketplaceTopBar.kt` | Safe-drawing top+horizontal insets; single-line title/tagline |
| `android/app/src/main/java/com/nexhaat/app/ui/components/ErrorState.kt` | Centered-but-scrollable state view |
| `android/app/src/main/java/com/nexhaat/app/ui/components/EmptyState.kt` | Centered-but-scrollable state view |
| `android/app/src/main/java/com/nexhaat/app/ui/components/CategoryCard.kt` | Adaptive width, no fixed label height |
| `android/app/src/main/java/com/nexhaat/app/ui/components/ProductCard.kt` | Theme colours, overflow handling, press scale |
| `android/app/src/main/java/com/nexhaat/app/ui/screens/auth/SignInScreen.kt` | Scroll + IME padding + lifecycle collection |
| `android/app/src/main/java/com/nexhaat/app/ui/screens/home/HomeScreen.kt` | Lifecycle collection |
| `android/app/src/main/java/com/nexhaat/app/ui/screens/home/HomeViewModel.kt` | Active-job guard |
| `android/app/src/main/java/com/nexhaat/app/ui/screens/catalog/CategoriesScreen.kt` | Adaptive cards, terminal error handling |
| `android/app/src/main/java/com/nexhaat/app/ui/screens/catalog/CategoriesViewModel.kt` | Terminal states, exception/cancellation handling |
| `android/app/src/main/java/com/nexhaat/app/ui/screens/products/ProductsScreen.kt` | Inline pagination error, adaptive skeleton |
| `android/app/src/main/java/com/nexhaat/app/ui/screens/products/ProductsViewModel.kt` | Terminal states, job guards |
| `android/app/src/main/java/com/nexhaat/app/ui/screens/search/SearchScreen.kt` | IME padding, query/error consistency |
| `android/app/src/main/java/com/nexhaat/app/ui/screens/search/SearchViewModel.kt` | Clear results per query, terminal states |
| `android/app/src/main/java/com/nexhaat/app/ui/screens/product/ProductDetailScreen.kt` | Adaptive hero height, terminal error UI |
| `android/app/src/main/java/com/nexhaat/app/ui/screens/product/ProductDetailViewModel.kt` | Terminal states, job guard, exception handling |
| `android/app/src/main/java/com/nexhaat/app/ui/screens/cart/CartScreen.kt` | Cart line reflow, code-specific Sign In, accessible quantity controls |
| `android/app/src/main/java/com/nexhaat/app/ui/screens/cart/CartViewModel.kt` | Terminal states, error code, exception/cancellation handling |
| `android/app/src/main/AndroidManifest.xml` | `windowSoftInputMode="adjustResize"` |
| `android/app/src/main/res/values/strings.xml` | `decrease_quantity`, `increase_quantity` |
| `android/app/src/main/res/values-bn/strings.xml` | Bangla equivalents |
| `android/app/src/test/java/com/nexhaat/app/ui/screens/**` (5 new files) | State-mapping tests for Cart, Categories, Products, Search, Product Detail |

Completed specifically in this session (after re-verifying the working tree):
`MarketplaceTopBar` horizontal-inset defect and single-line toolbar text,
scrollable `EmptyState`/`ErrorState`, Cart quantity descriptions and Cart line
reflow, the two string resources, `adjustResize`, and the landscape inset fix.

### 3.2 Pre-existing, unrelated uncommitted work preserved

The working tree also contains earlier-phase work that this phase neither modified
nor reverted: biometric session crypto (`BiometricSessionCrypto.kt`,
`BiometricStorage.kt`, `BiometricPromptHelper.kt`, `BiometricError.kt`),
session plumbing (`data/session/`, `SessionExpiryInterceptor.kt`,
`SessionViewModel.kt`, `AuthRepository.kt`, `NavGraph.kt`), safe network logging
(`SafeNetworkLoggingInterceptor.kt`, `NetworkModule.kt`, `CookieJar.kt`),
`SettingsScreen.kt`/`SettingsViewModel.kt` logout work, backup/extraction rules,
and the Phase 1.4–1.7 reports. None of it was restored, reset, or rewritten.

---

## 4. Tests and build — actual commands and results

Run from `android/`:

| Command | Result |
|---|---|
| `./gradlew :app:testDebugUnitTest :app:assembleDebug --console=plain` | **BUILD SUCCESSFUL** (exit 0), `52 actionable tasks` |
| Debug Kotlin compilation | Included in the build — **no errors**. Two pre-existing deprecation warnings: `Locale(String, String)` in `CartScreen.kt:193` and `ProductDetailScreen.kt:269`. |
| `:app:testDebugUnitTest` | **67 tests, 0 failures, 0 errors, 0 skipped** (15 test classes) |
| `git diff --check` | **PASS** (exit 0) |

Focused Phase 1.8 tests added (17 of the 67):

- `ProductsUiStateTest` (3) — empty success ends loading and exhausts the list; error
  preserves items; unexpected `Loading` ends the spinner and enables error UI.
- `SearchUiStateTest` (3) — results belong to the requested query; an error clears
  stale results for the previous query; unexpected `Loading` terminates.
- `CartUiStateTest` (4) — empty cart success; `401` carries the sign-in code; a
  generic network error has no sign-in code; unexpected `Loading` enables retry UI.
- `CategoriesUiStateTest` (4) — success, empty success, error, unexpected `Loading`.
- `ProductDetailUiStateTest` (3) — success, error, unexpected `Loading`.

Not run: instrumentation/UI tests (none exist for these screens), lint
(`./gradlew lint` was not requested and not run), Android release build.

### Debug APK

| Property | Value |
|---|---|
| Path | `android/app/build/outputs/apk/debug/app-debug.apk` |
| Size | 22,255,564 bytes |
| SHA-256 | `94ed3f9d2f0cea5bafa40f80bae932ccc9f306bf45d135d847883fff1b634a0f` |
| Variant | debug, `applicationId com.nexhaat.app`, versionCode 1 / versionName 1.0.0 |
| SDK | compileSdk 36, minSdk 24, targetSdk 36 |
| `BASE_URL` (installed build) | `http://10.0.2.2:5000/` (standard project default — restored) |
| Signing | debug keystore (`validateSigningDebug`) |

Installed with `adb install -r` only; the app was never uninstalled and app data was
never cleared.

---

## 5. Device verification method

- Device: authorized V2111, `adb devices -l` → `device product:2111N model:V2111`.
- Navigation and interaction used `adb shell input tap/swipe/text/keyevent` only.
- Orientation was forced with `settings put system accelerometer_rotation 0` +
  `user_rotation 1` (restored to `1` / `0` afterwards); font scale was raised to
  `1.3` and restored to `1.0`.
- Data for populated states came from two **loopback-only** sources, reached over a
  temporary `adb reverse`:
  1. The project's own local Flask dev API already listening on `127.0.0.1:5000`
     (empty catalog, unauthenticated cart → `401`).
  2. A synthetic mock API on `127.0.0.1:5001` (no images, intentionally long titles)
     used through a verification-only debug build configured with the project's
     existing `NEXHAAT_DEBUG_BASE_URL` override.
- The standard debug APK was rebuilt and reinstalled afterwards, and its compiled
  `BASE_URL` was re-checked as `http://10.0.2.2:5000/`. Reverse mappings were
  removed, `http_proxy` reset to `:0`, and the mock listener was stopped. The
  pre-existing Flask dev server on port 5000 was not touched.
- No production endpoint, no real payment, no transaction, and no credentials were
  entered or submitted.

Screenshots were captured to `android/app/build/phase18/` (build output, ignored by
Git) and are **not** committed.

---

## 6. Physical-device evidence

| Screen | Evidence observed |
|---|---|
| **Home** | Top bar sits fully below the status bar (no overlap); logo, name, search/cart/settings actions and tagline all legible. Populated 2-column adaptive grid with SALE badge, truncated long titles, out-of-stock label, vertical scrolling, horizontally scrolling category row, skeleton loading state, and empty/error states all render. Verified in portrait, landscape, and at font scale 1.3. |
| **Categories** | Populated adaptive grid in landscape (4 columns); long category name wraps inside the card without clipping; loading spinner and empty state confirmed in portrait; `All categories` heading clear of the toolbar. |
| **Products** | Populated grid, 2 columns on 384 dp, long titles ellipsized, "Out of stock" card distinct, scrolling works, top bar clear of the status bar. |
| **Search** | Prompt state, typed query ("tea"), 300 ms debounce result, "Results for “tea”" with one card; keyboard open in landscape — field and results remain visible and the field clears the side nav bar. Clear (×) affordance visible. |
| **Product Detail** | Portrait: hero + title + price + stock card + description + disabled/enabled Add to Cart; long title wraps without clipping; vertical scrolling works; landscape shows the reduced hero height with content scrolling under a fixed bottom bar. |
| **Cart** | Unauthenticated: `401` → "Sign in as a customer to use your cart." with **Sign in** and **Retry**; loading spinner shown before the terminal result. (Populated cart not reachable without credentials.) |
| **Sign In** | Portrait render verified: back affordance, title, explanatory copy, email/password fields, biometric checkbox, submit button, all within bounds and clear of the status bar. |
| **Settings** | Portrait render verified: status card ("Ready (Enrolled & Supported)"), biometric switch card with wrapped description, scrolling column, top bar inset correct. |

Additional observations:

- **Offline loading**: with an unreachable endpoint, the skeleton/spinner states
  display and then resolve to the retryable error UI (Categories/Cart captured in
  loading; the terminal error UI for Cart was captured via the `401` path).
- **No app crash or ANR marker** was seen during the session; the app remained the
  resumed activity across every navigation and rotation performed.
- **Privacy note:** while focusing the Sign In email field, the platform filled the
  fields with a pre-existing credential (not entered by this test). No sign-in was
  submitted. The two captures containing that text were deleted and are not
  referenced here. This is recorded in §8 as an observation to verify separately.

---

## 7. Before / after measurements

Only structural, reproducible comparisons are claimed; there are no frame-time,
FPS, memory, or startup numbers because no profiler capture was taken.

| Item | Before (Phase 1.7) | After (Phase 1.8) |
|---|---|---|
| Top bar vs status bar | Content overlapped the status bar (Phase 1.7 screenshot) | Content starts below it; Surface still paints the edge-to-edge background |
| Top bar in landscape | Trailing actions under the side navigation bar | Actions end at the safe-drawing edge; no clipping |
| Product Detail hero | Fixed 310 dp | `clamp(35% of window height, 120 dp, 310 dp)` |
| Category card | 152 dp width + 152 dp image + 48 dp label box | Grid: full cell width; label height content-driven |
| Sign In with IME / short window | Non-scrollable centred column | Scrollable, IME-aware, still centered when it fits |
| Unexpected `Loading` result | Spinner could persist | Terminal state → error/retry UI (unit-tested) |
| Search with a new query | Previous query's products stayed visible | Results cleared immediately, error visible |
| Cart error actions | Sign In shown for every error | Sign In only for `401`/`403`, Retry always |
| State collection | `collectAsState()` | `collectAsStateWithLifecycle()` |
| Cart quantity a11y | "−"/"+" glyphs only | Localized "Decrease/Increase quantity" |

---

## 8. Remaining issues (known, not blocking)

1. **Toolbar tagline truncation at 384 dp with three actions.** The tagline is
   ellipsized ("Local finds, delivered …") on the Home top bar; it renders in full
   wherever the bar has two actions or in landscape. Accepted as the trade-off for
   a stable single-line bar; no redesign was made.
2. **Uneven product-card heights within a row** when brand/sale metadata differs.
   Content-driven and clipping-free; no fix applied because it would change card
   density beyond this phase's scope.
3. **"Load more" retry resets to page 1** (refresh semantics) rather than retrying
   the failed page. Results replace the list, so no duplicate rows occur; the error
   path was not exercised beyond source review.
4. **30 s connect/read/write timeouts remain.** An unreachable endpoint can show a
   loading skeleton for up to 30 s. This is configured behaviour, not a measured
   latency, and was deliberately not changed.
5. **Search clears results on every keystroke**, so a skeleton flashes during the
   300 ms debounce. This is the intentional replacement for stale results.
6. **Sign In field prefill observation.** A platform-level credential appeared in
   the email/password fields when the field was focused (not typed by this test,
   never submitted). Whether this is Android Autofill or app-side persistence was
   not investigated; it is not claimed as a Phase 1.8 regression and should be
   verified separately before any security conclusion.

---

## 9. Untested / not verified

- **Sign In with the keyboard open** — the IME capture returned an empty frame, so
  overlap/scroll behaviour under the keyboard is source-verified only, **not
  device-verified**. Sign In landscape was not captured cleanly either.
- **Populated Cart** (needs an authenticated customer) — item reflow and quantity
  controls are not device-verified; only the unauthenticated `401` state is.
- **Load-more failure / page > 1 pagination** — not exercised on-device.
- **Offline retry recovery (Phase 1.6 blocker)** — still **NOT TESTED**. No isolated,
  controlled offline→online retry sequence with captured evidence was performed, and
  the blocker remains open.
- **Performance** — no Compose recomposition tracing, profiler capture, frame-time
  reset, memory, startup or input-latency measurement; therefore no performance
  improvement is claimed.
- **Bangla locale rendering, RTL, light theme, TalkBack traversal** — the device
  stayed in dark mode with English; these were not switched (settings untouched
  beyond orientation/font scale, which were restored).
- **Biometric and session flows** — out of scope for this phase and not exercised.

---

## 10. Git status and diff safety

- `git status --short --branch`: `## main...origin/main` with the pre-existing
  uncommitted Phase 1.4–1.8 work listed in §3, including this report as a new
  untracked file. No file was reset, cleaned, checked out over, or reverted.
- `git diff --check`: **PASS** (exit 0). The only warning printed is the existing
  CRLF notice for `android/.gradle/buildOutputCleanup/cache.properties`.
- **No commit, no push, no merge, no deployment.**
- **No backend source or configuration changed**, no production API URL changed,
  no release signing changed, **no dependency added or upgraded**, no security
  control weakened, no authentication bypassed.
- Gradle build output and the Phase 1.8 screenshots live under `android/build/` and
  `android/app/build/` and are ignored by Git.
- Device state restored: `accelerometer_rotation = 1`, `user_rotation = 0`,
  `font_scale = 1.0`, `http_proxy = :0`, no `adb reverse` mappings, temporary mock
  listener stopped. App installed normally with data preserved; nothing was
  uninstalled or cleared.

---

## 11. Overall status

**PARTIAL**

The verified Phase 1.7 defects (status-bar overlap, non-scrollable Sign In, stuck
loading branches, stale Search results, fixed category-card geometry, light-only
card colours, unguarded Home reload, lifecycle-unaware collection) are fixed,
unit-tested (67 tests passing), compiled, packaged, installed and re-checked on the
physical V2111 across portrait, landscape, font scale 1.3, scrolling, keyboard,
populated, empty, loading and unauthenticated states. The landscape side-bar inset
defect found during this phase is also fixed and verified.

Remaining gaps: Sign In IME behaviour and landscape capture, populated Cart,
pagination error handling, and the Phase 1.6 offline-retry blocker — all listed in
§8/§9 as unverified rather than fixed. Phase 2 was not started.
