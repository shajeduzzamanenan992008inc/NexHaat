# NexHaat — APK Release Architecture & Distribution Specification

**Date:** 2026-11-05  
**Version:** 1.0.0  
**Status:** Target design — not achieved. Release status is **BLOCKED**: no verified
APK exists, and `scripts/validate_apk.py` (added 2026-11-06) now enforces the
structural and signature checks described below. See
`docs/APK_RELEASE_RECOVERY_STATUS.md` for current evidence and blockers.  

---

## 1. Overview & Directory Topology

The root `/APK/` directory is the canonical repository artifact authority for all tested and verified Android releases.

```
/APK/
├── latest.apk                  # Symlink or atomic copy of the current verified release
├── latest.json                 # Machine-readable release metadata and verification status
├── checksums.txt               # Cumulative SHA-256 ledger of all verified APK releases
└── releases/                   # Versioned immutable release archive
    ├── NexHaat-v1.0.0-20261105.apk
    └── NexHaat-v1.0.0-20261105.json
```

---

## 2. Release Gates & The Fail Rule

### 2.1 The Fail Rule (Strict Invariant)

**No APK is ever published or promoted to `latest.apk` unless every preceding gate has completed with an unambiguous PASS.**

If any gate fails (compilation error, unit test failure, package integrity mismatch, or emulator startup failure):
1. **No Artifact Replacement:** `latest.apk` and `latest.json` remain completely untouched, retaining the last known-good release.
2. **Isolation:** The failed artifact is placed in a temporary quarantine or discarded; it is never moved to `APK/releases/`.
3. **Audit Logging:** Detailed execution logs and failure reasons are saved into `reports/apk-release-report.html` and `reports/test-summary.json`.
4. **Notification:** CI or the local release runner outputs explicit failure diagnostics with the exact failing step.

---

## 3. Metadata Specification (`latest.json`)

The `latest.json` file contains verified, non-confidential telemetry:

```json
{
  "appName": "NexHaat",
  "packageId": "com.nexhaat.app",
  "versionName": "1.0.0",
  "versionCode": 1,
  "minSdkVersion": 24,
  "targetSdkVersion": 36,
  "filename": "NexHaat-v1.0.0-20261105.apk",
  "displayName": "NexHaat-v1.0.0.apk",
  "sha256": "4a73e5...",
  "sizeBytes": 1583204,
  "sizeFormatted": "1.51 MB",
  "buildTimestamp": "2026-11-05T01:25:00Z",
  "gitCommit": "d5fb7ab",
  "releaseChannel": "production",
  "testStatus": "PASS",
  "qualityGates": {
    "lint": "PASS",
    "unitTests": "PASS",
    "packageIntegrity": "PASS",
    "emulatorSmoke": "PASS",
    "securityAudit": "PASS"
  },
  "downloadUrl": "/api/download/apk",
  "directUrl": "/downloads/nexhaat.apk"
}
```

---

## 4. Distribution Architecture (Website Integration)

1. **Client Request:** When a visitor clicks `Get App` on the NexHaat website:
   - The client invokes `getApkMetadata()` from `src/services/apkDownloadService.ts`.
   - `getApkMetadata()` queries `GET /api/download/apk/info`.
2. **Server Resolution:** Express reads `/APK/latest.json`.
   - If verified, it returns the metadata with `exists: true`.
   - If no verified release exists, it returns `exists: false`, causing the website to display a safe "Coming Soon" or PWA install option rather than a broken link.
3. **Binary Streaming:** When downloading:
   - Browser calls `GET /api/download/apk` (or direct `/downloads/nexhaat.apk`).
   - Server resolves `/APK/latest.apk` and streams with headers:
     - `Content-Type: application/vnd.android.package-archive`
     - `Content-Disposition: attachment; filename="NexHaat-v1.0.0.apk"`
     - `X-Content-Type-Options: nosniff`
     - `Content-Length: <exact size>`
4. **Integrity Validation:** The client verifies the completed download size matches `content-length` and offers SHA-256 checksum verification.

---

## 5. Rollback & Disaster Recovery

- In the event of a critical defect discovered post-release:
  1. The operator runs the rollback command: `python scripts/nexhaat_qa_release_orchestrator.py --rollback-to <version>`.
  2. The orchestrator inspects `APK/releases/` for the target version.
  3. Copies the target version to `APK/latest.apk` and atomically updates `APK/latest.json`.
  4. Synchronizes to `/public/downloads/nexhaat.apk`.
  5. The website immediately serves the rolled-back verified release with zero downtime.
