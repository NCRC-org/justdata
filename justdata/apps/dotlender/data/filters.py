"""Validate and normalize DotLender filter parameters.

All values that flow into SQL are validated against explicit allowlists here.
No user input reaches a SQL template without passing through this module.

The validator returns a clean dict; build_loan_scope_predicates() turns that
dict into a list of WHERE clause fragments (without an AND prefix) that the
caller joins with AND.

Schema note: `lien_status` is currently NOT a column on
`justdata-ncrc.dataexplorer.de_hmda` (the recent build-SQL commit adding it
has not been rebuilt into the deployed table). The validator still accepts
lien_status so the API contract is stable, but the predicate builder emits
no clause for it. Remove the TODO once de_hmda is rebuilt with lien_status.
"""

VALID_GEO_TYPES = {"metro", "state"}


def validate_geography(params: dict) -> dict:
    """Validate the new multi-county geography contract.

    Accepts either of two body shapes:

      {"geo_type": "metro" | "state",
       "geoid5_list": ["11001", "24031", ...],
       "cbsa_code": "47900" | null,
       "state_fips": "11" | null}

    Or the legacy shape (for backward compatibility with callers that
    haven't been updated yet):

      {"geography_type": "county" | "state",
       "geography_value": "11001"}

    Returns a dict with normalized fields:
      {"geo_type": "metro" | "state",
       "geoid5_list": [str, ...],
       "cbsa_code": str | None,
       "state_fips": str | None}
    """
    if not isinstance(params, dict):
        raise ValueError("geography must be a JSON object")

    # Legacy shape passthrough
    legacy_type = params.get("geography_type")
    legacy_value = params.get("geography_value")
    if legacy_type and not params.get("geoid5_list"):
        value = str(legacy_value or "").strip()
        if not value.isdigit():
            raise ValueError("geography_value must be a digit string")
        if legacy_type == "county":
            if len(value) != 5:
                raise ValueError("county geography_value must be 5-digit FIPS")
            return {
                "geo_type": "metro",  # treat single county as a one-element list
                "geoid5_list": [value],
                "cbsa_code": None,
                "state_fips": value[:2],
            }
        if legacy_type == "state":
            if len(value) != 2:
                raise ValueError("state geography_value must be 2-digit FIPS")
            return {
                "geo_type": "state",
                "geoid5_list": [],
                "cbsa_code": None,
                "state_fips": value,
            }
        raise ValueError(
            f"unsupported geography_type: {legacy_type!r} (allowed: ['county', 'state'])"
        )

    # New shape
    geo_type = params.get("geo_type")
    if geo_type not in VALID_GEO_TYPES:
        raise ValueError(
            f"geo_type must be one of {sorted(VALID_GEO_TYPES)}, got {geo_type!r}"
        )
    raw_list = params.get("geoid5_list") or []
    if not isinstance(raw_list, list):
        raise ValueError("geoid5_list must be a JSON array")
    geoid5_list = []
    for v in raw_list:
        s = str(v or "").strip()
        if not s.isdigit() or len(s) != 5:
            raise ValueError(f"each geoid5 must be a 5-digit numeric string, got {v!r}")
        geoid5_list.append(s)
    if not geoid5_list:
        raise ValueError("geoid5_list must contain at least one county")

    cbsa_code = params.get("cbsa_code")
    if cbsa_code is not None:
        cbsa_code = str(cbsa_code).strip()
        if not cbsa_code.isdigit() or len(cbsa_code) != 5:
            raise ValueError("cbsa_code must be 5-digit numeric")

    state_fips = params.get("state_fips")
    if state_fips is not None:
        state_fips = str(state_fips).strip()
        if not state_fips.isdigit() or len(state_fips) != 2:
            raise ValueError("state_fips must be 2-digit numeric")

    return {
        "geo_type": geo_type,
        "geoid5_list": geoid5_list,
        "cbsa_code": cbsa_code,
        "state_fips": state_fips,
    }


VALID_LOAN_PURPOSE = {"1", "2", "3", "4", "5", "31", "32", "all"}
VALID_LIEN_STATUS = {"1", "2", "all"}
VALID_OCCUPANCY_TYPE = {"1", "2", "3", "all"}
VALID_CONSTRUCTION_METHOD = {"1", "2", "all"}
VALID_TOTAL_UNITS = {"1", "2", "3", "4", "1234", "5plus", "all"}
VALID_ACTION_TAKEN = {"1", "2", "3", "4", "5", "6", "7", "8", "all"}
VALID_REVERSE_MORTGAGE = {"exclude", "include"}
VALID_LOAN_TYPE = {"1", "2", "3", "4", "all"}

DEFAULTS = {
    "loan_purpose": "1",
    "lien_status": "1",
    "occupancy_type": "1",
    "construction_method": "1",
    "total_units": "1234",
    "action_taken": "1",
    "reverse_mortgage": "exclude",
    "loan_type": "all",
}

_ALLOWLISTS = {
    "loan_purpose": VALID_LOAN_PURPOSE,
    "lien_status": VALID_LIEN_STATUS,
    "occupancy_type": VALID_OCCUPANCY_TYPE,
    "construction_method": VALID_CONSTRUCTION_METHOD,
    "total_units": VALID_TOTAL_UNITS,
    "action_taken": VALID_ACTION_TAKEN,
    "reverse_mortgage": VALID_REVERSE_MORTGAGE,
    "loan_type": VALID_LOAN_TYPE,
}


def validate_filters(params: dict) -> dict:
    """Validate and normalize filter parameters from a request.

    Returns a dict containing exactly the keys in DEFAULTS, each carrying
    a value drawn from its allowlist. Raises ValueError on invalid input.
    """
    if not isinstance(params, dict):
        raise ValueError("filters must be a JSON object")
    out = {}
    for key, default in DEFAULTS.items():
        raw = params.get(key, default)
        value = str(raw) if raw is not None else default
        allowed = _ALLOWLISTS[key]
        if value not in allowed:
            raise ValueError(
                f"invalid value for {key}: {value!r} (allowed: {sorted(allowed)})"
            )
        out[key] = value
    return out


def build_loan_scope_predicates(filters: dict) -> list:
    """Convert a validated filter dict into a list of SQL predicate fragments.

    Each fragment is a standalone WHERE clause (no AND prefix). Callers join
    them with AND. 'all' values are omitted entirely so no redundant clause
    is added.
    """
    predicates = []

    if filters["reverse_mortgage"] == "exclude":
        predicates.append("reverse_mortgage != '1'")

    # TODO(lien_status): de_hmda does not yet carry lien_status. Re-enable
    # once the table is rebuilt with the column added in commit 6f47b64.
    # if filters["lien_status"] != "all":
    #     predicates.append(f"lien_status = '{filters['lien_status']}'")

    if filters["loan_purpose"] != "all":
        predicates.append(f"loan_purpose = '{filters['loan_purpose']}'")

    if filters["occupancy_type"] != "all":
        predicates.append(f"occupancy_type = '{filters['occupancy_type']}'")

    if filters["construction_method"] != "all":
        predicates.append(f"construction_method = '{filters['construction_method']}'")

    if filters["loan_type"] != "all":
        predicates.append(f"loan_type = '{filters['loan_type']}'")

    if filters["action_taken"] != "all":
        predicates.append(f"action_taken = '{filters['action_taken']}'")

    tu = filters["total_units"]
    if tu == "1234":
        predicates.append("total_units IN ('1','2','3','4')")
    elif tu == "5plus":
        # total_units is stored as STRING in de_hmda; SAFE_CAST handles
        # non-numeric values like '5-24' which need a different branch.
        predicates.append(
            "(SAFE_CAST(total_units AS INT64) >= 5 "
            "OR total_units IN ('5-24','25-49','50-99','100-149','150-249','250-499','500-1000','>1000'))"
        )
    elif tu != "all":
        predicates.append(f"total_units = '{tu}'")

    return predicates
