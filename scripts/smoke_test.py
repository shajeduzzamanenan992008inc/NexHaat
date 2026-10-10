"""Read-only post-deployment smoke check for a public NexHaat site.

Checks liveness, database readiness, homepage delivery, and security headers.
It performs GET requests only and never submits forms or makes purchases.
"""
from __future__ import annotations

import argparse
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _fetch(opener, url: str, timeout: float):
    request = Request(url, headers={"User-Agent": "NexHaat-Deployment-SmokeTest/1.0", "Accept": "text/html,application/json"})
    try:
        response = opener.open(request, timeout=timeout)
        with response:
            return response.status, response.headers
    except HTTPError as error:
        return error.code, error.headers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Canonical site URL, e.g. https://shop.example.com")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--allow-http-local", action="store_true", help="Allow HTTP only for localhost smoke tests")
    args = parser.parse_args()

    parsed = urlsplit(args.base_url.strip())
    host = (parsed.hostname or "").lower()
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    if (
        parsed.scheme not in {"https", "http"}
        or not parsed.hostname
        or parsed.username or parsed.password
        or parsed.query or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        print("ERROR: --base-url must be a clean origin URL without credentials, path, query, or fragment.", file=sys.stderr)
        return 2
    if parsed.scheme != "https" and not (args.allow_http_local and host in local_hosts):
        print("ERROR: public smoke checks require HTTPS. HTTP is allowed only for localhost with --allow-http-local.", file=sys.stderr)
        return 2
    if args.timeout <= 0 or args.timeout > 120:
        print("ERROR: timeout must be between 0 and 120 seconds.", file=sys.stderr)
        return 2

    base = urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")
    opener = build_opener(NoRedirect())
    failures = 0
    homepage_headers = None
    for path in ("/health/live", "/health/ready", "/"):
        try:
            status, headers = _fetch(opener, base + path, args.timeout)
        except (URLError, TimeoutError, OSError) as error:
            print(f"FAIL {path}: request failed ({type(error).__name__})")
            failures += 1
            continue
        print(f"{'PASS' if status == 200 else 'FAIL'} {path}: HTTP {status}")
        if status != 200:
            failures += 1
        if path == "/":
            homepage_headers = {key.lower(): value for key, value in headers.items()}

    if homepage_headers is not None:
        expected = {
            "x-content-type-options": "nosniff",
            "x-frame-options": "DENY",
        }
        if parsed.scheme == "https":
            expected["strict-transport-security"] = "max-age=31536000; includeSubDomains"
        for name, expected_value in expected.items():
            actual = homepage_headers.get(name, "")
            passed = actual.lower() == expected_value.lower()
            print(f"{'PASS' if passed else 'FAIL'} security header {name}")
            if not passed:
                failures += 1
        if not homepage_headers.get("content-security-policy"):
            print("FAIL security header content-security-policy")
            failures += 1
        else:
            print("PASS security header content-security-policy")

    if failures:
        print(f"Smoke test FAILED: {failures} check(s) did not pass.", file=sys.stderr)
        return 1
    print("Smoke test PASSED. This is a basic HTTP readiness check, not a full security or payment audit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
