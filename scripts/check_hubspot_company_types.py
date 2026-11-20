"""Compare HubSpot's live company_type options with the JustData config.

Prints options HubSpot has that the config lacks, and the reverse. Exits 1 if
they differ. Read-only. Needs HUBSPOT_ACCESS_TOKEN in the environment.

    python scripts/check_hubspot_company_types.py
"""
import os
import sys

import requests

from justdata.main.auth.services.organization import ORG_TYPE_BY_COMPANY_TYPE

URL = "https://api.hubapi.com/crm/v3/properties/companies/company_type"


def main() -> int:
    token = os.getenv("HUBSPOT_ACCESS_TOKEN")
    if not token:
        print("HUBSPOT_ACCESS_TOKEN is not set")
        return 2
    resp = requests.get(URL, headers={"Authorization": f"Bearer {token}"}, timeout=20)
    resp.raise_for_status()
    live = {o["label"] for o in resp.json().get("options", []) if not o.get("hidden")}
    config = set(ORG_TYPE_BY_COMPANY_TYPE)
    missing, extra = sorted(live - config), sorted(config - live)
    print(f"HubSpot options: {len(live)}; in config: {len(config)}")
    for name in missing:
        print(f"  not in config: {name}")
    for name in extra:
        print(f"  not in HubSpot: {name}")
    return 1 if missing or extra else 0


if __name__ == "__main__":
    sys.exit(main())
