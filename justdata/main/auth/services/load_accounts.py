"""
Load-test accounts for spec 10, and their removal (the first spec 09 pass).

Twenty tester accounts, jd-load-01@example.org to jd-load-20@example.org,
each tagged three ways so they can be found and removed in one pass:
- the Firebase custom claim load_account: true;
- loadAccount: true on the Firestore users record;
- the address pattern (and, in HubSpot, the "JustData load accounts" list).

Jad imports the HubSpot contacts first: justdata_tester_authorized ticked,
set as non-marketing, on that list. create() then makes the Firebase
password accounts with a verified email (an admin vouches for an address no
one reads), and the first sign-in admits each one as tester through the
normal HubSpot check.

Both operations are dry runs unless apply=True. The scripts in scripts/
are thin wrappers: create_load_accounts.py and remove_load_accounts.py.
"""

import json
import os
import re
import secrets
from datetime import datetime, timezone
from urllib.parse import quote

LOAD_PREFIX = "jd-load-"
LOAD_DOMAIN = "example.org"
LOAD_COUNT = 20
CLAIM = "load_account"
LOAD_ADDRESS_RE = re.compile(rf"^{re.escape(LOAD_PREFIX)}\d{{2}}@{re.escape(LOAD_DOMAIN)}$")
PASSWORD_FILE = os.path.expanduser("~/.justdata-load-accounts.json")

HUBSPOT_CONTACT = "https://api.hubapi.com/crm/v3/objects/contacts/{}"
HUBSPOT_PROPERTIES = "justdata_tester_authorized,hs_marketable_status"
TOKEN_ENV = "HUBSPOT_ACCESS_TOKEN"


def load_addresses(count: int = LOAD_COUNT) -> list:
    return [f"{LOAD_PREFIX}{n:02d}@{LOAD_DOMAIN}" for n in range(1, count + 1)]


def is_load_address(email) -> bool:
    return bool(email) and bool(LOAD_ADDRESS_RE.match(email.lower()))


# ---------------------------------------------------------------------------
# HubSpot (read, and archive on removal)
# ---------------------------------------------------------------------------

def _hubspot_headers():
    token = os.getenv(TOKEN_ENV)
    return {"Authorization": f"Bearer {token}"} if token else None


def hubspot_contact(email, http=None) -> dict:
    """{'exists', 'id', 'ticked', 'marketable'} for one address, or
    {'error': ...} when HubSpot can't be read."""
    import httpx
    http = http or httpx
    headers = _hubspot_headers()
    if not headers:
        return {"error": f"{TOKEN_ENV} not set"}
    try:
        resp = http.get(HUBSPOT_CONTACT.format(quote(email, safe="")), headers=headers, timeout=10,
                        params={"idProperty": "email", "properties": HUBSPOT_PROPERTIES})
    except Exception as e:
        return {"error": f"HubSpot unreachable: {type(e).__name__}"}
    if resp.status_code == 404:
        return {"exists": False}
    if resp.status_code != 200:
        return {"error": f"HubSpot answered {resp.status_code}"}
    body = resp.json()
    props = body.get("properties") or {}
    return {
        "exists": True,
        "id": body.get("id"),
        "ticked": str(props.get("justdata_tester_authorized", "")).lower() == "true",
        # Marketing contact status: only an explicit "false" counts as
        # non-marketing; blank or anything else is treated as marketing
        "marketable": str(props.get("hs_marketable_status", "")).lower() != "false",
    }


def _hubspot_ready(contact) -> str:
    """'' when the contact is ready for a load account, else the reason."""
    if "error" in contact:
        return contact["error"]
    if not contact.get("exists"):
        return "no HubSpot contact"
    if not contact.get("ticked"):
        return "tester box not ticked"
    if contact.get("marketable"):
        return "still a marketing contact"
    return ""


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def _firebase_user(auth, email):
    try:
        return auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        return None


def create(auth, db, addresses=None, apply=False, password_file=PASSWORD_FILE,
           lookup=hubspot_contact, require_hubspot=True, out=print) -> int:
    """Create the Firebase side of each load account. Returns the number of
    addresses that could not be handled (0 is success)."""
    addresses = addresses or load_addresses()
    problems = 0
    passwords = {}
    for email in addresses:
        if not is_load_address(email):
            out(f"{email}: refused, not a load address")
            problems += 1
            continue
        existing = _firebase_user(auth, email)
        if existing is not None:
            if (existing.custom_claims or {}).get(CLAIM):
                out(f"{email}: already a load account (uid {existing.uid}), skipped")
            else:
                out(f"{email}: a Firebase account exists without the load tag; refused")
                problems += 1
            continue
        reason = _hubspot_ready(lookup(email)) if require_hubspot else ""
        if reason:
            out(f"{email}: not ready, {reason}")
            problems += 1
            continue
        if not apply:
            out(f"{email}: would create a verified password account, tag it and write its user record")
            continue
        password = secrets.token_urlsafe(24)
        number = email[len(LOAD_PREFIX):len(LOAD_PREFIX) + 2]
        user = auth.create_user(email=email, password=password, email_verified=True,
                                display_name=f"JustData load {number}")
        auth.set_custom_user_claims(user.uid, {CLAIM: True})
        db.collection("users").document(user.uid).set({
            "uid": user.uid, "email": email, "displayName": f"JustData load {number}",
            "userType": "public_registered", "authProvider": "password",
            "emailVerified": True, "loadAccount": True,
            "createdAt": datetime.now(timezone.utc), "loginCount": 0,
        })
        passwords[email] = password
        out(f"{email}: created (uid {user.uid})")
    if passwords:
        _save_passwords(password_file, passwords)
        out(f"Passwords for {len(passwords)} account(s) saved to {password_file} (mode 600)")
    return problems


def _save_passwords(path, new):
    existing = {}
    if os.path.exists(path):
        with open(path) as f:
            existing = json.load(f)
    existing.update(new)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(existing, f, indent=2)
    os.chmod(path, 0o600)


# ---------------------------------------------------------------------------
# Find and remove
# ---------------------------------------------------------------------------

def find_load_accounts(auth) -> list:
    """Firebase users carrying the load claim AND a load address. Both tags
    are required, so a stray claim can't put a real account in scope."""
    found = []
    page = auth.list_users()
    while page:
        for user in page.users:
            if (user.custom_claims or {}).get(CLAIM) and is_load_address(user.email):
                found.append(user)
        page = page.get_next_page()
    return found


def remove(auth, db, bq, project, apply=False, http=None, lookup=hubspot_contact, out=print) -> int:
    """Remove every load account: Firebase user, Firestore users record and
    activity rows, testing usage_log and signin_refusals rows, and the
    HubSpot contact. Returns the number of steps that failed."""
    users = find_load_accounts(auth)
    out(f"Found {len(users)} load account(s)")
    if not users:
        return 0
    uids = [u.uid for u in users]
    problems = 0

    for table in ("cache_testing.usage_log", "cache_testing.signin_refusals"):
        column = "user_id" if table.endswith("usage_log") else "uid"
        sql = f"DELETE FROM `{project}.{table}` WHERE {column} IN UNNEST(@uids)"
        if not apply:
            out(f"would run: {sql} ({len(uids)} uid(s))")
            continue
        try:
            bq.delete_rows(sql, uids)
            out(f"{table}: rows deleted")
        except Exception as e:
            # Rows streamed in the last ~30 minutes can't be deleted yet
            out(f"{table}: delete failed ({type(e).__name__}); rerun later")
            problems += 1

    for user in users:
        activity = list(db.collection("activity").where("uid", "==", user.uid).stream())
        contact = lookup(user.email)
        if not apply:
            out(f"{user.email}: would delete {len(activity)} activity row(s), the user record, "
                f"the Firebase account and {_hubspot_plan(contact)}")
            continue
        for doc in activity:
            doc.reference.delete()
        db.collection("users").document(user.uid).delete()
        auth.delete_user(user.uid)
        problems += _archive_contact(user.email, contact, http, out)
        out(f"{user.email}: removed")
    return problems


def _hubspot_plan(contact) -> str:
    if "error" in contact:
        return f"leave HubSpot alone ({contact['error']})"
    if not contact.get("exists"):
        return "no HubSpot contact"
    if contact.get("marketable"):
        return "NOT the HubSpot contact: it is a marketing contact, check it by hand"
    return f"archive HubSpot contact {contact['id']}"


def _archive_contact(email, contact, http, out) -> int:
    if "error" in contact or not contact.get("exists"):
        return 0
    if contact.get("marketable"):
        out(f"{email}: HubSpot contact is a marketing contact; left for a person to check")
        return 1
    import httpx
    http = http or httpx
    resp = http.delete(HUBSPOT_CONTACT.format(contact["id"]), headers=_hubspot_headers(), timeout=10)
    if resp.status_code not in (204, 404):
        out(f"{email}: HubSpot archive answered {resp.status_code}; remove it from the list by hand")
        return 1
    return 0


class BigQueryDeleter:
    """The one BigQuery call remove() makes, kept small so tests can fake it."""

    def __init__(self, client):
        self.client = client

    def delete_rows(self, sql, uids):
        from google.cloud.bigquery import ArrayQueryParameter, QueryJobConfig
        config = QueryJobConfig(query_parameters=[ArrayQueryParameter("uids", "STRING", uids)])
        self.client.query(sql, job_config=config).result()
