#!/usr/bin/env python3
"""NexHaat strict Android APK validator.

This module exists because the previous release pipeline accepted an ordinary ZIP
file (plain-text manifest, zero-filled ``classes.dex``, fake ``CERT.RSA``) as a
valid APK. Only a real, built, signed APK must ever reach ``APK/latest.apk``.

The validator is deliberately dependency-free apart from the Android SDK's
``apksigner``/``adb``. It performs structural and cryptographic checks:

1. The artifact is a well-formed ZIP with no unsafe or duplicate entries.
2. ``AndroidManifest.xml`` exists and is a *binary* Android XML document.
3. The binary manifest parses, declares package ``com.nexhaat.app`` and a
   launcher activity.
4. Encoded version/SDK values match the release metadata.
5. ``resources.arsc`` is a real resource table, not filler bytes.
6. At least one ``classes*.dex`` exists with a valid header, correct checksum,
   correct SHA-1 signature and non-empty code/class tables.
7. A signature block is present (v1 and/or v2/v3 APK Signing Block).
8. ``apksigner verify`` cryptographically verifies the signature scheme(s) and
   yields a signer certificate.
9. The file's SHA-256 matches the expected checksum/metadata.
10. When requested, ``adb install`` accepts the APK and the launcher starts
    without an ``AndroidRuntime`` fatal exception.

Exit codes (consumed by ``scripts/nexhaat_qa_release_orchestrator.py``):

* ``0`` — PASS: every mandatory check was executed and succeeded.
* ``1`` — FAIL: at least one mandatory check failed.
* ``2`` — BLOCKED: a mandatory check could not be executed (missing tool,
  missing device, missing artifact). Verification was NOT established.

There is intentionally no code path that turns a placeholder into a PASS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

EXPECTED_PACKAGE = "com.nexhaat.app"
APK_MAGIC = b"PK\x03\x04"
DEX_MAGIC = b"dex\n"
APK_SIG_BLOCK_MAGIC = b"APK Sig Block 42"

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_BLOCKED = "BLOCKED"

# Android chunk types used by binary XML / resources.arsc.
CHUNK_STRING_POOL = 0x0001
CHUNK_TABLE = 0x0002
CHUNK_XML = 0x0003
CHUNK_XML_RESOURCE_MAP = 0x0180
CHUNK_XML_START_ELEMENT = 0x0102
CHUNK_XML_END_ELEMENT = 0x0103

# android: attribute resource ids, used when the string pool has no attribute name.
ATTR_VERSION_CODE = 0x0101021B
ATTR_VERSION_NAME = 0x0101021C
ATTR_MIN_SDK = 0x0101020C
ATTR_TARGET_SDK = 0x01010270

TYPE_REFERENCE = 0x01
TYPE_STRING = 0x03
TYPE_INT_DEC = 0x10
TYPE_INT_HEX = 0x11

# APK Signature Scheme block ids.
SIG_SCHEME_IDS = {
    0x7109871A: "v2",
    0xF05368C0: "v3",
    0x1B93AD61: "v3.1",
}


class ApkStructureError(Exception):
    """Raised when the container itself is not a parseable APK."""


@dataclass
class Check:
    name: str
    status: str
    detail: str

    def to_dict(self) -> Dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


@dataclass
class ValidationResult:
    apk_path: str = ""
    verdict: str = STATUS_BLOCKED
    checks: List[Check] = field(default_factory=list)
    facts: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""

    def add(self, name: str, status: str, detail: str) -> None:
        self.checks.append(Check(name, status, detail))

    def fail_count(self) -> int:
        return sum(1 for c in self.checks if c.status == STATUS_FAIL)

    def blocked_count(self) -> int:
        return sum(1 for c in self.checks if c.status == STATUS_BLOCKED)

    def finalize(self) -> "ValidationResult":
        if self.fail_count() > 0:
            self.verdict = STATUS_FAIL
            self.reason = "; ".join(f"{c.name}: {c.detail}" for c in self.checks if c.status == STATUS_FAIL)[:1200]
        elif self.blocked_count() > 0:
            self.verdict = STATUS_BLOCKED
            self.reason = "; ".join(f"{c.name}: {c.detail}" for c in self.checks if c.status == STATUS_BLOCKED)[:1200]
        else:
            self.verdict = STATUS_PASS
            self.reason = "All structural, signature, checksum and installation checks passed."
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "apkPath": self.apk_path,
            "verdict": self.verdict,
            "reason": self.reason,
            "checks": [c.to_dict() for c in self.checks],
            "facts": self.facts,
        }


# ---------------------------------------------------------------------------
# Android binary XML parsing
# ---------------------------------------------------------------------------


def _read_u16_string(data: bytes, pos: int) -> Tuple[str, int]:
    (length,) = struct.unpack_from("<H", data, pos)
    pos += 2
    if length & 0x8000:
        (low,) = struct.unpack_from("<H", data, pos)
        pos += 2
        length = ((length & 0x7FFF) << 16) | low
    raw = data[pos: pos + length * 2]
    pos += length * 2
    return raw.decode("utf-16-le", errors="replace"), pos


def _read_u8_string(data: bytes, pos: int) -> Tuple[str, int]:
    """UTF-8 pool strings carry a UTF-16 length then a byte length."""
    def _len(p: int) -> Tuple[int, int]:
        b = data[p]
        p += 1
        if b & 0x80:
            b = ((b & 0x7F) << 8) | data[p]
            p += 1
        return b, p

    _utf16_len, pos = _len(pos)
    byte_len, pos = _len(pos)
    raw = data[pos: pos + byte_len]
    pos += byte_len
    return raw.decode("utf-8", errors="replace"), pos


def parse_string_pool(data: bytes, offset: int) -> List[str]:
    typ, header_size, _size = struct.unpack_from("<HHI", data, offset)
    if typ != CHUNK_STRING_POOL:
        raise ApkStructureError(f"expected string pool chunk at {offset}, found type 0x{typ:04x}")
    (string_count, _style_count, flags, strings_start, _styles_start) = struct.unpack_from("<IIIII", data, offset + 8)
    utf8 = bool(flags & 0x100)
    offsets = struct.unpack_from(f"<{string_count}I", data, offset + header_size) if string_count else ()
    base = offset + strings_start
    strings: List[str] = []
    for item_offset in offsets:
        pos = base + item_offset
        try:
            text, _ = (_read_u8_string if utf8 else _read_u16_string)(data, pos)
        except (IndexError, struct.error):
            text = ""
        strings.append(text)
    return strings


def parse_axml(data: bytes) -> Dict[str, Any]:
    """Parse an Android binary XML document into a shallow element tree."""
    if len(data) < 8:
        raise ApkStructureError("binary manifest is shorter than its header")
    typ, header_size, chunk_size = struct.unpack_from("<HHI", data, 0)
    if typ != CHUNK_XML:
        raise ApkStructureError(f"not a binary XML document (chunk type 0x{typ:04x})")
    if header_size < 8 or chunk_size > len(data) or chunk_size < header_size:
        raise ApkStructureError("binary manifest declares an inconsistent chunk size")

    strings: List[str] = []
    resource_ids: List[int] = []
    root: Optional[Dict[str, Any]] = None
    stack: List[Dict[str, Any]] = []

    pos = header_size
    while pos + 8 <= chunk_size:
        c_type, c_header, c_size = struct.unpack_from("<HHI", data, pos)
        if c_size < 8 or pos + c_size > chunk_size:
            raise ApkStructureError(f"malformed chunk 0x{c_type:04x} at offset {pos}")
        if c_type == CHUNK_STRING_POOL:
            strings = parse_string_pool(data, pos)
        elif c_type == CHUNK_XML_RESOURCE_MAP:
            count = (c_size - c_header) // 4
            resource_ids = list(struct.unpack_from(f"<{count}I", data, pos + c_header)) if count else []
        elif c_type == CHUNK_XML_START_ELEMENT:
            # ResXMLTree_node = chunk header (8) + lineNumber (4) + comment (4);
            # ResXMLTree_attrExt then starts at pos + c_header.
            ext = pos + c_header
            (line,) = struct.unpack_from("<I", data, pos + 8)
            (_ns, name_idx) = struct.unpack_from("<II", data, ext)
            (attr_start, attr_size, attr_count, _id_idx, _class_idx, _style_idx) = struct.unpack_from("<HHHHHH", data, ext + 8)
            attrs: Dict[str, Any] = {}
            attr_base = ext + attr_start
            for i in range(attr_count):
                a_off = attr_base + i * attr_size
                if a_off + 20 > pos + c_size:
                    break
                (a_ns, a_name, a_raw) = struct.unpack_from("<III", data, a_off)
                (v_size, _res0, v_type, v_data) = struct.unpack_from("<HBBI", data, a_off + 12)
                name = strings[a_name] if a_name < len(strings) else ""
                if not name and a_name < len(resource_ids):
                    name = f"res:0x{resource_ids[a_name]:08x}"
                if v_type in (TYPE_STRING, TYPE_REFERENCE) and a_raw and a_raw < len(strings):
                    value: Any = strings[a_raw]
                elif v_type == TYPE_STRING and v_data < len(strings):
                    value = strings[v_data]
                elif v_type in (TYPE_INT_DEC, TYPE_INT_HEX):
                    value = int(v_data if v_type == TYPE_INT_DEC else v_data)
                else:
                    value = v_data
                if name:
                    attrs[name] = value
                if a_name < len(resource_ids):
                    attrs[f"res:0x{resource_ids[a_name]:08x}"] = value
            element = {
                "name": strings[name_idx] if name_idx < len(strings) else "",
                "attrs": attrs,
                "children": [],
                "line": line,
            }
            if stack:
                stack[-1]["children"].append(element)
            elif root is None:
                root = element
            stack.append(element)
        elif c_type == CHUNK_XML_END_ELEMENT:
            if stack:
                stack.pop()
        pos += c_size

    if root is None:
        raise ApkStructureError("binary manifest contains no elements")
    return {"root": root, "strings": strings, "resourceIds": resource_ids}


def _iter_elements(element: Dict[str, Any]):
    yield element
    for child in element["children"]:
        yield from _iter_elements(child)


def _attr(element: Dict[str, Any], name: str, res_id: int) -> Any:
    attrs = element["attrs"]
    if name in attrs:
        return attrs[name]
    return attrs.get(f"res:0x{res_id:08x}")


# ---------------------------------------------------------------------------
# APK container checks
# ---------------------------------------------------------------------------


def locate_signing_block(data: bytes) -> Optional[Dict[str, Any]]:
    """Return APK Signing Block facts, or ``None`` when the block is absent."""
    eocd = data.rfind(b"PK\x05\x06", max(0, len(data) - 65557))
    if eocd < 0:
        raise ApkStructureError("end-of-central-directory record not found")
    (cd_offset,) = struct.unpack_from("<I", data, eocd + 16)
    if cd_offset < 32 or cd_offset > len(data):
        raise ApkStructureError("central directory offset is outside the file")
    footer_start = cd_offset - 24
    if data[footer_start + 8: footer_start + 24] != APK_SIG_BLOCK_MAGIC:
        return None
    (block_size,) = struct.unpack_from("<Q", data, footer_start)
    block_start = cd_offset - block_size - 8
    if block_start < 0 or block_start >= footer_start:
        raise ApkStructureError("APK Signing Block declares an invalid size")
    (header_size,) = struct.unpack_from("<Q", data, block_start)
    if header_size != block_size:
        raise ApkStructureError(
            f"APK Signing Block header size {header_size} does not match footer size {block_size}"
        )
    schemes: List[str] = []
    pos = block_start + 8
    pair_limit = footer_start - 8
    while pos + 12 <= pair_limit:
        (pair_len,) = struct.unpack_from("<Q", data, pos)
        if pair_len < 4 or pos + 8 + pair_len > footer_start:
            raise ApkStructureError("APK Signing Block contains a malformed id-value pair")
        (pair_id,) = struct.unpack_from("<I", data, pos + 8)
        label = SIG_SCHEME_IDS.get(pair_id)
        if label:
            schemes.append(label)
        pos += 8 + pair_len
    return {"blockSize": block_size, "schemes": sorted(set(schemes))}


def validate_dex(name: str, data: bytes) -> Tuple[bool, str, Dict[str, Any]]:
    """Structurally validate a single DEX container."""
    facts: Dict[str, Any] = {"entry": name, "size": len(data)}
    if len(data) < 0x70:
        return False, f"{name}: shorter than the 112-byte DEX header", facts
    if not data.startswith(DEX_MAGIC):
        return False, f"{name}: missing 'dex\\n' magic", facts
    version = data[4:7].decode("ascii", errors="replace")
    if not re.fullmatch(r"\d{3}", version):
        return False, f"{name}: malformed DEX version {version!r}", facts
    facts["version"] = version
    (checksum, sig0, sig1, sig2, sig3, sig4, file_size, header_size, endian_tag) = struct.unpack_from(
        "<I5I3I", data, 8
    )
    facts.update({"declaredSize": file_size, "headerChecksum": checksum})
    if header_size != 0x70:
        return False, f"{name}: header_size {header_size} != 0x70", facts
    if endian_tag != 0x12345678:
        return False, f"{name}: unexpected endian tag 0x{endian_tag:08x}", facts
    if file_size == 0:
        return False, f"{name}: DEX header declares a zero-length file (placeholder)", facts
    if file_size != len(data):
        return False, f"{name}: DEX header declares {file_size} bytes but entry has {len(data)}", facts
    actual_checksum = zlib.adler32(data[12:]) & 0xFFFFFFFF
    if actual_checksum != checksum:
        return False, f"{name}: adler32 checksum mismatch (header {checksum:08x}, actual {actual_checksum:08x})", facts
    actual_sig = hashlib.sha1(data[32:]).digest()
    if actual_sig != bytes(struct.pack("<5I", sig0, sig1, sig2, sig3, sig4)):
        return False, f"{name}: SHA-1 signature mismatch", facts
    # DEX header layout: each id section has a *size* followed by an *offset*.
    # string_ids_size @56, method_ids_size @88, class_defs_size @96.
    (string_ids,) = struct.unpack_from("<I", data, 56)
    (method_ids,) = struct.unpack_from("<I", data, 88)
    (class_defs,) = struct.unpack_from("<I", data, 96)
    facts.update({"methodIds": method_ids, "classDefs": class_defs, "stringIds": string_ids})
    if class_defs == 0 and method_ids == 0:
        return False, f"{name}: DEX declares no classes and no methods (placeholder)", facts
    return True, f"{name}: valid DEX v{version}, {class_defs} classes, {method_ids} methods", facts


def verify_with_apksigner(apksigner: Path, apk: Path, min_sdk: Optional[int]) -> Tuple[str, Dict[str, Any], str]:
    """Run apksigner. Returns (status, facts, detail)."""
    cmd = [str(apksigner), "verify", "--verbose", "--print-certs"]
    if min_sdk:
        cmd += ["--min-sdk-version", str(min_sdk)]
    cmd.append(str(apk))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False)
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - environment specific
        return STATUS_BLOCKED, {}, f"apksigner could not be executed: {exc}"
    output = f"{proc.stdout}\n{proc.stderr}".strip()
    facts: Dict[str, Any] = {"exitCode": proc.returncode, "output": output[-4000:]}
    if proc.returncode != 0:
        return STATUS_FAIL, facts, f"apksigner rejected the signature:\n{output[-1500:]}"
    if not re.search(r"^Verifies$", output, re.MULTILINE):
        return STATUS_FAIL, facts, "apksigner did not report 'Verifies'"

    schemes = {
        "v1": bool(re.search(r"v1 scheme \(JAR signing\):\s*true", output, re.IGNORECASE)),
        "v2": bool(re.search(r"v2 scheme \(APK Signature Scheme v2\):\s*true", output, re.IGNORECASE)),
        "v3": bool(re.search(r"v3 scheme \(APK Signature Scheme v3\):\s*true", output, re.IGNORECASE)),
    }
    facts["schemes"] = schemes
    if not (schemes["v2"] or schemes["v3"] or schemes["v1"]):
        return STATUS_FAIL, facts, "apksigner verified no signing scheme"

    dn = re.search(r"Signer #1 certificate DN:\s*(.+)", output)
    digest = re.search(r"Signer #1 certificate SHA-256 digest:\s*([0-9a-fA-F]+)", output)
    if digest:
        facts["signerCertificateSha256"] = digest.group(1).lower()
    if dn:
        facts["signerCertificateDn"] = dn.group(1).strip()
    if not digest:
        return STATUS_FAIL, facts, "apksigner returned no signer certificate digest"
    return STATUS_PASS, facts, (
        f"apksigner verified signature ({', '.join(k for k, v in schemes.items() if v)}); "
        f"certificate SHA-256 {facts['signerCertificateSha256'][:16]}..."
    )


def find_tool(name: str, explicit: Optional[str] = None, extra_dirs: Optional[List[Path]] = None) -> Optional[Path]:
    candidates: List[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    env_value = os.environ.get(name.upper())
    if env_value:
        candidates.append(Path(env_value))
    on_path = shutil.which(name)
    if on_path:
        candidates.append(Path(on_path))
    for directory in extra_dirs or []:
        for suffix in ("", ".bat", ".exe", ".cmd"):
            candidates.append(directory / f"{name}{suffix}")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def sdk_build_tool_dirs() -> List[Path]:
    dirs: List[Path] = []
    for var in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
        value = os.environ.get(var, "").strip()
        if not value or not Path(value).is_dir():
            continue
        build_tools = Path(value) / "build-tools"
        if build_tools.is_dir():
            for child in sorted(build_tools.iterdir(), reverse=True):
                if child.is_dir():
                    dirs.append(child)
        platform_tools = Path(value) / "platform-tools"
        if platform_tools.is_dir():
            dirs.append(platform_tools)
    return dirs


def device_install_and_launch(
    apk: Path, package: str, launcher: str, serial: Optional[str]
) -> Tuple[str, Dict[str, Any], str]:
    adb = find_tool("adb", extra_dirs=[d for d in sdk_build_tool_dirs() if d.name == "platform-tools"])
    if adb is None:
        return STATUS_BLOCKED, {}, "adb is not installed; installation and launch were not verified"
    base = [str(adb)] + (["-s", serial] if serial else [])

    def run(cmd: List[str], timeout: int = 180) -> Tuple[int, str]:
        try:
            proc = subprocess.run(base + cmd, capture_output=True, text=True, timeout=timeout, check=False)
            return proc.returncode, f"{proc.stdout}\n{proc.stderr}".strip()
        except (OSError, subprocess.SubprocessError) as exc:
            return 1, str(exc)

    rc, devices = run(["devices"])
    if rc != 0 or len([line for line in devices.splitlines()[1:] if line.strip()]) == 0:
        return STATUS_BLOCKED, {"devices": devices}, "no Android device or emulator is attached"

    rc, out = run(["install", "-r", "-g", str(apk)], timeout=300)
    facts: Dict[str, Any] = {"install": out[-2000:]}
    if rc != 0 or "Success" not in out:
        return STATUS_FAIL, facts, f"adb install rejected the APK: {out[-800:]}"

    run(["shell", "logcat", "-c"])
    rc, out = run(["shell", "am", "start", "-W", "-n", f"{package}/{launcher}"])
    facts["launch"] = out[-2000:]
    if rc != 0 or "Error" in out:
        return STATUS_FAIL, facts, f"launcher activity did not start: {out[-800:]}"
    if "mActivityResumed" not in out and "LaunchState" not in out and "Status: ok" not in out:
        return STATUS_FAIL, facts, f"launcher start produced no activity confirmation: {out[-800:]}"

    run(["shell", "dumpsys", "window", "windows"], timeout=60)
    rc, pid = run(["shell", "pidof", package], timeout=60)
    facts["pid"] = pid.strip()
    if rc != 0 or not pid.strip():
        return STATUS_FAIL, facts, f"package {package} is not running after launch"

    rc, crash = run(["shell", "logcat", "-d", "-b", "crash", "-s", "AndroidRuntime:E"], timeout=90)
    facts["crashLog"] = crash[-2000:]
    if "FATAL EXCEPTION" in crash:
        return STATUS_FAIL, facts, f"AndroidRuntime fatal exception during startup:\n{crash[-1200:]}"
    return STATUS_PASS, facts, f"APK installed, {launcher} launched and stayed alive (pid {pid.strip()})"


# ---------------------------------------------------------------------------
# Main validation flow
# ---------------------------------------------------------------------------


def validate(
    apk_path: Path,
    metadata_path: Optional[Path] = None,
    expected_sha256: Optional[str] = None,
    expected_package: str = EXPECTED_PACKAGE,
    expected_version: Optional[str] = None,
    expected_version_code: Optional[int] = None,
    expected_min_sdk: Optional[int] = None,
    expected_target_sdk: Optional[int] = None,
    expected_signer_sha256: Optional[str] = None,
    apksigner_path: Optional[str] = None,
    install: bool = False,
    serial: Optional[str] = None,
    require_install: bool = True,
) -> ValidationResult:
    result = ValidationResult(apk_path=str(apk_path))
    apk_path = Path(apk_path)

    if not apk_path.is_file():
        result.add("Artifact", STATUS_FAIL, f"{apk_path} does not exist")
        return result.finalize()

    size = apk_path.stat().st_size
    result.facts["sizeBytes"] = size
    if size == 0:
        result.add("Artifact", STATUS_FAIL, "APK file is empty")
        return result.finalize()
    result.add("Artifact", STATUS_PASS, f"{size} bytes at {apk_path}")

    digest = hashlib.sha256()
    with open(apk_path, "rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    sha256 = digest.hexdigest()
    result.facts["sha256"] = sha256

    with open(apk_path, "rb") as handle:
        head = handle.read(4)
    if head != APK_MAGIC:
        result.add("ZIP container", STATUS_FAIL, f"missing local file header magic (found {head!r})")
        return result.finalize()

    if not zipfile.is_zipfile(apk_path):
        result.add("ZIP container", STATUS_FAIL, "file is not a readable ZIP archive")
        return result.finalize()

    try:
        archive = zipfile.ZipFile(apk_path, "r")
    except (zipfile.BadZipFile, OSError) as exc:
        result.add("ZIP container", STATUS_FAIL, f"ZIP archive could not be opened: {exc}")
        return result.finalize()

    with archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        result.facts["entryCount"] = len(names)
        duplicates = {name for name in names if names.count(name) > 1}
        unsafe = [name for name in names if name.startswith(("/", "\\")) or ".." in Path(name).parts]
        encrypted = [entry.filename for entry in entries if entry.flag_bits & 0x1]
        if duplicates:
            result.add("ZIP container", STATUS_FAIL, f"duplicate entries: {sorted(duplicates)[:5]}")
        elif unsafe:
            result.add("ZIP container", STATUS_FAIL, f"unsafe entry paths: {unsafe[:5]}")
        elif encrypted:
            result.add("ZIP container", STATUS_FAIL, f"encrypted entries are not allowed: {encrypted[:5]}")
        else:
            result.add("ZIP container", STATUS_PASS, f"{len(names)} entries, no duplicates, encrypted or unsafe paths")
        bad_crc = archive.testzip()
        if bad_crc:
            result.add("ZIP CRC", STATUS_FAIL, f"CRC failure in {bad_crc}")
        else:
            result.add("ZIP CRC", STATUS_PASS, "all entry CRCs match")

        # ---- AndroidManifest.xml -------------------------------------------------
        if "AndroidManifest.xml" not in names:
            result.add("Binary manifest", STATUS_FAIL, "AndroidManifest.xml is missing from the APK")
            return result.finalize()
        manifest_bytes = archive.read("AndroidManifest.xml")
        if manifest_bytes.lstrip()[:5] in (b"<?xml", b"<mani"):
            result.add(
                "Binary manifest",
                STATUS_FAIL,
                "AndroidManifest.xml is plain-text XML; a compiled binary AXML document is required",
            )
            return result.finalize()
        try:
            manifest = parse_axml(manifest_bytes)
        except ApkStructureError as exc:
            result.add("Binary manifest", STATUS_FAIL, f"binary manifest could not be parsed: {exc}")
            return result.finalize()

        root = manifest["root"]
        if root["name"] != "manifest":
            result.add("Binary manifest", STATUS_FAIL, f"root element is <{root['name']}>, expected <manifest>")
            return result.finalize()

        package_name = str(_attr(root, "package", 0x0101020B) or "")
        version_code = _attr(root, "versionCode", ATTR_VERSION_CODE)
        version_name = _attr(root, "versionName", ATTR_VERSION_NAME)
        uses_sdk = next((e for e in _iter_elements(root) if e["name"] == "uses-sdk"), None)
        min_sdk = _attr(uses_sdk, "minSdkVersion", ATTR_MIN_SDK) if uses_sdk else None
        target_sdk = _attr(uses_sdk, "targetSdkVersion", ATTR_TARGET_SDK) if uses_sdk else None
        result.facts.update(
            {
                "package": package_name,
                "versionName": version_name,
                "versionCode": version_code,
                "minSdk": min_sdk,
                "targetSdk": target_sdk,
            }
        )
        result.add(
            "Binary manifest",
            STATUS_PASS,
            f"binary AXML parses: package={package_name} version={version_name} ({version_code}) "
            f"sdk={min_sdk}->{target_sdk}",
        )

        if package_name != expected_package:
            result.add(
                "Package identity",
                STATUS_FAIL,
                f"package is {package_name!r}, expected {expected_package!r}",
            )
        else:
            result.add("Package identity", STATUS_PASS, f"package is {package_name}")

        # Launcher activity: <activity> containing MAIN action + LAUNCHER category.
        launcher: Optional[str] = None
        app_element = next((e for e in _iter_elements(root) if e["name"] == "application"), None)
        for activity in (app_element["children"] if app_element else []):
            if activity["name"] != "activity":
                continue
            filters = [c for c in activity["children"] if c["name"] == "intent-filter"]
            for intent_filter in filters:
                intents = [c for c in intent_filter["children"] if c["name"] in ("action", "category")]
                actions = {str(_attr(c, "name", 0x01010003)).lower() for c in intents if c["name"] == "action"}
                categories = {str(_attr(c, "name", 0x01010003)).lower() for c in intents if c["name"] == "category"}
                if "android.intent.action.main" in actions and "android.intent.category.launcher" in categories:
                    launcher = str(_attr(activity, "name", 0x01010003) or "")
                    break
            if launcher:
                break
        result.facts["launcherActivity"] = launcher
        if not launcher:
            result.add("Launcher activity", STATUS_FAIL, "no MAIN/LAUNCHER activity is declared")
        else:
            if launcher.startswith("."):
                launcher = f"{package_name}{launcher}"
            elif "." not in launcher:
                launcher = f"{package_name}.{launcher}"
            result.facts["launcherActivity"] = launcher
            result.add("Launcher activity", STATUS_PASS, launcher)

        # ---- resources.arsc ------------------------------------------------------
        if "resources.arsc" not in names:
            result.add("Resource table", STATUS_FAIL, "resources.arsc is missing")
        else:
            arsc = archive.read("resources.arsc")
            if len(arsc) < 12:
                result.add("Resource table", STATUS_FAIL, "resources.arsc is truncated")
            else:
                a_type, a_header, a_size = struct.unpack_from("<HHI", arsc, 0)
                if a_type != CHUNK_TABLE or a_header < 12 or a_size > len(arsc) or a_size < a_header:
                    result.add(
                        "Resource table",
                        STATUS_FAIL,
                        f"resources.arsc is not a valid resource table (type 0x{a_type:04x}, size {a_size}/{len(arsc)})",
                    )
                else:
                    result.add("Resource table", STATUS_PASS, f"valid resources.arsc ({a_size} bytes)")

        # ---- DEX -----------------------------------------------------------------
        dex_names = sorted(n for n in names if re.fullmatch(r"classes\d*\.dex", n))
        if not dex_names:
            result.add("DEX bytecode", STATUS_FAIL, "no classes*.dex entry exists")
        else:
            dex_facts: List[Dict[str, Any]] = []
            dex_failures: List[str] = []
            for name in dex_names:
                ok, detail, facts = validate_dex(name, archive.read(name))
                dex_facts.append(facts)
                if not ok:
                    dex_failures.append(detail)
            result.facts["dex"] = dex_facts
            if dex_failures:
                result.add("DEX bytecode", STATUS_FAIL, "; ".join(dex_failures)[:900])
            else:
                result.add("DEX bytecode", STATUS_PASS, f"{len(dex_names)} valid DEX container(s): {', '.join(dex_names)}")

    # ---- Signature structure -----------------------------------------------------
    raw = apk_path.read_bytes()
    try:
        signing_block = locate_signing_block(raw)
    except ApkStructureError as exc:
        result.add("Signature structure", STATUS_FAIL, f"signing block parse failed: {exc}")
        signing_block = None
    with zipfile.ZipFile(apk_path) as archive:
        names = archive.namelist()
    has_v1 = any(n.upper().startswith("META-INF/") and n.upper().endswith((".SF", ".RSA", ".DSA", ".EC"))
                 for n in names)
    result.facts["signingBlock"] = signing_block
    result.facts["v1Files"] = has_v1
    if not has_v1 and not signing_block:
        result.add(
            "Signature structure",
            STATUS_FAIL,
            "no JAR signature files and no APK Signing Block: the archive is unsigned",
        )
    else:
        schemes = ", ".join(signing_block["schemes"]) if signing_block and signing_block["schemes"] else "none"
        result.add(
            "Signature structure",
            STATUS_PASS,
            f"v1={has_v1}, signing block schemes={schemes or 'none'}",
        )

    # ---- Cryptographic signature verification -----------------------------------
    apksigner = find_tool("apksigner", apksigner_path, [d for d in sdk_build_tool_dirs() if d.name != "platform-tools"])
    min_sdk_value = result.facts.get("minSdk")
    if isinstance(min_sdk_value, int):
        min_sdk_int: Optional[int] = min_sdk_value
    else:
        min_sdk_int = expected_min_sdk
    if apksigner is None:
        result.add(
            "Signature verification",
            STATUS_BLOCKED,
            "apksigner is unavailable (set APKSIGNER or install Android build-tools); signature not verified",
        )
    else:
        status, sig_facts, detail = verify_with_apksigner(apksigner, apk_path, min_sdk_int)
        result.facts["apksigner"] = sig_facts
        result.add("Signature verification", status, detail)
        signer = sig_facts.get("signerCertificateSha256")
        if expected_signer_sha256 and signer and signer.lower() != expected_signer_sha256.lower():
            result.add(
                "Signer identity",
                STATUS_FAIL,
                f"signer certificate {signer[:16]}... does not match the pinned signer",
            )
        elif expected_signer_sha256 and not signer:
            result.add("Signer identity", STATUS_BLOCKED, "pinned signer could not be confirmed")

    # ---- Expected metadata -------------------------------------------------------
    expectations: List[Tuple[str, Any, Any]] = []
    if expected_version is not None:
        expectations.append(("versionName", expected_version, result.facts.get("versionName")))
    if expected_version_code is not None:
        expectations.append(("versionCode", expected_version_code, result.facts.get("versionCode")))
    if expected_min_sdk is not None:
        expectations.append(("minSdk", expected_min_sdk, result.facts.get("minSdk")))
    if expected_target_sdk is not None:
        expectations.append(("targetSdk", expected_target_sdk, result.facts.get("targetSdk")))
    if expectations:
        mismatches = [
            f"{label} APK={actual!r} expected={expected!r}"
            for label, expected, actual in expectations
            if actual != expected
        ]
        if mismatches:
            result.add("Build metadata", STATUS_FAIL, "; ".join(mismatches))
        else:
            result.add(
                "Build metadata",
                STATUS_PASS,
                ", ".join(f"{label}={expected}" for label, expected, _ in expectations),
            )

    if metadata_path is not None:
        metadata_check = compare_metadata(Path(metadata_path), result.facts)
        result.add(*metadata_check)

    if expected_sha256:
        if expected_sha256.strip().lower() != sha256:
            result.add(
                "Checksum",
                STATUS_FAIL,
                f"SHA-256 {sha256} does not match expected {expected_sha256.strip().lower()}",
            )
        else:
            result.add("Checksum", STATUS_PASS, f"SHA-256 matches expected value ({sha256[:16]}...)")
    else:
        result.add("Checksum", STATUS_PASS, f"SHA-256 computed: {sha256}")

    # ---- Installation / launch ---------------------------------------------------
    if install:
        package_name = result.facts.get("package")
        launcher_activity = result.facts.get("launcherActivity")
        if not package_name or not launcher_activity:
            result.add("Installation", STATUS_BLOCKED, "package/launcher unknown; installation not attempted")
        else:
            status, dev_facts, detail = device_install_and_launch(
                apk_path, str(package_name), str(launcher_activity), serial
            )
            result.facts["device"] = dev_facts
            result.add("Installation", status, detail)
    elif require_install:
        result.add(
            "Installation",
            STATUS_BLOCKED,
            "installation verification was required but not requested (see --install)",
        )

    return result.finalize()


def compare_metadata(metadata_path: Path, facts: Dict[str, Any]) -> Tuple[str, str, str]:
    """Cross-check release metadata against the parsed APK."""
    if not metadata_path.is_file():
        return "Metadata", STATUS_FAIL, f"release metadata {metadata_path} is missing"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return "Metadata", STATUS_FAIL, f"release metadata is not valid JSON: {exc}"

    problems: List[str] = []
    comparisons = {
        "packageId": facts.get("package"),
        "version": facts.get("versionName"),
        "versionCode": facts.get("versionCode"),
        "minSdk": facts.get("minSdk"),
        "targetSdk": facts.get("targetSdk"),
        "sha256": facts.get("sha256"),
        "sizeBytes": facts.get("sizeBytes"),
    }
    for key, actual in comparisons.items():
        if key not in metadata:
            problems.append(f"metadata has no {key}")
            continue
        if metadata[key] != actual:
            problems.append(f"{key}: metadata={metadata[key]!r} apk={actual!r}")

    if metadata.get("verified") is True and problems:
        problems.append("metadata claims verified=true while the APK does not match")
    if problems:
        return "Metadata", STATUS_FAIL, "; ".join(problems)[:900]
    return "Metadata", STATUS_PASS, f"metadata {metadata_path.name} matches the APK"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Strict NexHaat APK validator")
    parser.add_argument("--apk", required=True, type=Path)
    parser.add_argument("--metadata", type=Path, default=None)
    parser.add_argument("--expected-sha256", default=None)
    parser.add_argument("--expected-package", default=EXPECTED_PACKAGE)
    parser.add_argument("--expected-version", default=None)
    parser.add_argument("--expected-version-code", type=int, default=None)
    parser.add_argument("--expected-min-sdk", type=int, default=None)
    parser.add_argument("--expected-target-sdk", type=int, default=None)
    parser.add_argument("--expected-signer-sha256", default=None)
    parser.add_argument("--apksigner", default=None)
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--allow-missing-install", action="store_true",
                        help="do not require installation verification (never use for a release)")
    parser.add_argument("--serial", default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    result = validate(
        apk_path=args.apk,
        metadata_path=args.metadata,
        expected_sha256=args.expected_sha256,
        expected_package=args.expected_package,
        expected_version=args.expected_version,
        expected_version_code=args.expected_version_code,
        expected_min_sdk=args.expected_min_sdk,
        expected_target_sdk=args.expected_target_sdk,
        expected_signer_sha256=args.expected_signer_sha256,
        apksigner_path=args.apksigner,
        install=args.install,
        serial=args.serial,
        require_install=not args.allow_missing_install,
    )

    width = max((len(c.name) for c in result.checks), default=10)
    for check in result.checks:
        print(f"[{check.status:<7}] {check.name.ljust(width)}  {check.detail}")
    print()
    print(f"VERDICT: {result.verdict} — {result.reason}")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")

    return {STATUS_PASS: 0, STATUS_FAIL: 1, STATUS_BLOCKED: 2}[result.verdict]


if __name__ == "__main__":
    sys.exit(main())
