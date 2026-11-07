#!/usr/bin/env python3
"""DEPRECATED — this script used to fabricate an APK-shaped ZIP archive.

It assembled ``public/downloads/nexhaat.apk`` from a source XML manifest, filler
``resources.arsc`` bytes, a zero-filled ``classes.dex`` and a metadata file, and
reported it as an APK. The archive was never installable: the manifest was not
compiled binary XML, the DEX had no classes, and there was no signing block.

It now refuses to run rather than producing a placeholder that could be mistaken
for a release artifact. Genuine packages come from the Gradle release build and
are validated by ``scripts/validate_apk.py`` inside
``scripts/nexhaat_qa_release_orchestrator.py``.
"""

from __future__ import annotations

import sys


def main() -> int:
    sys.stderr.write(
        "generate_apk_package.py has been disabled.\n\n"
        "It produced a non-installable ZIP and must not be used as a release artifact.\n"
        "Use the real pipeline instead:\n\n"
        "    python scripts/nexhaat_qa_release_orchestrator.py\n\n"
        "That pipeline builds :app:assembleRelease, validates the APK structurally and\n"
        "cryptographically, installs and launches it on a device/emulator, and only then\n"
        "publishes APK/latest.apk.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
