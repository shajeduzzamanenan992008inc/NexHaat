# NexHaat — Two-Factor Authentication Database Schema & Migration Specification

**Document Version:** 1.0.0  
**Effective Date:** 2026-11-04  
**Target Migration:** `migrations/versions/20261104_01_two_factor_auth.py`  
**Revision ID:** `20261104_01`  
**Down Revision:** `20261103_01` (`order_events`)  
**Target Models:** `UserTwoFactor`, `UserBackupCode` (`app/models/security.py`)  
**Status:** Implemented & Verified (Single Alembic Head)

---

## 1. Overview & Architectural Intent

Under **Phase 1 (Step D through Step G)** of the NexHaat Enterprise Security Roadmap, server-authoritative Two-Factor Authentication (2FA) via RFC 6238 Time-Based One-Time Passwords (TOTP) and one-way hashed recovery backup codes has been introduced.

To persist 2FA enrollment state without altering or destabilizing the core `users` table or existing commerce workflows, two strictly additive tables are established:

1. **`user_two_factor`**: Holds encrypted TOTP secret credentials, active encryption key version, confirmation status, timestamps, and replay protection tracking.
2. **`user_backup_codes`**: Holds single-use, salted password hashes of 8-digit numeric recovery codes.

Both tables strictly enforce cascading foreign keys linked to `users.id`, ensuring zero orphaned records upon account deletion while preventing plaintext credential exposure in logs, session state, or database dumps.

---

## 2. Relational Schema Specification

### 2.1 Table: `user_two_factor`

| Column Name | SQL Type (Alembic) | SQLite Storage | PostgreSQL Storage | Nullable | Default | Description & Security Constraints |
|---|---|---|---|---|---|---|
| `id` | `INTEGER` | `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` | No | Auto | Surrogate primary key. |
| `user_id` | `INTEGER` | `INTEGER` | `INTEGER` | No | None | Foreign Key referencing `users(id)` with `ON DELETE CASCADE`. Unique index `ix_user_two_factor_user_id`. |
| `encrypted_secret` | `LargeBinary` | `BLOB` | `BYTEA` | No | None | Raw AES-256-GCM ciphertext consisting of 12-byte random nonce, ciphertext payload, and 16-byte authentication tag. Plaintext is never persisted. |
| `encryption_key_version` | `INTEGER` | `INTEGER` | `INTEGER` | No | `1` | Key generation version identifier (server default `1`). Guarded by check constraint `ck_user_two_factor_key_version_positive` (`encryption_key_version >= 1`). |
| `enabled` | `BOOLEAN` | `BOOLEAN (0/1)` | `BOOLEAN` | No | `0` (false) | Active enforcement flag (server default `0`). Indexed via `ix_user_two_factor_enabled` for high-throughput login checks. |
| `created_at` | `DateTime(timezone=True)` | `TIMESTAMP` | `TIMESTAMPTZ` | No | None | UTC timestamp when 2FA setup was initialized. |
| `updated_at` | `DateTime(timezone=True)` | `TIMESTAMP` | `TIMESTAMPTZ` | No | None | UTC timestamp of last secret regeneration or status update. |
| `confirmed_at` | `DateTime(timezone=True)` | `TIMESTAMP` | `TIMESTAMPTZ` | Yes | `NULL` | UTC timestamp set only after first successful TOTP code validation, transitioning state from pending to confirmed. |
| `last_used_step` | `BIGINT` | `INTEGER` (64-bit) | `BIGINT` | Yes | `NULL` | Stores the integer time step `floor(unix_timestamp / 30)` of the most recently accepted TOTP token to prevent token replay attacks within the clock drift window. |

#### Constraints & Indexes (`user_two_factor`)
- **Primary Key:** `pk_user_two_factor` (`id`)
- **Foreign Key:** `fk_user_two_factor_user_id` (`user_id` -> `users.id` `ON DELETE CASCADE`)
- **Check Constraint:** `ck_user_two_factor_key_version_positive` (`encryption_key_version >= 1`)
- **Index:** `ix_user_two_factor_user_id` (Unique index on `user_id`)
- **Index:** `ix_user_two_factor_enabled` (B-tree index on `enabled`)

---

### 2.2 Table: `user_backup_codes`

| Column Name | SQL Type (Alembic) | SQLite Storage | PostgreSQL Storage | Nullable | Default | Description & Security Constraints |
|---|---|---|---|---|---|---|
| `id` | `INTEGER` | `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` | No | Auto | Surrogate primary key. |
| `user_id` | `INTEGER` | `INTEGER` | `INTEGER` | No | None | Foreign Key referencing `users(id)` with `ON DELETE CASCADE`. Indexed via `ix_user_backup_codes_user_id`. |
| `code_hash` | `VARCHAR(255)` | `TEXT` | `VARCHAR(255)` | No | None | Salted one-way hash (`werkzeug.security.generate_password_hash`) of an 8-digit numeric backup code. Plaintext code is shown once during enrollment and never stored. |
| `created_at` | `DateTime(timezone=True)` | `TIMESTAMP` | `TIMESTAMPTZ` | No | None | UTC generation timestamp. |
| `used_at` | `DateTime(timezone=True)` | `TIMESTAMP` | `TIMESTAMPTZ` | Yes | `NULL` | UTC consumption timestamp. Once consumed, the record remains for auditability with `used_at != NULL` and cannot be re-used. |

#### Constraints & Indexes (`user_backup_codes`)
- **Primary Key:** `pk_user_backup_codes` (`id`)
- **Foreign Key:** `fk_user_backup_codes_user_id` (`user_id` -> `users.id` `ON DELETE CASCADE`)
- **Index:** `ix_user_backup_codes_user_id` (B-tree index on `user_id`)
- **Composite Index:** `ix_user_backup_codes_user_used` (Composite index on `user_id, used_at`) enables efficient queries for unconsumed backup codes (`WHERE user_id = :uid AND used_at IS NULL`).

---

## 3. SQLAlchemy Model Integrity (`app/models/security.py`)

The database schema matches the declarative models defined in `app/models/security.py` exactly:

```python
class UserTwoFactor(db.Model):
    __tablename__ = "user_two_factor"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    encrypted_secret = db.Column(db.LargeBinary, nullable=False)
    encryption_key_version = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    enabled = db.Column(db.Boolean, nullable=False, default=False, server_default="0", index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    confirmed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_used_step = db.Column(db.BigInteger, nullable=True)

    __table_args__ = (
        db.CheckConstraint("encryption_key_version >= 1", name="ck_user_two_factor_key_version_positive"),
    )

    user = db.relationship("User", backref=db.backref("two_factor", uselist=False, cascade="all, delete-orphan"))


class UserBackupCode(db.Model):
    __tablename__ = "user_backup_codes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        db.Index("ix_user_backup_codes_user_used", "user_id", "used_at"),
    )

    user = db.relationship("User", backref=db.backref("backup_codes", cascade="all, delete-orphan"))
```

### Relationship Guarantees:
- `User.two_factor`: 1-to-1 relationship with `uselist=False`.
- `User.backup_codes`: 1-to-many relationship with `cascade="all, delete-orphan"`.
- Cascading Deletes: When a `User` is removed, all associated `user_two_factor` and `user_backup_codes` rows are automatically deleted at the database engine level via `ON DELETE CASCADE`.

---

## 4. Alembic Migration Structure (`20261104_01_two_factor_auth.py`)

### 4.1 Linear Revision History
The migration maintains strict single-head linear continuity:
- **Previous Head:** `20261103_01` (`order_events`)
- **Current Head:** `20261104_01` (`two_factor_auth`)
- **Branch Labels / Depends On:** `None`

### 4.2 Idempotent Table & Index Creation
The `upgrade()` function inspects existing table metadata before executing DDL, allowing safe execution across local SQLite test fixtures and PostgreSQL staging environments without crashing if partial tables exist:

```python
def upgrade():
    inspector = inspect(op.get_bind())
    table_names = inspector.get_table_names()

    if "user_two_factor" not in table_names:
        op.create_table(
            "user_two_factor",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("encrypted_secret", sa.LargeBinary(), nullable=False),
            sa.Column("encryption_key_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_used_step", sa.BigInteger(), nullable=True),
            sa.CheckConstraint(
                "encryption_key_version >= 1",
                name="ck_user_two_factor_key_version_positive",
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name="fk_user_two_factor_user_id",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name="pk_user_two_factor"),
        )
        op.create_index(
            "ix_user_two_factor_user_id",
            "user_two_factor",
            ["user_id"],
            unique=True,
        )
        op.create_index(
            "ix_user_two_factor_enabled",
            "user_two_factor",
            ["enabled"],
        )

    if "user_backup_codes" not in table_names:
        op.create_table(
            "user_backup_codes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("code_hash", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name="fk_user_backup_codes_user_id",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name="pk_user_backup_codes"),
        )
        op.create_index(
            "ix_user_backup_codes_user_id",
            "user_backup_codes",
            ["user_id"],
        )
        op.create_index(
            "ix_user_backup_codes_user_used",
            "user_backup_codes",
            ["user_id", "used_at"],
        )
```

---

## 5. Security & Cryptographic Invariants

1. **Zero-Knowledge Secret Storage (AES-256-GCM):**
   - The TOTP secret is never stored in plaintext.
   - Encryption uses a dedicated 32-byte key resolved from `TWO_FACTOR_ENCRYPTION_KEY`.
   - Each encryption operation generates a unique, cryptographically random 12-byte nonce (`os.urandom(12)`).
   - An authentication tag is verified during decryption. If the ciphertext, nonce, or key is modified, decryption fails closed with `TwoFactorCryptoError`.

2. **One-Way Salted Hashes for Backup Codes:**
   - 8-digit numeric recovery codes are hashed using `werkzeug.security.generate_password_hash`.
   - Plaintext recovery codes are presented once upon initial generation or regeneration and are never held in server memory or database records.

3. **Replay Attack Mitigation (`last_used_step`):**
   - RFC 6238 specifies a 30-second time step.
   - When a TOTP token is verified, the matching time step is recorded in `user_two_factor.last_used_step`.
   - Future token submissions must satisfy `current_step > last_used_step`. If a client attempts to submit the same token again within the ±1 step skew window, it is rejected immediately.

4. **Multi-Vendor & Role Isolation:**
   - All 2FA API routes inspect the session-authenticated `user_id` or the securely bound ephemeral challenge session.
   - Users cannot view, modify, or verify 2FA credentials belonging to another user.

---

## 6. Rollback & Disaster Recovery Runbook

To adhere to repository engineering discipline and prevent accidental data loss in production, automatic downgrade is intentionally disabled in the migration:

```python
def downgrade():
    raise RuntimeError(
        "Automatic downgrade of revision 20261104_01 is intentionally disabled "
        "so user two-factor secrets and backup codes are never dropped silently.\n\n"
        "To roll back safely, back up the user_two_factor and user_backup_codes tables first:\n"
        "  - psql -c \"COPY user_two_factor TO STDOUT\" > user_two_factor_backup.sql\n"
        "  - psql -c \"COPY user_backup_codes TO STDOUT\" > user_backup_codes_backup.sql\n"
        "Verify the backup contains the rows you expect, then drop the indexes and tables manually in reverse dependency order:\n"
        "  - DROP INDEX IF EXISTS ix_user_backup_codes_user_used;\n"
        "  - DROP INDEX IF EXISTS ix_user_backup_codes_user_id;\n"
        "  - DROP TABLE IF EXISTS user_backup_codes;\n"
        "  - DROP INDEX IF EXISTS ix_user_two_factor_enabled;\n"
        "  - DROP INDEX IF EXISTS ix_user_two_factor_user_id;\n"
        "  - DROP TABLE IF EXISTS user_two_factor;\n"
        "After completing those manual steps, re-run the earlier revision with `alembic upgrade 20261103_01`."
    )
```

### Manual Rollback Steps:
1. **Take Backup:**
   ```bash
   psql $DATABASE_URL -c "\copy user_two_factor TO 'user_two_factor_backup.csv' WITH CSV HEADER"
   psql $DATABASE_URL -c "\copy user_backup_codes TO 'user_backup_codes_backup.csv' WITH CSV HEADER"
   ```
2. **Verify Backup Size & Integrity.**
3. **Drop Schema Objects in Reverse Dependency Order:**
   ```sql
   DROP INDEX IF EXISTS ix_user_backup_codes_user_used;
   DROP INDEX IF EXISTS ix_user_backup_codes_user_id;
   DROP TABLE IF EXISTS user_backup_codes;
   DROP INDEX IF EXISTS ix_user_two_factor_enabled;
   DROP INDEX IF EXISTS ix_user_two_factor_user_id;
   DROP TABLE IF EXISTS user_two_factor;
   ```
4. **Re-align Alembic Version:**
   ```bash
   flask --app run.py db stamp 20261103_01
   ```

---

## 7. Verification Evidence & Quality Assurance

- **Alembic Graph Check:** Verified single head `['20261104_01']` without branches or missing down_revisions.
- **Python Syntax Compilation:** `python3 -m py_compile` passed with zero errors across migration, models, and service files.
- **SQLite Engine Execution:** Executed clean in-memory schema generation, constraint checks, and mock data insertion.
- **Node/React Client Build:** `compile_applet` and `lint_applet` verified successful compilation.
- **Node Security Suite:** `npm test` passed (8/8 test suites).
