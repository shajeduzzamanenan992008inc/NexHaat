# Phase 10 — Authentication Integration Design

## Inspection of flows

### Web routes (`app/routes/auth.py`)
- **Registration (customer)**: `GET/POST /register` collects `email`, `full_name`, `phone`, `password`, `password_confirmation`. Validates formats/lengths, checks duplicates, requires `_staff_email_ready()` (Brevo configured or dev mode). Creates `RegistrationChallenge` via `_create_registration_challenge()` which generates 6-digit code, stores HMAC digest in `RegistrationChallenge`, saves challenge, sets `session['registration_challenge_id']`, calls `queue_registration_code(email, code, locale=...)` (Brevo/email). Redirects to `verify_registration`. Email verification is required to create account.
- **Seller application**: similar flow, creates seller profile with `approval_status='pending'` after email verification.
- **Email verification**: `GET/POST /verify-registration` validates challenge (exists, not consumed, not expired). On POST verifies code with HMAC compare against stored digest, checks attempts (max 5, locks/deletes on exceed), checks for duplicate email, creates User+profile, deletes challenge, clears session. Resend via `/resend-registration-code` with 60s cooldown, only if email ready.
- **Password reset**: `GET/POST /forgot-password` finds active user (non-admin), if eligible generates code, stores digest/hash in `user.password_reset_hash/expires_at/sent_at`, resets attempts, calls `queue_password_reset_code()` (email). Creates dummy session state for enumeration protection. `GET/POST /verify-reset-code` verifies code against user's stored hash with attempt limits (max 5 locks). On success marks session verified, redirects to `/reset-password`. `/reset-password` requires verified session, updates password, increments `auth_version`, clears reset fields.
- **Admin login**: email-based OTP via `AdminLoginChallenge`, sent via `queue_admin_login_code()` (Brevo). Separate flow from regular login.
- **Regular login**: password-based for customer/seller/rider/super_admin/support; admin uses separate OTP flow.
- **Account**: authenticated customers can view/update profile (including phone) at `/account` - no verification required currently.

### API routes (`app/api/routes/auth.py`)
- **POST /auth/register**: similar validation, calls `_create_registration_challenge()` from web routes (reuses same mechanism), requires `_staff_email_ready()`. Returns 202 with email/expires_at.
- **POST /auth/register/verify**: verifies code from session's registration challenge using same HMAC/digest logic as web, creates user/profile, deletes challenge.
- **POST /auth/login**: password login for customer/seller/rider only (API restriction).
- **POST /auth/admin/code**, **POST /auth/admin/verify**: admin OTP via email (same pattern as web).

## Chosen flow (safest, additive)
**Add SMS as an alternative delivery/verification channel for phone number verification in the customer account settings, without replacing or bypassing email verification.**

Rationale:
1. **Doesn't weaken auth**: Email verification remains the sole mechanism for account creation (registration still requires email OTP). SMS is additive.
2. **Respects constraints**: Doesn't silently replace email OTP; unverified phone cannot bypass existing account-verification requirements (account creation still requires email verification).
3. **Fits existing patterns**: Uses existing `PhoneOtpChallenge`, `send_phone_otp()`, `verify_phone_otp()`, phone normalization utilities. Follows same security patterns (HMAC digests, TTL, attempts, cooldown, single-use).
4. **Pragmatic**: Allows users to verify phone ownership for their profile (useful for future features) without changing core registration/login/password-reset flows.
5. **Minimal scope**: Only touches account management, doesn't affect unrelated flows.

Alternative flows considered but rejected:
- **SMS for password reset**: Could be useful but requires careful phone-account binding and verification state; higher risk of enumeration/lockout issues. Email reset is well-established.
- **SMS as alternative for registration verification**: Would need to allow choosing channel - complex to do safely without replacing email; easier to add as separate step.
- **SMS for login**: Not present in current flows, would be major change.

## Affected files
- `app/routes/auth.py` - add phone verification routes in account section (request code, verify code)
- `app/templates/auth/account.html` - add UI for phone verification (if exists)
- `app/models/user.py` or add verification flag? - Check if we need to track phone verification status. CustomerProfile has phone but no verification flag. We need to add a way to track verified phones. Options: add `phone_verified` to CustomerProfile, or track via PhoneOtpChallenge consumption for specific purpose. Better to add `phone_verified_at` or boolean to CustomerProfile for clarity.
- `app/models/__init__.py` - may need updates if models change
- Tests: add `tests/test_phone_verification.py` or extend existing tests

## Phone ownership requirements
- Phone must be normalized and validated as Bangladesh number using `normalize_bangladesh_phone()`/`is_valid_bangladesh_phone()`
- Phone must belong to the authenticated user's profile (customer only for this integration)
- Cannot verify a phone already verified/owned by another account? Need to check - but this is account management for existing authenticated users
- Verification is purpose-bound (e.g., purpose="verify_phone" or "account_phone")
- Only verified phones should be considered "owned/verified" - but we don't allow bypassing existing requirements

## Session behavior
- All routes require authentication (`@customer_required`)
- Use existing session management
- CSRF protection required (forms use CSRF)
- No changes to login session behavior
- Phone verification is independent of auth session beyond requiring authenticated user

## Backward compatibility
- Email OTP flows completely unchanged
- Existing account update flow continues to work (users can still update phone without verification)
- SMS disabled by default - no behavior change when disabled
- If SMS enabled but fails, gracefully degrade (show error, don't block phone update)
- All existing tests continue to pass

## Security considerations
- Purpose binding: use distinct purpose like `"verify_phone"` 
- Phone/account binding: verify challenge.phone_canonical matches normalized profile phone and is for correct user
- Expiry, single-use, attempt limits enforced by `verify_phone_otp()`
- Resend cooldown enforced by service
- Per-phone throttling via service (uses IP throttling + challenge-based cooldown; audit noted need for stronger per-phone throttling - we can add DB-level tracking)
- Prevent concurrent verification/resend (use SELECT FOR UPDATE where appropriate)
- Generic error messages to prevent enumeration
- Never log OTPs or full phones
- SMS only sent if enabled and provider configured
- Tests must mock SMS sending (never send real SMS)
