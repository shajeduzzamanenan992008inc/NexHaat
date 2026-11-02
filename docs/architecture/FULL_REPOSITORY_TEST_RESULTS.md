# Full Repository Test Results

**Date:** 2026-11-02
**Status:** PARTIAL

## Checks run

| Command / check | Result | Evidence / limits |
|---|---|---|
| `.venv\Scripts\python.exe -m pytest -q` (baseline, before API guard) | PASS | 305 passed in 583.57 seconds. |
| `.venv\Scripts\python.exe -m pytest -q tests\test_api_foundation.py` (after API guard) | PASS | 17 passed in 18.60 seconds. Includes the new non-object JSON regression test. |
| `.venv\Scripts\python.exe -m pytest -q` (after API guard) | PASS | 306 passed in 731.80 seconds. |
| `.venv\Scripts\python.exe -m ruff check .` (baseline) | PASS | Full repository lint completed before the API change. |
| `.venv\Scripts\python.exe -m ruff check app\api\__init__.py tests\test_api_foundation.py` | PASS | Changed Python files linted after the fix. |
| `npm test` | PASS | 8 Node tests passed, 0 failures. |
| `npm run lint` | PASS | TypeScript check (`tsc --noEmit`) passed. |
| `npm run build -- --outDir <unique temporary directory>` | PASS | Vite build passed; emitted large-chunk warnings. Temporary output was removed and existing `dist` was not overwritten. |
| `.venv\Scripts\python.exe -m pip check` | PASS | No broken requirements reported. |
| `.venv\Scripts\python.exe -m flask --app run.py db heads` | PASS | One Alembic head: `20261031_01`. |
| Python AST parse over tracked Python files | PASS | 162 files parsed; syntax validation only. |
| `npm ls --depth=0 --json` | PASS | Top-level dependency tree command exited successfully. |
| `npm audit --offline --omit=dev --json` | PARTIAL | No vulnerabilities in available offline advisory data; remote/current advisory status is not established. |
| `.venv\Scripts\python.exe scripts\validate_repository_structure.py --fail-on-review` | PASS | Final run passed; reported seven current worktree entries (two code/test files and five requested reports). |
| `git diff --check` | PASS | No whitespace errors after code change. |

## Not run

- Android Gradle unit tests/build: NOT TESTED. Tracked local Gradle/SDK state makes in-place test outputs a preservation concern; an isolated output/cache plan was not established.
- YAML parser or `actionlint`: NOT TESTED. No validator was installed; no tool was installed for this audit.
- Online dependency vulnerability scans: NOT TESTED. No authorized/current remote scan was available; offline npm data is not a substitute.
- Authenticated GitHub Actions/CodeQL and Azure log review: BLOCKED. GitHub CLI authentication was unavailable.
- Firebase emulator/rules tests and deployed-rule verification: NOT TESTED.
- Live payment, email, Azure, Firebase, or production health checks: NOT RUN.
