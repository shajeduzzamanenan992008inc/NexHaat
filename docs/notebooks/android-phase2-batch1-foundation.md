# Phase 2, Batch 1 — Security and Build Foundation
## Scope: NexHaat Android (`android/`)

This document records the preflight findings, proposed smallest safe changes, and the
implementation plan for this batch only. It preserves the repository's existing
Flask/Jinja/Kotlin/Jetpack Compose patterns and does not change the backend or
existing marketplace features.

---

## Step 1 — Preflight findings (read-only)

### 1.1 Worktree state
- `git status --short -- android/` reports `?? android/`.
- The entire `android/` tree is currently **untracked**, and there are no staged/unstaged
  modifications inside it. That means every file in `android/` is treated by Git as a new
  addition rather than as changed tracked content.
- Local build artifacts already exist before this session:
  - `android/app/build/` contains `debug` and `release` Hilt-generated sources and other
    intermediates. Those are build outputs and should stay ignored for version control purposes.
  - `android/.gradle/` and `android/.kotlin/` are tool caches.
- **Preservation note:** This batch will not delete the existing build outputs, only edit the
  source/config files under `android/`. If you want the build folders ignored before a later
  commit, that is a separate housekeeping decision that should be approved explicitly.

### 1.2 Backend/API alignment already confirmed
- Backend API blueprint is mounted at `/api/v1` in `app/api/__init__.py`.
- Catalog endpoints currently used by Android are correct against the documented backend:
  - `GET /api/v1/categories`
  - `GET /api/v1/products`
  - `GET /api/v1/products/{id}`
  - `GET /api/v1/search`
- Networking primitives already exist on the app side:
  - `PersistentCookieJar` stores cookies per host in memory.
  - `CsrfInterceptor` attaches a stored `X-CSRFToken` header to mutating requests.
  - Hilt provides both, plus a logging `HttpLoggingInterceptor`, to `OkHttpClient`.
- Auth-related backend endpoints already exist but are **not yet consumed** by the app:
  - `GET /api/v1/auth/csrf`
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/register`
  - `POST /api/v1/auth/register/verify`
  - `POST /api/v1/auth/logout`
  - `GET /api/v1/auth/me`
  - plus admin-code flows.

### 1.3 Current Android release/debug backend URL state
- `android/app/build.gradle.kts`:
  - `debug`: `BASE_URL = "http://10.0.2.2:5000/"`
  - `release`: `BASE_URL = "https://nexhaat.com/"`
- On this machine, both hosts are unreachable from outside an emulator context right now:
  - `nexhaat.com` resolves to `127.0.0.1` here, and TCP to ports 80/443 is refused.
  - `10.0.2.2` is only meaningful **from inside the Android emulator** as the host-loopback
    alias; it is unreachable from this host's native network stack right now.
- **Important:** I could not find any repository artifact that independently confirms
  `https://nexhaat.com` is the intended production backend origin. The hostname appears only
  in the Android release `build.gradle.kts` so far.

### 1.4 Network security and signing state
- `app/src/main/res/xml/network_security_config.xml`:
  - global `cleartextTrafficPermitted="true"`
  - explicit cleartext permitted for `10.0.2.2` and `localhost`
- `AndroidManifest.xml`:
  - `android:usesCleartextTraffic="true"`
  - `android:networkSecurityConfig="@xml/network_security_config"`
- `android/app/build.gradle.kts` **release** block has **no signing configuration**.
- No keystore file is present in the repository, and none was generated during this session.

### 1.5 Existing tests
- Instrumentation test sources under `android/app/src/androidTest/` exist as empty
  package directories only. There are no `.kt` files there yet.
- Local JUnit test exists:
  - `android/app/src/test/java/com/nexhaat/app/data/remote/dto/CategoryDtoTest.kt`

---

## Step 2 — Smallest safe changes

### 2.1 Debug / staging / release `BASE_URL` configuration
**Goal:** make the backend host a first-class build-time concern instead of a
hardcoded magic string, while leaving it unresolved where needed.

Suggested design:
- Keep `debug` pointing at the emulator-friendly host used for local development.
- Keep `release` pointing at the production backend host **only after it is confirmed**.
- Introduce an explicit staging/build config if you want a middle ground, for example:
  - `debug`: emulator host
  - `staging`: pre-production backend host
  - `release`: production backend host
- Backend host and scheme should be supplied by engineering/deployment owners, not invented
  by the Android build.

**Open decision:**
- I will not pick `https://nexhaat.com` as the production backend host without evidence.
- If you confirm the production backend host for the mobile API, I can update the release
  build config to that value in the same review. Until then, the release URL stays unresolved.

### 2.2 Release-only HTTPS enforcement without breaking emulator development
**Goal:** release builds talk only HTTPS, while debug builds can still reach a local HTTP backend.

Suggested design:
- `debug`:
  - keep cleartext permitted for the local dev host, because the local backend in this project
    has historically been HTTP.
  - ideally continue to support `10.0.2.2` as emulator host-loopback and/or `localhost` when
    debugging on a local backend.
- `release`:
  - disable cleartext globally.
  - keep only the production backend host in the network security config for release, with
    system trust anchors only.
  - do **not** add broad cleartext exceptions.
- Manifest:
  - currently `android:usesCleartextTraffic="true"` is set unconditionally.
  - it should become build-type-conditional, or the network security config should be the sole
    controlling mechanism per build type.

This is a safe change because it is explicitly build-type-scoped. It does not change backend
behavior and does not touch the existing marketplace code.

### 2.3 Release signing configuration from local-only properties or environment
**Goal:** make a release build signable without embedding secrets or generating a keystore.

Suggested design:
- Add an **optional** release signing configuration in `android/app/build.gradle.kts`.
- Read keystore path, store password, key alias, and key password from:
  - a local-only `android/local.properties`-style file when present, **or**
  - environment variables when present
- Default to an **unsigned release build** when those credentials are absent, rather than
  failing the build or prompting for secrets.
- Store the local-only secret file in `.gitignore` and do not commit it.
- Do **not** generate a keystore as part of this batch. Signing credentials are operator-side
  material.

This is independent of the unresolved production URL, so it is safe to implement now.

### 2.4 Secure cookie/session and CSRF persistence design
**Goal:** set up the app to persist session cookies and CSRF state in a way that matches the
backend's session-cookie + `X-CSRFToken` model.

Backend reality to design around:
- The backend issues a session cookie named `nexhaat_session`.
- In production, that cookie is `Secure`, `HttpOnly`, `SameSite=Lax`.
- CSRF tokens are generated server-side and echoed back in JSON; mutating API requests must
  include `X-CSRFToken`.
- Session lifetime is long-lived on the server, but the cookie transport rules depend on the
  request origin scheme.

Suggested Android-facing design:
- **Cookie persistence:**
  - The current `PersistentCookieJar` is in-memory per process. That is acceptable for early
    dev, but for a real release flow it should persist cookies across app restarts.
  - A small and safe upgrade is to back the cookie jar with `SharedPreferences` or
    `DataStore` so the session cookie survives process death.
  - Care must be taken not to log or expose the session cookie value.
- **CSRF lifecycle:**
  - On app start / after sign-in, fetch `GET /api/v1/auth/csrf` before any mutating request.
  - Store the returned `csrf_token` in memory or secure storage, depending on sensitivity.
  - Refresh it when a session is considered stale or after a protected mutation if the backend
    indicates a new token is needed.
- **Scheme awareness:**
  - If the backend sets `Secure` on its session cookie, Android must call the backend over HTTPS
    or the cookie will not be stored/set by the OS. That is one more reason the release path must
    be HTTPS-only with a real backend host.
  - Do not disable cookie/HTTPS requirements in release just to make an unverified debug host work.

**Open decision:**
- I am not implementing the full auth flow here. I am proposing the persistence/model design so
  we can agree on it before wiring auth endpoints. If you want the cookie/CSRF plumbing first, I
  can implement a safe skeleton that fetches and stores the CSRF token and persists cookies, and
  leaves the login/register UI for a later batch.

### 2.5 Required tests and build verification
Suggested verification for this batch:
1. **Local unit test**
   - Keep `CategoryDtoTest` passing.
   - Add a small config-level unit check for:
     - build-type-specific base URL selection if we expose a readable config object
     - deterministic fallback behavior when signing properties/env vars are absent
2. **Android Lint**
   - Run the existing Android lint task for the release variant where available, to catch
     manifest/cleartext/network configuration issues.
3. **Release build sanity**
   - Where the environment allows, assemble the release bundle/apk without signing, to confirm
     the build still produces an artifact.
4. **Instrumented smoke test (recommended next, not necessarily in this batch)**
   - A minimal instrumented test that launches the app and confirms the catalog screen renders
     without crashing, using the debug backend during development.

**What this batch will not claim:**
- I will not claim the resulting AAB is Play-ready until release signing and release network
  configuration have been verified on your side with the real signing material and the confirmed
  production backend host.

---

## Step 3 — Implementation boundary

### 3.1 Safe to implement now
These are independently safe because they do not depend on an unverified production URL:
- Build-type-scoped cleartext and network security configuration.
- Optional release signing configuration backed by local-only properties/env vars.
- Manifest changes to make cleartext behavior build-type-aware.
- Any supporting config that does not require the production host to be known.

### 3.2 Do not implement until confirmed
- Final `release` `BASE_URL` value.
- Any change that assumes `https://nexhaat.com` is the production backend host.
- Auth UI flows.
- Fake/mock production behavior that pretends the production host is known.

### 3.3 Do not do in this batch
- Generate a keystore.
- Commit signing credentials.
- Deploy, upload to Play Console, or push anything.
- Modify backend code or marketplace logic.

---

## Step 4 — Validation plan

### 4.1 Local checks
- After edits, rerun the project's existing unit tests for the Android module if the environment
  supports it.
- Run Android Lint for the configured release variant.
- Confirm the release build still assembles an artifact without signing when signing credentials
  are absent.

### 4.2 Acceptance criteria for this batch
- Debug builds continue to support the emulator/local backend workflow.
- Release builds fail closed on cleartext instead of silently allowing it.
- Release signing is configurable from local-only properties or environment and does not fail
  hard when those are absent.
- No secrets are committed.
- No change depends on an unverified production backend URL.

---

## Step 5 — Remaining blockers

1. **Production backend host for mobile not confirmed in this repository.**
   - Current evidence supports the emulator/local backend and the catalog API shape only.
   - Before the release `BASE_URL` and release network config can be finalized, we need a
     confirmed production backend origin for mobile.

2. **Java/Android SDK build environment on this machine is not currently usable from Git Bash.**
   - `JAVA_HOME` is currently set to a path that does not resolve into a usable JDK from this
     shell, and `java` is not on the current `PATH` in Git Bash.
   - The Android SDK tree exists under `%LOCALAPPDATA%\Android\Sdk` with `cmdline-tools`,
     `build-tools`, `platform-tools`, and `platforms`.
   - A working Gradle build will need a valid `JAVA_HOME`/JDK and the SDK path resolvable from
     the build environment. If you prefer, you can set that up and re-run the Gradle checks, or
     tell me the exact environment setup you want me to use.

3. **Release signing credentials are operator-side only.**
   - This batch can make release signing configurable, but a signed Play-ready artifact depends
     on your keystore material and your approval.

---

## Decision points for you

1. **Production backend host for mobile**
   - Do you want me to wait here until you confirm the mobile production backend host, or do you
     want me to proceed with only the build/security foundation changes that do not need it?

2. **Staging configuration**
   - Do you want a separate staging build variant/config now, or only debug + release for now?

3. **Cookie/CSRF plumbing now vs later**
   - Do you want the safe cookie persistence + CSRF fetch/storage skeleton now, or only the
     build/security config first?

4. **Signing configuration scope**
   - Is the proposed "optional release signing from local-only properties/env, unsigned fallback"
     model acceptable?

---

*Prepared from repository evidence only. No production host was assumed, no keystore was
generated, and no secrets were committed.*
