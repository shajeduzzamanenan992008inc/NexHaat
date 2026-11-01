# Phase 43 — Production Dependency Separation

**Date:** 2026-11-02  
**Repository:** `D:\FTP\NexHaat`  
**Branch / baseline HEAD:** `main` / `e1b8449c57cfdfb23352349d91e95158cff456f3`  
**Overall status:** **PARTIAL** — repository manifests and build/test workflows are separated and locally verified; Azure App Service's live build/runtime settings were not available for verification.

## Baseline and preservation

The branch and HEAD match the expected baseline. At Phase 43 start, the
worktree already contained changes in `.gitattributes`,
`.github/workflows/sbom-provenance.yml`, `.gitignore`, `AGENTS.md`,
`README.md`, and `docs/plans/nexhaat-master-plan.md`, plus an untracked
`LICENSE` and Phase 40–42 reports. Those existing changes were preserved;
the README and roadmap were updated narrowly without replacing their prior
content. No secret values or `.env` contents were read.

## Dependency source and classification

`requirements.txt` remains the runtime dependency manifest. It contains the
existing Flask extensions, database/migration packages, PostgreSQL driver,
AWS/image/PDF integrations, HTTP client, Gunicorn, and environment support.
No runtime dependency was added, upgraded, downgraded, or removed.

`pytest>=8.0,<9.0` was moved from the runtime manifest into the new
`requirements-dev.txt`, which includes `-r requirements.txt` so test and
development installs receive the runtime packages plus pytest. Ruff remains
installed separately by CI and the Azure pre-deployment verification job at
the existing `0.17.0` version. No Python build-only dependency was identified.
`pyproject.toml` continues to provide Python-version and tool configuration,
not a competing dependency source.

The GitHub CI matrix and Azure workflow's **GitHub build job** now install
`requirements-dev.txt`, retaining test dependencies for `pip check`, compile,
migration-head, and pytest checks. The build job packages the source tree; it
does not upload its virtual environment. The production artifact still
contains both requirements manifests, and no deployment target, trigger,
artifact path, secret reference, or production setting was changed.

The intended production manifest is now runtime-only `requirements.txt`.
However, the repository does not establish which remote build setting the
live Azure App Service currently uses. Azure/Oryx runtime installation and
the actual deployed app settings were not inspected, so production's
effective installed package set remains **NOT VERIFIED**. If the service is
configured to install `requirements-dev.txt` explicitly, pytest would still
be installed; confirm the hosted build configuration before claiming the
live service is runtime-only.

Dependabot continues to use its existing root pip ecosystem configuration;
its comment now reflects the runtime and development manifests. No update
policy, GitHub setting, or remote dependency operation was changed.

## CI and Python-version evidence

CI's Python matrix remains 3.11–3.14, and the Azure build job remains Python
3.14. Both cache against the runtime and development manifests. The existing
test, lint, migration, compile, permissions, trigger, and artifact steps are
retained. The exact workflow edits only switch dependency installation to the
development manifest and expand the pip cache dependency paths.

The Phase 42 report records full tests and dependency checks on Windows
CPython 3.11.17, 3.12.10, 3.13.16, 3.14.7, and 3.15.2 for the same effective
runtime-plus-pytest set before it was split. Phase 43 re-tested the new
manifest composition and complete test suite on CPython 3.14.7 only.
Therefore compatibility evidence for the other versions is inherited from
Phase 42's equivalent dependency set, not a fresh run of the new manifests.

| Python version | Resolver / install after split | Import/smoke | Tests after split | Result |
|---|---|---|---|---|
| 3.11.17 | NOT RETESTED; Phase 42 equivalent dependency set passed | Phase 42 PASS | Phase 42 PASS — 305 | **PARTIAL** — new manifest composition not rerun |
| 3.12.10 | NOT RETESTED; Phase 42 equivalent dependency set passed | Phase 42 PASS | Phase 42 PASS — 305 | **PARTIAL** — new manifest composition not rerun |
| 3.13.16 | NOT RETESTED; Phase 42 equivalent dependency set passed | Phase 42 PASS | Phase 42 PASS — 305 | **PARTIAL** — new manifest composition not rerun |
| 3.14.7 | PASS — runtime install then development manifest | PASS — runtime imports; pytest added by dev manifest | PASS — 305 passed | **PASS locally** |
| 3.15.2 | NOT RETESTED; Phase 42 equivalent dependency set passed | Phase 42 PASS | Phase 42 PASS — 305 | **PARTIAL** — new manifest composition not rerun |

These are Windows x64 local results. GitHub-hosted CI, Linux wheel selection,
and live Azure installation were not tested.

## README and license notice

`README.md` now documents the runtime/development manifest split, uses the
development manifest in local setup instructions, and links the root
`LICENSE`. The link describes the file accurately as a proprietary draft
notice, not an open-source license or general public permission grant, and
retains the document's legal-review caveat. The `LICENSE` file itself was not
modified.

## Validation evidence

The following checks ran in a disposable Windows CPython 3.14.7 virtual
environment, which was removed after validation:

| Check | Result |
|---|---|
| `python -m pip install -r requirements.txt` | **PASS** |
| Runtime import check and assertion that pytest is absent after runtime-only install | **PASS** |
| `python -m pip install -r requirements-dev.txt` | **PASS**; pytest installed while reusing runtime dependencies |
| `python -m pip check` | **PASS** — no broken requirements |
| Runtime dependency import smoke after development install | **PASS** |
| `python -m ruff check .` with Ruff 0.17.0 | **PASS** — all checks passed |
| `python -m compileall -q app migrations tests run.py wsgi.py` | **PASS** |
| `python -m flask --app run.py db heads` | **PASS** — `20261031_01 (head)` |
| `python -m pytest -q` | **PASS** — 305 passed in 342.96s |
| `python scripts\validate_repository_structure.py --fail-on-review` | **PASS** — 6/6 required docs, 190 registry paths, no missing imports/config, no source deletion/rename review |
| `pyproject.toml` TOML parse | **PASS** |
| `git diff --check` | **PASS** after all Phase 43 report and roadmap edits |
| Workflow YAML parser / actionlint | **NOT TESTED** — PyYAML, Ruby, and actionlint were unavailable; no workflow was remotely run |
| Live Azure/Oryx installed-package verification | **BLOCKED / NOT VERIFIED** — hosted settings and runtime access were not available |
| Fresh post-split Python 3.11, 3.12, 3.13, and 3.15 install/test runs | **NOT TESTED** — see inherited Phase 42 evidence above |

## Files changed in Phase 43

- `.github/NEXHAAT-GITHUB-SETUP.md`
- `.github/copilot-instructions.md`
- `.github/dependabot.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/main_nexhaat.yml`
- `README.md`
- `SETUP.md`
- `docs/architecture/PHASE43_PRODUCTION_DEPENDENCY_SEPARATION_REPORT.md`
- `docs/plans/nexhaat-master-plan.md`
- `pyproject.toml`
- `requirements.txt`
- `requirements-dev.txt` (new)

No application source, route, model, migration, integration, or feature was
changed. Phase 40–42 reports and all pre-existing worktree changes remain
preserved. No commit, push, merge, deployment, production restart/database
mutation, or GitHub setting change occurred.
