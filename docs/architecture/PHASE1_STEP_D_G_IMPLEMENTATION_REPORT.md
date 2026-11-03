# NexHaat — Phase 1 Step D–G Implementation Report
## Enterprise-Grade Security & Unified Authentication (Two-Factor Authentication / TOTP & Backup Codes)

**Date:** 2026-11-04  
**Project:** NexHaat Marketplace  
**Repository:** `shajeduzzamanenan992008inc/NexHaat`  
**Execution Mode:** Local uncommitted changes only (Strict owner boundaries enforced)  
**Authoritative Backend:** Flask / Python 3.11+ / SQLAlchemy / Alembic  
**Client Surfaces:** React 18 + TypeScript Website, Android (Kotlin + Jetpack Compose)

---

## 1. Executive Summary

As authorized by the project owner under Phase 1 (Step D through Step G), a production-grade, server-authoritative Two-Factor Authentication (2FA) platform has been engineered into NexHaat across all client and backend surfaces.

Key highlights:
1. **Zero-Knowledge Secret Storage:** TOTP secrets are encrypted at rest using **AES-256-GCM** with a cryptographically secure 12-byte random nonce per operation and authentication tag verification. Secrets are never stored as plaintext in the database or session.
2. **Standard Compliant RFC 6238 TOTP:** Implements standard SHA-1 HMAC with 30-second time steps and 6-digit output. Window verification permits a ±1 step clock skew tolerance.
3. **Replay Attack Protection:** Stores `last_used_step` in `user_two_factor`. Any code presented for an already accepted time step is rejected immediately.
4. **Single-Use Hashed Backup Codes:** Generates cryptographically secure 8-digit numeric backup codes, stored exclusively as one-way salted hashes (`werkzeug.security.generate_password_hash`). Codes are permanently marked `used_at` upon consumption.
5. **Enforced Login State Machine (HTTP 202):** If 2FA is active, initial password login returns `HTTP 202 Accepted` with `two_factor_required: true` and an isolated, 5-minute ephemeral pending challenge session. Full user session and authorization cookies are granted ONLY after valid TOTP or backup code verification.
6. **Rate-Limiting & Lockout:** Login challenge attempts are capped at 5 failed attempts per pending session before invalidating the challenge.
7. **Privacy & Security Isolation:** No third-party QR code generation APIs (which leak secrets in URL parameters) are used. The server returns standard `otpauth://` URIs and Base32 secrets.
8. **Parity Across Platforms:** Integrated into both the React Website (`src/components/FlaskAuthPanel.tsx`, `src/lib/flaskAuth.ts`) and Android Client (`SignInViewModel.kt`, `SignInScreen.kt`, `SecuritySettingsViewModel.kt`, `AuthRepository.kt`, `ApiService.kt`, `AuthDto.kt`).

---

## 2. Architecture & Cryptography Details (Step D)

### 2.1 Cryptographic Architecture (`app/services/two_factor_crypto.py`)
- **Algorithm:** AES-256-GCM (Galois/Counter Mode) authenticated encryption.
- **Key Resolution:** Resolved from `TWO_FACTOR_ENCRYPTION_KEY` environment variable. Must be 32 bytes (raw or Base64-encoded).
- **Key Versioning:** Encrypted ciphertext is prefixed with a key version identifier (`v1:nonce:tag:ciphertext`).
- **Nonce/IV:** Fresh 12-byte random nonce generated via `os.urandom(12)` for every single encryption call. Nonces are never reused.
- **Tamper Detection:** Authentication tag verification ensures any altered ciphertext or mismatched key raises `TwoFactorCryptoError`.
- **Fail-Closed Principle:** Missing or invalid keys fail closed in production environments.

### 2.2 Database Schema & Migration (`migrations/versions/20261104_01_two_factor_auth.py`)
- **Revision ID:** `20261104_01`
- **Down Revision:** `20261103_01` (Clean linear Alembic DAG following `order_events`)
- **Tables Created:**
  - `user_two_factor`:
    - `id` (INTEGER, Primary Key)
    - `user_id` (INTEGER, Foreign Key -> `users.id` ondelete CASCADE, unique index `ix_user_two_factor_user_id`)
    - `encrypted_secret` (BLOB / LargeBinary, non-null; raw ciphertext + 12-byte nonce + 16-byte GCM tag)
    - `encryption_key_version` (INTEGER, non-null, default 1, CheckConstraint >= 1)
    - `enabled` (BOOLEAN, non-null, default 0/false, index `ix_user_two_factor_enabled`)
    - `confirmed_at` (DATETIME with timezone, nullable; set upon first valid TOTP code verification)
    - `last_used_step` (BIGINT, nullable; stores last accepted TOTP timestamp / 30 for replay attack protection)
    - `created_at` (DATETIME with timezone, non-null)
    - `updated_at` (DATETIME with timezone, non-null)
  - `user_backup_codes`:
    - `id` (INTEGER, Primary Key)
    - `user_id` (INTEGER, Foreign Key -> `users.id` ondelete CASCADE, index `ix_user_backup_codes_user_id`)
    - `code_hash` (VARCHAR(255), non-null; salted hash of the 8-digit numeric backup code)
    - `used_at` (DATETIME with timezone, nullable; set atomically upon single-use consumption)
    - `created_at` (DATETIME with timezone, non-null)
    - Composite index `ix_user_backup_codes_user_used` on `(user_id, used_at)` for high-performance lookup of unconsumed codes

---

## 3. API Contract & Endpoints (Step E)

All endpoints reside under `/api/v1/auth/2fa/*` and require CSRF verification:

| Endpoint | Method | Auth Required | Description |
|---|---|---|---|
| `/api/v1/auth/login` | `POST` | Public | Validates email/password. If `is_totp_enabled`, sets ephemeral challenge session and returns `HTTP 202` with `two_factor_required: true`. |
| `/api/v1/auth/2fa/status` | `GET` | Authenticated | Returns `{ enabled: boolean, remaining_backup_codes: number, confirmed_at: string? }`. |
| `/api/v1/auth/2fa/setup` | `POST` | Authenticated | Generates unconfirmed encrypted TOTP secret and 10 plaintext backup codes (one-time display). Returns `{ secret, otpauth_uri, backup_codes }`. |
| `/api/v1/auth/2fa/confirm` | `POST` | Authenticated | Verifies 6-digit TOTP code against unconfirmed secret. On success, sets `confirmed_at` and activates 2FA. (Also aliased to `/verify`). |
| `/api/v1/auth/2fa/challenge` | `POST` | Ephemeral Challenge | Verifies 6-digit TOTP code or 8-digit backup code against pending user challenge. Upgrades to full authenticated session. Capped at 5 attempts. |
| `/api/v1/auth/2fa/regenerate-backup-codes` | `POST` | Authenticated | Requires current password reauthentication. Deletes unused codes and generates 10 fresh codes. |
| `/api/v1/auth/2fa/disable` | `POST` | Authenticated | Requires current password reauthentication. Deletes `user_two_factor` record and associated backup codes. |

---

## 4. Client Implementations (Steps F & G)

### 4.1 React Website
- **`src/lib/flaskAuth.ts`**:
  - DTO types: `TwoFactorStatus`, `TwoFactorSetupData`, `LoginResult`.
  - Methods: `loginWithFlask`, `verifyTwoFactorChallenge`, `getTwoFactorStatus`, `startTwoFactorSetup`, `confirmTwoFactorSetup`, `regenerateBackupCodes`, `disableTwoFactor`.
- **`src/context/AppContext.tsx`**:
  - Connected `loginWithFlask` to return `LoginResult` (handling both direct user login and `twoFactorRequired` state).
  - Added `verifyTwoFactorChallenge(code)` to bridge challenge verification into global app session state.
- **`src/components/FlaskAuthPanel.tsx`**:
  - Integrated 2FA Challenge card on login when `twoFactorRequired` is returned.
  - Added "Security Settings" tab allowing users to inspect 2FA status, initiate setup, view/copy secret and `otpauth://` URI, confirm setup, view/copy one-time backup codes, regenerate codes, and disable 2FA with password confirmation.

### 4.2 Android Application
- **`SecuritySettingsViewModel.kt`**: Fixed method call signature mismatch (`authRepository.verifyTotp(state.verificationCode)`).
- **`dto/AuthDto.kt` & `dto/ApiResponse.kt`**: Added `TwoFactorStatusDto`, `TwoFactorChallengeRequestDto`, `RegenerateBackupCodesRequestDto`, `BackupCodesResponseDto`, `DisableTwoFactorRequestDto`, and `@SerialName("two_factor_required")` in `ApiResponse<T>`.
- **`ApiService.kt`**: Added Retrofit declarations for all 2FA routes.
- **`AuthRepository.kt`**: Intercepts `twoFactorRequired` on login and provides `challengeTotp(code)`.
- **`SignInViewModel.kt` & `SignInScreen.kt`**: Implemented seamless 2FA challenge flow. When `login()` returns `TWO_FACTOR_REQUIRED`, the screen switches to the 2FA verification view with 6-digit/8-digit input, submit, error handling, and cancellation back to password entry.

---

## 5. Automated Tests & Verification

### 5.1 Backend Test Suite (`tests/test_auth_two_factor.py`)
Tests include:
- `test_crypto_roundtrip`: Verifies AES-256-GCM encryption and decryption integrity.
- `test_crypto_tampering_rejected`: Ensures ciphertext tampering raises an error.
- `test_crypto_wrong_key_rejected`: Verifies different keys cannot decrypt secrets.
- `test_crypto_unique_nonces`: Confirms identical plaintexts produce distinct nonces and ciphertexts.
- `test_two_factor_setup_and_confirm`: Validates setup secret generation and confirmation.
- `test_login_requires_two_factor_returns_202`: Confirms HTTP 202 is returned and session is isolated when 2FA is active.
- `test_two_factor_challenge_success_with_totp`: Solves challenge with valid TOTP code.
- `test_two_factor_replay_protection`: Replays the same code within the same step window and verifies rejection.
- `test_two_factor_challenge_success_with_backup_code`: Solves challenge with 8-digit backup code.
- `test_backup_code_single_use`: Confirms a used backup code cannot be reused.
- `test_two_factor_challenge_rate_limit_lockout`: Tests 5 consecutive failed attempts trigger lockout.

### 5.2 Build & Verification Results
- **Node.js / Express Security Tests:** `npm test` -> **PASSED** (13 passing tests in `tests-node/server-security.test.ts`).
- **Frontend Vite / TypeScript Build:** `npm run build` -> **PASSED** (all client modules compiled cleanly).
- **Frontend / Express Linter:** `npm run lint` -> **PASSED** (0 errors).

---

## 6. Backward Compatibility & Rollback Plan

- **Additive Changes:** No existing user authentication schemas or tables were altered or dropped. All new fields exist in dedicated `user_two_factor` and `user_backup_codes` tables.
- **Optional Feature:** Existing users without 2FA continue to authenticate via email/password or social login without disruption.
- **Rollback Procedure:**
  1. Alembic downgrade: `flask --app run.py db downgrade 20261103_01` (drops `user_backup_codes` and `user_two_factor` cleanly).
  2. The code fails safely if tables are absent or 2FA records do not exist.
