"""
Membership business logic placeholder.

Membership-related routes live in justdata.main.auth.routes.organizations:
- /set-organization
- /membership-status
- /member-request/status
- /member-request/dismiss-prompt

The corresponding business logic is currently inside those route handlers.
This module exists as the destination for future extraction of standalone
membership helpers (e.g. is_member, evaluate_membership_status, build_member_request).

External membership data lookups against HubSpot live in
justdata.apps.hubspot.membership and are imported lazily inside the route
handlers to avoid circular imports.
"""
