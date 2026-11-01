# Phase 42 — Cross-Version Dependency and CI Audit

**Date:** 2026-11-01  
**Repository:** `D:\FTP\NexHaat`  
**Branch / HEAD:** `main` / `e1b8449c57cfdfb23352349d91e95158cff456f3`

## Baseline and preservation

At Phase 42 start, the branch and HEAD matched the expected baseline. The
initial worktree contained pre-existing changes:

- `M docs/plans/nexhaat-master-plan.md`
- `?? docs/architecture/PHASE40_FINAL_CI_VERIFICATION_REPORT.md`
- `?? docs/architecture/PHASE41_GITIGNORE_REQUIREMENTS_AND_AISTUDIO_AUDIT_REPORT.md`

These reports and roadmap entries were preserved. No secret values or `.env`
contents were read or reported.

At final verification, additional worktree changes were present in
`.gitattributes`, `.gitignore`, `AGENTS.md`, and `README.md`, with an
untracked `LICENSE`. These paths were absent from the initial status and are
not attributed to Phase 42; they were not edited or reverted. Because
`README.md` and `.gitignore` changed concurrently, the compatibility and
ignore observations above describe the inspected baseline, not a review of
those later worktree edits.

## Dependency source of truth

`requirements.txt` is the authoritative dependency installation file used by
CI and the Azure build workflow. It contains runtime requirements and a
test-only `pytest>=8.0,<9.0` requirement. `pyproject.toml` holds
`requires-python` and Ruff/pytest configuration, but declares no project
dependencies. Dependabot monitors root pip dependencies in `/`; no
`requirements-dev.txt`, nested requirements manifest, Pipfile, Poetry/uv
lockfile, or Dockerfile was found. JavaScript has its own `package.json` and
`package-lock.json`; it is not a competing Python dependency source.

No Python dependency constraint conflict was found among declared package
requirements. Isolated installs on each tested interpreter resolved the
current allowed versions and installed the declared requirements successfully
on this Windows x64 environment, including Pillow and `psycopg[binary]`.
This does not independently verify Linux wheel selection on GitHub runners.

### Dependency/install-scope finding

The `pytest` line is labelled test-only, but it resides in the sole root
requirements file. Both CI and the Azure workflow install that file. The
Azure build workflow also runs pytest before packaging. Its artifact upload
includes the checkout (`.`) and does not exclude `tests/` or a dev
requirements file. Therefore the source currently does not implement the
comment's claim that production packaging excludes the tests directory, and
the shared install set includes pytest.

This is a confirmed manifest/workflow scope inconsistency, not a failing
resolver result. No package was removed or relocated: safely splitting
runtime/test dependencies would require coordinated CI and Azure build/
artifact review and verification of the deployed App Service build behavior.
That production-adjacent change is deferred rather than guessed in this
compatibility audit.

## Declared Python range and compatibility evidence

The repository expresses support in several ways:

- `pyproject.toml`: `requires-python = ">=3.11,<4.0"`.
- README: Python `3.11+`.
- CI test matrix: Python 3.11, 3.12, 3.13, and 3.14.
- `runtime.txt` and the Azure build: Python 3.14.

Thus metadata/README are open-ended through Python 3.x, while CI tests only
3.11–3.14 and the Azure runtime is pinned to 3.14. Python 3.15.2 was also
tested locally because that interpreter was available. Python 3.16 and later
are not available or covered by current CI. No support-range or CI-matrix
change was made.

For each exact interpreter below, a newly created temporary virtual
environment ran the CI dependency install sequence (pip upgrade, then
`pip install -r requirements.txt`), `pip check`, imports of the direct
application/test dependencies, `compileall`, Flask migration-head listing,
and `pytest -q`. All environments were removed after the checks. The
interpreter executables were CPython on Windows x64; these results are local,
not GitHub-hosted Ubuntu runner results.

| Python version | Resolver / install | Import/smoke | Tests | Result |
|---|---|---|---|---|
| 3.11.17 | PASS | PASS; compile and migration heads PASS | PASS — 305 passed (584.02s) | **PASS locally** |
| 3.12.10 | PASS | PASS; compile and migration heads PASS | PASS — 305 passed (365.28s) | **PASS locally** |
| 3.13.16 | PASS | PASS; compile and migration heads PASS | PASS — 305 passed (734.71s) | **PASS locally** |
| 3.14.7 | PASS | PASS; compile and migration heads PASS | PASS — 305 passed (420.91s) | **PASS locally** |
| 3.15.2 | PASS | PASS; compile and migration heads PASS | PASS — 305 passed (382.79s) | **PASS locally; not in CI matrix** |
| 3.16+ | NOT TESTED | NOT TESTED | NOT TESTED | **NOT TESTED** — not installed or in CI matrix |

Ruff 0.17.0 was installed in the disposable Python 3.14 environment and
`python -m ruff check .` passed. These checks show compatibility for the
resolved dependency set on the local Windows platform, not every future
release allowed by `<4.0` or Linux native-wheel compatibility.

## CI workflow audit

The CI Python test job runs on Ubuntu, tests 3.11–3.14, caches pip against
`requirements.txt`, upgrades pip, installs the root requirements, runs
`pip check`, byte-compiles sources, checks Flask migration heads, and runs
`pytest -q`. The lint job uses Python 3.14 and Ruff 0.17.0. Web checks use
Node 22 and the root npm lockfile. Jobs have timeouts, concurrency controls,
and read-only repository permissions.

The Azure deployment workflow uses Python 3.14 and the same requirements
file, runs Ruff, compile, migration-head and test checks before packaging.
For automatic deployment it gates on a successful CI push to `main` and
checks out that exact tested commit; manual dispatch requires an explicit
confirmation input. The `production` environment and OIDC permission are
scoped to the deploy job. No deployment was triggered.

CodeQL uses the existing Actions/Python/JavaScript-TypeScript matrix and
`security-extended`; it was not changed. GitHub configuration validation is
configured to use Ruby, which is not installed locally; no YAML parser or
actionlint was available.

The workflow action references are mixed: checkout, setup-python,
setup-node, Azure login/deploy, CodeQL, Syft, and attest use full commit SHAs
with version comments. The dependency-review action and artifact
upload/download actions use version tags. The repository GitHub Actions
instructions prefer verified full-SHA pins. No action ref was changed:
verifying and replacing action refs is a separate workflow supply-chain
change and no SHA was inferred or invented.

## SBOM follow-up

The Phase 39 archive fix remains present: the source tarball is written under
`RUNNER_TEMP`, outside the `.` tree being traversed; generated
`sbom.spdx.json` is excluded; archive content is copied to the workspace
after creation; existing exclusions remain; and artifact upload and optional
attestation paths remain intact.

The workflow generated `SHA256SUMS.txt` but previously checked only that the
manifest was nonempty. This phase added `sha256sum --check SHA256SUMS.txt`
immediately after generation. A disposable fixture confirmed the valid
manifest passes and a modified archive fails checksum verification. The
workflow shell block passed `bash -n`. This is local evidence only; no
remote SBOM run was inspected.

## CodeQL and remote CI

`gh --version` returned 2.103.3, but `gh auth status` reported no
authenticated GitHub host. Remote inspection stopped there. Latest remote CI,
SBOM/artifact, and CodeQL job conclusions/logs are **BLOCKED / NOT VERIFIED**.
Prior Phase 37/38 reports record the CodeQL upload error
`Code scanning is not enabled for this repository.` Current setting and
latest run remain unverified. An authorized repository administrator must
review **Settings → Security → Code security and analysis → Code scanning**
and enable/review Code Scanning while retaining the existing CodeQL workflow;
if policy-controlled, the organization/enterprise administrator must
authorize it. Then a new CodeQL run must pass all three language jobs.

## Checks, changes, and status

| Check | Result |
|---|---|
| Isolated `pip install -r requirements.txt` on CPython 3.11–3.15 | **PASS** on each listed Windows interpreter |
| `pip check`, dependency import smoke, `compileall`, Flask migration heads | **PASS** on CPython 3.11–3.15 |
| `pytest -q` | **PASS** — 305 tests on each CPython 3.11–3.15 |
| Ruff 0.17.0 / Python 3.14 | **PASS** — `python -m ruff check .` |
| SBOM workflow `bash -n` | **PASS** |
| Disposable checksum acceptance/tamper fixture | **PASS** |
| `python scripts\validate_repository_structure.py --fail-on-review` | **PASS** — required docs 6/6; 190 registry paths; no missing imports/config or source deletions/renames |
| `git diff --check` | **PASS** |
| TOML parse | **PASS** |
| YAML/workflow parser | **NOT AVAILABLE** |
| Live GitHub CI, SBOM, artifact, and CodeQL verification | **BLOCKED** — GitHub CLI unauthenticated |
| Python 3.16+ compatibility | **NOT TESTED** |
| Linux wheel selection and Azure runtime behavior | **NOT TESTED** |

Files changed in Phase 42:

- `.github/workflows/sbom-provenance.yml` — validate generated checksum
  manifest using `sha256sum --check`.
- `docs/architecture/PHASE42_CROSS_VERSION_DEPENDENCY_AND_CI_AUDIT_REPORT.md`
  — this report.
- `docs/plans/nexhaat-master-plan.md` — dated Phase 42 evidence entry.

The final worktree also retains the pre-existing Phase 40/41 report files and
the additional unrelated concurrent changes listed in the baseline section.
It is not clean; no user or concurrent changes were discarded.

`requirements.txt`, `pyproject.toml`, CI, deployment, and CodeQL workflows
were not otherwise changed. No feature, route, integration, or security
control was removed or weakened. No commit, push, merge, deployment, database
mutation, production restart, or GitHub setting change occurred.
