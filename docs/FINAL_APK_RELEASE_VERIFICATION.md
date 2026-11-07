# NexHaat — স্বতন্ত্র APK রিলিজ যাচাই

**অডিটের তারিখ:** 2026-11-05
**Repository:** `D:\FTP\NexHaat`
**Branch / HEAD:** `main` / `ac6636afd54a7f91002604b6ae160d7d6f791972`
**সামগ্রিক ফল:** **FAIL — FULLY VERIFIED নয়; রিলিজ করবেন না এবং production APK download চালু করবেন না।**

এই অডিটে আগের রিপোর্ট, JSON metadata বা generated report-কে APK-এর প্রমাণ ধরা হয়নি। কোনো commit, push, deployment বা production পরিবর্তন করা হয়নি। শুরুতেই working tree-তে বহু staged, unstaged, deleted ও untracked user change ছিল। APK/failure/rollback পরীক্ষার সব output আলাদা temporary directory-তে তৈরি হয়েছে।

## প্রধান ফল

Metadata-তে 33,762-byte (`33.0 KB`) APK, SHA-256 `68ce8ad85cbe3868ea2f178c95e82476675501891ef939f146cc774dba9e3e22`, package `com.nexhaat.app`, version `1.0.0` (code 1) ও ছয়টি PASS দাবি করা হয়েছে। কিন্তু এই checkout-এ `APK/latest.apk`, `public/downloads/nexhaat.apk`, `APK/releases/` এবং Android build output-এর APK—কোনোটিই নেই। `APK/checksums.txt`-এর তিনটি পুরোনো APK নামের ফাইলও নেই। ফলে metadata-র size, SHA, manifest, package/version, signature, installability বা execution কোনো কিছুই ওই নির্দিষ্ট binary থেকে যাচাই করা যায়নি।

শুধু 33 KB আকার দেখে APK-কে dummy বলা যায় না। তবে checked-in orchestrator-এর fallback source ফাইল থেকে ZIP বানায়—তার ভিতরে থাকে compile না করা XML manifest, placeholder zero-filled DEX এবং জাল signature ফাইল—তারপর ZIP গঠন ঠিক থাকলেই PASS দেয়। সেই একই Gate 5 isolated copy-তে চালিয়ে 33,949-byte ফাইল তৈরি হয় এবং gate PASS জানায়। ফাইলটির `classes.dex` মাত্র 1,032 bytes; DEX header-এর declared file size শূন্য। `AndroidManifest.xml` plain XML এবং v1 PKCS#7 record malformed, কোনো certificate-ও resolve হয়নি। এই fallback installable Android app নয়। এটি fallback-কে invalid প্রমাণ করে; কিন্তু হারিয়ে যাওয়া 33,762-byte পুরোনো artifact-এর নিজস্ব bytes না থাকায় সেটির exact content নিশ্চিত করে বলা যায় না।

## Metadata-তে দাবি করা APK (binary থেকে যাচাই নয়)

| বিষয় | Metadata-র দাবি | অডিটের ফল |
|---|---|---|
| Package | `com.nexhaat.app` | APK থেকে **যাচাই হয়নি**; JSON/source constant-এ আছে |
| Version / code | `1.0.0` / `1` | APK থেকে **যাচাই হয়নি** |
| Min / target SDK | 24 / 36 | APK থেকে **যাচাই হয়নি** |
| Size | 33,762 bytes / 33.0 KB | `APK/latest.json`-এ দাবি আছে; APK নেই |
| SHA-256 | `68ce8ad85cbe3868ea2f178c95e82476675501891ef939f146cc774dba9e3e22` | metadata ও checksum তালিকায় দাবি আছে; hash করার ফাইল নেই |
| Build ID | `20261105013049` | metadata-র দাবি মাত্র |
| Release signing | `release` | **FAIL / সেট করা নেই**: signing env value, `android/local.properties` বা repository keystore নেই; credentials না থাকলে Gradle unsigned release তৈরি করে |
| API/media origin | Production release | **FAIL / placeholder**: release API default `https://RELEASE_BASE_URL_REPLACE_ME/`; নির্দিষ্ট production API/media URL নেই |

Repository-তে `.apk` খোঁজার ফল শূন্য। `APK/checksums.txt`-এ `20261105012746`, `20261105013033`, `20261105013049` build-এর তিনটি entry আছে, কিন্তু সংশ্লিষ্ট archive নেই।

## QA orchestrator ও ছয় gate

সফল orchestrator run `APK/latest.apk`, archive, metadata ও public mirror বদলাতে পারে। তাই পুরো orchestrator `--dry-run`-এ repository-র বদলে temporary source mirror-এ চালানো হয়েছে। Gate 1 PASS করার পর Gate 2-তে exit code 1 দিয়ে থেমেছে; পরের gate-গুলো ওই run-এ পৌঁছায়নি। আগের `reports/test-summary.json`-এর PASS-গুলো release proof নয়: Gate 5/6 dummy ZIP-কে PASS করে, আর UI report-এর 23 “VERIFIED” row hard-coded HTML—UI automation ফল নয়।

| Gate | Status | প্রকৃত evidence |
|---|---|---|
| 1. Repository structure ও manifest source check | **PASS** | `python scripts/validate_repository_structure.py --fail-on-review` exit 0। এটি source/config যাচাই করে, APK binary নয়। |
| 2. Node security tests | **FAIL** | `npm.cmd test` exit 1: `tsx` অনুপস্থিত। `npm.cmd ci`-ও ব্যর্থ: `package.json` ও `package-lock.json` মেলে না (`fsevents`, platform esbuild/Rollup entry অনুপস্থিত)। Isolated orchestrator Gate 2-তে থেমেছে; Windows-এ তার child `npm` command-ও resolve হয়নি (`WinError 2`)। |
| 3. Marketplace API tests | **FAIL** | `node tests-node/marketplace-api.test.mjs` exit 1: `vite` অনুপস্থিত। Full orchestrator-এ gate-টি চলেনি। |
| 4. TypeScript compilation | **NOT RUN** | `node_modules`/`tsc` নেই; `npx tsc --noEmit` চালানো হয়নি, কারণ lockfile অসামঞ্জস্যে clean install ব্যর্থ। Full orchestrator-এও পৌঁছায়নি। |
| 5. APK packaging ও integrity | **FAIL** | Isolated `run_gate_5_package_apk()` invalid 33,949-byte source ZIP তৈরি করেও PASS বলেছে। Parse করা manifest, valid DEX/certificate, `apksigner` বা emulator install কোনোটি gate পরীক্ষা করে না। দাবিকৃত APK-ও অনুপস্থিত। |
| 6. Smoke / website integration | **FAIL** | Isolated `run_gate_6_smoke_verification()` শুধু ZIP-এর প্রথম 4 byte (`PK\x03\x04`) পরীক্ষা করে PASS বলেছে। HTTP endpoint, APK parser, install বা launch পরীক্ষা করে না। Hosted endpoint probe-ও ব্যর্থ। |

**পূর্ণ orchestrator command:** `python <temporary-mirror>\scripts\nexhaat_qa_release_orchestrator.py --dry-run` → Gate 1 PASS, Gate 2 FAIL, exit 1; release promote হয়নি।
**Gate-এর গুরুতর ত্রুটি:** `assembleDebug` অনুপস্থিত বা ব্যর্থ হলেও Gate 5 নীরবে fake ZIP বানিয়ে এগোয়। Gradle সফল হলে `app-debug.apk` কপি করে তাকে release বলে, কিন্তু release build বা production signing যাচাই করে না।

## APK contents, install ও emulator

| পরীক্ষা | Status | Evidence / কারণ |
|---|---|---|
| 33,762-byte historical file আছে কি না | **FAIL** | `APK/latest.apk` ও archive-গুলো নেই। |
| Historical APK ZIP/content পরীক্ষা | **NOT RUN** | Historical APK নেই। Temporary fallback ZIP-এর CRC ঠিক থাকলেও manifest plain XML, DEX size header শূন্য এবং signature malformed। |
| Historical APK থেকে package/version/SDK পড়া | **NOT RUN** | APK নেই। REA JADX provider-ও unavailable: `REA_JADX_MCP_JAR` configure করা হয়নি। |
| Historical APK signature যাচাই | **NOT RUN** | Historical APK নেই। Temporary fallback-এ **FAIL**: malformed v1 PKCS#7, certificate নেই, v2/v3 নেই, signature verification হয়নি। |
| Android Emulator-এ install | **NOT RUN** | `adb`/`emulator` নেই। `ANDROID_HOME` ও `ANDROID_SDK_ROOT`-এর মান nonexistent literal `:LOCALAPPDATA\Android\Sdk` নির্দেশ করে। REA device discovery-ও `adb binary was not found` দেয়। |
| App launch, screen ও log পরীক্ষা | **NOT RUN** | Emulator/device এবং installable APK কোনোটিই নেই। |

এই host-এ Java `1.8.0_511`; Android project Java 17 চায়। CI workflow-তে JDK 17 setup লেখা আছে, কিন্তু এই local host তার বিকল্প নয়।

## Authentication ও shopping UI journey

**ফল: NOT RUN।** সত্যিকারের Android install/emulator session ছিল না। Android source-এ DTO, URL resolver, cookie ও view-model/UI-state নিয়ে 15টি local JVM unit-test file আছে। `androidTest` source বা Espresso/UIAutomator/Compose UI test harness পাওয়া যায়নি। Workflow-এর emulator script install ও launcher start করার চেষ্টা করে, screenshot নেয়, তারপর `FATAL EXCEPTION` খোঁজে; authentication, OTP, navigation, product discovery, cart বা checkout automate করে না। আগের রিপোর্টের 23টি “VERIFIED” row static report content, execution evidence নয়।

## GitHub Actions ও CI config

**ফল: FAIL / সফল remote run যাচাই হয়নি।** `.github/workflows/android-qa-release.yml` এই working tree-তে untracked; তাই এটি `main` revision-এ নেই এবং push না হওয়া পর্যন্ত GitHub এটি চালাতে পারে না। Public Actions page-এ বিদ্যমান Python deployment ও Dependabot workflow দেখা গেছে; Android QA run পাওয়া যায়নি। এই অডিটে workflow dispatch বা edit করা হয়নি।

Local workflow-তে JDK 17, Gradle setup ও Android Emulator Runner ব্যবহার করা হয়েছে। Emulator Runner action চাওয়া SDK/emulator component install করে supplied script চালানোর কথা বলে। কিন্তু workflow `./gradlew` চালায়; `git ls-files -s android/gradlew` mode `100644` দেখায়, executable নয়। ফলে Ubuntu-তে `./gradlew :app:testDebugUnitTest` ও `./gradlew :app:assembleDebug` permission error-এ ব্যর্থ হবে—যতক্ষণ executable bit ঠিক না করা হয় বা command বদলানো না হয়। Emulator ধাপও কেবল startup smoke, চাওয়া UI journey নয়। `actions/setup-java@v4`, `gradle/actions/setup-gradle@v3`, `reactivecircus/android-emulator-runner@v2`-এর মতো unpinned reference repository-র immutable SHA pinning নিয়মও মানে না।

তথ্যসূত্র: [NexHaat GitHub Actions](https://github.com/shajeduzzamanenan992008inc/NexHaat/actions), [ReactiveCircus Android Emulator Runner](https://github.com/ReactiveCircus/android-emulator-runner)।

## Failure rule, atomicity ও release history

| পরীক্ষা | Status | প্রকৃত ফল |
|---|---|---|
| Gate failure-এ latest অক্ষত থাকে কি না | **PASS, কেবল isolated fixture** | Temporary copy-তে sentinel `APK/latest.apk` রেখে `--force-fail gate1` চালানো হয়। Exit 1, failure diagnostic তৈরি, এবং SHA-256 আগে/পরে একই `2079ea0eda67753f7524716294b9d05c4099faa5c25d8b91e5c0e107193100ba`। এটি আসল NexHaat latest APK নয়—সেটি অনুপস্থিত। |
| আসল previous APK-এর failure-পূর্ব/পর SHA | **NOT RUN** | Hash করার আসল `APK/latest.apk` নেই। |
| Repository-র আসল release-এ rollback | **FAIL** | `python scripts/nexhaat_qa_release_orchestrator.py --rollback-to __audit_nonexistent_release__` exit 1; `APK/releases/` নেই। |
| Temporary fixture-এ rollback function | **PASS, simulated** | Marker file latest ও public mirror-এ কপি হয়েছে; hash মিলে। এটি valid APK rollback নয়। |
| Rollback atomic কি না | **FAIL** | `rollback_to()` latest ও public mirror-এ সরাসরি `shutil.copy2()` চালায়, metadata-ও সরাসরি লেখে; temp file/`os.replace` নেই। মাঝপথে থামলে ফাইলগুলো অসামঞ্জস্য হতে পারে। Fixture-এ `checksums.txt`-ও বদলায়নি। |
| Release history সামঞ্জস্য | **FAIL** | `APK/releases/` ও archive নেই। Checksums-এর তিন entry-র কোনোটির APK নেই। |
| পুরো release set atomic কি না | **FAIL** | Promotion-এ পৃথক APK/JSON file atomic replace হলেও archive, latest, mirror, public metadata ও checksum append এক transaction নয়। |

## Website Get App ও download

| পরীক্ষা | Status | প্রকৃত ফল |
|---|---|---|
| আসল hosted site-এর Get App | **FAIL / unavailable** | `https://nexhaat.com` HEAD probe-তে host `127.0.0.1`-এ resolve হয়ে connection refused। `nexhaat.com.bd` DNS resolve হয়নি। |
| Hosted APK metadata endpoint | **NOT RUN against a host** | Host অপ্রাপ্য। Source-এ Express handler আছে, কিন্তু root `Procfile` শুধু Flask/Gunicorn চালায়; Flask route-এ APK endpoint পাওয়া যায়নি। |
| Hosted APK download | **NOT RUN** | HTTP response বা file bytes পাওয়া যায়নি। |
| Downloaded file-এর স্বাধীন SHA-256 | **NOT RUN** | Download হয়নি, তুলনার digest নেই। |
| Local route source sanity | **FAIL for actual artifact** | APK path না থাকলে Express 404 দেয়। Stale JSON-এ `verified: true` থাকলে metadata handler `exists: false` হলেও `verified: true` ফেরত দিতে পারে; UI-ও `exists === true` বাধ্যতামূলক না করে “Verified Release” দেখায়। তাই unavailable file-কে verified বলে দেখানোর ঝুঁকি আছে। |

Get App client `/api/download/apk` ও `/APK/latest.apk` ব্যবহার করে; metadata `/downloads/nexhaat.apk`-ও দেয়। Source-এ path থাকা থেকে production Flask host-এ Node/Express route চালু বা APK deploy করা প্রমাণ হয় না।

## Production signing ও distribution config

**Status: FAIL / configure করা নেই।** `android/` বা `APK/`-তে keystore নেই; `android/local.properties` অনুপস্থিত; release signing-এর চারটি environment variable unset। Gradle config স্পষ্টভাবে বলে credentials না থাকলে release unsigned হবে। কোনো credential value পড়া বা প্রকাশ করা হয়নি। Release API/media URL-ও নির্দিষ্ট করা নেই; API placeholder-এ থাকে।

## চালানো command ও পর্যবেক্ষণ

| Command / কাজ | ফল |
|---|---|
| `git status --short --branch`; `git rev-parse --show-toplevel`; `git branch --show-current`; `git rev-parse HEAD` | Root, `main`, উপরের HEAD এবং আগে থেকে থাকা worktree change নিশ্চিত। |
| `Get-ChildItem -Force APK,public/downloads,.temp_apk_build,android/app/build/outputs/apk -Recurse -File` ও repository-তে `.apk` search | কোনো APK/build output নেই; metadata/checksum/report আছে। |
| `APK/latest.json`, `public/downloads/metadata.json`, `APK/checksums.txt`, পুরোনো summary/report পড়া | Metadata claim পড়েছি, প্রমাণ হিসেবে ধরি নি। |
| `python scripts/validate_repository_structure.py --fail-on-review` | Exit 0; structure validator PASS। |
| `npm.cmd test` | Exit 1: `tsx` নেই। |
| `node tests-node/marketplace-api.test.mjs` | Exit 1: `vite` নেই। |
| `npm.cmd ci` | Exit 1: manifest/lockfile অসামঞ্জস্য। Lockfile পরিবর্তন/repair করা হয়নি। |
| `python <isolated-mirror>\scripts\nexhaat_qa_release_orchestrator.py --dry-run` | Gate 1 PASS, Gate 2 FAIL, exit 1; promotion হয়নি। |
| Isolated Python harness: `run_gate_5_package_apk()` ও `run_gate_6_smoke_verification()` | Invalid ZIP-এ দুটিই নিজে PASS বলেছে; 33,949 bytes, SHA `58fb7ebb11d6e580e3be5753f09489d7dd4dbece62a752afbc69937b343b6766`। REA/static inspection APK validity খণ্ডন করেছে। |
| `python scripts/nexhaat_qa_release_orchestrator.py --rollback-to __audit_nonexistent_release__` | Exit 1; release directory নেই। Release artifact বদলায়নি। |
| Temporary sentinel সহ isolated `--force-fail gate1` | Exit 1; failure log তৈরি; sentinel SHA অপরিবর্তিত। |
| Isolated rollback fixture harness | Marker কপি ও hash match; checksum অপরিবর্তিত; rollback source-এ atomic replace নেই। এটি আসল APK নয়। |
| `git ls-files -s android/gradlew android/gradlew.bat` | দুটির mode `100644`; Unix wrapper workflow-র `./gradlew`-এর জন্য executable নয়। |
| `where.exe adb`, `where.exe emulator`, SDK path, REA `list_adb_devices` | Local SDK/ADB/emulator নেই; REA-ও adb unavailable জানিয়েছে। |
| `Invoke-WebRequest -Method Head` দিয়ে `nexhaat.com` ও `.com.bd`-এর home, metadata, APK path | `.com` connection refused; `.com.bd` DNS ব্যর্থ; কোনো response bytes নেই। |
| Signing env, local-properties ও keystore presence check | Config অনুপস্থিত; কোনো secret value দেখানো হয়নি। |

### Simulated, skipped ও unavailable

- **Simulated:** sentinel fail-rule, positive rollback fixture, Gate 5/6 temporary candidate। এগুলো real release/device/download test নয়।
- **Skipped / not run:** historical APK extraction/install; emulator launch; auth/OTP/shopping UI; remote workflow run; hosted download/SHA; production signature; dependency install-পরবর্তী TypeScript; real release rollback।
- **Unavailable:** historical APK bytes, release archive, local Android SDK/ADB/emulator, untracked workflow-এর GitHub run, public domain/download service।

## Working tree-এর অতিরিক্ত integrity blocker

`git diff --check` **FAIL** করেছে: 103 finding-এর মধ্যে 102টি leftover merge-conflict marker, 1টি `app/api/serializers.py`-এর EOF blank line। Marker পাওয়া গেছে `android/app/src/main/java/com/nexhaat/app/data/repository/AuthRepository.kt`, `app/api/routes/auth.py`, `app/models/security.py`, `app/routes/auth.py`, `app/services/two_factor.py`, `app/services/two_factor_crypto.py`, `docs/architecture/WEBSITE_ANDROID_FEATURE_PARITY.md`, `tests/test_auth_two_factor.py` এবং `app/api/serializers.py`-তে। এই ফাইলগুলো অডিট শুরুর `git status`-এই staged ও unstaged modification হিসেবে ছিল; এই অডিটে সেগুলো সম্পাদনা করা হয়নি। Repository structure Gate 1 এই marker-গুলো ধরেনি। release যাচাইয়ের পরও এগুলো আলাদা করে review/repair করতে হবে।

## চূড়ান্ত রিলিজ সুপারিশ

**এই APK release করবেন না, production Get App download চালু করবেন না, এবং 33 KB metadata-কে verified বলবেন না।** পুনরায় বিবেচনার আগে প্রকৃত Gradle-built APK দিতে হবে; binary manifest/DEX parse, production signing ও API/media origin configure, একই artifact-এর বিরুদ্ধে fail-closed ছয় gate, Linux Gradle wrapper ও CI dependency ঠিক, emulator install/launch এবং চাওয়া UI journey সফল, এবং deployed website থেকে নামানো bytes-এর independent SHA reviewed artifact-এর সঙ্গে মিলতে হবে। আসল archived release দিয়ে rollback rehearsal-ও চালিয়ে atomic multi-file recovery নিশ্চিত করতে হবে।

**Repository change:** এই অডিটে এই রিপোর্ট ছাড়া source, workflow, lockfile, APK metadata বা release file বদলানো হয়নি। Commit, push, merge, deployment বা production action হয়নি।
