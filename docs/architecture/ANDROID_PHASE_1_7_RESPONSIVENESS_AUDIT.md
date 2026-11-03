# Android Phase 1.7 Responsiveness Audit

**Audit date:** 2026-11-02
**Overall status: PARTIAL**

## 1. Executive summary

Source inspection found responsive foundations—adaptive product/category grids,
lazy lists, scrollable Settings and Product Detail, asynchronous repository I/O,
and a debounced Search input—but also several concrete layout and loading-state
risks. The strongest directly observed UI defect is that the custom top bar is
drawn beneath the status bar after edge-to-edge is enabled; the V2111 portrait
screenshot shows the logo, back affordance, and tagline visibly clipped.

Other confirmed source findings include a Sign In form with no scroll/IME
handling, fixed CategoryCard dimensions, product cards using fixed light-theme
colors in dark mode, and empty `NetworkResult.Loading` branches in Products and
Product Detail ViewModels. The latter branches are not shown to be reachable
with current repository implementations, so they are not established runtime
causes. The 30-second network timeouts can prolong loading on a slow/unreachable
endpoint; no latency cause was measured.

The authorized V2111 was connected in portrait at 720x1600. The installed app
resumed to the Sign In screen, and a screenshot confirmed the top-bar overlap.
No real credentials were entered. A device frame summary was collected but has
no controlled workload or reset baseline, so it is diagnostic only. No
app-specific ANR or fatal-crash marker was found in the filtered log window.
Landscape, keyboard interaction, navigation, scrolling, font scaling, and
content-overflow behavior were not comprehensively exercised.

The Phase 1.6 retry check was safely attempted with a loopback-only test server,
in-memory SQLite, and temporary USB reverse forwarding. Host-side GET checks
returned Categories 200 and unauthenticated Cart 401, but no device request was
recorded during the incomplete retry attempt. The app process was later absent
and the launcher was foregrounded; filtered logs had no app-specific fatal or
ANR marker. The retry/recovery UI result therefore remains **NOT TESTED**.
The test server and reverse mapping were stopped/removed.

## 2. Definition of the observed responsiveness problem

“Does not feel or behave responsively” is treated here as two distinct
questions:

- **Adaptive UI responsiveness:** whether layout, content, and controls remain
  usable across widths, heights, orientation, font scale, and keyboard
  visibility.
- **Runtime responsiveness:** whether touch, navigation, rendering, loading,
  and recovery complete promptly without UI-thread stalls or indefinite
  progress states.

The user supplied no reproducible symptom beyond the general observation. The
source findings below are not claims that every risk was observed at runtime.
The device test covered only a limited portrait session.

## 3. Screen-by-screen findings

| Screen | Layout and scrolling | Loading and error behavior | Touch, overflow, and performance |
|---|---|---|---|
| **Home** — `ui/screens/home/HomeScreen.kt`, `HomeViewModel.kt`, `home/BannerPager.kt` | `LazyVerticalGrid` with adaptive 156dp minimum cells; categories use a horizontal `LazyRow`; the outer grid provides vertical scrolling. Hero content wraps, and banner text is capped at two lines. | Home loads categories, products, and banners concurrently and waits for all results before ending the initial loading state. Product skeletons and a retryable error row exist. Individual failed sections can be replaced with empty lists while the single error is shown. | Product and banner images use Coil-backed `ProductImage`. Banner auto-scroll and per-page graphics-layer animation add work while the Home screen is composed. No Home-only scroll or interaction timing was captured in this phase. |
| **Categories** — `ui/screens/catalog/CategoriesScreen.kt`, `ui/components/CategoryCard.kt` | Adaptive grid; a populated list is scrollable. Each card and image is fixed at 152dp wide and its label region at 48dp high, so a narrow one-column grid can leave unused cell width; large text/long labels may strain the fixed label region. | Loading, error/retry, and empty states are present. Phase 1.6 handled the unexpected Loading terminal state. | CategoryCard has a full-card click area and image loading fallback. Device rendering of the empty state was confirmed in Phase 1.6; this phase did not test a populated list or long labels. |
| **Products** — `ui/screens/products/ProductsScreen.kt`, `ProductsViewModel.kt` | Adaptive 156dp grid with lazy product items and a manual “Load more” action; skeleton and empty states are available. | Initial error has retry. During pagination, an error with existing products is not rendered by the error branch; the grid remains shown and the user may see “Load more” again. `NetworkResult.Loading` does not clear `isLoading` in the ViewModel. Current repository methods return Success/Error, so this Loading branch is not proven reachable. | Product cards are bounded to two title lines. No device test of pagination, large result sets, or recoverable errors was performed. |
| **Search** — `ui/screens/search/SearchScreen.kt`, `SearchViewModel.kt` | Search field sits above a lazy adaptive grid. Query field is single-line; results scroll. | Search is debounced by 300ms. On query change, prior products are retained; while the new query loads, the result branch can continue rendering those old products under the new query. Error UI appears only when the product list is empty, so a failed new query can leave stale results without a visible error. | No IME search action is explicitly configured. Keyboard visibility, rapid query changes, and result scrolling were not tested on-device. |
| **Product Detail** — `ui/screens/product/ProductDetailScreen.kt`, `ProductDetailViewModel.kt` | Main content is vertically scrollable, supporting long descriptions/options. The image is fixed at 310dp high and consumes significant space in landscape/short windows. Variant rows are emitted eagerly with `forEach`, not lazily. | Error/retry and loading states exist. `NetworkResult.Loading` leaves product loading active; the current repository returns only Success/Error, so reachability is unconfirmed. Add-to-cart loading is terminated for Loading, but unexpected exceptions are not handled in this ViewModel. | Title/description can wrap. Long variant lists and short landscape height could require substantial scrolling; no product detail was opened during this phase. |
| **Cart** — `ui/screens/cart/CartScreen.kt`, `CartViewModel.kt` | Cart items use `LazyColumn`; empty and unauthenticated/error states are supported. Each line places price, quantity controls, and Remove in one horizontal row, which may compress or overflow under narrow width or large font scale. | Phase 1.6 verified unauthenticated 401 → Sign In/Retry UI. Current cart ViewModel loading terminal handling was covered by tests. Offline retry recovery is still unverified. | Material IconButtons provide standard control targets; no populated cart or multi-item scroll was tested. |
| **Sign In** — `ui/screens/auth/SignInScreen.kt` | A full-screen Column is vertically centered but is neither scrollable nor explicitly IME-inset/padding aware. The biometric option, two fields, checkbox, and action can exceed the remaining height when the keyboard is visible or the window is short/landscape. | Loading indicator and inline error are present. No credential submission was performed. | The Sign In screen was visible on-device in portrait. The keyboard was not opened; overlap/clipping is a source-based risk, not a runtime finding. |
| **Settings** — `ui/screens/settings/SettingsScreen.kt` | Settings uses `verticalScroll`, so the cards and actions can extend beyond short screens. A weighted text column shares a row with a Switch. | Biometric status, user notice/snackbar, and logout progress are represented. | System biometric settings and biometric prompt were not activated in this audit. Large font/landscape behavior was not tested. |

## 4. Adaptive layout, insets, and accessibility

### Confirmed / evidence-backed

- `MainActivity.kt:28` enables edge-to-edge with transparent system bars.
  `MarketplaceTopBar.kt:35-47` creates a custom Surface/Row without status-bar
  inset padding. The device screenshot on the Sign In screen showed the top bar
  content partly behind the status bar. Affected screens use this shared top
  bar, including Home, Categories, Products, Search, Cart, Product Detail, and
  Settings.
- `SignInScreen.kt:62-68` centers a full-size, non-scrollable form column.
  `SignInScreen.kt:107-160` contains the fields, optional biometric controls,
  error, and submit action without explicit `imePadding` or a scroll container.
- `CategoryCard.kt:30-46` fixes card/image width and label-region height.
  This weakens adaptation to one-column widths and larger font scales.
- `ProductDetailScreen.kt:99-106` supports vertical scrolling but fixes the
  hero image to 310dp, limiting the available first-screen area in landscape.
- `ProductCard.kt:67-162` uses the `NexHaatColors` light palette instead of the
  active `MaterialTheme.colorScheme`; product cards can therefore look
  inconsistent in dark mode.
- `AndroidManifest.xml` sets `supportsRtl=true`; English and Bengali string
  resources exist. RTL layout and locale switching were not device-tested.
- `MarketplaceBottomBar.kt` uses Material 3 `NavigationBar`/`NavigationBarItem`,
  while the app uses edge-to-edge. No bottom-navigation overlap was observed
  in this audit; gesture-mode and three-button navigation were not compared.

### Accessibility observations

- Navigation items, top-bar actions, text fields, buttons, and switches have
  text or content descriptions in the inspected code. Product images receive
  descriptions; banner pages expose a page label. The image itself is decorative
  only where `contentDescription=null` is supplied.
- Product titles and banner titles may be truncated (`ProductCard.kt:128-130`,
  `BannerPager.kt:236-250`); no full accessible-label behavior was validated.
- Most touch controls are Material components; no measured touch-target audit
  or screen-reader traversal was performed.
- Typography uses `sp`, allowing system font scaling, but fixed card dimensions
  and the non-scrollable Sign In form are risks at larger font scales.
- Reduced-motion behavior is implemented for product skeleton pulse in
  `ProductGridSkeleton.kt`; banner auto-slide and card press animation were not
  verified against reduced-motion settings.

## 5. Touch, navigation, and loading behavior

- `SearchViewModel.search()` cancels the previous search job and debounces input
  by 300ms (`SearchViewModel.kt:32-46`); it avoids dispatching one request per
  keystroke but retains prior results while the next query is in flight.
- Repository network operations use `Dispatchers.IO` (for example
  `CatalogRepository.kt:18-19, 52-53, 69-70, 82-83`). No network call was found
  synchronously blocking the Compose main thread in the inspected paths.
- `NetworkModule.kt:51-53` sets 30-second connect/read/write timeouts. A
  connection that stalls can therefore leave a loading UI visible for a long
  time; that is a configured upper bound, not a measured response time.
- `ProductsViewModel.kt:30-64` and `ProductDetailViewModel.kt:34-52` have empty
  `NetworkResult.Loading` branches that do not clear the main loading flag.
  `CatalogRepository` currently maps its API results to Success/Error, so no
  evidence proves those branches caused observed stalls.
- Home `loadHomeData()` can be invoked repeatedly without an active-job guard
  (`HomeViewModel.kt:38-61`); no duplicate request count was observed during
  this phase.
- No source evidence demonstrated a same-axis nested-scroll conflict in the
  inspected screens. Home's vertical grid contains a horizontal row; Product
  Detail and Settings use one vertical scroll container each.

## 6. Performance findings and actual device evidence

### Source-based findings

- Product/catalog lists are lazy (`HomeScreen.kt:86`, `CategoriesScreen.kt:78`,
  `ProductsScreen.kt:82`, `SearchScreen.kt:109`, `CartScreen.kt:92`).
- Network work is dispatched to IO and the Home requests are launched
  concurrently (`HomeViewModel.kt:40-50`).
- Potential work to profile includes Coil image decode/network activity,
  Home's auto-advancing banner (`BannerPager.kt:89-93`), and the fixed 30-second
  timeout behavior. No image-size, memory, or CPU benchmark was run.
- State is collected with `collectAsState()` in the inspected screens rather
  than a lifecycle-aware collection API; this is a lifecycle efficiency
  consideration, not measured excess recomposition.
- No repeated recomposition or main-thread blocking was established from source
  alone. No Compose recomposition tracing or Android Studio profiler capture
  was performed.

### Device diagnostics (not a benchmark)

On the authorized V2111, `dumpsys gfxinfo com.nexhaat.app` returned:

| Device counter | Observed value |
|---|---:|
| Total frames rendered | 188 |
| Janky frames | 34 (18.09%) |
| Janky frames (legacy) | 38 (20.21%) |
| 50th percentile | 17ms |
| 90th percentile | 150ms |
| 95th percentile | 200ms |
| 99th percentile | 4950ms |
| Missed Vsync | 21 |
| High input latency counter | 147 |

These are raw counters returned during an uncontrolled interactive device
session. The counters were not reset, the sampling interval/workload was not
controlled, and they cannot be attributed to a specific screen or interpreted
as an app performance baseline. No FPS, memory, startup latency, or touch
latency claim is made.

## 7. Physical-device test evidence

- One `adb devices -l` check found authorized device `V2111`, Android 12 / SDK
  31 as previously recorded, connected under serial
  `98743727330002N`. Device display reported 720x1600.
- `am start` resumed the existing `MainActivity`; the app showed the Sign In
  screen in portrait after a short wait. The screenshot showed the shared top
  bar partly clipped beneath the status bar.
- No real email/password was entered and no sign-in submitted.
- No production endpoint, payment, checkout, or transaction was used.
- During the later retry attempt, the device screenshot became black and the
  app process was no longer present; the launcher was then the resumed activity.
  Filtered logs had no matching app-specific fatal/ANR marker. Cause is unknown;
  this is not classified as a confirmed application crash.
- Portrait was the only orientation observed. No display-size, density,
  rotation, accessibility, keyboard, or font-scale settings were changed.

## 8. Phase 1.6 offline retry verification

The test was safe to attempt with a loopback-only Flask `TestingConfig`
application using in-memory SQLite, plus temporary `adb reverse`. The server
listened only on `127.0.0.1:5001`; the phone's local port 5000 was temporarily
forwarded to it. Host-side unauthenticated checks returned:

- `GET /api/v1/categories`: **HTTP 200**
- `GET /api/v1/cart`: **HTTP 401**

The local server log contained those host-side checks but no corresponding
device requests during the incomplete retry interaction. The device capture
became black and the app process was absent before the error/recovery state
could be verified. Therefore:

- Offline retry error UI: **NOT TESTED**
- Retry recovery after restoring the test endpoint: **NOT TESTED**
- Phase 1.6 retry blocker: **remains open**

The temporary reverse mapping and test server were removed after the attempt.
No customer account, production data, or live endpoint was used.

## 9. Findings by severity

| Severity | Finding | Evidence and impact |
|---|---|---|
| **Critical** | None confirmed. | No critical runtime/security issue was established in this responsiveness audit. |
| **High** | None confirmed. | Device coverage is limited; absence of a finding is not a broad release-readiness certification. |
| **Medium** | Shared top bar is under the status bar with edge-to-edge. | Confirmed by `MainActivity.kt:28`, `MarketplaceTopBar.kt:35-47`, and the portrait device screenshot. Affects multiple screens and visibly clips controls/branding. |
| **Medium** | Sign In form has no scroll/explicit IME accommodation. | Confirmed by `SignInScreen.kt:62-68, 107-160`; keyboard/short-height behavior may hide fields or submit action. Runtime keyboard overlap was not tested. |
| **Medium** | Products/Product Detail can leave loading active for unexpected Loading results. | Empty branches in `ProductsViewModel.kt:62` and `ProductDetailViewModel.kt:51`; current repository result mapping does not establish runtime reachability. |
| **Medium** | Search can show stale results for the latest query and suppress an error when old results remain. | `SearchViewModel.kt:34-46` retains products; `SearchScreen.kt:92-107` only shows error when products are empty. |
| **Medium** | 30-second network timeouts can make unavailable/slow API loading feel stalled. | `NetworkModule.kt:51-53`; this is conditional configuration, not measured device latency. |
| **Low** | Category cards have fixed 152dp width and 48dp label area. | `CategoryCard.kt:30-53`; unused space/large-font strain possible on narrow displays. |
| **Low** | Product cards use light-only colors in dark mode. | `ProductCard.kt:67-162` and `theme/Color.kt` `NexHaatColors`; dark-mode inconsistency, not device-tested here. |
| **Low** | Home reload lacks an active-job guard; Home banner has auto-slide/graphics animation. | `HomeViewModel.kt:38-61`, `BannerPager.kt:89-93, 132-138`; potential redundant work/animation cost, not observed as a measured problem. |

## 10. Recommended remediation order (not implemented)

1. Correct shared system-bar inset handling for the custom top bar and validate
   status/navigation bar modes on Android 12+.
2. Make Sign In content keyboard-aware and vertically scrollable; verify short
   landscape and increased font-scale layouts without reducing accessible text.
3. Ensure Products and Product Detail ViewModels always reach terminal loading
   states, including cancellation/exception paths; add focused tests before
   claiming the unexpected Loading path is fixed.
4. Make Search state/query transitions explicit so stale results and errors
   cannot be mistaken for results to the current query.
5. Replace fixed category-card constraints where they prevent adaptive sizing;
   verify narrow width and large font.
6. Align product card colors to the active theme.
7. Profile the app with a controlled workload and reset/recorded frame metrics
   before optimizing banner animation, list composition, or timeout policy.
8. Repeat Phase 1.6 retry recovery with a controlled, verified device
   foreground and capture server request evidence; do not use production.

## 11. Git status, checks, and scope safety

- Before adding this report, `git status --short --branch` showed existing
  uncommitted Android changes and Phase 1.4–1.6 reports. They were preserved.
- No Android source, backend source/configuration, dependency, API URL, or
  device setting was changed during Phase 1.7.
- The only Phase 1.7 repository addition is this report.
- `git diff --check` before report creation: **PASS**.
- Android tests/build/lint: **NOT RUN**; this phase was a read-only audit and
  made no source changes.
- No commit, push, deployment, uninstall, data clear, credential submission,
  transaction, or Phase 2 work was performed.

## 12. Untested items and blockers

- Landscape, rotation recovery, keyboard/IME behavior, accessibility traversal,
  larger font scale, narrow-width rendering, RTL, and dark-mode screen-by-screen
  rendering.
- Home scrolling, rapid navigation, product-list pagination, product detail,
  populated cart scrolling, and retry UI rendering on the physical phone.
- App startup time, controlled frame time, memory, CPU, image decode cost, and
  actual input latency.
- Phase 1.6 offline error and restored-endpoint retry behavior remain
  **NOT TESTED** due to loss of the app process/foreground during the attempt
  and absence of device requests in the isolated server log.
- The black device capture/process disappearance was not explained by available
  filtered logs; no confirmed crash or ANR was observed.

**Overall status: PARTIAL** — source audit and limited portrait/device
diagnostics are complete, but adaptive/runtime coverage is incomplete and the
Phase 1.6 retry recovery remains unverified.
