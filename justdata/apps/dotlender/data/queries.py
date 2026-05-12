"""BigQuery query functions for DotLender.

All functions return plain Python types (dicts, lists, ints) — no BigQuery
row objects leak out. SQL templates load from sql_templates/ and are
parameterized via @param placeholders + ScalarQueryParameter; only the
geography type, loan-scope predicates, and LEI inclusion are stitched in
as Python strings, and those values come from allowlists or strict
numeric-string validation in the caller (blueprint.py and filters.py).
"""
from typing import List, Optional

from google.cloud.bigquery import ScalarQueryParameter

from justdata.apps.dotlender.sql_loader import load_sql
from justdata.shared.utils.bigquery_client import get_bigquery_client, run_query


TABLE = "justdata-ncrc.dataexplorer.de_hmda"
APP_NAME = "dotlender"

# Per-tract-per-race dot cap when no housing-units denominator is available.
# de_hmda lacks tract_one_to_four_family_homes; until an ACS housing table
# is wired in, dot count = min(loan_count, MAX_DOTS_PER_TRACT_RACE).
MAX_DOTS_PER_TRACT_RACE = 50

# NCRC standard race/ethnicity hierarchy. Hispanic ethnicity takes precedence
# over any race selection; multi-racial falls between AI/AN and White.
# Defined as a single string so loan_dots.sql can interpolate it via
# .format(derived_race_expr=DERIVED_RACE_SQL).
DERIVED_RACE_SQL = (
    "CASE "
    "WHEN is_hispanic THEN 'Hispanic or Latino' "
    "WHEN is_black THEN 'Black or African American' "
    "WHEN is_asian THEN 'Asian' "
    "WHEN is_native_american OR is_hopi THEN 'American Indian or Alaska Native' "
    "WHEN is_multi_racial THEN 'Two or More Races' "
    "WHEN is_white THEN 'White' "
    "ELSE 'Unknown or Not Provided' "
    "END"
)


def _client():
    return get_bigquery_client(project_id="justdata-ncrc", app_name=APP_NAME)


def _format_predicates(predicates: List[str]) -> str:
    """Join loan-scope predicates with AND, or 'TRUE' when empty."""
    return " AND ".join(predicates) if predicates else "TRUE"


def get_max_year() -> int:
    """Return the most recent activity_year currently loaded in de_hmda."""
    sql = load_sql("max_year.sql").format(table=TABLE)
    rows = run_query(_client(), sql)
    if not rows or rows[0].get("max_year") is None:
        return 0
    return int(rows[0]["max_year"])


def lender_search(search_term: str, year_start: int, year_end: int) -> List[dict]:
    """Typeahead lender search.

    Returns a list of {lei, respondent_name, loan_count} dicts, ranked by
    origination count. Returns [] for terms shorter than 2 chars.
    """
    term = (search_term or "").strip()
    if len(term) < 2:
        return []
    sql = load_sql("lender_lookup.sql").format(table=TABLE)
    params = [
        ScalarQueryParameter("search_term", "STRING", f"%{term}%"),
        ScalarQueryParameter("year_start", "INT64", int(year_start)),
        ScalarQueryParameter("year_end", "INT64", int(year_end)),
    ]
    rows = run_query(_client(), sql, params=params)
    return [
        {
            "lei": r.get("lei"),
            "respondent_name": r.get("respondent_name"),
            "loan_count": int(r.get("loan_count") or 0),
        }
        for r in rows
    ]


def _income_band(tract_income_pct) -> str:
    if tract_income_pct is None:
        return "unknown"
    pct = float(tract_income_pct)
    if pct < 50:
        return "low"
    if pct < 80:
        return "moderate"
    if pct < 120:
        return "middle"
    return "upper"


def get_choropleth_data(
    geography_predicate: str,
    geography_params: List[ScalarQueryParameter],
    year_start: int,
    year_end: int,
    loan_scope_predicates: List[str],
) -> List[dict]:
    """Tract-level choropleth payload.

    Each returned dict has census_tract, minority_pct, tract_income_pct,
    income_band, msa_median_income, loan_count, housing_units.
    income_band is derived in Python from tract_income_pct.
    """
    sql = load_sql("tract_choropleth.sql").format(
        table=TABLE,
        geography_predicate=geography_predicate,
        loan_scope_predicates=_format_predicates(loan_scope_predicates),
    )
    params = list(geography_params) + [
        ScalarQueryParameter("year_start", "INT64", int(year_start)),
        ScalarQueryParameter("year_end", "INT64", int(year_end)),
    ]
    rows = run_query(_client(), sql, params=params)
    return [
        {
            "census_tract": r.get("census_tract"),
            "minority_pct": (
                float(r["minority_pct"]) if r.get("minority_pct") is not None else None
            ),
            "tract_income_pct": (
                float(r["tract_income_pct"])
                if r.get("tract_income_pct") is not None
                else None
            ),
            "income_band": _income_band(r.get("tract_income_pct")),
            "msa_median_income": (
                int(r["msa_median_income"])
                if r.get("msa_median_income") is not None
                else None
            ),
            "loan_count": int(r.get("loan_count") or 0),
            "housing_units": (
                int(r["housing_units"]) if r.get("housing_units") is not None else None
            ),
        }
        for r in rows
    ]


def _dot_count(loan_count: int, housing_units) -> int:
    """Compute dot count for one (tract, race) cell.

    No per-tract minimum floor: voids in lending should be visible as empty
    areas on the map. The client-side density stride may further reduce
    counts (a 2-dot tract at stride=5 emits 0 dots client-side).

    With no housing-units denominator available (de_hmda lacks
    tract_one_to_four_family_homes), the fallback caps at
    MAX_DOTS_PER_TRACT_RACE. Once a housing-units source is wired in, the
    proportional path will activate.
    """
    if loan_count <= 0:
        return 0
    if housing_units in (None, 0):
        return min(loan_count, MAX_DOTS_PER_TRACT_RACE)
    # Future path (currently unreachable because the query returns NULL
    # for housing_units): proportional scaling capped at the per-cell max.
    SCALE_FACTOR = 20
    raw = int(round(loan_count / float(housing_units) * SCALE_FACTOR))
    return min(raw, MAX_DOTS_PER_TRACT_RACE) if raw > 0 else 0


def get_loan_dots(
    geography_predicate: str,
    geography_params: List[ScalarQueryParameter],
    year_start: int,
    year_end: int,
    loan_scope_predicates: List[str],
    lei: Optional[str] = None,
) -> List[dict]:
    """Tract+race dot-density payload.

    Each returned dict has census_tract, derived_race, dot_count.
    dot_count is computed in Python (see _dot_count).
    """
    if lei:
        lei_predicate = "AND lei = @lei"
    else:
        lei_predicate = ""
    sql = load_sql("loan_dots.sql").format(
        table=TABLE,
        derived_race_expr=DERIVED_RACE_SQL,
        geography_predicate=geography_predicate,
        loan_scope_predicates=_format_predicates(loan_scope_predicates),
        lei_predicate=lei_predicate,
    )
    params = list(geography_params) + [
        ScalarQueryParameter("year_start", "INT64", int(year_start)),
        ScalarQueryParameter("year_end", "INT64", int(year_end)),
    ]
    if lei:
        params.append(ScalarQueryParameter("lei", "STRING", lei))
    rows = run_query(_client(), sql, params=params)
    return [
        {
            "census_tract": r.get("census_tract"),
            "derived_race": r.get("derived_race"),
            "dot_count": _dot_count(
                int(r.get("loan_count") or 0), r.get("housing_units")
            ),
            "centroid_lat": (
                float(r["centroid_lat"]) if r.get("centroid_lat") is not None else None
            ),
            "centroid_lng": (
                float(r["centroid_lng"]) if r.get("centroid_lng") is not None else None
            ),
        }
        for r in rows
    ]


def get_summary_stats(
    geography_predicate: str,
    geography_params: List[ScalarQueryParameter],
    year_start: int,
    year_end: int,
    loan_scope_predicates: List[str],
    lei: Optional[str] = None,
) -> dict:
    """Top-line summary stats dict.

    Keys: total_loans, tracts_with_lending, lender_count,
    loans_in_lmi_tracts, loans_in_majority_minority_tracts,
    pct_lmi_tracts, pct_majority_minority_tracts, total_loan_amount.
    """
    if lei:
        lei_predicate = "AND lei = @lei"
    else:
        lei_predicate = ""
    sql = load_sql("summary_stats.sql").format(
        table=TABLE,
        geography_predicate=geography_predicate,
        loan_scope_predicates=_format_predicates(loan_scope_predicates),
        lei_predicate=lei_predicate,
    )
    params = list(geography_params) + [
        ScalarQueryParameter("year_start", "INT64", int(year_start)),
        ScalarQueryParameter("year_end", "INT64", int(year_end)),
    ]
    if lei:
        params.append(ScalarQueryParameter("lei", "STRING", lei))
    rows = run_query(_client(), sql, params=params)
    if not rows:
        return {
            "total_loans": 0,
            "tracts_with_lending": 0,
            "lender_count": 0,
            "loans_in_lmi_tracts": 0,
            "loans_in_majority_minority_tracts": 0,
            "pct_lmi_tracts": 0.0,
            "pct_majority_minority_tracts": 0.0,
            "total_loan_amount": 0,
        }
    r = rows[0]
    total = int(r.get("total_loans") or 0)
    lmi = int(r.get("loans_in_lmi_tracts") or 0)
    mm = int(r.get("loans_in_majority_minority_tracts") or 0)
    return {
        "total_loans": total,
        "tracts_with_lending": int(r.get("tracts_with_lending") or 0),
        "lender_count": int(r.get("lender_count") or 0),
        "loans_in_lmi_tracts": lmi,
        "loans_in_majority_minority_tracts": mm,
        "pct_lmi_tracts": (lmi / total * 100) if total else 0.0,
        "pct_majority_minority_tracts": (mm / total * 100) if total else 0.0,
        "total_loan_amount": int(r.get("total_loan_amount") or 0),
    }
