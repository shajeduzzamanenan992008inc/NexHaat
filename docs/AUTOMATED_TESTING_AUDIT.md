# NexHaat — Automated Testing Audit Report

**Date:** 2026-11-05  
**Version:** 1.0.0  
**Status:** Canonical Repository Audit  
**Author:** QA Automation Architect, DevOps Engineer & Senior Android Engineer  

---

## 1. Executive Summary

NexHaat is a Bangladesh-first, hyper-local multivendor commerce platform comprising four principal execution surfaces:
1. **Native Android Application (`android/`)**: Built in Kotlin 2.2.20 with Jetpack Compose, Hilt DI, Retrofit 2, persistent cookie session jar, CSRF interception, and biometric security.
2. **Flask / Python Backend (`app/`, `run.py`)**: Authoritative for marketplace identity, commerce operations, orders, checkout, payments, role portals, and persistence via SQLAlchemy/Alembic.
3. **React / TypeScript Web Application (`src/`)**: High-performance customer and role workspace SPA with Tailwind CSS, Neumorphic UI, bilingual Bengali/English localization, and offline PWA capabilities.
4. **Node / Express AI & Media Gateway (`server.ts`, `serverSecurity.ts`)**: Server-side Google Gemini AI integration, PubChem agro-food analysis, and Android APK distribution endpoints.

This audit establishes the baseline for the fully automated testing pipeline, APK release lifecycle, and web `Get App` button integration.

---

## 2. Runtime Surface & Component Audit

### 2.1 Android Application Architecture

| Parameter | Configuration | Verification Status |
|---|---|---|
| **Namespace / Package** | `com.nexhaat.app` | Confirmed in `AndroidManifest.xml` & `build.gradle.kts` |
| **Compile SDK / Target SDK** | `36` (Android 16 preview / Android 15 compatibility) | Configured in `android/app/build.gradle.kts` |
| **Minimum SDK** | `24` (Android 7.0 Nougat) | Verified in `defaultConfig` |
| **UI Framework** | Jetpack Compose (BOM 2024.09.02), Material 3 | Verified in Compose screens and navigation graph |
| **Dependency Injection** | Dagger Hilt 2.57.2 | Configured in `android/app/build.gradle.kts` |
| **Networking & API** | Retrofit 2.11.0, OkHttp 4.12.0, KotlinX Serialization | `ApiService.kt` matches Flask `/api/v1` envelope |
| **Cookie & CSRF Handling** | `PersistentCookieJar.kt`, `CsrfInterceptor.kt` | Enforces double-submit cookie & session preservation |
| **Biometrics** | AndroidX Biometric 1.1.0, EncryptedSharedPreferences | Tested in `BiometricAuthStatusTest.kt` |
| **Build Variants** | `debug` (10.0.2.2 / local API), `release` (ProGuard / Keystore signing) | Verified in `buildTypes` |

#### Existing Android Unit Tests:
- `BiometricAuthStatusTest.kt` & `BiometricErrorTest.kt`
- `ImageUrlResolverTest.kt` & `MediaBaseUrlResolverTest.kt`
- `BannerDtoTest.kt`, `CartDtoTest.kt`, `CategoryDtoTest.kt`, `ProductDtoTest.kt`
- `PersistentCookieJarTest.kt` & `SafeNetworkLoggingInterceptorTest.kt`
- `CartUiStateTest.kt`, `CategoriesUiStateTest.kt`, `ProductDetailUiStateTest.kt`, `ProductsUiStateTest.kt`, `SearchUiStateTest.kt`

### 2.2 Backend & API Architecture

| Surface | Authority | API Prefix | Security Gates |
|---|---|---|---|
| Flask / Python | Authoritative Commerce | `/api/v1` | Session Cookie, CSRF token (`X-CSRFToken`), Role checks, Rate limiting |
| Express / Node | AI & Distribution | `/api/gemini`, `/api/download`, `/api/science` | Strict CORS allowlists, payload bounds (1MB/16MB/32MB), concurrency limiters |
| Shared Express Router | Dev Gateway | `/api/v1` fallback | In-memory verified catalog data for container environments |

### 2.3 Web Application & `Get App` Button Integration

The customer-facing website features a dedicated `Get App` button in `src/components/PWAInstallButton.tsx`:
- **Current Flow**:
  1. User clicks `Get App` in the navigation header.
  2. `PWAInstallButton` calls `getApkMetadata()` from `src/services/apkDownloadService.ts`.
  3. Queries `GET /api/download/apk/info` to fetch APK details (version, size, filename, SHA-256).
  4. Triggers `downloadApk()` via streaming fetch with `application/vnd.android.package-archive` MIME enforcement.
  5. Fallback triggers direct anchor download or PWA home screen installation modal if APK is unverified or unavailable.

---

## 3. Test Environments & Quality Gates

### 3.1 Quality Gate Hierarchy

```
[Level 1: Static Analysis & Lint]
  ├─ Python Ruff / byte-compile
  ├─ TypeScript 'tsc --noEmit'
  └─ Repository Structure & Lockfile Verification ('validate_repository_structure.py')
         │
[Level 2: Unit & Security Tests]
  ├─ Node Security Suite (CORS, Rate Limits, Body Validation)
  ├─ Marketplace API Contract Suite (Checkout, Payment, Catalog)
  └─ Android Local Unit Tests (DTOs, State Holders, Biometrics)
         │
[Level 3: Backend & Integration Tests]
  ├─ Python Pytest (Auth, Orders, Payments, Cart, Banners)
  └─ In-Memory / Sandbox Payment Scenarios
         │
[Level 4: Android Build & Package Validation]
  ├─ APK Generation & Archive Structure Check
  ├─ Manifest & DEX Integrity Verification
  └─ SHA-256 Checksum Generation
         │
[Level 5: Emulator / Device Verification]
  ├─ Virtual Device Boot & APK Install
  ├─ Cold Startup & ANR / Crash Detection
  └─ Critical User Journey Smoke Tests
         │
[Release Gate: Atomic Promotion]
  ├─ Atomic update to '/APK/latest.apk' & '/APK/latest.json'
  ├─ Sync to '/public/downloads/nexhaat.apk'
  └─ Report Generation in '/reports/'
```

---

## 4. Environment Variables & Secret Hygiene

All secrets and credentials remain server-side and protected:
- `NEXHAAT_KEYSTORE_PATH`, `NEXHAAT_KEYSTORE_STORE_PASSWORD`, `NEXHAAT_KEYSTORE_KEY_ALIAS`, `NEXHAAT_KEYSTORE_KEY_PASSWORD`: Android signing keys (never committed, read via environment in CI).
- `GEMINI_API_KEY`: Server-side AI model invocation (never exposed to browser client).
- `SECRET_KEY`, `DATABASE_URL`: Flask session encryption and database connectivity.
- `SSLCOMMERZ_STORE_ID`, `SSLCOMMERZ_STORE_PASSWORD`: Payment gateway test sandbox credentials.

No secrets are printed in logs, exposed in release metadata, or committed to Git.
