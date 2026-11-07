# APK RELEASE — PHASE 2.7 GET APP INTEGRATION REPORT

Created: 2026-11-06
Workspace: `D:\FTP\NexHaat`
Package: `com.nexhaat.app`
Public APK path: `APK/NexHaat.apk`
Public APK filename: `NexHaat.apk`
Mode: REPORT ONLY — NO CODE CHANGES, NO BUILD, NO DEPLOY

## 1. Objective

Recover the interrupted Phase 2.7 Get App integration task and produce a final,
evidence-based report on whether the NexHaat website Get App download flow is
safe, tested, and strictly Stable-only.

## 2. Current status

```
GET_APP_STATUS: UNAVAILABLE
STABLE_APK: NOT_RELEASED
DEBUG_APK: INTERNAL_TESTING_ONLY
PUBLIC_DOWNLOAD: BLOCKED
```

Get App is unavailable because no verified Stable APK exists. Production signing
is not configured, the release pipeline is BLOCKED, and the only APK currently
present in the repository is an internal Gradle debug build.

## 3. Files inspected

- `APK/status.json`
- `APK/latest.json`
- `APK/checksums.txt`
- `public/downloads/metadata.json`
- `server.ts`
- `src/services/apkDownloadService.ts`
- `src/components/PWAInstallButton.tsx`
- `docs/APK_RELEASE_PHASE2_7A_LOADING_DIAGNOSTIC.md`
- `docs/APK_RELEASE_PHASE2_6_INSTALLATION_REPORT.md`
- `git status --short --branch`

## 4. Current Get App implementation

### 4.1 Backend

The existing Express download backend in `server.ts` serves APK artifacts from a
strict candidate list and fails closed when no verified artifact is available.

현재의 `server.ts` APK 후보 경로:
1. `APK/NexHaat.apk`
2. `APK/latest.apk`
3. `public/downloads/nexhaat.apk`

현재 구현의 주요 동작:
- `getApkCandidatePaths()`는 `APK/NexHaat.apk`를 첫 번째 공개 후보로 사용하며,
  더 이상 `APK/debug/latest-debug.apk`를 포함하지 않습니다.
- `resolveApkArtifact()`는 존재하는 첫 번째 후보를 찾은 뒤,
  Metadata SHA-256가 유효하고 파일의 실제 SHA-256와 일치할 때만 `verified: true`로 처리합니다.
- `/api/download/apk`와 `/downloads/nexhaat.apk`, `/APK/latest.apk`는
  아티팩트가 존재하지 않거나 검증되지 않으면 다운로드 응답을 거부합니다.
  - 파일 부재 시 `404 APK_NOT_AVAILABLE`
  - 검증 실패 시 `503 APK_NOT_VERIFIED`
- `/api/download/apk/info`는 `verified`, `sha256`, `exists`, `unavailableReason`를 클라이언트에게 전달합니다.
- 다운로드 응답에는 `application/vnd.android.package-archive` MIME과
  `Content-Disposition`, `X-Content-Type-Options: nosniff` 등 다운로드 헤더가 설정됩니다.

### 4.2 Frontend

- `src/services/apkDownloadService.ts`는
  `PRIMARY_DOWNLOAD_URL = '/api/download/apk'`와
  `DIRECT_DOWNLOAD_URL = '/downloads/nexhaat.apk'`를 사용하며,
  `DEFAULT_APK_FILENAME = 'NexHaat-v1.0.0.apk'`를 기본 파일명으로 사용합니다.
- `src/components/PWAInstallButton.tsx`는
  `apkAvailable = Boolean(apkMetadata?.exists && apkMetadata?.verified)`일 때만
  다운로드 버튼과 직접 링크를 활성화합니다.
- Get App 버튼이 활성화되려면 서버가 `exists: true`와 `verified: true`를 모두 반환해야 합니다.

## 5. Stable / Debug separation verification

### 5.1 Stable APK
- `APK/NexHaat.apk`: **존재하지 않음**
- `APK/status.json`: `liveRelease.latestApkExists: false`,
  `liveRelease.publicMirrorExists: false`, `liveRelease.releases: []`
- Release orchestration status: `status: "BLOCKED"`
- `toolchain.signingConfigured: false`
- Gate 1: **FAIL**
  - 사유: 작업 트리에 병합 충돌 마커가 남아 있음
  - 관련 파일 예시:
    - `android/app/src/main/java/com/nexhaat/app/data/repository/AuthRepository.kt`
    - `app/api/routes/auth.py`
    - `app/models/security.py`
    - `app/routes/auth.py`
    - `app/services/two_factor.py`
    - `app/services/two_factor_crypto.py`
    - `docs/architecture/WEBSITE_ANDROID_FEATURE_PARITY.md`
    - `public/assets/aistudio/Paste_November_03__2026_-_6_56PM_524861a5`
    - `tests/test_auth_two_factor.py`

### 5.2 Debug APK
- `APK/debug/latest-debug.apk`: **존재하지 않음**
- Gradle 디버그 빌드 출력: `android/app/build/outputs/apk/debug/app-debug.apk`만 존재함
- Debug APK는 내부 테스트 위치에 남아 있으며, 공개 다운로드 경로에는 노출되지 않음

### 5.3 분리 상태 결론
- 공개 Stable 경로 `APK/NexHaat.apk`는 비어 있음
- Debug APK는 공개 경로로 이동, 복사, 이름 변경, 제공되지 않음
- 서버 후보 경로에서 Debug 경로가 제거되어, 공개 API가 Debug 빌드를 제공하지 않도록 변경됨

## 6. Metadata and checksum status

### 6.1 `APK/latest.json`
- `verified: false`
- `status: "unavailable"`
- `buildType: "none"`
- `sha256: ""`
- `sizeBytes: 0`
- `verification.status: "NOT_RELEASED"`
- `verification.notes:` "No verified Stable APK has been published. Production signing is not configured. Get App is unavailable until a genuine Stable release passes all mandatory gates."
- `artifactPath: "APK/NexHaat.apk"`
- `withdrawnReleaseClaim`에 이전 Debug 관련 검증 주장이 철회된 경위가 기록됨:
  - 이전 빌드 유형: `debug`
  - 이전 상태: `available`
  - 이전 아티팩트 경로: `APK/debug/latest-debug.apk`
  - 이전 SHA-256: `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c`
  - 이전 크기: `21884019`
  - 철회 사유: 해당 디버그 아티팩트가 기록된 경로에 더 이상 존재하지 않으며,
    누락된 파일에 대한 `verified: true` 주장이 철회됨

### 6.2 `public/downloads/metadata.json`
- `APK/latest.json`과 동일한 현재 진실 상태를 반영:
  - `verified: false`
  - `status: "unavailable"`
  - `buildType: "none"`
  - `sha256: ""`
  - `artifactPath: "APK/NexHaat.apk"`
  - 동일한 `withdrawnReleaseClaim` 포함

### 6.3 `APK/checksums.txt`
- 기존 체크섬 항목:
  - `6a2921730d53637e6e0ce999c068b3189608d9bfdf81260149fe0becdd5dfae3  NexHaat-v1.0.0-20261105012746.apk`
  - `1fe3286986e404ea3aad2ebdd8873f6520a06f59e61c90639045065d837d5c19  NexHaat-v1.0.0-20261105013033.apk`
  - `68ce8ad85cbe3868ea2f178c95e82476675501891ef939f146cc774dba9e3e22  NexHaat-v1.0.0-20261105013049.apk`
- 현재 `APK/` 디렉터리에는 위 파일들이 존재하지 않음
- 따라서 현재 체크섬 파일은 유효한 공개 Stable APK를 가리키지 않음

### 6.4 메타데이터 무결성 결론
- 현재 Metadata는 Stable APK가 존재한다고 주장하지 않음
- Metadata는 SHA-256가 비어 있고 `verified: false`이므로,
  존재하지 않거나 검증되지 않은 APK를 설치 가능하다고 표시하지 않음
- 서버 로직은 Metadata SHA-256가 유효하고 파일 SHA-256와 일치하는 경우에만
  다운로드를 허용하므로, Metadata 단독으로는 다운로드를 활성화할 수 없음

## 7. Tests executed and evidence

### 7.1 이전에 실행된 검사

- `APK/debug/latest-debug.apk`가 존재하던 시점에
  `scripts/validate_apk.py --apk APK/debug/latest-debug.apk --json-out /tmp/debug-apk-validate.json` 실행됨
  - Artifact 크기: 21884019 바이트
  - ZIP 컨테이너: 542개 엔트리, 중복 없음, 암호화 없음, 안전하지 않은 경로 없음
  - ZIP CRC: 모두 일치
  - 바이너리 매니페스트: `package=com.nexhaat.app version=1.0.0 (1) sdk=24->36`
  - 패키지 ID: `com.nexhaat.app`
  - 런처 액티비티: `com.nexhaat.app.MainActivity`
  - 리소스 테이블: 존재
  - DEX: 18개 유효
  - 서명 구조: v2만 존재
  - 체크섬 SHA-256: `f42061b46ade21d0bfc584fb75cb374d8bc45ac775655454fa8d7c21ce87608c`
  - **BLOCKED**: `apksigner` 미가용으로 서명 검증 미실행
  - **BLOCKED**: 설치 검증 미요청
- 이 검증은 **과거 디버그 아티팩트가 존재하던 시점**의 결과이며,
  현재 체크아웃의 공개 Stable APK를 검증한 것이 아님

- Python 게이트:
  - `python -m pytest -q --tb=short tests/test_apk_validator.py tests/test_auth_two_factor.py tests/test_api_foundation.py`
  - 결과: **41 passed in 32.15s, exit 0**
  - 이는 APK 다운로드 통합 자체를 검증한 것이 아니라 관련 테스트 스위트가 통과했음을 의미함

- Git 무결성:
  - `git diff --check` → exit 0
  - 단, `android/.gradle/buildOutputCleanup/cache.properties`에 CRLF 경고 존재

### 7.2 현재 Get App 관련 실행 결과

현재 체크아웃에서 직접 실행/확인한 사항:
- `APK/NexHaat.apk` 부재 확인: **true** (파일 없음)
- `APK/debug/latest-debug.apk` 부재 확인: **true** (파일 없음)
- Gradle 디버그 APK 존재 확인: **true** (`android/app/build/outputs/apk/debug/app-debug.apk`)
- `server.ts`의 APK 후보 경로 확인:
  - `APK/NexHaat.apk`가 첫 번째 후보임
  - `APK/debug/latest-debug.apk`는 목록에 없음

## 8. Tests NOT RUN

다음 검사는 현재 환경에서 실행되지 않았습니다:

- **NOT RUN**: 라이브 HTTP 서빙 테스트
  - 사유: 격리된 Node 런타임 설치 실패
  - npm 캐시 손상으로 인해 `express`, `ms`, `cors` 등 의존성 로드 실패
  - 반복된 `tarball ... corrupted` 및 `EINTEGRITY` 오류 발생
  - Windows junctions 생성 실패
  - 따라서 실제 다운로드 endpoint 응답(200/404/503, MIME, 헤더, 바이트 일치)을
    라이브 서버에서 확인하지 못함

- **NOT RUN**: `APK/NexHaat.apk` 다운로드 바이트 일치 테스트
  - 공개 Stable APK가 존재하지 않으므로 실행 불가

- **NOT RUN**: 서명 검증(`apksigner`)
  - 현재 공개 Stable APK가 없고, `apksigner`도 가용하지 않음

- **NOT RUN**: 실제 기기/에뮬레이터 설치 및 스모크 테스트
  - 사유: ADB에 기기/에뮬레이터가 표시되지 않음
  - `APK/status.json`의 `toolchain.adb: null`, `toolchain.emulator: null`과 일치

- **NOT RUN**: 새 Stable APK 빌드 및 서명
  - Phase 2.7 통합 단계에서는 모든 게이트가 실제로 통과하고
    기존 릴리스 정책이 승인하지 않는 한 Stable APK를 생성/공개하지 않음

## 9. Remaining blockers

1. **공개 Stable APK 부재**
   - `APK/NexHaat.apk`가 존재하지 않음
   - 이로 인해 Get App은 현재 다운로드 불가능하다

2. **프로덕션 서명 미구성**
   - `APK/status.json`: `toolchain.signingConfigured: false`
   - 서명 자격 증명이 없으면 Stable APK를 공개할 수 없다
   - 이 보고서에서 서명 자격 증명을 생성, 발명, 대체하지 않았다

3. **저장소 무결성 실패 (Gate 1)**
   - 작업 트리에 병합 충돌 마커가 남아 있음
   - 이로 인해 현재 릴리스 파이프라인이 BLOCKED 상태
   - 이 보고서에서 충돌 마커를 해결하거나 Git 상태를 변경하지 않았다

4. **라이브 HTTP 검증 미완료**
   - 서버 코드가 변경된 뒤 실제 서빙 동작을 라이브 HTTP로 확인하지 못함
   - 이는 환경 문제(npm 캐시 손상)로 인한 NOT RUN이며, 코드 변경이 아니다

5. **기기/에뮬레이터 부재로 인한 설치 검증 불가**
   - 설치, 런칭, 스모크 테스트는 현재 환경에서 실행할 수 없다

## 10. Get App 가용 여부

### 10.1 현재 상태
- Get App은 **사용 불가(unavailable)**
- 이유:
  - 공개 Stable APK가 존재하지 않음
  - 메타데이터가 `verified: false`, `sha256: ""`, `status: "unavailable"`로 설정됨
  - 서버가 검증되지 않은 아티팩트는 제공하지 않음
  - 프론트엔드는 `exists && verified`일 때만 다운로드 버튼을 활성화함

### 10.2 동작 결론
- Stable APK가 없으면 Get App은 비활성화/비표시 상태로 남는다
- Debug APK가 내부에 존재하더라도 Get App은 이를 제공하지 않는다
- 가짜 Stable APK나 가짜 메타데이터는 생성되지 않았다

## 11. Git changes observed

현재 브랜치: `main...origin/main`

### 11.1 수정된 파일 (일부)
- `.env.example`
- `android/.gradle/...` 여러 파일
- `android/app/src/main/java/com/nexhaat/app/data/repository/AuthRepository.kt`
- `android/gradlew`
- `android/gradlew.bat`
- `app/api/routes/auth.py`
- `app/api/serializers.py`
- `app/models/security.py`
- `app/routes/auth.py`
- `app/services/two_factor.py`
- `app/services/two_factor_crypto.py`
- `bun.lock` 삭제됨
- `docs/architecture/FEATURE_REGISTRY.json`
- `docs/architecture/WEBSITE_ANDROID_FEATURE_PARITY.md`
- `package-lock.json`
- `public/assets/aistudio/Paste_November_03__2026_-_6_56PM_524861a5`
- `scripts/generate_apk_package.py`
- `server.ts`
- `src/components/FlaskAuthPanel.tsx`
- `src/components/PWAInstallButton.tsx`
- `src/services/apkDownloadService.ts`
- `tests/test_auth_two_factor.py`
- `vite.config.ts`

### 11.2 추적되지 않은 항목 (일부)
- `APK/`
- `public/downloads/`
- `docs/APK_RELEASE_PHASE2_6_INSTALLATION_REPORT.md`
- `docs/APK_RELEASE_PHASE2_7_GET_APP_INTEGRATION_REPORT.md`
- `scripts/validate_apk.py`
- `scripts/nexhaat_qa_release_orchestrator.py`
- `tests/test_apk_validator.py`
- 기타 여러 `docs/`, `reports/`, `.temp_recovery/`, `.aistudio/artifacts/...`

### 11.3 Git 변경 결론
- 작업 트리는 더러운 상태이며, 병합 충돌 마커가 남아 있다
- 이 보고서에서 새로운 커밋, 푸시, 병합, 배포는 수행하지 않았다
- 이 보고서는 기존 작업 위에 READ-ONLY로 작성되었다

## 12. Safety confirmations

- **가짜 Stable APK를 생성하지 않았다**
  - `APK/NexHaat.apk`는 여전히 존재하지 않는다
- **`APK/debug/latest-debug.apk`를 이동하거나 노출하지 않았다**
  - 해당 파일은 현재 존재하지 않으며,
    Gradle 디버그 출력 `android/app/build/outputs/apk/debug/app-debug.apk`만 존재한다
- **공개 메타데이터가 Stable APK를 존재하는 것처럼 표시하지 않는다**
  - `APK/latest.json`과 `public/downloads/metadata.json`은 현재 `verified: false`이다
- **Debug APK를 공개 다운로드 경로에서 제거했다**
  - `server.ts` 후보 경로에서 `APK/debug/latest-debug.apk`가 제거되었다
- **서명 자격 증명을 발명하거나 대체하지 않았다**
- **프로덕션 데이터베이스를 수정하지 않았다**
- **커밋, 푸시, 병합, 배포를 수행하지 않았다**

## 13. Implementation defect note

현재 구현에서는 공개 다운로드 후보가 `APK/NexHaat.apk`를 우선으로 사용하지만,
현실에서 해당 Stable APK가 없기 때문에 Get App은 현재 작동하지 않는다.
이는 결함이 아니라 **의도된 fail-closed 상태**다.

단, 이전 작업에서 `server.ts`의 `getApkCandidatePaths()`가
`APK/debug/latest-debug.apk`를 공개 후보로 포함하고 있었고,
Metadata도 해당 Debug 아티팩트를 `verified: true`로 주장하고 있었다.
이는 Stable-only 정책과 어긋나는 상태였으며,
이번 복구 과정에서 다음과 같이 정정되었다:
- Metadata: `verified: false`, `buildType: "none"`, SHA-256 공란
- 서버 후보: `APK/NexHaat.apk`를 우선으로 하고 Debug 경로 제거

## 14. Conclusion

Phase 2.7 Get App 통합은 현재 **완료되지 않았고, 공개될 수 없는 상태**다.
 이유는 공개 Stable APK가 존재하지 않고, 프로덕션 서명도 구성되지 않았으며,
 릴리스 파이프라인이 Gate 1에서 실패했기 때문이다.

즉, 현재 진실한 결과는 다음과 같다:

```
GET_APP_STATUS: UNAVAILABLE
STABLE_APK: NOT_RELEASED
DEBUG_APK: INTERNAL_TESTING_ONLY
PUBLIC_DOWNLOAD: BLOCKED
```

이 결과는 Get App이 기능적으로 보이도록 약화되지 않았으며,
오히려 공개 Stable APK가 없을 때 Get App이 노출/비활성화되지 않도록
메타데이터와 서버 후보 경로가 정정되었다.

## 15. Recommended next steps

1. 저장소 병합 충돌 마커를 해결한다
2. 프로덕션 서명 구성을 완성한다
3. 실제 Stable APK를 빌드하고 모든 필수 게이트를 통과시킨다
4. 통과 후에만 `APK/NexHaat.apk`를 공개한다
5. 공개 전/후로 라이브 HTTP 다운로드 검증과 기기 설치를 수행한다
6. 그 이후에 Get App을 사용 가능하게 만든다

## Report file

`docs/APK_RELEASE_PHASE2_7_GET_APP_INTEGRATION_REPORT.md`
