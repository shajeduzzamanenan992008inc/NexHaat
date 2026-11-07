#!/usr/bin/env python3
"""Regression tests for scripts/validate_apk.py.

These tests build disposable APK-shaped fixtures in a temporary directory. They
prove two things that the old pipeline got wrong:

1. A ZIP built from source files (plain-text manifest, zero-filled DEX, fake
   certificate) is rejected — it can never reach ``PASS``.
2. The validator never returns ``PASS`` unless the signature was
   cryptographically verified by ``apksigner`` and the APK was installed.

Run directly (``python tests/test_apk_validator.py``) or with pytest.
"""

from __future__ import annotations

import hashlib
import json
import struct
import sys
import tempfile
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_apk  # noqa: E402

PACKAGE = "com.nexhaat.app"

STRING_POOL_ENTRIES = [
    "package",
    "versionCode",
    "versionName",
    "minSdkVersion",
    "targetSdkVersion",
    "name",
    "android",
    PACKAGE,
    "1.0.0",
    "manifest",
    "uses-sdk",
    "application",
    "activity",
    "intent-filter",
    "action",
    "category",
    f"{PACKAGE}.MainActivity",
    "android.intent.action.MAIN",
    "android.intent.category.LAUNCHER",
]
RESOURCE_IDS = [0x0101020B, 0x0101021B, 0x0101021C, 0x0101020C, 0x01010270, 0x01010003]


def _string_pool(strings) -> bytes:
    encoded = []
    for text in strings:
        raw = text.encode("utf-16-le")
        encoded.append(struct.pack("<H", len(text)) + raw)
    header_size = 28
    offsets = []
    cursor = 0
    for item in encoded:
        offsets.append(cursor)
        cursor += len(item)
    strings_start = header_size + 4 * len(strings)
    body = b"".join(encoded)
    size = strings_start + len(body)
    chunk = struct.pack("<HHI", 0x0001, header_size, size)
    chunk += struct.pack("<IIIII", len(strings), 0, 0, strings_start, 0)
    chunk += b"".join(struct.pack("<I", offset) for offset in offsets)
    return chunk + body


def _attr(name_index: int, data_type: int, data: int) -> bytes:
    return struct.pack("<III", 0xFFFFFFFF, name_index, 0xFFFFFFFF) + struct.pack(
        "<HBBI", 8, 0, data_type, data
    )


def _start_element(name_index: int, attrs) -> bytes:
    header_size = 16
    attr_start = 20
    attr_size = 20
    payload = struct.pack("<II", 0xFFFFFFFF, name_index)  # ns, name
    payload += struct.pack("<HHHHHH", attr_start, attr_size, len(attrs), 0, 0, 0)
    payload += b"".join(attrs)
    size = header_size + len(payload)
    return struct.pack("<HHI", 0x0102, header_size, size) + struct.pack("<II", 1, 0xFFFFFFFF) + payload


def _end_element() -> bytes:
    return struct.pack("<HHI", 0x0103, 16, 24) + struct.pack("<II", 1, 0xFFFFFFFF) + struct.pack("<II", 0xFFFFFFFF, 9)


def build_binary_manifest(package: str = PACKAGE, version_code: int = 1,
                          version_name: str = "1.0.0", min_sdk: int = 24,
                          target_sdk: int = 36) -> bytes:
    """Assemble a real Android binary XML manifest."""
    strings = list(STRING_POOL_ENTRIES)
    if package != PACKAGE:
        strings[7] = package
    if version_name != "1.0.0":
        strings[8] = version_name

    resource_map = struct.pack("<HHI", 0x0180, 8, 8 + 4 * len(RESOURCE_IDS))
    resource_map += b"".join(struct.pack("<I", rid) for rid in RESOURCE_IDS)

    chunks = [_string_pool(strings), resource_map]
    chunks.append(_start_element(9, [  # <manifest>
        _attr(0, 0x03, 7),                       # package -> strings[7]
        _attr(1, 0x10, version_code),            # versionCode
        _attr(2, 0x03, 8),                       # versionName -> strings[8]
    ]))
    chunks.append(_start_element(10, [           # <uses-sdk>
        _attr(3, 0x10, min_sdk),
        _attr(4, 0x10, target_sdk),
    ]))
    chunks.append(_end_element())
    chunks.append(_start_element(11, []))        # <application>
    chunks.append(_start_element(12, [_attr(5, 0x03, 16)]))  # <activity android:name>
    chunks.append(_start_element(13, []))        # <intent-filter>
    chunks.append(_start_element(14, [_attr(5, 0x03, 17)]))
    chunks.append(_end_element())
    chunks.append(_start_element(15, [_attr(5, 0x03, 18)]))
    chunks.append(_end_element())
    chunks.append(_end_element())
    chunks.append(_end_element())
    chunks.append(_end_element())
    chunks.append(_end_element())

    body = b"".join(chunks)
    size = 8 + len(body)
    return struct.pack("<HHI", 0x0003, 8, size) + body


def build_dex(class_defs: int = 1, method_ids: int = 1, placeholder: bool = False) -> bytes:
    """Build a DEX container with a correct header, checksum and SHA-1."""
    payload = b"\x00" * 64
    total = 0x70 + len(payload)
    data = bytearray(total)
    data[0:8] = b"dex\n039\x00"
    struct.pack_into("<I", data, 32, 0 if placeholder else total)   # file_size
    struct.pack_into("<I", data, 36, 0x70)                          # header_size
    struct.pack_into("<I", data, 40, 0x12345678)                    # endian_tag
    struct.pack_into("<I", data, 56, 1)                             # string_ids_size
    struct.pack_into("<I", data, 64, 1)                             # type_ids_size
    struct.pack_into("<I", data, 88, 0 if placeholder else method_ids)
    struct.pack_into("<I", data, 96, 0 if placeholder else class_defs)
    data[0x70:] = payload
    if not placeholder:
        # The SHA-1 signature covers bytes[32:]; the adler32 checksum covers
        # bytes[12:] and therefore must be computed after the signature is set.
        data[12:32] = hashlib.sha1(bytes(data[32:])).digest()
        struct.pack_into("<I", data, 8, zlib.adler32(bytes(data[12:])) & 0xFFFFFFFF)
    return bytes(data)


def build_apk(path: Path, *, binary_manifest: bool = True, dex: bytes | None = None,
              include_signature: bool = False) -> Path:
    manifest = build_binary_manifest() if binary_manifest else (
        b'<?xml version="1.0" encoding="utf-8"?>\n<manifest package="com.nexhaat.app" />\n'
    )
    dex_bytes = dex if dex is not None else build_dex()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("AndroidManifest.xml", manifest)
        archive.writestr("resources.arsc", struct.pack("<HHII", 0x0002, 12, 20, 1) + b"\x00" * 8)
        archive.writestr("classes.dex", dex_bytes)
        if include_signature:
            archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\r\n\r\n")
            archive.writestr("META-INF/CERT.SF", "Signature-Version: 1.0\r\n\r\n")
            archive.writestr("META-INF/CERT.RSA", b"\x30\x82\x01\x0a" + b"\xff" * 256)
    return path


def _validate(path: Path, **kwargs):
    kwargs.setdefault("require_install", False)
    kwargs.setdefault("apksigner_path", str(path.parent / "absent-apksigner"))
    return validate_apk.validate(path, **kwargs)


def test_plain_text_manifest_zip_is_rejected(tmp_path: Path) -> None:
    apk = build_apk(tmp_path / "placeholder.apk", binary_manifest=False)
    result = _validate(apk)
    assert result.verdict == validate_apk.STATUS_FAIL, result.to_dict()
    assert any("plain-text XML" in c.detail for c in result.checks if c.status == "FAIL")


def test_zeroed_dex_placeholder_is_rejected(tmp_path: Path) -> None:
    apk = build_apk(tmp_path / "zerodex.apk", dex=build_dex(placeholder=True))
    result = _validate(apk)
    assert result.verdict == validate_apk.STATUS_FAIL
    assert any("DEX" in c.name and c.status == "FAIL" for c in result.checks), result.to_dict()


def test_synthetic_source_zip_from_old_orchestrator_is_rejected(tmp_path: Path) -> None:
    """Reproduce the old fallback archive shape: plain XML + 0x00 DEX + fake CERT.RSA."""
    apk = tmp_path / "old-fallback.apk"
    with zipfile.ZipFile(apk, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("AndroidManifest.xml", '<manifest package="com.nexhaat.app"/>')
        archive.writestr("assets/app-info.json", json.dumps({"packageId": PACKAGE}))
        archive.writestr("classes.dex", b"dex\n039\x00" + b"\x00" * 1024)
        archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
        archive.writestr("META-INF/CERT.SF", "Signature-Version: 1.0\n")
        archive.writestr("META-INF/CERT.RSA", b"\x30\x82\x01\x0a" + b"\xff" * 256)
    result = _validate(apk, expected_version="1.0.0")
    assert result.verdict == validate_apk.STATUS_FAIL, result.to_dict()
    assert result.facts.get("package") in (None, ""), result.facts


def test_binary_manifest_values_are_parsed(tmp_path: Path) -> None:
    apk = build_apk(tmp_path / "parsed.apk")
    result = _validate(apk)
    assert result.facts["package"] == PACKAGE
    assert result.facts["versionName"] == "1.0.0"
    assert result.facts["versionCode"] == 1
    assert result.facts["minSdk"] == 24
    assert result.facts["targetSdk"] == 36
    assert result.facts["launcherActivity"] == f"{PACKAGE}.MainActivity"


def test_wrong_package_fails(tmp_path: Path) -> None:
    apk = build_apk(tmp_path / "wrongpkg.apk")
    # Rewrite the manifest with a different package name.
    with zipfile.ZipFile(apk) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    bad_manifest = build_binary_manifest(package="com.example.other")
    with zipfile.ZipFile(apk, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, bad_manifest if name == "AndroidManifest.xml" else data)
    result = _validate(apk)
    assert result.verdict == validate_apk.STATUS_FAIL
    assert any(c.name == "Package identity" and c.status == "FAIL" for c in result.checks)


def test_unsigned_apk_fails_even_with_valid_structure(tmp_path: Path) -> None:
    apk = build_apk(tmp_path / "unsigned.apk")
    result = _validate(apk)
    assert result.verdict == validate_apk.STATUS_FAIL, result.to_dict()
    assert any("unsigned" in c.detail for c in result.checks if c.status == "FAIL")


def test_never_passes_without_cryptographic_verification(tmp_path: Path) -> None:
    """A structurally perfect APK with signature files must still not PASS here."""
    apk = build_apk(tmp_path / "structure-only.apk", include_signature=True)
    result = _validate(apk)
    assert result.verdict == validate_apk.STATUS_BLOCKED, result.to_dict()
    assert any(c.name == "Signature verification" and c.status == "BLOCKED" for c in result.checks)


def test_checksum_and_metadata_mismatch_fail(tmp_path: Path) -> None:
    apk = build_apk(tmp_path / "checksum.apk", include_signature=True)
    metadata = tmp_path / "latest.json"
    metadata.write_text(json.dumps({
        "packageId": PACKAGE,
        "version": "1.0.0",
        "versionCode": 1,
        "minSdk": 24,
        "targetSdk": 36,
        "sha256": "0" * 64,
        "sizeBytes": apk.stat().st_size,
        "verified": True,
    }), encoding="utf-8")
    result = _validate(apk, metadata_path=metadata, expected_sha256="0" * 64)
    assert result.verdict == validate_apk.STATUS_FAIL
    assert any(c.name == "Checksum" and c.status == "FAIL" for c in result.checks)
    assert any(c.name == "Metadata" and c.status == "FAIL" for c in result.checks)


def test_missing_artifact_fails(tmp_path: Path) -> None:
    result = _validate(tmp_path / "nope.apk")
    assert result.verdict == validate_apk.STATUS_FAIL
    assert result.checks[0].name == "Artifact"


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        for name, func in sorted(globals().items()):
            if not name.startswith("test_") or not callable(func):
                continue
            case_dir = Path(tmp) / name
            case_dir.mkdir(parents=True, exist_ok=True)
            try:
                func(case_dir)
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    print(f"\n{len([n for n in globals() if n.startswith('test_')]) - failures} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
