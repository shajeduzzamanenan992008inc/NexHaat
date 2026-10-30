# NexHaat SMS OTP — Read-Only Implementation Plan

**Status:** draft plan only
**Scope:** Bangladesh-first SMS OTP alongside the existing email OTP system, with provider fallback treated separately from channel fallback.
**Decision rule:** no code is changed by this document. No provider account is created. No SMS is sent. Implementation begins only after explicit approval.

---

## 1. What the repository currently does

### OTP surface

- Registration, seller application, admin login, password reset, Telegram account linking, and staff invitations all use one-time codes today.
- `app/routes/auth.py` is the main HTML/auth flow. `app/api/routes/auth.py` exposes the JSON equivalents for registration, admin code request/verify, login, logout, and `/me`.
- Both paths share a small set of security primitives from `app/security.py`, including:
  - `_reset_code_digest(code)` — HMAC-SHA256 digest of the code using `SECRET_KEY`
  - `_as_utc(value)` — timezone-safe UTC conversion
  - `login_is_throttled(...)`, `record_login_failure(...)`, `clear_login_failures(...)` — IP-based auth-rate protection
- The current challenge model family in `app/models/security.py` is:
  - `AuthThrottle`
  - `AdminLoginChallenge`
  - `RegistrationChallenge`
- Existing OTP defaults already look very close to the proposed SMS defaults:
  - `REGISTRATION_CODE_TTL` = 10 minutes
  - `ADMIN_LOGIN_CODE_TTL` = 10 minutes
  - `REGISTRATION_CODE_RESEND_SECONDS` = 60
  - `ADMIN_LOGIN_CODE_RESEND_SECONDS` = 60
  - `REGISTRATION_CODE_MAX_ATTEMPTS` = 5
  - `ADMIN_LOGIN_CODE_MAX_ATTEMPTS` = 5
  - One-time codes are generated with `secrets.randbelow(1_000_000):06d`, so they are already 6-digit numeric codes.

### OTP delivery reality today

- OTP delivery is currently email-first and effectively fire-and-forget at the point of generation.
- The HTML flow calls `queue_registration_code(...)`, `queue_admin_login_code(...)`, and `queue_password_reset_code(...)`.
- The API flow for admin login calls `_queue_admin_code(...)`.
- Background delivery is delegated to `app/services/mail.py`, which either calls Brevo directly or, in development/testing without a configured provider, logs a preview.
- There is a queued-email outbox in `app/models/outbox.py` (`OutboundEmail`) and retry tooling (`enqueue_order_emails`, `queue_order_receipt`, `queue_order_status`, `retry_pending_emails`), but the OTP flows do **not** use that outbox. They generate the code and queue background email delivery immediately.

So the current OTP architecture is:
1. generate code
2. store only the digest
3. queue background email delivery
4. verifier compares the submitted code against the stored digest

There is no SMS path today.

### Config surface that matters for SMS

From `app/config.py`:
- `SECRET_KEY` is the app-wide shared secret and is already used for OTP digests
- `ENVIRONMENT`, `TESTING`, `FLASK_TESTING`
- `MAIL_TIMEOUT` shows the app already treats provider HTTP calls as timeout-bound
- Provider tokens are loaded from the environment, e.g. `BREVO_API_KEY`, `TELEGRAM_...`
- `TestingConfig` already forces `AI_PROVIDER = "disabled"` and clears AI secrets, which is a good pattern to mirror for SMS in tests

From `.env.example`:
- No SMS provider variables exist yet
- The file already groups provider secrets into clear sections (Email, Telegram, Catalog & Security, AI), so SMS should get its own section

### What is **not** present

- No phone-number normalization helper
- No SMS provider adapter
- No SMS challenge model
- No SMS rate-limit or resend policy for phone OTP
- No provider abstraction layer for SMS
- No SMS-specific test coverage

---

## 2. Provider research summary

This plan does **not** select a final provider. It treats the candidate list as provisional.

### Candidates

1. **Alpha SMS / sms.bd**
   - Appears to publish REST API usage and message status/report concepts.
   - Appears to publish pricing tiers for non-masking and masking SMS.
   - Best fit as the first candidate to inspect in detail because documentation surface is publicly visible.

2. **Osel Soft**
   - Presents itself for OTP/transactional SMS and local operator coverage.
   - Second candidate for comparison, especially if delivery-reporting API and error contracts differ materially from the first candidate.

3. **Twilio**
   - International provider with published Bangladesh outbound pricing.
   - Useful as a fallback comparison, but published rate is much higher than the local candidates in the research summary, so it should be treated as a costlier international option unless local delivery or compliance becomes the deciding factor.

### What must be verified before any provider is chosen

- REST API endpoint shape, authentication method, and required headers
- Whether the provider supports transactional/OTP use cases explicitly
- Whether Bangladesh operator coverage is documented or only claimed
- Sender ID rules: approved/registered sender IDs, masking, alpha sender, and any country-specific restrictions
- Message status semantics: what `sent`, `delivered`, `failed`, and intermediate states actually mean
- Timeout, retry, and rate-limit guidance from the provider
- Published pricing, package minimums, validity, renewal, and hidden carrier/billing charges
- Whether the provider exposes any idempotency key, duplicate suppression, or message reference that can be stored server-side
- Operational expectations: dashboard, support, resolution time, and any regulatory or eligibility paperwork

### Important distinction for the plan

Provider documentation can justify an integration **shape** and a fallback **policy**, but it cannot, by itself, prove:
- reliable delivery in Bangladesh
- regulatory eligibility
- approved sender ID status
- cost certainty
- testability without credentials

So the implementation plan should keep the provider choice replaceable and should not bake any single vendor into the core model.

---

## 3. Security and delivery architecture

### 3.1 Guiding principle

SMS OTP should be an **additional verification channel**, not a replacement for email OTP.

The existing flows should keep working:
- registration and seller application verification
- admin OTP login
- customer password reset
- staff invitations

SMS OTP should first be introduced only where a verified phone number and an authorized flow make it sensible.

### 3.2 Provider-independent design

The recommended shape is a small SMS provider interface with:
- a provider-independent service layer that the auth flows call
- provider adapters that normalize one provider’s request/response/error semantics into a shared internal contract
- configuration that selects a primary adapter and, optionally, a secondary adapter
- logging that records outcomes and provider error classes, never OTPs or provider credentials

This mirrors the existing email arrangement loosely:
- email has `mail.py` and a Brevo adapter
- SMS should have an `sms.py` (or similar) service and one adapter per provider

But SMS should **not** reuse the email outbox unless a separate decision is made that the OTP flow needs the same retry/backfill model. Today’s OTP flow does not use the outbox, so adding SMS does not automatically justify introducing one.

### 3.3 Suggested provider adapter contract

A provider adapter should be able to answer, in provider-neutral terms:
- `send_message(phone, text)` → provider message identifier, or a normalized failure
- `message_status(message_id)` → one of a small internal status set, if the provider exposes status
- provider-specific error classification:
  - credential/authorization failure
  - insufficient balance or quota
  - invalid destination/number
  - rate-limited / 429
  - transient network or provider error / 5xx
  - timeout
  - unknown or ambiguous delivery state

That classification is the key to safe fallback.

### 3.4 OTP storage and verification

SMS OTP should reuse the existing security pattern:
- generate a 6-digit code with `secrets`
- store only a digest, not the plaintext code
- verify with `hmac.compare_digest`
- expire after a fixed TTL
- count failed attempts and lock after the max

The main new question is where to store the phone-OTP challenge.

Two realistic options:
1. **Reuse/extend the existing challenge model family**  
   - Pros: consistent with current auth code, same digest/attempt/expiry pattern, fewer new models
   - Cons: current challenge rows are email-centric; the new model would need phone, channel, and possibly link-to-user handling
2. **Add a dedicated phone-verification challenge model**  
   - Pros: cleaner separation for phone OTP, easier to add phone-specific metadata and audit fields
   - Cons: another model and likely one more migration

Given the existing code already has `AdminLoginChallenge` and `RegistrationChallenge`, a dedicated model for phone OTP is the safer fit if SMS OTP is going to be used for more than one flow. It keeps email challenges and phone challenges cleanly separated and avoids overloading the current models with channel-specific semantics.

A phone-OTP challenge should at least store:
- normalized phone number
- hashed code
- creation time
- expiry time
- failed attempt count
- consumed time
- which channel/context requested it, if relevant
- enough linkage to the subject account or request to verify safely, without exposing secrets

### 3.5 Phone-number handling

Phone numbers must be normalized before throttling, storage, provider calls, and log redaction.

Suggested normalization rules:
- strip printable whitespace and obvious delimiters
- validate the candidate against a Bangladesh-friendly E.164-style pattern such as `+8801XXXXXXXXX`
- store a canonical form, not the raw user input
- if a number cannot be normalized safely, reject it early rather than guessing

This is important for:
- rate limiting by phone number
- avoiding duplicate challenges for the same destination
- preventing log/bookkeeping drift across different input formats

### 3.6 Rate limiting and abuse controls

SMS is a cost-sensitive endpoint, so the SMS OTP path needs its own abuse controls in addition to the existing IP-level login throttle.

Suggested controls:
- per-IP rate limits for requesting an SMS code
- per-phone rate limits for requesting an SMS code
- per-phone rate limits for verifying an SMS code
- resend cooldown per phone challenge
- max attempt lockout per phone challenge
- consistent non-enumerating errors:
  - requesting a code should not reveal whether the phone is registered
  - verifying a code should not reveal whether the failure was “expired”, “wrong”, or “not found” if that helps enumeration
- server-side cost controls:
  - do not send SMS speculatively
  - do not automatically switch channels without explicit authorization
  - keep resend behavior conservative

A good default is to mirror the current OTP behavior closely:
- 6-digit code
- 10-minute expiry
- 5 max failed attempts
- 60-second resend cooldown

These are starting values, not final policy. Final values should be chosen after reviewing existing behavior and operational risk.

### 3.7 Provider fallback

Provider fallback should be explicit and conservative.

Safe fallback rules:
- classify the failure first
- retry/failover only for errors that are plausibly transient and safe to re-attempt
- treat timeouts and unknown delivery state cautiously
- avoid a blind parallel send through a second provider just because the first call timed out, because that can create duplicate OTPs
- if the first provider’s status can be checked later, prefer checking before resending
- if the provider has no reliable status query and a timeout leaves the outcome uncertain, the safer default is usually to surface a generic “try again” state rather than immediately duplicate-sending
- if all configured providers fail, return a safe error and keep the existing email path where it applies

This means fallback logic should be policy-driven, not just “try the next provider on any error.”

Possible internal policy shapes:
- on credential or configuration failure: do **not** retry with another provider; fail fast with a safe error
- on balance/quota exhaustion: fail fast unless the product decision is to fail over to another provider with its own quota
- on 429: respect retry-after behavior where available, and do not immediately hammer a second provider
- on 5xx or connection errors: a limited retry/failover may be appropriate, subject to the duplicate-delivery risk above
- on timeout with unknown outcome: do not assume success or failure; prefer a conservative response and, if needed, a status check before any resend

### 3.8 Channel fallback vs provider fallback

These should be kept separate.

Provider fallback = “the SMS provider returned an error, so try another SMS provider if policy allows.”

Channel fallback = “send the same OTP through a different communication channel.”

Channel fallback is more sensitive because:
- it can move verification to a phone number the user did not just authorize
- it can weaken the assurance model of a given flow
- it can expose account existence or contact details across channels if done carelessly

So:
- email OTP should remain email OTP unless a specific flow and authorization explicitly allow otherwise
- SMS OTP should be introduced as a new channel with its own entry points and verified use cases
- automatic Email → SMS or SMS → Email switching should not be assumed safe by default

---

## 4. Existing-code evidence used in this plan

### OTP secrets are already handled with HMAC + SECRET_KEY

- `app/routes/auth.py` defines `_reset_code_digest(code)` using `current_app.secret_key` and `hmac.new(..., hashlib.sha256).hexdigest()`
- It also defines a separate `_telegram_link_code_digest(code)` using a namespaced message prefix
- Verification in both HTML and API paths uses `hmac.compare_digest`

This means SMS OTP does not need a new cryptographic approach; it can reuse the same digest/compare pattern.

### 6-digit codes and existing TTL/attempt/resend constants

- `REGISTRATION_CODE_TTL`, `ADMIN_LOGIN_CODE_TTL` are 10 minutes
- `REGISTRATION_CODE_RESEND_SECONDS`, `ADMIN_LOGIN_CODE_RESEND_SECONDS` are 60
- `REGISTRATION_CODE_MAX_ATTEMPTS`, `ADMIN_LOGIN_CODE_MAX_ATTEMPTS` are 5
- codes are generated as `f"{secrets.randbelow(1_000_000):06d}"`

That is direct evidence that the proposed SMS OTP defaults are consistent with current app behavior.

### OTP is currently email-delivered with background queuing

- `app/routes/auth.py` calls `queue_registration_code`, `queue_admin_login_code`, `queue_password_reset_code`
- `app/services/mail.py` defines those queue helpers and uses background threads for off-request delivery
- `app/api/routes/auth.py` admin code flow calls `_queue_admin_code`, which calls `queue_admin_login_code`

This is evidence that OTP delivery is already abstracted behind queue helpers, which is a good place to add an SMS delivery option later. It also shows OTP does **not** currently go through the queued-email outbox.

### Email provider is Brevo, and credentials are environment-only

- `app/services/mail.py` calls Brevo at `https://api.brevo.com/v3/smtp/email`
- `app/config.py` loads `BREVO_API_KEY`, `MAIL_DEFAULT_SENDER`, and other provider secrets from environment/config
- `.env.example` has no SMS provider yet

This supports a provider-independent SMS design and reinforces that SMS credentials must also stay in private runtime config.

### Throttling primitives already exist

- `app/security.py` implements `login_is_throttled`, `record_login_failure`, `clear_login_failures`
- it uses `AuthThrottle` with a keyed hash of the client address
- `app/api/routes/auth.py` already applies `login_is_throttled` to the admin code and verify endpoints

This is a good base, but SMS OTP will likely need phone- and account-aware throttling in addition to IP throttling.

### Existing test patterns are mock-friendly

- the test suite already exercises auth, API foundation, email/orders, and provider-adjacent behavior
- `TestingConfig` already disables AI and clears AI secrets
- this suggests tests should mock the SMS provider HTTP layer and assert only safe, non-secret outcomes

---

## 5. File-by-file implementation plan

This is a proposed implementation plan, not a change set.

### 5.1 Configuration

**File:** `app/config.py`

**Why:** SMS provider tokens, sender settings, and environment flags need a config home analogous to the existing email/Telegram/AI sections.

**Planned responsibility:**
- add SMS provider section:
  - primary provider name/adapter identifier
  - primary provider credentials
  - optional secondary provider identifier and credentials
  - sender ID/ originator settings, if applicable
  - provider timeout
  - max SMS attempts before giving up
  - feature flag for enabling SMS OTP in a given environment
- keep all SMS secrets out of source control and out of error responses

**Security implications:**
- these are secrets and must be treated like `BREVO_API_KEY` and the Telegram tokens
- tests should use a safe test config that disables real SMS

**Dependencies:**
- later adapters and service layer will read these values

---

**File:** `.env.example`

**Why:** operators need a clear, commented place to configure SMS without guessing.

**Planned responsibility:**
- add a documented SMS section
- show the primary/secondary provider identifiers
- show where credentials, sender ID, timeout, and environment flag go
- keep examples non-functional until real credentials are supplied

**Security implications:**
- no real credentials in the example file
- no provider-specific behavior implied beyond the documented config shape

---

### 5.2 Provider adapter layer

**File:** `app/services/sms.py` (service layer)

**Why:** auth flows should call one service, not each provider directly.

**Planned responsibility:**
- normalize provider configuration into an active provider choice
- offer a provider-neutral `send_otp(phone, code)` operation
- classify provider responses into safe internal outcomes
- implement fallback policy, if enabled
- keep OTP text generation out of the provider adapter where possible, so the same OTP can be handled consistently
- return only safe outcomes to callers

**Security implications:**
- never log the OTP
- never log full provider credentials
- avoid leaking whether a phone number is registered through different error paths
- keep provider error details internal; expose only stable client-facing messages

---

**File(s):** provider adapter module(s), for example:
- `app/services/sms_adapters.py` or
- `app/services/sms/__init__.py` plus provider modules

**Why:** each provider has different auth, request shape, status semantics, and error shapes.

**Planned responsibility:**
- implement one adapter per provider
- each adapter implements the same internal interface
- each adapter normalizes its own errors into the shared classification
- each adapter returns a provider message identifier when applicable
- each adapter should be mockable in tests

**Security implications:**
- adapter should not persist secrets in logs or response payloads
- adapter should honor request timeouts
- adapter should not assume success from a missing or ambiguous response

**Dependencies:**
- config
- shared internal error classification
- possibly a small provider-message status model if delivery tracking is needed

---

### 5.3 Phone-number handling

**File:** new helper, likely in `app/services/sms.py` or a small `app/services/phone.py`

**Why:** phone numbers are the key throttling and delivery key for SMS OTP.

**Planned responsibility:**
- normalize phone input to a canonical form
- validate format strictly enough to reject garbage and ambiguous inputs
- provide a safe representation for storage and throttling
- provide a redacted form for logs

**Security implications:**
- normalization must not weaken validation
- logs must not store raw sensitive phone detail unnecessarily
- enumeration protection depends on consistent phone handling

---

### 5.4 Phone OTP challenge model

**File:** `app/models/security.py` or a new model file

**Why:** SMS OTP needs its own challenge lifecycle if it is more than a one-off feature.

**Planned responsibility:**
- store hashed code
- store normalized phone
- store expiry, failed attempts, consumed time
- store enough context to verify safely
- support rate-limit and lockout semantics similar to current challenges

**Security implications:**
- never store plaintext OTP
- keep challenge identifiers non-guessable
- ensure verification does not leak why a code failed when that would help enumeration

**Possible migration:**
- if this is a new model, an additive Alembic migration is the natural fit
- do **not** assume a migration is required before this is approved; only add it if the model decision is final

---

### 5.5 OTP generation and verification helpers

**File:** likely `app/routes/auth.py`, `app/api/routes/auth.py`, or a shared helper module

**Why:** registration, admin login, and password reset already share OTP generation/verification patterns. SMS OTP should reuse them rather than invent a parallel system.

**Planned responsibility:**
- reuse `_reset_code_digest` pattern and `hmac.compare_digest` verification
- define SMS OTP TTL, max attempts, and resend cooldown consistently
- optionally centralize OTP generation so email and SMS flows use the same secure generation method

**Security implications:**
- keep timing-safe comparison
- keep code generation random and server-side
- avoid creating differences between email and SMS security properties unless intentionally reviewed

---

### 5.6 Auth flow changes

**Files:** `app/routes/auth.py`, `app/api/routes/auth.py`

**Why:** SMS OTP will need request and verify endpoints for the flows where it is enabled.

**Planned responsibility:**
- add phone code request and verify behavior for the chosen initial flow(s)
- apply IP throttling and phone-aware throttling
- enforce resend cooldown and attempt limits
- gate SMS availability behind config/feature flag and provider readiness
- preserve existing email paths untouched

**Security implications:**
- do not reveal account existence through different SMS behavior
- do not auto-route to SMS unless the flow and authorization permit it
- keep error messages generic where enumeration is a risk
- keep provider and channel fallback decisions explicit

**Dependencies:**
- SMS service layer
- phone normalization
- phone OTP challenge model
- config/feature flag

---

### 5.7 Operations and observability

**File:** likely `app/services/sms.py` and/or audit/notification hooks

**Why:** SMS delivery failures, retries, and provider errors need safe observability.

**Planned responsibility:**
- log outcomes and provider error class
- log provider message identifiers only if safe and necessary
- never log OTP values or provider credentials
- provide operational retry/checking behavior only where it is safe

**Security implications:**
- redact sensitive fields
- avoid creating a log path that could leak OTPs or secrets in production

---

### 5.8 CLI/ops parity with email

**File:** possibly `app/__init__.py` or a small ops helper

**Why:** the app already has `check-mail` and `retry-emails` CLI commands.

**Planned responsibility:**
- consider an analogous SMS configuration check command, if the provider supports a safe non-send check
- consider a safe retry command only if a persisted SMS delivery queue is introduced and justified

**Security implications:**
- any check command must not send real SMS or expose credentials

---

## 6. Test plan

### 6.1 General rules

- No test may send a real SMS.
- Provider HTTP calls must be mocked.
- No test may print OTPs, phone numbers, or provider credentials.
- Tests should assert stable, non-secret outcomes only.

### 6.2 Provider adapter unit tests

Mock HTTP and assert:
- successful send returns a usable provider message identifier or service-level success
- credential/authorization failure is classified correctly
- insufficient balance/quota is classified correctly
- 429 is classified correctly
- 5xx is classified correctly
- timeout is classified correctly
- malformed responses do not crash the adapter
- provider responses do not leak secrets into logs or return values

### 6.3 SMS service unit tests

Mock the adapter and assert:
- provider selection uses configuration
- fallback policy only triggers for allowed error classes
- ambiguous outcomes do not automatically produce duplicate sends
- safe errors are returned when all providers fail
- logs contain no OTP or credential values

### 6.4 Phone normalization tests

Assert:
- canonical Bangladesh numbers normalize correctly
- various input formats map to one canonical form
- invalid/unusual inputs are rejected safely
- redacted representations hide sensitive detail

### 6.5 OTP challenge and verification tests

Assert:
- code is stored only as a digest
- valid code passes, invalid code fails, expired code fails
- attempt lockout works
- resend cooldown works
- verification does not leak enumeration-prone details through different error paths

### 6.6 API and route tests

Assert:
- SMS code request is throttled appropriately
- verify endpoint enforces attempts, expiry, and cooldown
- SMS is unavailable when provider/config is not ready
- existing email OTP flows still behave the same in the test suite
- responses do not include secrets

### 6.7 Email regression tests

Assert that:
- registration email OTP still works
- admin email OTP still works
- password reset email OTP still works
- existing email-related behaviors are not regressed by the new SMS abstractions

This is important because SMS OTP must not silently change email behavior.

---

## 7. Acceptance criteria

### Security and privacy
- OTP is stored only as a digest
- OTP, provider credentials, and sensitive phone/request data are not logged
- requests are rate-limited and abuse-controlled
- enumeration-prone behavior is minimized
- secrets stay in private runtime config

### Delivery behavior
- a valid SMS OTP verifies successfully
- an invalid SMS OTP is rejected safely
- an expired SMS OTP is rejected safely
- attempt lockout works
- resend cooldown works
- provider authentication failure is handled without exposing secrets
- rate limiting and insufficient balance are handled appropriately
- HTTP 429 and 5xx are handled according to the chosen policy
- connection timeout and unknown delivery status are handled conservatively
- primary provider failure does not cause unsafe duplicate delivery
- secondary provider handling is conservative and policy-driven
- email OTP continues to work unchanged in the test suite

### Testability and safety
- SMS provider calls are mocked in tests
- no real SMS is sent during tests or CI
- no secret values appear in test output

---

## 8. Blockers and open questions

### Blockers before selection
- provider API documentation must be checked directly from the provider source
- sender ID rules and approval requirements must be confirmed for Bangladesh
- published pricing must be checked for package minimums, validity, and extra charges
- regulatory/eligibility status should not be assumed from marketing claims
- delivery reporting quality must be confirmed, not assumed

### Open questions
- which flows should support SMS OTP first
- whether SMS OTP should be tied to a verified phone number or an explicit user action
- whether provider fallback should be enabled initially or only after the send behavior is proven
- whether a persisted SMS delivery queue is justified, or whether the current fire-and-forget OTP model is acceptable for SMS too
- whether a new phone-OTP model is required or whether the existing challenge family can be extended safely
- final TTL, max attempts, and resend cooldown values for SMS OTP
- whether SMS OTP should ever be a recovery path for email OTP, and if so, under what authorization

---

## 9. Recommended next step

Approve this read-only plan first.

If approved, the next implementation phase should be small and safe:
1. add config skeleton and test config
2. add phone normalization helper with tests
3. add provider adapter interface and one mocked provider adapter with tests
4. add SMS service layer with mocked fallback behavior and tests
5. add a phone-OTP challenge model plan and, only if approved, a migration plan
6. add SMS OTP endpoints for one initial flow behind a feature flag
7. add email regression coverage
8. add observability/privacy-safe logging behavior

No provider sign-up, API key, migration, or real SMS happens in that phase either unless explicitly requested and approved separately.
