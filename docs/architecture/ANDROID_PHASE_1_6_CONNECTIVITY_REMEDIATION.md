# Android Phase 1.6 Connectivity and Loading-State Remediation

**Overall status: PARTIAL**

## Executive summary

The Android Debug build was connected to an isolated local Flask test app using
USB ADB reverse forwarding. The Flask server listened only on `127.0.0.1` and
used the test configuration with an in-memory SQLite database. No LAN/public
listener, firewall rule, production endpoint, production data, or customer
account was used.

On the authorized V2111, the app launched, Home rendered, Categories completed
its request and showed its empty state, and Cart received the expected
unauthenticated response and displayed Sign In and Retry. Sign In opened without
credentials being entered. The device screenshot captured after attempting an
offline retry showed another app in the foreground, so that retry scenario is
**not verified**. No matching NexHaat fatal crash marker was found in the
filtered Android runtime log.

The Categories/Cart loading-state handling was hardened and eight focused unit
tests were added. The full Android unit-test suite (58 tests), Debug APK
assembly, and Release BuildConfig generation passed. Release configuration did
not include the temporary Debug endpoint.

## Initial findings

- Phase 1.5 identified the emulator-only default URL and no approved physical
  device override. Its report is `docs/architecture/ANDROID_PHASE_1_5_API_CONNECTIVITY_DIAGNOSIS.md`.
- The existing Gradle configuration already supports the Debug-only
  `NEXHAAT_DEBUG_BASE_URL` override; no shared Gradle or production URL change
  was made for this phase.
- Categories could leave loading active for an unexpected `NetworkResult.Loading`
  or an exception. The repository normally returns Success/Error, so that branch
  was a defensive defect, not the proven original device root cause.
- Cart requires an authenticated customer. No test account was available or
  used; the expected unauthenticated result is sign-in UI, not a guest cart.

## Implementation and changed files

The following Android files were changed for this phase:

- `android/app/src/main/java/com/nexhaat/app/ui/screens/catalog/CategoriesViewModel.kt`
- `android/app/src/main/java/com/nexhaat/app/data/repository/CatalogRepository.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/catalog/CategoriesScreen.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/cart/CartViewModel.kt`
- `android/app/src/main/java/com/nexhaat/app/data/repository/CartRepository.kt`
- `android/app/src/main/java/com/nexhaat/app/ui/screens/cart/CartScreen.kt`
- `android/app/src/main/res/values/strings.xml`
- `android/app/src/main/res/values-bn/strings.xml`
- `android/app/src/test/java/com/nexhaat/app/ui/screens/catalog/CategoriesUiStateTest.kt` (new)
- `android/app/src/test/java/com/nexhaat/app/ui/screens/cart/CartUiStateTest.kt` (new)

Both ViewModels now terminate loading for success, error, unexpected Loading,
exceptions, and coroutine cancellation; repeated concurrent loads are ignored.
Repository methods rethrow cancellation rather than converting it to an ordinary
network error. Categories keeps localized error/empty states and retry. Cart
shows Sign In only for 401/403 and provides a recoverable error/retry path for
other failures. Existing authentication and cookie/CSRF behavior was not
replaced.

No dependency, backend source, manifest, network-security configuration,
production URL, or release configuration was changed.

## Development endpoint and build variants

For the device run, the Debug build was supplied a loopback base URL through the
existing Debug override. The test Flask server bound only to `127.0.0.1:5000`;
`adb reverse tcp:5000 tcp:5000` routed the authorized USB-connected phone's
loopback traffic to that local port. This avoided exposing the development
server to the LAN and required no firewall change.

The test app used `TestingConfig` and an in-memory SQLite database. It did not
use production data. The temporary server and ADB reverse mapping were stopped
and removed after testing.

`android/app/build.gradle.kts` keeps the Debug base URL and Release base URL in
separate build-type assignments. Release BuildConfig generation was run
separately and confirmed not to contain the temporary Debug endpoint. The
existing network security configuration was unchanged: cleartext is allowed
only for the existing emulator/loopback hosts, while the base policy denies
cleartext. No LAN cleartext exception or TLS-validation weakening was added.

## Categories remediation and evidence

`CategoriesUiState.withResult()` now maps Success and Error to terminal states
and treats an unexpected Loading result as a terminal unexpected-result state.
`CategoriesViewModel.loadCategories()` prevents duplicate active calls, handles
cancellation and unexpected exceptions, and has a `finally` safeguard against
an active spinner remaining after a terminal path.

Focused tests cover non-empty success, empty success, error, and unexpected
Loading. On-device, the test backend recorded successful
`GET /api/v1/categories` responses (HTTP 200); the Categories screen rendered its
normal empty state because the isolated test database contained no categories.
This verifies the empty-response path, not populated category rendering.

## Cart remediation and evidence

`CartUiState.withResult()` ends loading for success, error, and unexpected
Loading. `CartViewModel` prevents duplicate active requests and clears loading
on cancellation, exceptions, and terminal results. The screen presents Sign In
for 401/403, and Retry for both authentication and recoverable errors; it does
not bypass the backend customer-session requirement.

Focused tests cover successful empty cart, unauthenticated 401, recoverable
network error, and unexpected Loading. The isolated backend recorded
`GET /api/v1/cart` with HTTP 401. On-device, Cart displayed the customer
sign-in message, Sign In button, and Retry. Sign In opened the form; no
credentials were entered.

An offline retry was attempted after removing the reverse mapping. The resulting
capture showed another app in the foreground rather than NexHaat, so this
attempt does not establish the Cart offline error/retry behavior. The mapping
was restored for a subsequent tap, but that capture also showed the other app;
the retry result is therefore not verified.

## Builds and tests

Previously run during Phase 1.6:

| Check | Result |
|---|---|
| `:app:testDebugUnitTest` | **PASS** — 58 tests, 58 passed, 0 failed/errors/skipped, offline |
| Debug Kotlin/Java compilation and resource processing | **PASS** |
| `:app:assembleDebug` | **PASS** |
| `:app:generateReleaseBuildConfig` | **PASS** |
| Debug/Release BuildConfig comparison | **PASS** — temporary loopback endpoint only in Debug |
| APK metadata and signature validation | **PASS** — `com.nexhaat.app`, version 1.0.0/code 1, min SDK 24, target SDK 36, debug v2 signature |

Gradle emitted existing deprecation/tooling warnings; the listed tasks completed
successfully. No dependency upgrade was performed.

## Physical-device verification

- Device: authorized V2111, Android 12 / SDK 31.
- Debug APK: Phase 1.6 APK installed with `adb install -r`; package process
  started and remained present during the initial app checks.
- App launch and Home rendering: **PASS**.
- Categories: **PASS** for successful empty response and rendered empty state.
- Cart unauthenticated behavior: **PASS** for HTTP 401 and visible Sign In /
  Retry UI.
- Sign In screen: **PASS** for opening the form without submitting credentials.
- Offline network failure and Cart retry recovery: **NOT VERIFIED**; device
  foreground changed during the attempted retry.
- Authenticated Cart: **NOT TESTED**; no approved test customer was available.
- Settings, payment, checkout, and biometric hardware behavior: **NOT TESTED**
  in this phase.

## Security regression checks

- Production API URL and backend source: unchanged.
- Debug endpoint remained a build-time Debug override; Release BuildConfig did
  not contain it.
- Test server bound to loopback and used in-memory test data; ADB reverse was
  removed and the server stopped.
- Cart remained server-authenticated; the observed unauthenticated response was
  HTTP 401.
- Existing cookie, CSRF, network-security, and TLS-validation configuration was
  not weakened.
- No credentials, payment activity, transaction, app-data clear, uninstall,
  biometric enrollment change, or production request was performed.
- Filtered Android `AndroidRuntime` log review found no matching NexHaat fatal
  crash markers. This is limited to the captured device log window and is not a
  general crash-free claim.

## Git safety and remaining limitations

The working tree was already dirty with Phase 1/1.1 Android security changes
and the Phase 1.4/1.5 reports. Those files were preserved. Phase 1.6 changes and
this report are also uncommitted. No commit, push, deployment, or Phase 2 work
was performed. `git diff --check` passed after the report was added; a separate
trailing-whitespace scan of the new report also found none.

Remaining unverified items are the Cart offline/retry recovery path, authenticated
Cart behavior, populated catalog rendering, and broader device/UI coverage. No
biometric hardware behavior is claimed.

**Overall status: PARTIAL** — code, unit/build checks, and key unauthenticated
device paths passed; offline retry recovery and authenticated Cart were not
verified.
