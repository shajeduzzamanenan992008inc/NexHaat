# Phase 1 — Stage 1: Provider Sign-in and 2FA Hardening

**Date:** 3 November 2026
**Base commit:** `0f7798d` (local `main`, 2 commits behind `origin/main` at `d9dfa2e`)
**Scope:** Close the account-takeover path in provider sign-in, stop accepting a
caller-supplied TOTP secret, remove the client's fake social sign-in, and pin the
behaviour with regression tests. **No schema change, no dependency change, no
deployment.**

---

## 1. Findings reverified before editing

| Phase 0 finding | Verified state in current code |
|---|---|
| `POST /api/v1/auth/social-login` authenticated a client-supplied email | **Confirmed** — the handler read `email`/`display_name` and never read any token field; it started a session and auto-created accounts |
| 2FA material in the session cookie | **Confirmed** — `session["totp_pending_secret"]`, `session["totp_backup_codes"]`, `session["totp_secret"]` |
| `/2fa/verify` accepted a caller-supplied secret | **Confirmed** — `payload.get("secret")` took priority over the server value |
| Android shipped fake provider sign-in | **Confirmed (new detail)** — `SignInScreen.kt`/`SignUpScreen.kt` sent literal `"google_token"`, `"ms_token"`, `"gh_token"` with placeholder emails |
| No tests covered either area | **Confirmed** — zero matches for `social`, `2fa`, `totp` in `tests/` |

---

## 2. Changes

| File | Change |
|---|---|
| `app/api/routes/auth.py` | `social_login()` rewritten: no email/display-name input is read, provider must be one of `google`/`microsoft`/`github`, login throttle applies, the attempt is audited as `auth.social_login_blocked`, and the route fails closed with `503 SOCIAL_LOGIN_UNAVAILABLE`. Removed the now-unused `generate_password_hash` import and the auto-account-creation branch. |
| `app/api/routes/auth.py` | `/2fa/verify` now reads the secret **only** from `session["totp_pending_secret"]`; returns `400 SETUP_EXPIRED` when no server-side setup exists; adds a 5-attempt session limit that discards the pending secret (`429 CODE_LOCKED`) and counts failed codes. |
| `android/.../ui/screens/auth/SignInScreen.kt` | Removed the Google/Microsoft/GitHub buttons and the surrounding divider. |
| `android/.../ui/screens/auth/SignUpScreen.kt` | Same removal, including the `*_login_button` test tags; dropped now-unused `HorizontalDivider`/`OutlinedButton` imports. |
| `android/.../ui/screens/auth/SignInViewModel.kt`, `SignUpViewModel.kt` | Removed `socialLogin(...)`. |
| `android/.../data/repository/AuthRepository.kt` | `socialLogin(provider, idToken)` — no email/name parameters. |
| `android/.../data/remote/dto/AuthDto.kt` | `SocialLoginRequestDto(provider, id_token)` — the `email`/`name` fields are gone. |
| `tests/test_auth_social_login.py` (new) | 5 regression tests (below). |

No route was deleted, so clients still receive a JSON envelope instead of a 404.
Email/password login, registration, OTP, reset, and `/auth/me` are untouched.

---

## 3. Behaviour: before / after

| Scenario | Before | After |
|---|---|---|
| `POST /auth/social-login {"provider":"google","email":"victim@…"}` | Session created for the victim's account; account auto-created if absent | `503 SOCIAL_LOGIN_UNAVAILABLE`, no session, no account |
| Unknown provider | Ignored, treated like any other | `422 UNSUPPORTED_PROVIDER` |
| `POST /auth/2fa/verify {"code":"<valid for attacker secret>","secret":"<attacker secret>"}` | `200` — attacker-defined factor "enabled" | `400 SETUP_EXPIRED` |
| Repeated wrong 2FA codes | Unlimited | Locked after 5; pending secret discarded |

---

## 4. Tests executed

| Check | Command | Result |
|---|---|---|
| New regression tests | `python -m pytest tests/test_auth_social_login.py -q` | **PASS** — 5 passed |
| API foundation regression | `python -m pytest tests/test_api_foundation.py -q` | **PASS** — 21 passed |
| Full Python suite | `python -m pytest -q` | **PASS** — 321 passed in 386.54s (316 before this stage + 5 new) |
| Python lint | `python -m ruff check app tests` | **PASS** |
| Whitespace | `git diff --check` | **PASS** |
| Android Kotlin compile | `./gradlew :app:compileDebugKotlin --offline` | **BLOCKED / NOT TESTED** — the wrapper did not finish within 10 minutes locally; the Kotlin edits are therefore uncompiled |

---

## 5. Explicitly not done

* Real TOTP persistence, login enforcement, backup-code hashing, QR generation: **Stage 2**
  (approved design: `cryptography` AES-GCM, `202` + `/api/v1/auth/2fa/challenge`).
* Provider token verification (Google/Microsoft/GitHub): **Stage 5**, needs provider credentials.
  Until then every provider request returns `503` — never an email fallback.
* Session listing / logout-all-devices: **Stage 3**.
* Android and web UI for the new 2FA flow: **Stage 4**.
* The old session-based `setup_2fa` still exists and still writes the secret to the cookie; it is
  **not** safe and must be replaced by Stage 2 before 2FA is presented as a protection.
* Firebase Google popup remains unlinked to Flask (owner decision: keep and document).

---

## 6. Git state

Working tree changes are limited to the eight source files above plus the new test file. No
commit, push, deployment, migration, or production change was made. Gradle cache files touched by
the aborted compile attempt were restored; Gradle daemons were stopped.
