# Android Phase 1.4 Device Smoke Test

**Overall status: PARTIAL**

## Device identity and authorization

ADB reported one authorized device: serial `98743727330002N`, product `2111N`, model `V2111`. Read-only properties confirmed Android 12, SDK 31. The NexHaat package was not installed before the test.

## APK validation

Validated the exact Phase 1.3 artifact before installation:

`C:\Users\enan9\AppData\Local\Temp\nexhaat-phase13-69f4289ace414a4ba91c8d8b60d81c22\build-output\_app\outputs\apk\debug\app-debug.apk`

- Package: `com.nexhaat.app`
- Version: `1.0.0`, code `1`
- Minimum SDK: `24`; target SDK: `36`
- APK size: `21,349,286` bytes
- Debug signature: verified; APK Signature Scheme v2 valid; one signer

## Installation and launch

Installed with `adb install -r` using only the verified APK. ADB returned `Success`. No existing package data was cleared or removed.

Launched `com.nexhaat.app/.MainActivity`. The process remained present and the activity resumed. Home rendered without an immediate crash.

## Screen and navigation smoke checks

- **Home:** Rendered the marketplace welcome content and bottom navigation. Product/category data did not populate in this network configuration.
- **Search:** Navigation succeeded; search field and empty prompt rendered.
- **Categories:** Navigation succeeded and selected state rendered, but content remained on a loading spinner.
- **Cart:** Navigation succeeded, but content remained on a loading spinner after waiting. Sign-in was not reached from Cart.
- **Settings:** Opened the Security & Authentication settings screen. Device sensor status displayed “Ready (Enrolled & Supported)” and the biometric preference was disabled. The preference was not toggled and no biometric prompt was invoked.
- **Sign-in:** Not tested; no safe UI route to Sign In became available while the Cart remained loading. No credentials were submitted.
- **Logout/session UI:** Not tested; no authenticated session was created.

These are functional navigation observations only; no order, payment, account change, or other transaction was attempted.

## Crash and log review

The app process remained present after the smoke checks. A filtered AndroidRuntime error-log summary found zero `FATAL EXCEPTION` markers and zero crash markers naming `com.nexhaat.app`. No raw log lines or unrelated device logs were included in this report. This does not establish that no non-fatal sensitive data could appear in other log tags.

## API connectivity

Backend connectivity is **BLOCKED**. The build’s debug API configuration uses the emulator-loopback default, which is not directly reachable from the physical phone. Search/categories/cart showed empty/loading states consistent with unavailable backend data; no endpoint was inferred or changed.

To test server-backed flows, provide an approved physical-device-reachable **debug** API endpoint through the project’s existing debug configuration and build a new Debug APK. Do not use a production endpoint or credentials for this smoke test.

## Biometric checks

Only the settings UI’s device-reported readiness indicator was observed. Keystore key creation, hardware/software backing, CryptoObject authentication, cancellation, lockout, enrollment invalidation, and session unlock were **NOT TESTED**. No enrolled biometrics or device security settings were changed.

## Git and project safety

`git diff --check` passed after updating this report. Existing Phase 1/1.1 Android modifications were preserved. No source, dependency, backend, or build configuration was changed for Phase 1.4. No commit, push, deployment, app-data clear, uninstall, or Phase 2 work occurred.

## Remaining blockers

- An approved device-reachable debug API endpoint is required to exercise backend-backed UI and reach Sign In via the Cart flow.
- Sign-in, logout, authenticated session, and server connectivity remain untested.
- Biometric cryptographic behavior remains untested; the readiness status is not proof of Keystore behavior.

