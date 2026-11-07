#!/usr/bin/env python3
"""NexHaat QA & APK release orchestrator (fail-closed).

Replaces the previous orchestrator, which manufactured a ZIP archive from source
files (plain-text manifest, zero-filled DEX, fake certificate) and reported PASS
for it, then published it as a "release".

Design rules enforced here:

* Six mandatory gates. A gate that fails **or cannot be executed** aborts the
  release. There is no fallback, skip, or fabricated artifact path.
* Gate 5 builds a genuine ``assembleRelease`` APK and requires
  ``scripts/validate_apk.py`` to return PASS for it. Gate 6 requires an actual
  device/emulator installation and launch.
* ``APK/latest.apk`` is only ever replaced by a staged, validated artifact, in a
  journalled multi-file publication that can be reverted.
* On failure the previous release is preserved byte-for-byte, diagnostics are
  written, and ``APK/status.json`` is set to ``BLOCKED``.
* Reports contain observed facts only. Anything not executed is ``NOT RUN``.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
APK_DIR = ROOT / "APK"
RELEASES_DIR = APK_DIR / "releases"
REPORTS_DIR = ROOT / "reports"
FAILURES_DIR = REPORTS_DIR / "failures"
PUBLIC_DOWNLOADS_DIR = ROOT / "public" / "downloads"
STATUS_PATH = APK_DIR / "status.json"
JOURNAL_PATH = APK_DIR / ".publish-journal.json"
VALIDATOR = ROOT / "scripts" / "validate_apk.py"
ANDROID_DIR = ROOT / "android"
GRADLE_BUILD_FILE = ANDROID_DIR / "app" / "build.gradle.kts"
MANIFEST_FILE = ANDROID_DIR / "app" / "src" / "main" / "AndroidManifest.xml"
RELEASE_APK = ANDROID_DIR / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk"

PACKAGE_ID = "com.nexhaat.app"
APP_NAME = "NexHaat"
SIGNING_ENV_VARS = (
    "NEXHAAT_KEYSTORE_PATH",
    "NEXHAAT_KEYSTORE_STORE_PASSWORD",
    "NEXHAAT_KEYSTORE_KEY_ALIAS",
    "NEXHAAT_KEYSTORE_KEY_PASSWORD",
)

PASS, FAIL, BLOCKED, NOT_RUN = "PASS", "FAIL", "BLOCKED", "NOT RUN"
MANDATORY = "mandatory"


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.2f} MB"


def find_tool(name: str, extra: Optional[List[Path]] = None) -> Optional[str]:
    for candidate_name in (name, f"{name}.cmd", f"{name}.BAT", f"{name}.exe"):
        found = shutil.which(candidate_name)
        if found:
            return found
    for directory in extra or []:
        for candidate_name in (name, f"{name}.bat", f"{name}.cmd", f"{name}.exe"):
            candidate = directory / candidate_name
            if candidate.is_file():
                return str(candidate)
    return None


def android_sdk_dirs() -> List[Path]:
    found: List[Path] = []
    for var in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
        value = os.environ.get(var, "").strip()
        if value and Path(value).is_dir():
            found.append(Path(value))
    return found


def toolchain_facts() -> Dict[str, Any]:
    """Observed tool availability. Never assumes that a tool is present."""
    python = sys.executable or "python"
    java = find_tool("java")
    java_version: Optional[str] = None
    if java:
        try:
            proc = subprocess.run([java, "-version"], capture_output=True, text=True, timeout=30, check=False)
            java_version = (proc.stderr or proc.stdout).strip().splitlines()[0] if (proc.stderr or proc.stdout) else None
        except (OSError, subprocess.SubprocessError):
            java_version = None
    sdk_dirs = android_sdk_dirs()
    build_tools: List[str] = []
    for directory in sdk_dirs:
        bt = directory / "build-tools"
        if bt.is_dir():
            build_tools.extend(sorted(child.name for child in bt.iterdir() if child.is_dir()))
    return {
        "python": python,
        "java": java,
        "javaVersion": java_version,
        "npm": find_tool("npm"),
        "node": find_tool("node"),
        "adb": find_tool("adb"),
        "emulator": find_tool("emulator"),
        "gradleWrapper": str(ANDROID_DIR / ("gradlew.bat" if os.name == "nt" else "gradlew")),
        "androidSdkDirs": [str(p) for p in sdk_dirs],
        "buildTools": build_tools,
        "gradleIdentity": read_gradle_identity(),
        "signingConfigured": all(os.environ.get(v, "").strip() for v in SIGNING_ENV_VARS),
    }


def read_gradle_identity() -> Dict[str, Any]:
    """Read version/SDK values from the Gradle build file (single source of truth)."""
    if not GRADLE_BUILD_FILE.is_file():
        return {}
    text = GRADLE_BUILD_FILE.read_text(encoding="utf-8")
    identity: Dict[str, Any] = {}

    def grab(pattern: str) -> Optional[str]:
        match = re.search(pattern, text)
        return match.group(1) if match else None

    version_name = grab(r'versionName\s*=\s*"([^"]+)"')
    version_code = grab(r"versionCode\s*=\s*(\d+)")
    min_sdk = grab(r"minSdk\s*=\s*(\d+)")
    target_sdk = grab(r"targetSdk\s*=\s*(\d+)")
    application_id = grab(r'applicationId\s*=\s*"([^"]+)"')
    if version_name:
        identity["versionName"] = version_name
    if version_code:
        identity["versionCode"] = int(version_code)
    if min_sdk:
        identity["minSdk"] = int(min_sdk)
    if target_sdk:
        identity["targetSdk"] = int(target_sdk)
    if application_id:
        identity["applicationId"] = application_id
    return identity


def normalize_conflict_marker_lines(raw: str) -> List[str]:
    """Return a clean, reproducible list of anchored conflict-marker lines.

    Gate 1 leads with the current checkout, not with any previously persisted
    status. Standalone ``=======`` lines are not, by themselves, conflict
    markers; only a line-start marker pair context is treated as a possible
    conflict. This keeps intentional separators (for example CSS comment
    dividers) from becoming false positives while never relaxing the real
    marker detection.
    """
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    start_marker_re = re.compile(r"^<<<<<<< ")
    end_marker_re = re.compile(r"^>>>>>>> ")
    sep_marker_re = re.compile(r"^=======$")
    markers: List[str] = []
    saw_start_or_end = False
    for line in lines:
        if start_marker_re.match(line) or end_marker_re.match(line):
            markers.append(line)
            saw_start_or_end = True
        elif sep_marker_re.match(line) and saw_start_or_end:
            markers.append(line)
    return markers


def _strip_grep_path_line_prefix(line: str) -> str:
    """Return the marker text from a ``git grep -n`` output line.

    ``git grep -n`` emits ``path:line:match``. Conflict-marker patterns are
    anchored at the start of the matched line in the file, so the relevant text
    begins after the second colon.
    """
    first = line.find(":")
    if first == -1:
        return line
    second = line.find(":", first + 1)
    if second == -1:
        return line
    return line[second + 1:]


class GateResult:
    def __init__(
        self,
        gate_id: int,
        name: str,
        status: str,
        duration: float,
        detail: str,
        facts: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.gate_id = gate_id
        self.name = name
        self.status = status
        self.duration = duration
        self.detail = detail
        self.facts = facts or {}

    @property
    def passed(self) -> bool:
        return self.status == PASS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate": self.gate_id,
            "name": self.name,
            "status": self.status,
            "mandatory": MANDATORY,
            "durationSec": round(self.duration, 2),
            "detail": self.detail,
            "facts": self.facts,
        }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class ReleaseOrchestrator:
    def __init__(self, dry_run: bool = False, force_fail_gate: Optional[str] = None) -> None:
        self.dry_run = dry_run
        self.force_fail_gate = force_fail_gate
        self.started = utc_now()
        self.build_id = self.started.strftime("%Y%m%d%H%M%S")
        self.gates: List[GateResult] = []
        self.toolchain = toolchain_facts()
        self.identity = self.toolchain.get("gradleIdentity", {}) or {}
        self.staged_apk: Optional[Path] = None
        self.apk_facts: Dict[str, Any] = {}

    # -- logging ----------------------------------------------------------
    def log(self, message: str, level: str = "INFO") -> None:
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{stamp}] [{level}] {message}", flush=True)

    def run(self, cmd: List[str], cwd: Path = ROOT, timeout: int = 300) -> Tuple[int, str]:
        self.log(f"$ {' '.join(cmd)}")
        env = dict(os.environ)
        env.setdefault("PYTHONIOENCODING", "utf-8")
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return 124, f"command timed out after {timeout}s: {' '.join(cmd)}"
        except OSError as exc:
            return 127, f"command could not be executed: {exc}"
        output = "\n".join(part for part in (proc.stdout, proc.stderr) if part).strip()
        return proc.returncode, output

    # -- gate helpers -----------------------------------------------------
    def _record(self, result: GateResult) -> GateResult:
        self.gates.append(result)
        prefix = "PASS" if result.passed else result.status
        self.log(f"[{prefix}] Gate {result.gate_id} — {result.name} ({result.duration:.2f}s)")
        if not result.passed:
            self.log(result.detail[:2000], level="ERROR")
        return result

    # -- Gate 1 -----------------------------------------------------------
    def gate_1_repository_integrity(self) -> GateResult:
        start = time.time()
        self.log(">>> Gate 1: repository structure, identity and integrity")

        rc, out = self.run([sys.executable, str(ROOT / "scripts" / "validate_repository_structure.py"), "--fail-on-review"], timeout=120)
        if rc != 0:
            return self._record(GateResult(1, "Repository integrity & manifest", FAIL, time.time() - start,
                                           f"validate_repository_structure.py exited {rc}:\n{out[-2000:]}"))

        markers_rc, markers = self.run(["git", "grep", "-n", "-I", "-e", "^<<<<<<< ", "-e", "^>>>>>>> ", "-e", "^=======$"], timeout=120)
        raw_marker_lines = [line for line in markers.splitlines() if line.strip()] if markers_rc in (0, 1) else []
        marker_text_lines = [_strip_grep_path_line_prefix(line) for line in raw_marker_lines]
        marker_lines = normalize_conflict_marker_lines("\n".join(marker_text_lines))
        gate_1_facts: Dict[str, Any] = {
            "conflictMarkers": marker_lines[:200],
            "currentScan": {
                "command": ["git", "grep", "-n", "-I", "-e", "^<<<<<<< ", "-e", "^>>>>>>> ", "-e", "^=======$"],
                "exitStatus": markers_rc,
                "rawMarkerLines": raw_marker_lines[:200],
                "normalizedMarkerLines": marker_lines[:200],
            },
        }
        if marker_lines:
            detail = (
                "leftover merge-conflict markers found in the working tree:\n"
                + "\n".join(marker_lines[:40])
                + ("\n..." if len(marker_lines) > 40 else "")
                + "\nThese belong to the in-progress 2FA/auth work; the tree cannot be released until the owner resolves them."
            )
            return self._record(GateResult(1, "Repository integrity & manifest", FAIL, time.time() - start, detail, gate_1_facts))

        check_rc, check_out = self.run(["git", "diff", "--check"], timeout=120)
        if check_rc != 0:
            return self._record(GateResult(1, "Repository integrity & manifest", FAIL, time.time() - start,
                                           f"git diff --check reported whitespace/conflict problems:\n{check_out[-2000:]}"))

        if not MANIFEST_FILE.is_file() or not GRADLE_BUILD_FILE.is_file():
            return self._record(GateResult(1, "Repository integrity & manifest", FAIL, time.time() - start,
                                           "AndroidManifest.xml or app/build.gradle.kts is missing"))
        manifest = MANIFEST_FILE.read_text(encoding="utf-8")
        if ".MainActivity" not in manifest or "android.intent.action.MAIN" not in manifest:
            return self._record(GateResult(1, "Repository integrity & manifest", FAIL, time.time() - start,
                                           "launcher activity / MAIN intent filter missing from AndroidManifest.xml"))
        if self.identity.get("applicationId") != PACKAGE_ID:
            return self._record(GateResult(1, "Repository integrity & manifest", FAIL, time.time() - start,
                                           f"applicationId is {self.identity.get('applicationId')!r}, expected {PACKAGE_ID!r}"))
        gradlew = ANDROID_DIR / "gradlew"
        if not gradlew.is_file():
            return self._record(GateResult(1, "Repository integrity & manifest", FAIL, time.time() - start,
                                           "android/gradlew is missing"))

        return self._record(GateResult(
            1, "Repository integrity & manifest", PASS, time.time() - start,
            "structure validator passed; no conflict markers; manifest and Gradle identity match",
            {"applicationId": PACKAGE_ID, "identity": self.identity, **gate_1_facts},
        ))

    # -- Gate 2 -----------------------------------------------------------
    def gate_2_security_tests(self) -> GateResult:
        start = time.time()
        self.log(">>> Gate 2: Node server security suite (npm test)")
        npm = self.toolchain.get("npm")
        if not npm:
            return self._record(GateResult(2, "Security test suite", BLOCKED, time.time() - start,
                                           "npm is not available on PATH"))
        rc, out = self.run([npm, "test"], timeout=600)
        if rc != 0:
            return self._record(GateResult(2, "Security test suite", FAIL, time.time() - start,
                                           f"npm test exited {rc}:\n{out[-4000:]}", {"exitCode": rc}))
        return self._record(GateResult(2, "Security test suite", PASS, time.time() - start,
                                       "npm test exited 0", {"exitCode": 0, "outputTail": out[-1500:]}))

    # -- Gate 3 -----------------------------------------------------------
    def gate_3_marketplace_api_tests(self) -> GateResult:
        start = time.time()
        self.log(">>> Gate 3: marketplace API integration suite")
        node = self.toolchain.get("node")
        if not node:
            return self._record(GateResult(3, "Marketplace API suite", BLOCKED, time.time() - start, "node is not available"))
        test_file = ROOT / "tests-node" / "marketplace-api.test.mjs"
        if not test_file.is_file():
            return self._record(GateResult(3, "Marketplace API suite", FAIL, time.time() - start,
                                           f"{test_file} is missing"))
        rc, out = self.run([node, str(test_file)], timeout=600)
        if rc != 0:
            return self._record(GateResult(3, "Marketplace API suite", FAIL, time.time() - start,
                                           f"marketplace-api.test.mjs exited {rc}:\n{out[-4000:]}", {"exitCode": rc}))
        return self._record(GateResult(3, "Marketplace API suite", PASS, time.time() - start,
                                       "marketplace-api.test.mjs exited 0", {"exitCode": 0, "outputTail": out[-1500:]}))

    # -- Gate 4 -----------------------------------------------------------
    def gate_4_typescript(self) -> GateResult:
        start = time.time()
        self.log(">>> Gate 4: TypeScript compilation (tsc --noEmit)")
        npm = self.toolchain.get("npm")
        if not npm:
            return self._record(GateResult(4, "TypeScript compilation", BLOCKED, time.time() - start, "npm is not available"))
        tsc = ROOT / "node_modules" / "typescript" / "bin" / "tsc"
        if not tsc.is_file():
            return self._record(GateResult(4, "TypeScript compilation", BLOCKED, time.time() - start,
                                           "node_modules/typescript is missing; run npm ci first (no remote fallback accepted)"))
        node = self.toolchain.get("node")
        rc, out = self.run([node or "node", str(tsc), "--noEmit"], timeout=600)
        if rc != 0:
            return self._record(GateResult(4, "TypeScript compilation", FAIL, time.time() - start,
                                           f"tsc --noEmit exited {rc}:\n{out[-4000:]}", {"exitCode": rc}))
        return self._record(GateResult(4, "TypeScript compilation", PASS, time.time() - start,
                                       "tsc --noEmit exited 0 with no diagnostics", {"exitCode": 0}))

    # -- Gate 5 -----------------------------------------------------------
    def _release_prerequisites(self) -> List[str]:
        problems: List[str] = []
        java = self.toolchain.get("java")
        if not java:
            problems.append("java is not installed (JDK 17 is required)")
        else:
            version = self.toolchain.get("javaVersion") or ""
            match = re.search(r'version "(\d+)', version)
            major = int(match.group(1)) if match else 0
            if major and major < 17:
                problems.append(f"JDK 17+ is required, found: {version}")
        if not self.toolchain.get("androidSdkDirs"):
            problems.append("ANDROID_SDK_ROOT / ANDROID_HOME does not point at an existing Android SDK")
        if not self.toolchain.get("signingConfigured"):
            missing = [v for v in SIGNING_ENV_VARS if not os.environ.get(v, "").strip()]
            problems.append(f"release signing is not configured (missing: {', '.join(missing)}); unsigned output is not releasable")
        release_base = os.environ.get("NEXHAAT_RELEASE_BASE_URL", "").strip()
        if not release_base:
            problems.append("NEXHAAT_RELEASE_BASE_URL is not set; the release build would target a placeholder origin")
        elif "replace_me" in release_base.lower():
            problems.append("NEXHAAT_RELEASE_BASE_URL still contains a placeholder")
        media_base = os.environ.get("NEXHAAT_MEDIA_BASE_URL", "").strip()
        if not media_base:
            problems.append("NEXHAAT_MEDIA_BASE_URL is not set; release media base would be unresolved")
        elif "replace_me" in media_base.lower():
            problems.append("NEXHAAT_MEDIA_BASE_URL still contains a placeholder")
        return problems

    def gate_5_build_and_validate_apk(self) -> GateResult:
        start = time.time()
        self.log(">>> Gate 5: genuine release build + strict APK validation")

        problems = self._release_prerequisites()
        if problems:
            return self._record(GateResult(
                5, "Release build & APK validation", BLOCKED, time.time() - start,
                "release prerequisites are not satisfied:\n- " + "\n- ".join(problems),
                {"prerequisites": problems},
            ))

        gradlew = ANDROID_DIR / ("gradlew.bat" if os.name == "nt" else "gradlew")
        if os.name != "nt" and not os.access(gradlew, os.X_OK):
            return self._record(GateResult(
                5, "Release build & APK validation", FAIL, time.time() - start,
                "android/gradlew is not executable; fix with: git update-index --chmod=+x android/gradlew",
            ))

        cmd = [str(gradlew), ":app:assembleRelease", "--no-daemon"] if os.name == "nt" else [str(gradlew), ":app:assembleRelease", "--no-daemon"]
        if os.name == "nt":
            cmd = ["cmd", "/c", *cmd]
        rc, out = self.run(cmd, cwd=ANDROID_DIR, timeout=3600)
        if rc != 0:
            return self._record(GateResult(5, "Release build & APK validation", FAIL, time.time() - start,
                                           f"gradle :app:assembleRelease exited {rc}:\n{out[-6000:]}", {"exitCode": rc}))
        if not RELEASE_APK.is_file():
            return self._record(GateResult(
                5, "Release build & APK validation", FAIL, time.time() - start,
                f"gradle reported success but {RELEASE_APK.relative_to(ROOT)} does not exist; "
                "no substitute artifact is generated",
            ))

        staging = APK_DIR / f".staging-{self.build_id}"
        staging.mkdir(parents=True, exist_ok=True)
        staged = staging / f"NexHaat-v{self.identity.get('versionName', '0.0.0')}-{self.build_id}.apk"
        shutil.copy2(RELEASE_APK, staged)

        report = staging / "validation.json"
        rc, out = self.run([
            sys.executable, str(VALIDATOR),
            "--apk", str(staged),
            "--expected-package", PACKAGE_ID,
            "--expected-version", str(self.identity.get("versionName")),
            "--expected-version-code", str(self.identity.get("versionCode")),
            "--expected-min-sdk", str(self.identity.get("minSdk")),
            "--expected-target-sdk", str(self.identity.get("targetSdk")),
            "--allow-missing-install",
            "--json-out", str(report),
        ], timeout=600)
        verdict = self._read_json(report).get("verdict") if report.is_file() else None
        facts = self._read_json(report)

        if rc == 0 and verdict == PASS:
            self.staged_apk = staged
            self.apk_facts = facts.get("facts", {})
            return self._record(GateResult(
                5, "Release build & APK validation", PASS, time.time() - start,
                f"assembleRelease produced a valid signed APK ({format_bytes(staged.stat().st_size)}); "
                "binary manifest, DEX, signature and checksum verified",
                {
                    "sha256": facts.get("facts", {}).get("sha256"),
                    "sizeBytes": facts.get("facts", {}).get("sizeBytes"),
                    "signerCertificateSha256": facts.get("facts", {}).get("apksigner", {}).get("signerCertificateSha256"),
                    "validatorOutput": out[-3000:],
                },
            ))

        status = BLOCKED if verdict == BLOCKED or rc == 2 else FAIL
        return self._record(GateResult(
            5, "Release build & APK validation", status, time.time() - start,
            f"strict APK validation did not pass (verdict={verdict}, exit={rc}):\n{out[-4000:]}",
            {"validator": facts},
        ))

    # -- Gate 6 -----------------------------------------------------------
    def gate_6_device_install_and_launch(self) -> GateResult:
        start = time.time()
        self.log(">>> Gate 6: device/emulator installation, launch and crash check")
        if not self.staged_apk or not self.staged_apk.is_file():
            return self._record(GateResult(6, "Device install & launch", FAIL, time.time() - start,
                                           "no validated APK is staged for device verification"))
        if not self.toolchain.get("adb"):
            return self._record(GateResult(6, "Device install & launch", BLOCKED, time.time() - start,
                                           "adb is not installed; installation and launch cannot be verified"))
        serial = os.environ.get("NEXHAAT_ADB_SERIAL", "").strip() or None
        report = self.staged_apk.parent / "device-validation.json"
        cmd = [sys.executable, str(VALIDATOR), "--apk", str(self.staged_apk), "--install", "--json-out", str(report)]
        if serial:
            cmd += ["--serial", serial]
        rc, out = self.run(cmd, timeout=900)
        facts = self._read_json(report)
        if rc == 0 and facts.get("verdict") == PASS:
            device = (facts.get("facts") or {}).get("device", {})
            return self._record(GateResult(6, "Device install & launch", PASS, time.time() - start,
                                           "APK installed, launcher started, process alive, no AndroidRuntime crash",
                                           {"pid": device.get("pid"), "launch": device.get("launch", "")[-800:]}))
        status = BLOCKED if rc == 2 or facts.get("verdict") == BLOCKED else FAIL
        return self._record(GateResult(6, "Device install & launch", status, time.time() - start,
                                       f"device verification did not pass (exit={rc}):\n{out[-3000:]}", {"validator": facts}))

    # -- helpers ----------------------------------------------------------
    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        if not path.is_file():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def gate_runners(self):
        return [
            self.gate_1_repository_integrity,
            self.gate_2_security_tests,
            self.gate_3_marketplace_api_tests,
            self.gate_4_typescript,
            self.gate_5_build_and_validate_apk,
            self.gate_6_device_install_and_launch,
        ]

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------
    def run_pipeline(self) -> bool:
        self.log(f"NexHaat release pipeline — build {self.build_id} on {sys.platform}")
        self.recover_pending_publication()
        for index, runner in enumerate(self.gate_runners(), start=1):
            if self.force_fail_gate == f"gate{index}":
                self._record(GateResult(index, f"Gate {index} (simulated)", FAIL, 0.0,
                                        f"simulated failure via --force-fail gate{index}"))
                self.on_failure(self.gates[-1])
                return False
            result = runner()
            if not result.passed:
                self.on_failure(result)
                return False
        return True

    def on_failure(self, failed: GateResult) -> None:
        """FAIL RULE: never touch the live release; record BLOCKED diagnostics."""
        self.log("=" * 72, level="ERROR")
        self.log("RELEASE BLOCKED — the fail rule was triggered, live artifacts untouched", level="ERROR")
        self.log("=" * 72, level="ERROR")
        FAILURES_DIR.mkdir(parents=True, exist_ok=True)
        diagnostic = {
            "timestamp": utc_now().isoformat(),
            "buildId": self.build_id,
            "status": BLOCKED,
            "failedGate": failed.to_dict(),
            "gates": [g.to_dict() for g in self.gates],
            "toolchain": self.toolchain,
            "liveRelease": self.describe_live_release(),
        }
        (FAILURES_DIR / f"failure-{self.build_id}.json").write_text(json.dumps(diagnostic, indent=2), encoding="utf-8")
        self.write_status(BLOCKED, failed)
        self.generate_reports(status=BLOCKED, failed=failed)
        if self.staged_apk and self.staged_apk.parent.name.startswith(".staging-"):
            shutil.rmtree(self.staged_apk.parent, ignore_errors=True)
        self.log(f"Diagnostics: reports/failures/failure-{self.build_id}.json")

    def write_status(self, status: str, failed: Optional[GateResult] = None, extra: Optional[Dict[str, Any]] = None) -> None:
        APK_DIR.mkdir(parents=True, exist_ok=True)
        payload: Dict[str, Any] = {
            "status": status,
            "appName": APP_NAME,
            "packageId": PACKAGE_ID,
            "buildId": self.build_id,
            "updatedAt": utc_now().isoformat(),
            "version": self.identity.get("versionName"),
            "versionCode": self.identity.get("versionCode"),
            "liveRelease": self.describe_live_release(),
            "toolchain": self.toolchain,
            "gates": [g.to_dict() for g in self.gates],
        }
        if failed is not None:
            payload["blockedBy"] = {
                "gate": failed.gate_id,
                "name": failed.name,
                "status": failed.status,
                "detail": failed.detail[:4000],
            }
        if extra:
            payload.update(extra)
        tmp = STATUS_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, STATUS_PATH)

    def describe_live_release(self) -> Dict[str, Any]:
        latest_apk = APK_DIR / "latest.apk"
        latest_json = APK_DIR / "latest.json"
        info: Dict[str, Any] = {
            "latestApkExists": latest_apk.is_file(),
            "latestJsonExists": latest_json.is_file(),
            "publicMirrorExists": (PUBLIC_DOWNLOADS_DIR / "nexhaat.apk").is_file(),
            "releases": sorted(p.name for p in RELEASES_DIR.glob("*.apk")) if RELEASES_DIR.is_dir() else [],
        }
        if latest_apk.is_file():
            info["latestApkSha256"] = compute_sha256(latest_apk)
            info["latestApkSize"] = latest_apk.stat().st_size
        return info

    # ------------------------------------------------------------------
    # Publication (atomic, journalled)
    # ------------------------------------------------------------------
    def _build_release_metadata(self, staged: Path) -> Dict[str, Any]:
        sha256 = compute_sha256(staged)
        facts = self.apk_facts or {}
        return {
            "appName": APP_NAME,
            "packageId": PACKAGE_ID,
            "version": self.identity.get("versionName"),
            "versionCode": self.identity.get("versionCode"),
            "minSdk": facts.get("minSdk", self.identity.get("minSdk")),
            "targetSdk": facts.get("targetSdk", self.identity.get("targetSdk")),
            "buildId": self.build_id,
            "buildDate": self.started.isoformat(),
            "buildType": "release",
            "filename": "nexhaat.apk",
            "displayName": f"{APP_NAME}-v{self.identity.get('versionName')}.apk",
            "releaseFilename": staged.name,
            "sha256": sha256,
            "sizeBytes": staged.stat().st_size,
            "sizeFormatted": format_bytes(staged.stat().st_size),
            "verified": True,
            "verification": {
                "validator": "scripts/validate_apk.py",
                "signerCertificateSha256": facts.get("apksigner", {}).get("signerCertificateSha256"),
                "signatureSchemes": facts.get("apksigner", {}).get("schemes"),
                "deviceInstallVerified": any(g.gate_id == 6 and g.passed for g in self.gates),
                "gates": {f"gate{g.gate_id}": g.status for g in self.gates},
            },
            "downloadUrl": "/api/download/apk",
            "directUrl": "/downloads/nexhaat.apk",
            "instructions": [
                "1. Tap 'Download APK' to fetch the verified NexHaat application package.",
                "2. When the download completes, open the notification or your Downloads folder.",
                "3. If prompted, allow 'Install unknown apps' for your browser or file manager.",
                "4. Tap 'Install' and launch NexHaat.",
            ],
        }

    def promote_release(self) -> bool:
        """Stage every published file, then swap them in with a rollback journal."""
        if not self.staged_apk or not self.staged_apk.is_file() or self.apk_facts.get("sha256") is None:
            raise RuntimeError("cannot promote: no validated APK with a recorded checksum")

        staged_sha = compute_sha256(self.staged_apk)
        if staged_sha != self.apk_facts.get("sha256"):
            raise RuntimeError("cannot promote: staged APK checksum changed after validation")

        for directory in (APK_DIR, RELEASES_DIR, PUBLIC_DOWNLOADS_DIR):
            directory.mkdir(parents=True, exist_ok=True)

        metadata = self._build_release_metadata(self.staged_apk)
        staging = APK_DIR / f".publish-{self.build_id}"
        staging.mkdir(parents=True, exist_ok=True)
        staged_files = {
            "latest.apk": staging / "latest.apk",
            "latest.json": staging / "latest.json",
            "public.apk": staging / "public.apk",
            "public.metadata.json": staging / "public-metadata.json",
            "checksums.txt": staging / "checksums.txt",
            "release.apk": staging / metadata["releaseFilename"],
            "release.json": staging / f"{Path(metadata['releaseFilename']).stem}.json",
        }
        shutil.copy2(self.staged_apk, staged_files["latest.apk"])
        shutil.copy2(self.staged_apk, staged_files["public.apk"])
        shutil.copy2(self.staged_apk, staged_files["release.apk"])
        staged_files["latest.json"].write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        staged_files["public.metadata.json"].write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        staged_files["release.json"].write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        checksums = (APK_DIR / "checksums.txt").read_text(encoding="utf-8") if (APK_DIR / "checksums.txt").is_file() else ""
        entries = [
            line for line in checksums.splitlines()
            if line.strip() and metadata["releaseFilename"] not in line
        ]
        entries.append(f"{metadata['sha256']}  {metadata['releaseFilename']}")
        staged_files["checksums.txt"].write_text("\n".join(entries) + "\n", encoding="utf-8")

        targets = {
            "release.apk": RELEASES_DIR / metadata["releaseFilename"],
            "release.json": RELEASES_DIR / f"{Path(metadata['releaseFilename']).stem}.json",
            "latest.apk": APK_DIR / "latest.apk",
            "public.apk": PUBLIC_DOWNLOADS_DIR / "nexhaat.apk",
            "latest.json": APK_DIR / "latest.json",
            "public.metadata.json": PUBLIC_DOWNLOADS_DIR / "metadata.json",
            "checksums.txt": APK_DIR / "checksums.txt",
        }

        backup_dir = APK_DIR / f".backup-{self.build_id}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backups: Dict[str, Optional[str]] = {}
        for key, target in targets.items():
            if target.is_file():
                backup = backup_dir / target.name
                shutil.copy2(target, backup)
                backups[key] = str(backup)
            else:
                backups[key] = None

        journal = {
            "buildId": self.build_id,
            "state": "prepared",
            "startedAt": utc_now().isoformat(),
            "targets": {k: str(v) for k, v in targets.items()},
            "backups": backups,
            "sha256": metadata["sha256"],
        }
        JOURNAL_PATH.write_text(json.dumps(journal, indent=2), encoding="utf-8")

        try:
            for key in ("release.apk", "release.json", "latest.apk", "public.apk",
                        "latest.json", "public.metadata.json", "checksums.txt"):
                os.replace(staged_files[key], targets[key])
            journal["state"] = "committed"
            journal["committedAt"] = utc_now().isoformat()
            JOURNAL_PATH.write_text(json.dumps(journal, indent=2), encoding="utf-8")
            JOURNAL_PATH.unlink()
        except Exception as exc:  # noqa: BLE001 - deliberate: any failure must restore
            self.log(f"publication failed ({exc}); restoring previous release", level="ERROR")
            self.restore_from_journal(journal)
            raise

        shutil.rmtree(backup_dir, ignore_errors=True)
        shutil.rmtree(staging, ignore_errors=True)
        if self.staged_apk.parent.name.startswith((".staging-", ".temp_apk_build")):
            shutil.rmtree(self.staged_apk.parent, ignore_errors=True)
        self.log(f"published {metadata['releaseFilename']} (SHA-256 {metadata['sha256'][:16]}...)")
        return True

    def restore_from_journal(self, journal: Dict[str, Any]) -> None:
        for key, target in journal["targets"].items():
            target_path = Path(target)
            backup = journal["backups"].get(key)
            if backup and Path(backup).is_file():
                tmp = target_path.with_name(target_path.name + ".restore")
                shutil.copy2(backup, tmp)
                os.replace(tmp, target_path)
            elif target_path.is_file() and target_path.parent == RELEASES_DIR:
                target_path.unlink(missing_ok=True)
        JOURNAL_PATH.unlink(missing_ok=True)

    def recover_pending_publication(self) -> None:
        if not JOURNAL_PATH.is_file():
            return
        journal = self._read_json(JOURNAL_PATH)
        if journal.get("state") == "committed":
            JOURNAL_PATH.unlink(missing_ok=True)
            return
        self.log("found an incomplete publication journal; restoring the previous release", level="ERROR")
        self.restore_from_journal(journal)

    # ------------------------------------------------------------------
    # Post-publication verification & rollback
    # ------------------------------------------------------------------
    def verify_publication(self) -> Tuple[str, str, Dict[str, Any]]:
        """Verify the published artifact is the validated artifact and is served byte-for-byte."""
        facts: Dict[str, Any] = {}
        latest = APK_DIR / "latest.apk"
        metadata_path = APK_DIR / "latest.json"
        if not latest.is_file() or not metadata_path.is_file():
            return FAIL, "published latest.apk or latest.json is missing", facts
        expected = self.apk_facts.get("sha256")
        actual = compute_sha256(latest)
        facts["publishedSha256"] = actual
        facts["expectedSha256"] = expected
        if expected and actual != expected:
            return FAIL, f"APK/latest.apk SHA-256 {actual} != validated {expected}", facts

        mirror = PUBLIC_DOWNLOADS_DIR / "nexhaat.apk"
        if not mirror.is_file():
            return FAIL, "public/downloads/nexhaat.apk is missing after publication", facts
        facts["mirrorSha256"] = compute_sha256(mirror)
        if facts["mirrorSha256"] != actual:
            return FAIL, "website mirror bytes differ from APK/latest.apk", facts

        report = APK_DIR / f".verify-{self.build_id}.json"
        rc, out = self.run([sys.executable, str(VALIDATOR), "--apk", str(latest),
                            "--metadata", str(metadata_path), "--allow-missing-install",
                            "--json-out", str(report)], timeout=600)
        facts["validator"] = self._read_json(report)
        report.unlink(missing_ok=True)
        if rc != 0:
            return FAIL, f"published artifact failed re-validation:\n{out[-2000:]}", facts

        status, http_facts = self._http_download_check(metadata_path)
        facts["http"] = http_facts
        return status, http_facts.get("detail", ""), facts

    def _http_download_check(self, metadata_path: Path) -> Tuple[str, Dict[str, Any]]:
        node = self.toolchain.get("node")
        if not node or not (ROOT / "server.ts").is_file():
            return BLOCKED, {"detail": "node or server.ts unavailable; served bytes were not verified"}
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = dict(os.environ)
        env["PORT"] = str(port)
        env["NODE_ENV"] = "production"
        log_path = REPORTS_DIR / f"server-{self.build_id}.log"
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as log_file:
            try:
                proc = subprocess.Popen([node, str(ROOT / "server.ts")], cwd=str(ROOT), env=env,
                                        stdout=log_file, stderr=subprocess.STDOUT)
            except OSError as exc:
                return BLOCKED, {"detail": f"marketplace server could not be started: {exc}"}
        try:
            deadline = time.time() + 60
            info: Dict[str, Any] = {}
            while time.time() < deadline:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/download/apk/info", timeout=5) as response:
                        info = json.loads(response.read().decode("utf-8"))
                    break
                except (urllib.error.URLError, ConnectionError, json.JSONDecodeError, OSError):
                    if proc.poll() is not None:
                        return BLOCKED, {"detail": f"marketplace server exited early; see {log_path.name}"}
                    time.sleep(1)
            else:
                return BLOCKED, {"detail": "marketplace server did not become ready within 60s"}

            apk_info = info.get("apk", {})
            facts = {"info": apk_info}
            if not apk_info.get("exists") or not apk_info.get("verified"):
                return FAIL, f"download endpoint does not advertise a verified existing artifact: {json.dumps(apk_info)[:600]}", facts
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/download/apk", timeout=120) as response:
                content_type = response.headers.get("Content-Type", "")
                disposition = response.headers.get("Content-Disposition", "")
                payload = response.read()
            facts.update({"contentType": content_type, "contentDisposition": disposition,
                          "downloadedBytes": len(payload)})
            facts["downloadedSha256"] = hashlib.sha256(payload).hexdigest()
            if content_type != "application/vnd.android.package-archive":
                return FAIL, f"download Content-Type is {content_type!r}", facts
            if "attachment" not in disposition.lower():
                return FAIL, f"download Content-Disposition is {disposition!r}", facts
            if facts["downloadedSha256"] != self.apk_facts.get("sha256"):
                return FAIL, "downloaded bytes differ from the validated artifact", facts
            facts["detail"] = "published artifact verified and served byte-identically over HTTP"
            return PASS, facts
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()

    @staticmethod
    def rollback_to(target: str, require_device: bool = False) -> int:
        """Restore a verified historical release and its matching metadata atomically."""
        print(f"[ROLLBACK] target={target}")
        if not RELEASES_DIR.is_dir():
            print(f"[ROLLBACK][FAIL] {RELEASES_DIR} does not exist")
            return 1
        candidates = [p for p in sorted(RELEASES_DIR.glob("*.apk")) if p.name == target or target in p.name]
        if not candidates:
            print("[ROLLBACK][FAIL] no archived release matches that target. Available:")
            for item in sorted(RELEASES_DIR.glob("*.apk")):
                print(f"  - {item.name}")
            return 1
        release = candidates[0]
        sidecar = release.with_suffix(".json")
        if not sidecar.is_file():
            print(f"[ROLLBACK][FAIL] release metadata {sidecar.name} is missing; refusing an unverifiable rollback")
            return 1

        report = RELEASES_DIR / f".rollback-check-{os.getpid()}.json"
        cmd = [sys.executable, str(VALIDATOR), "--apk", str(release), "--metadata", str(sidecar)]
        if require_device:
            cmd.append("--install")
        else:
            cmd.append("--allow-missing-install")
        cmd += ["--json-out", str(report)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900, check=False)
        print(proc.stdout.strip()[-3000:])
        verdict = {}
        if report.is_file():
            try:
                verdict = json.loads(report.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                verdict = {}
            report.unlink(missing_ok=True)
        if proc.returncode != 0:
            print(f"[ROLLBACK][FAIL] target release did not pass validation (verdict={verdict.get('verdict')}); "
                  "rollback refused, live artifacts untouched")
            return 1

        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        metadata["isRollback"] = True
        metadata["rollbackSource"] = release.name
        metadata["rollbackAt"] = utc_now().isoformat()
        metadata["verified"] = True

        latest = APK_DIR / "latest.apk"
        tmp_latest = APK_DIR / f".rollback-{os.getpid()}.apk"
        shutil.copy2(release, tmp_latest)
        os.replace(tmp_latest, latest)

        mirror = PUBLIC_DOWNLOADS_DIR / "nexhaat.apk"
        PUBLIC_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        tmp_mirror = PUBLIC_DOWNLOADS_DIR / f".rollback-{os.getpid()}.apk"
        shutil.copy2(release, tmp_mirror)
        os.replace(tmp_mirror, mirror)

        for path in (APK_DIR / "latest.json", PUBLIC_DOWNLOADS_DIR / "metadata.json"):
            tmp = path.with_name(f".rollback-{os.getpid()}-{path.name}")
            tmp.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            os.replace(tmp, path)

        checksums = APK_DIR / "checksums.txt"
        lines = checksums.read_text(encoding="utf-8").splitlines() if checksums.is_file() else []
        entry = f"{metadata['sha256']}  {release.name}"
        if not any(line.strip() == entry for line in lines):
            lines.append(entry)
            checksums.write_text("\n".join(line for line in lines if line.strip()) + "\n", encoding="utf-8")

        status = {
            "status": "ROLLED_BACK",
            "buildId": metadata.get("buildId"),
            "rollbackSource": release.name,
            "updatedAt": utc_now().isoformat(),
            "liveRelease": {"latestApkSha256": compute_sha256(latest), "latestApkSize": latest.stat().st_size},
            "verified": True,
        }
        STATUS_PATH.write_text(json.dumps(status, indent=2), encoding="utf-8")
        print(f"[ROLLBACK][OK] restored {release.name} (SHA-256 {metadata['sha256']})")
        return 0

    # ------------------------------------------------------------------
    # Reports (observed facts only)
    # ------------------------------------------------------------------
    def generate_reports(self, status: str, failed: Optional[GateResult] = None) -> None:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        now = utc_now().isoformat()
        summary = {
            "appName": APP_NAME,
            "packageId": PACKAGE_ID,
            "buildId": self.build_id,
            "generatedAt": now,
            "overallStatus": status,
            "releaseReady": status == PASS,
            "failedGate": failed.to_dict() if failed else None,
            "gates": [g.to_dict() for g in self.gates],
            "artifact": self.apk_facts.get("sha256") and {
                "sha256": self.apk_facts.get("sha256"),
                "sizeBytes": self.apk_facts.get("sizeBytes"),
                "signerCertificateSha256": self.apk_facts.get("apksigner", {}).get("signerCertificateSha256"),
                "package": self.apk_facts.get("package"),
                "versionName": self.apk_facts.get("versionName"),
                "versionCode": self.apk_facts.get("versionCode"),
                "minSdk": self.apk_facts.get("minSdk"),
                "targetSdk": self.apk_facts.get("targetSdk"),
            } or None,
            "passwords": "[redacted]" and None,
            "toolchain": self.toolchain,
            "liveRelease": self.describe_live_release(),
            "notRun": [
                "Android instrumented UI journeys (no androidTest sources are present in the repository)",
                "Hosted (non-localhost) download and DNS behaviour",
            ] if status != PASS else [],
        }
        (REPORTS_DIR / "test-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

        css = (
            ":root{--ok:#0f7b3f;--bad:#b3261e;--blocked:#8a5a00;--muted:#5b6472}"
            "body{font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;margin:0;padding:2rem;color:#101418;background:#f6f7f9}"
            ".wrap{max-width:960px;margin:0 auto;background:#fff;border-radius:14px;padding:2rem;box-shadow:0 2px 10px rgba(16,20,24,.08)}"
            "table{width:100%;border-collapse:collapse;margin-top:1rem}th,td{padding:.55rem .7rem;border-bottom:1px solid #e4e7ec;text-align:left;vertical-align:top;font-size:.92rem}"
            "th{background:#f0f2f5}.pass{color:var(--ok);font-weight:600}.fail{color:var(--bad);font-weight:600}"
            ".blocked,.notrun{color:var(--blocked);font-weight:600}code{background:#eef1f4;padding:.1rem .3rem;border-radius:4px;word-break:break-all}"
            ".badge{display:inline-block;padding:.15rem .6rem;border-radius:999px;font-weight:700;font-size:.8rem}"
            ".badge.pass{background:#dff5e6}.badge.fail{background:#fde3e1}.badge.blocked,.badge.notrun{background:#fdf0d5}"
        )

        def page(title: str, body: str) -> str:
            return (
                f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>{title} — NexHaat QA</title>'
                f"<style>{css}</style></head><body><div class=\"wrap\"><h1>{title}</h1>"
                f'<p style="color:var(--muted)">Generated {now} · build <code>{self.build_id}</code> · '
                f"overall <span class=\"badge {'pass' if status == PASS else 'fail' if status == FAIL else 'blocked'}\">{status}</span></p>"
                f"{body}</div></body></html>"
            )

        def gate_table(ids: List[int]) -> str:
            rows = []
            for gate_id in ids:
                result = next((g for g in self.gates if g.gate_id == gate_id), None)
                if result is None:
                    rows.append(f"<tr><td>{gate_id}</td><td>not executed</td><td class='notrun'>NOT RUN</td><td>the pipeline stopped before this gate</td></tr>")
                else:
                    css_class = {"PASS": "pass", "FAIL": "fail", "BLOCKED": "blocked", "NOT RUN": "notrun"}[result.status]
                    rows.append(
                        f"<tr><td>{result.gate_id}</td><td>{result.name}</td>"
                        f"<td class='{css_class}'>{result.status}</td><td><code>{result.detail[:600]}</code></td></tr>"
                    )
            return "<table><tr><th>#</th><th>Gate</th><th>Result</th><th>Observed detail</th></tr>" + "".join(rows) + "</table>"

        artifact = self.apk_facts
        artifact_rows = "".join(
            f"<tr><td>{label}</td><td><code>{value if value not in (None, '') else 'unavailable'}</code></td></tr>"
            for label, value in [
                ("Package", artifact.get("package")),
                ("Version / code", f"{artifact.get('versionName')} / {artifact.get('versionCode')}"),
                ("Min / target SDK", f"{artifact.get('minSdk')} / {artifact.get('targetSdk')}"),
                ("Launcher activity", artifact.get("launcherActivity")),
                ("SHA-256", artifact.get("sha256")),
                ("Size", format_bytes(artifact["sizeBytes"]) if artifact.get("sizeBytes") else None),
                ("Signer certificate SHA-256", artifact.get("apksigner", {}).get("signerCertificateSha256")),
                ("Signature schemes", artifact.get("apksigner", {}).get("schemes")),
            ]
        )

        (REPORTS_DIR / "apk-release-report.html").write_text(page("APK Release Report", (
            "<h2>Gates</h2>" + gate_table([1, 2, 3, 4, 5, 6]) +
            "<h2>Validated artifact</h2>" +
            (f"<table><tr><th>Attribute</th><th>Observed value</th></tr>{artifact_rows}</table>" if artifact else
             "<p class='fail'>No APK reached validation in this run. No artifact was published.</p>") +
            "<h2>Live release state</h2><table><tr><th>Item</th><th>Value</th></tr>" +
            "".join(f"<tr><td>{key}</td><td><code>{value}</code></td></tr>" for key, value in self.describe_live_release().items()) +
            "</table>"
        )), encoding="utf-8")

        (REPORTS_DIR / "android-build-report.html").write_text(page("Android Build Report", (
            "<h2>Build configuration (source)</h2><table><tr><th>Item</th><th>Value</th></tr>" +
            "".join(f"<tr><td>{k}</td><td><code>{v}</code></td></tr>" for k, v in self.identity.items()) +
            f"<tr><td>Release signing configured</td><td><code>{self.toolchain.get('signingConfigured')}</code></td></tr>"
            f"<tr><td>JDK</td><td><code>{self.toolchain.get('javaVersion') or 'not found'}</code></td></tr>"
            f"<tr><td>Android SDK roots</td><td><code>{self.toolchain.get('androidSdkDirs') or 'not configured'}</code></td></tr>"
            "</table><h2>Release build gate</h2>" + gate_table([5])
        )), encoding="utf-8")

        (REPORTS_DIR / "android-ui-test-report.html").write_text(page("Android UI & Device Report", (
            "<p class='notrun'>No instrumented UI journey results are recorded. The repository contains no "
            "<code>androidTest</code> sources, so authentication, OTP, catalog, cart and checkout journeys are "
            "<strong>NOT RUN</strong> and are not claimed as verified.</p>"
            "<h2>Device installation and launch</h2>" + gate_table([6])
        )), encoding="utf-8")

        (REPORTS_DIR / "api-test-report.html").write_text(page("API Integration Report", (
            "<h2>Marketplace API suite</h2>" + gate_table([3]) +
            "<p style='color:var(--muted)'>Only the executed <code>node:test</code> suite is reported. No endpoint "
            "pass list is hard-coded.</p>"
        )), encoding="utf-8")

        (REPORTS_DIR / "security-test-report.html").write_text(page("Security Test Report",
                                                                     "<h2>Server security suite</h2>" + gate_table([2])), encoding="utf-8")

        (REPORTS_DIR / "website-test-report.html").write_text(page("Website & Distribution Report", (
            "<h2>TypeScript compilation and repository integrity</h2>" + gate_table([1, 4]) +
            "<h2>Published artifact consistency</h2><table><tr><th>Item</th><th>Observed</th></tr>" +
            "".join(f"<tr><td>{k}</td><td><code>{v}</code></td></tr>" for k, v in self.describe_live_release().items()) +
            "</table>"
        )), encoding="utf-8")

        (REPORTS_DIR / "performance-test-report.html").write_text(page("Timing Report", (
            "<p>Only measured timings are reported.</p><table><tr><th>Gate</th><th>Duration</th></tr>" +
            "".join(f"<tr><td>{g.name}</td><td>{g.duration:.2f}s</td></tr>" for g in self.gates) +
            "</table>"
        )), encoding="utf-8")
        self.log(f"reports written to {REPORTS_DIR.relative_to(ROOT)}/")

    # ------------------------------------------------------------------
    # Verification of the currently published release
    # ------------------------------------------------------------------
    def verify_published_release(self) -> int:
        latest = APK_DIR / "latest.apk"
        metadata = APK_DIR / "latest.json"
        print("=== Published release verification ===")
        if not latest.is_file():
            print(f"[{FAIL}] APK/latest.apk does not exist — no verified release is published")
            print(f"[{BLOCKED}] release status must stay BLOCKED")
            return 1
        report = APK_DIR / f".verify-published-{os.getpid()}.json"
        cmd = [sys.executable, str(VALIDATOR), "--apk", str(latest), "--allow-missing-install", "--json-out", str(report)]
        if metadata.is_file():
            cmd[3:3] = ["--metadata", str(metadata)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900, check=False)
        print(proc.stdout.strip()[-6000:])
        verdict = self._read_json(report)
        report.unlink(missing_ok=True)
        mirror = PUBLIC_DOWNLOADS_DIR / "nexhaat.apk"
        if mirror.is_file():
            same = compute_sha256(mirror) == compute_sha256(latest)
            print(f"[{PASS if same else FAIL}] public mirror identical to APK/latest.apk: {same}")
        else:
            print(f"[{FAIL}] public/downloads/nexhaat.apk is missing")
        print(f"VERDICT: {verdict.get('verdict', BLOCKED)}")
        return 0 if verdict.get("verdict") == PASS else 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="NexHaat fail-closed QA & APK release orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="run all gates but never publish")
    parser.add_argument("--force-fail", choices=[f"gate{i}" for i in range(1, 7)],
                        help="simulate a gate failure to exercise the fail rule")
    parser.add_argument("--rollback-to", metavar="RELEASE",
                        help="re-validate and restore an archived release (latest.apk, metadata and mirror)")
    parser.add_argument("--require-device-on-rollback", action="store_true",
                        help="also require an emulator/device installation before rolling back")
    parser.add_argument("--verify-release", action="store_true",
                        help="validate the currently published release and exit")
    parser.add_argument("--toolchain", action="store_true", help="print detected toolchain facts and exit")
    args = parser.parse_args(argv)

    if args.toolchain:
        print(json.dumps(toolchain_facts(), indent=2))
        return 0

    if args.rollback_to:
        return ReleaseOrchestrator.rollback_to(args.rollback_to, require_device=args.require_device_on_rollback)

    orchestrator = ReleaseOrchestrator(dry_run=args.dry_run, force_fail_gate=args.force_fail)

    if args.verify_release:
        return orchestrator.verify_published_release()

    all_passed = orchestrator.run_pipeline()
    if not all_passed:
        orchestrator.log("Pipeline BLOCKED. Live release untouched.", level="ERROR")
        return 1

    if args.dry_run:
        orchestrator.log("dry run: all gates passed, publication skipped")
        orchestrator.write_status(PASS)
        orchestrator.generate_reports(status=PASS)
        return 0

    try:
        orchestrator.promote_release()
    except Exception as exc:  # noqa: BLE001 - publication failure is a release failure
        orchestrator.log(f"publication failed: {exc}", level="ERROR")
        failed = GateResult(7, "Atomic publication", FAIL, 0.0, str(exc))
        orchestrator.on_failure(failed)
        return 1

    status, detail, facts = orchestrator.verify_publication()
    orchestrator.log(f"publication verification: {status} — {detail}")
    if status != PASS:
        previous = orchestrator.apk_facts.get("previousRelease")
        orchestrator.write_status(BLOCKED, GateResult(7, "Publication verification", status, 0.0, detail, facts))
        orchestrator.generate_reports(status=status)
        orchestrator.log("publication verification failed; the release is not releasable", level="ERROR")
        return 1

    orchestrator.write_status(PASS, extra={"publication": facts})
    orchestrator.generate_reports(status=PASS)
    orchestrator.log(">>> RELEASE READY: all six gates passed on the same artifact and it is served byte-identically")
    return 0


if __name__ == "__main__":
    sys.exit(main())
