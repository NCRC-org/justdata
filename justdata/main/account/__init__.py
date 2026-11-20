"""/account, "Your account" (spec 14, phase 1).

Phase 1 builds sections 1 to 4 and 6, and section 5's statement. "Download my
data", "Remove from my history" and "Delete account" are phase 2, after spec
09 is approved. Nothing renders that doesn't work: a section or line whose
data isn't available is left out, not shown empty.
"""
import logging
import unicodedata
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, render_template, request, session

from justdata.main.auth import (
    get_access_row,
    get_current_user,
    get_user_type,
    is_privileged_user,
    login_required,
)
from justdata.main.auth.services.firebase_client import get_firestore_client, get_user_doc
from justdata.main.auth.session_revocation import revoke_all_sessions
from justdata.main.account import content
from justdata.main.account.history import report_history
from justdata.shared.web.registry import resolve_registry

logger = logging.getLogger(__name__)

account_bp = Blueprint("account", __name__)

NAME_MAX = 80
# Shown once the Entra app registration exists (spec 08, step 5).
MICROSOFT_LINK_READY = False


def clean_display_name(raw):
    """(name, error). Collapses whitespace; refuses empty, too long, or any
    control or format character. The name is escaped wherever it is shown."""
    if not isinstance(raw, str):
        return None, "Enter a name."
    name = " ".join(raw.split())
    if not name:
        return None, "Enter a name."
    if len(name) > NAME_MAX:
        return None, f"Use {NAME_MAX} characters or fewer."
    if any(unicodedata.category(ch).startswith("C") for ch in name):
        return None, "Use letters, numbers and ordinary punctuation."
    return name, None


def _auth_record(uid):
    """Firebase Auth user record, or None."""
    try:
        from firebase_admin import auth as firebase_auth
        return firebase_auth.get_user(uid)
    except Exception as e:
        logger.info("Account page: no Firebase record for the user (%s)", type(e).__name__)
        return None


def _route_exists(path):
    return any(rule.rule == path for rule in current_app.url_map.iter_rules())


def _agreements(user_doc):
    """Section 6. Reads users/{uid}.agreements_accepted, the field reserved in
    spec 08: {"tester_agreement": {"acceptedAt": <timestamp>}}. Nothing writes it
    yet, so today the section renders nothing."""
    accepted = (user_doc.get("agreements_accepted") or {}) if isinstance(user_doc, dict) else {}
    tester = accepted.get("tester_agreement") if isinstance(accepted, dict) else None
    tester_date = content.ap_date(tester.get("acceptedAt")) if isinstance(tester, dict) else None
    links = [(label, path) for label, path in (("Privacy notice", "/privacy"), ("Terms of use", "/terms"))
             if _route_exists(path)]
    if not tester_date and not links:
        return None
    return {"tester_date": tester_date, "links": links}


@account_bp.route("/account")
@login_required
def account_page():
    user = get_current_user() or {}
    uid = user.get("uid")
    user_type = get_user_type()
    user_doc = get_user_doc(uid) or {}
    record = _auth_record(uid) if uid else None

    groups = resolve_registry(get_access_row, user_type, is_staff=is_privileged_user(user_type))
    apps = content.open_apps(groups)
    openable = {item["key"] for g in groups for item in g["items"] if item["state"] == "available"}

    display_name = (getattr(record, "display_name", None) or user_doc.get("displayName")
                    or user.get("name") or "")
    email_verified = getattr(record, "email_verified", None)
    if email_verified is None:
        email_verified = bool(user.get("email_verified"))
    providers = [p.provider_id for p in (getattr(record, "provider_data", None) or [])]

    tester_access = user_doc.get("testerAccess") or {}
    confirmed = content.ap_date(tester_access.get("checkedAt")) if tester_access.get("authorized") else None

    sections = [("profile", "Profile"), ("access", "Access"), ("security", "Sign-in and security"),
                ("reports", "Your reports"), ("data", "Your data")]
    agreements = _agreements(user_doc)
    if agreements:
        sections.append(("agreements", "Agreements"))

    return render_template(
        "account.html",
        app_name="Your account",
        sections=sections,
        display_name=display_name,
        email=user.get("email") or getattr(record, "email", "") or "",
        organization=user_doc.get("hubspot_company_name"),
        email_verified=email_verified,
        role_title=content.role_title(user_type),
        role_sentence=content.role_sentence(user_type, apps),
        has_apps=bool(apps),
        access_confirmed=confirmed,
        is_admin=(user_type == "admin"),
        providers=content.provider_names(providers),
        has_password=("password" in providers),
        microsoft_link=MICROSOFT_LINK_READY and is_privileged_user(user_type)
        and "microsoft.com" not in providers,
        reports=report_history(uid, openable),
        recorded=content.RECORDED,
        not_recorded=content.NOT_RECORDED,
        agreements=agreements,
        name_max=NAME_MAX,
    )


@account_bp.route("/api/account/profile", methods=["POST"])
@login_required
def update_profile():
    user = get_current_user() or {}
    uid = user.get("uid")
    data = request.get_json(silent=True) or {}
    name, error = clean_display_name(data.get("display_name"))
    if error:
        return jsonify({"success": False, "error": error}), 400
    try:
        from firebase_admin import auth as firebase_auth
        firebase_auth.update_user(uid, display_name=name)
        db = get_firestore_client()
        if db is not None:
            db.collection("users").document(uid).set(
                {"displayName": name, "updatedAt": datetime.now(timezone.utc)}, merge=True)
    except Exception as e:
        logger.warning("Account page: name not saved (%s)", type(e).__name__)
        return jsonify({"success": False, "error": "We couldn't save your name. Try again."}), 502
    if "firebase_user" in session:
        session_user = dict(session["firebase_user"])
        session_user["name"] = name
        session["firebase_user"] = session_user
    return jsonify({"success": True, "display_name": name})


@account_bp.route("/api/account/sign-out-everywhere", methods=["POST"])
@login_required
def sign_out_everywhere():
    from justdata.main.auth import clear_session_user

    uid = (get_current_user() or {}).get("uid")
    try:
        revoke_all_sessions(uid)
    except Exception as e:
        logger.warning("Account page: sign out everywhere failed (%s)", type(e).__name__)
        return jsonify({"success": False, "error": "We couldn't sign you out everywhere. Try again."}), 502
    clear_session_user()
    return jsonify({"success": True, "redirect": "/"})
