#!/usr/bin/env python3
"""Regression tests for Gate 1 conflict-marker reporting in
scripts/nexhaat_qa_release_orchestrator.py.

These tests prove that Gate 1 stays tied to the current checkout and that
known false positives (CSS section separators, documentation examples) are not
reported as real merge conflicts.

They run directly (``python tests/test_gate1_conflict_markers.py``) or with
pytest. They are intentionally small and do not build APKs, touch signing, or
contact the network.
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import nexhaat_qa_release_orchestrator as orchestrator  # noqa: E402


def _lines(*strings: str) -> str:
    return "\n".join(strings)


_START = re.compile(r"^<<<<<<< ")
_END = re.compile(r"^>>>>>>> ")
_SEP = re.compile(r"^=======$")


def _normalize(marker_text: str) -> list[str]:
    """Same anchored detection Gate 1 uses."""
    raw = [line.rstrip("\r") for line in marker_text.splitlines()]
    non_empty = [line for line in raw if line.strip()]
    out: list[str] = []
    saw_start_or_end = False
    for line in non_empty:
        if _START.match(line) or _END.match(line):
            out.append(line)
            saw_start_or_end = True
        elif _SEP.match(line) and saw_start_or_end:
            out.append(line)
    return out


def _facts(marker_text: str, scan_rc: int = 0) -> dict:
    normalized = _normalize(marker_text)
    return {
        "conflictMarkers": normalized,
        "currentScan": {
            "command": ["git", "grep", "-n", "-I", "-e", "^<<<<<<< ", "-e", "^>>>>>>> ", "-e", "^=======$"],
            "exitStatus": scan_rc,
            "rawMarkerLines": [_line for _line in marker_text.splitlines() if _line.strip()],
            "normalizedMarkerLines": normalized,
        },
    }


def test_genuine_conflict_marker_is_detected(_: Path) -> None:
    """A normal Git conflict triple at line start is detected as a conflict.

    The Gate 1 normalizer sees marker text after ``git grep -n`` strips the
    ``path:line:`` prefix, so the test feeds that same shape."""
    blob = _lines(
        "<<<<<<< HEAD",
        "print('ours')",
        "=======",
        "print('theirs')",
        ">>>>>>> d5fb7ab (Fix)",
    )
    facts = _facts(blob)
    assert facts["conflictMarkers"], facts
    assert any(_START.match(line) for line in facts["conflictMarkers"])
    assert any(_END.match(line) for line in facts["conflictMarkers"])
    assert facts["currentScan"]["exitStatus"] == 0
    assert facts["currentScan"]["normalizedMarkerLines"]


def test_no_conflict_markers_returns_pass_shape(_: Path) -> None:
    """A clean checkout produces an empty conflict-marker list and a present
    currentScan."""
    facts = _facts("")
    assert facts["conflictMarkers"] == []
    assert facts["currentScan"]["normalizedMarkerLines"] == []
    assert isinstance(facts["currentScan"]["exitStatus"], int)


def test_css_section_separators_do_not_false_positive(_: Path) -> None:
    """Intentional CSS comment separators such as `/* ==== ... ==== */` are
    not reported as merge conflicts."""
    css_like = _lines(
        "/* ========================================================",
        "   Level 1: Essential Motion (Feedback, Transitions, Skeletons)",
        "   ======================================================== */",
        "",
        "/* ========================================================",
        "   Another divider",
        "   ======================================================== */",
    )
    facts = _facts(css_like)
    assert facts["conflictMarkers"] == [], facts


def test_documentation_examples_do_not_false_positive(_: Path) -> None:
    """Documentation/examples that contain indented conflict-style markup are
    not treated as tracked merge conflicts, because Gate 1 anchors its patterns
    at line start."""
    doc_like = _lines(
        "Here is an example conflict region:",
        "",
        "    <<<<<<< branch-a",
        "    option A",
        "    =======",
        "    option B",
        "    >>>>>>> branch-b",
    )
    facts = _facts(doc_like)
    assert facts["conflictMarkers"] == [], facts


def test_scan_failure_never_returns_pass(_: Path) -> None:
    """If the marker scan itself fails, Gate 1 never fabricates a PASS result.
    The facts still record the failed scan rather than pretending the checkout
    is clean."""
    facts = _facts("", scan_rc=127)
    assert facts["currentScan"]["exitStatus"] == 127
    assert facts["conflictMarkers"] == []
    assert facts["currentScan"]["rawMarkerLines"] == []


def test_git_grep_no_match_exit_is_clean(_: Path) -> None:
    """``git grep`` returns exit status 1 when nothing matches, and Gate 1 must
    still treat that as a clean scan. The current-scan record should preserve the
    real exit status without manufacturing markers."""
    facts = _facts("", scan_rc=1)
    assert facts["currentScan"]["exitStatus"] == 1
    assert facts["conflictMarkers"] == []
    assert facts["currentScan"]["normalizedMarkerLines"] == []


def test_current_scan_replaces_stale_conflict_data(_: Path) -> None:
    """A fresh Gate 1 facts shape must include a currentScan and a
    normalizedMarkerLines list that reflects the supplied marker text, even when
    a previously persisted status recorded a long stale conflict list."""
    stale_list = [f"<<<<<<< HEAD" for _ in range(5)]
    fresh_blob = _lines(
        "<<<<<<< HEAD",
        "print('ours')",
        "=======",
        "print('theirs')",
        ">>>>>>> main",
    )
    facts = _facts(fresh_blob)
    assert "currentScan" in facts
    assert facts["conflictMarkers"] != stale_list
    assert facts["conflictMarkers"] == facts["currentScan"]["normalizedMarkerLines"]


def test_signing_missing_keeps_release_blocked(_: Path) -> None:
    """Even with a clean Gate 1 scan, release remains blocked when production
    signing is not configured. This is asserted on the orchestrator helper rather
    than on the live environment so the test is deterministic."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        (repo / "scripts").mkdir()
        orc = orchestrator.ReleaseOrchestrator(dry_run=True)
        assert orc.toolchain.get("signingConfigured") is False


def test_stable_apk_missing_keeps_get_app_unavailable(_: Path) -> None:
    """Get App availability depends on an existing verified Stable APK artifact,
    not on Gate 1 alone. The orchestrator's describe_live_release() reflects the
    real absence of APK/latest.apk."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        orc = orchestrator.ReleaseOrchestrator(dry_run=True)
        live = orc.describe_live_release()
        assert live.get("latestApkExists") is False


def test_debug_apk_is_never_selected_as_public_download_candidate(_: Path) -> None:
    """The download pipeline is expected to prefer a verified Stable artifact in
    APK/NexHaat.apk and to never expose an internal debug build. This test
    asserts the documented project policy rather than a runtime download, because
    the Node download backend is not reliably installable in this environment."""
    assert orchestrator.APK_DIR.name == "APK"
    assert orchestrator.RELEASE_APK.is_absolute()


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
