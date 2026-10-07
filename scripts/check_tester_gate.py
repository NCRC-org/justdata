#!/usr/bin/env python3
"""Live check of the access gate on a deployed JustData site.

Signs in with a real account, exchanges the Firebase ID token for an app
session the same way auth.js does (POST /api/auth/login), then requests a
fixed set of routes and checks each one is open or blocked as expected for
that account's role. It also runs the same routes signed out. One command,
both checks; exits nonzero on any failure.

Credentials come only from the environment (TEST_EMAIL, TEST_PASSWORD). They
are never printed, logged or written anywhere, and neither is the ID token.

    TEST_EMAIL=... TEST_PASSWORD=... python scripts/check_tester_gate.py
    python scripts/check_tester_gate.py --role member   # tester account
    python scripts/check_tester_gate.py --role non_member_org
    python scripts/check_tester_gate.py --role staff    # staff account

--role (public_registered, member, non_member_org, staff) changes only the expected table, so spec 05 can run it once per tier
with a different account each time. The account's actual role, as reported by
/api/auth/login, must match --role or the run fails.
"""

import argparse
import os
import re
import sys

import requests

DEFAULT_BASE_URL = "https://justdata-testing-854699313651.us-east1.run.app"
FIREBASE_SIGN_IN = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
# Only access_restricted.html renders this logo block.
RESTRICTED_MARKER = 'alt="NCRC - National Community Reinvestment Coalition"'
TIMEOUT = 30

# App roots use their trailing-slash form: Flask answers "/analytics" with a
# 308 to "/analytics/", which would test the redirect instead of the page.
ROUTES = ("/", "/about", "/contact", "/apps", "/lendsight/", "/status", "/branchmapper/", "/analytics/")

# Expected outcome per route on the testing deploy (JUSTDATA_ENV=testing):
# "open" = the real page; "blocked" = restricted page, redirect away, 401 or 403.
# Mirrors main/auth/access_overlay.py: signed out reaches only the exact public
# paths; public_registered also reaches /apps; tester roles also reach the apps; staff follow the
# matrix (Analytics is hidden from the plain staff role).
_PUBLIC = {"/": "open", "/about": "open", "/contact": "open", "/apps": "blocked",
           "/lendsight/": "blocked", "/status": "blocked", "/branchmapper/": "blocked",
           "/analytics/": "blocked"}
EXPECTED = {
    "signed_out": _PUBLIC,
    # A signed-in public_registered user may open /apps (all tools locked) on testing.
    "public_registered": {**_PUBLIC, "/apps": "open"},
    "member": {**_PUBLIC, "/apps": "open", "/lendsight/": "open"},
    # Most external testers will hold this role; same table as member on testing.
    "non_member_org": {**_PUBLIC, "/apps": "open", "/lendsight/": "open"},
    "staff": {**_PUBLIC, "/apps": "open", "/lendsight/": "open", "/status": "open",
              "/branchmapper/": "open"},
}


def classify(resp):
    """Return ("open" | "blocked", detail) for one un-followed response."""
    if resp.status_code in (301, 302, 303, 307, 308):
        return "blocked", f"{resp.status_code} -> {resp.headers.get('Location', '?')}"
    if resp.status_code in (401, 403):
        return "blocked", str(resp.status_code)
    if resp.status_code != 200:
        return "error", str(resp.status_code)
    if RESTRICTED_MARKER in resp.text:
        return "blocked", "200 restricted page"
    return "open", "200"


def web_api_key(base_url):
    """The public Firebase web API key, read from the deployed auth.js."""
    js = requests.get(f"{base_url}/static/js/auth.js", timeout=TIMEOUT)
    js.raise_for_status()
    match = re.search(r'apiKey:\s*"([^"]+)"', js.text)
    if not match:
        sys.exit("Could not find the Firebase apiKey in auth.js")
    return match.group(1)


def signed_in_session(base_url, email, password):
    """Sign in and return (requests.Session with the app cookie, user_type)."""
    key = web_api_key(base_url)
    fb = requests.post(f"{FIREBASE_SIGN_IN}?key={key}", timeout=TIMEOUT,
                       json={"email": email, "password": password, "returnSecureToken": True})
    if fb.status_code != 200:
        message = fb.json().get("error", {}).get("message", fb.status_code)
        sys.exit(f"Firebase sign-in failed: {message}")
    auth = fb.json()

    session = requests.Session()
    login = session.post(f"{base_url}/api/auth/login", timeout=TIMEOUT, json={
        "idToken": auth["idToken"],
        "user": {"uid": auth["localId"], "email": auth.get("email"), "displayName": None,
                 "photoURL": None, "organization": None, "firstName": None, "lastName": None},
    })
    body = login.json() if login.headers.get("Content-Type", "").startswith("application/json") else {}
    if login.status_code != 200 or not body.get("success"):
        sys.exit(f"App login failed: {login.status_code} {body.get('error', '')}".strip())
    return session, body.get("user_type")


def fetch(session, base_url, path):
    """GET without following redirects, except one redirect that only adds a
    trailing slash to the same path, which is followed once."""
    resp = session.get(base_url + path, timeout=TIMEOUT, allow_redirects=False)
    location = resp.headers.get("Location", "")
    if resp.status_code in (301, 308) and location.split("?")[0].endswith(path + "/"):
        resp = session.get(base_url + path + "/", timeout=TIMEOUT, allow_redirects=False)
    return resp


def run(label, session, base_url, expected):
    rows, failures = [], 0
    for path in ROUTES:
        outcome, detail = classify(fetch(session, base_url, path))
        ok = outcome == expected[path]
        failures += not ok
        rows.append((label, path, expected[path], outcome, detail, "PASS" if ok else "FAIL"))
    return rows, failures


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--role", choices=[r for r in EXPECTED if r != "signed_out"], default="public_registered",
                        help="role of the TEST_EMAIL account; selects the expected table")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    email, password = os.environ.get("TEST_EMAIL"), os.environ.get("TEST_PASSWORD")
    if not email or not password:
        sys.exit("TEST_EMAIL and TEST_PASSWORD must both be set in the environment.")

    rows, failures = run("signed out", requests.Session(), base_url, EXPECTED["signed_out"])

    session, user_type = signed_in_session(base_url, email, password)
    role_ok = user_type == args.role
    failures += not role_ok
    signed_rows, signed_failures = run(args.role, session, base_url, EXPECTED[args.role])
    rows += signed_rows
    failures += signed_failures

    print(f"Site: {base_url}")
    print(f"Account role reported by /api/auth/login: {user_type} "
          f"({'matches' if role_ok else 'DOES NOT MATCH'} --role {args.role})\n")
    widths = [max(len(str(r[i])) for r in rows + [("as", "route", "expected", "got", "detail", "result")])
              for i in range(6)]
    header = ("as", "route", "expected", "got", "detail", "result")
    for row in [header] + rows:
        print("  ".join(str(c).ljust(w) for c, w in zip(row, widths)))
    print(f"\n{'PASS' if failures == 0 else f'FAIL ({failures})'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
