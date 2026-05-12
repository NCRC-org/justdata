"""DotLender blueprint — HMDA dot-density lending map with PDF canvas export."""
import os

from flask import Blueprint, jsonify, render_template, request
from google.cloud.bigquery import ScalarQueryParameter

from justdata.apps.dotlender.data.filters import (
    build_loan_scope_predicates,
    validate_filters,
)
from justdata.apps.dotlender.data.queries import (
    get_choropleth_data,
    get_loan_dots,
    get_max_year,
    get_summary_stats,
    lender_search,
)
from justdata.main.auth import staff_required


dotlender_bp = Blueprint(
    "dotlender",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/dotlender/static",
)


# --- Pages -----------------------------------------------------------------


@dotlender_bp.route("/")
@staff_required
def index():
    """Filter page — DotLender main view."""
    mapbox_token = os.environ.get("MAPBOX_ACCESS_TOKEN", "")
    return render_template(
        "dotlender_main.html",
        app_name="DotLender",
        app_description="HMDA dot-density lending map by race/ethnicity and tract demographics.",
        mapbox_token=mapbox_token,
    )


@dotlender_bp.route("/health")
def health():
    """Smoke test target — no auth required."""
    return {"status": "ok", "app": "dotlender"}


# --- API helpers -----------------------------------------------------------

_VALID_GEOGRAPHY_TYPES = {"county", "state"}  # MSA pending — see TODO below


def _build_geography(geography_type: str, geography_value: str):
    """Return (predicate_sql, [ScalarQueryParameter, ...]) for a geography.

    Validates that geography_value is a digit-only string of the expected
    length, then emits a parameterized predicate against geoid5. MSA is
    not supported in v1 (de_hmda has no msa_md column).

    TODO(msa): Once an MSA join is wired in (shared.census.msamd on
    census_tract), add a 'msa' branch here.
    """
    if geography_type not in _VALID_GEOGRAPHY_TYPES:
        raise ValueError(
            f"unsupported geography_type: {geography_type!r} "
            f"(allowed: {sorted(_VALID_GEOGRAPHY_TYPES)})"
        )
    value = str(geography_value or "").strip()
    if not value.isdigit():
        raise ValueError("geography_value must be a digit string")

    if geography_type == "county":
        if len(value) != 5:
            raise ValueError("county geography_value must be 5-digit FIPS")
        return (
            "geoid5 = @county_fips",
            [ScalarQueryParameter("county_fips", "STRING", value)],
        )
    # state
    if len(value) != 2:
        raise ValueError("state geography_value must be 2-digit FIPS")
    return (
        "LEFT(geoid5, 2) = @state_fips",
        [ScalarQueryParameter("state_fips", "STRING", value)],
    )


def _resolve_year_range(body: dict, max_year: int) -> tuple:
    """Default year range is the last 3 years ending at max_year."""
    year_end = int(body.get("year_end") or max_year)
    year_start = int(body.get("year_start") or max(max_year - 2, 0))
    if year_start > year_end:
        raise ValueError("year_start must be <= year_end")
    return year_start, year_end


# --- API routes ------------------------------------------------------------


@dotlender_bp.route("/api/max-year")
@staff_required
def api_max_year():
    """Return the current max activity_year in de_hmda."""
    return jsonify({"max_year": get_max_year()})


@dotlender_bp.route("/api/lender-search")
@staff_required
def api_lender_search():
    """Typeahead endpoint. GET ?q=<term>&year_start=<int>&year_end=<int>"""
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    max_year = get_max_year()
    year_start = int(request.args.get("year_start") or max(max_year - 2, 0))
    year_end = int(request.args.get("year_end") or max_year)
    results = lender_search(q, year_start, year_end)
    return jsonify(results)


@dotlender_bp.route("/api/map-data", methods=["POST"])
@staff_required
def api_map_data():
    """Choropleth + dot-density payload for a geography/filter combination.

    POST JSON body:
      {
        "geography_type": "county" | "state",
        "geography_value": "<digit FIPS>",
        "year_start": int (optional),
        "year_end": int (optional),
        "lei": "<lei string>" (optional),
        "filters": { <loan scope filter fields> }
      }
    """
    body = request.get_json(silent=True) or {}
    try:
        geo_predicate, geo_params = _build_geography(
            body.get("geography_type"), body.get("geography_value")
        )
    except ValueError as e:
        return jsonify({"error": "invalid geography", "detail": str(e)}), 400

    try:
        filters = validate_filters(body.get("filters") or {})
    except ValueError as e:
        return jsonify({"error": "invalid filters", "detail": str(e)}), 400

    max_year = get_max_year()
    try:
        year_start, year_end = _resolve_year_range(body, max_year)
    except (ValueError, TypeError) as e:
        return jsonify({"error": "invalid year range", "detail": str(e)}), 400

    lei = body.get("lei") or None
    if lei is not None:
        lei = str(lei).strip() or None

    loan_scope = build_loan_scope_predicates(filters)
    choropleth = get_choropleth_data(
        geo_predicate, geo_params, year_start, year_end, loan_scope
    )
    dots = get_loan_dots(
        geo_predicate, geo_params, year_start, year_end, loan_scope, lei=lei
    )
    return jsonify(
        {
            "geography_type": body.get("geography_type"),
            "geography_value": body.get("geography_value"),
            "year_start": year_start,
            "year_end": year_end,
            "lei": lei,
            "filters": filters,
            "choropleth": choropleth,
            "dots": dots,
        }
    )


@dotlender_bp.route("/api/summary-stats", methods=["POST"])
@staff_required
def api_summary_stats():
    """Same POST body as /api/map-data. Returns summary statistics dict."""
    body = request.get_json(silent=True) or {}
    try:
        geo_predicate, geo_params = _build_geography(
            body.get("geography_type"), body.get("geography_value")
        )
    except ValueError as e:
        return jsonify({"error": "invalid geography", "detail": str(e)}), 400

    try:
        filters = validate_filters(body.get("filters") or {})
    except ValueError as e:
        return jsonify({"error": "invalid filters", "detail": str(e)}), 400

    max_year = get_max_year()
    try:
        year_start, year_end = _resolve_year_range(body, max_year)
    except (ValueError, TypeError) as e:
        return jsonify({"error": "invalid year range", "detail": str(e)}), 400

    lei = body.get("lei") or None
    if lei is not None:
        lei = str(lei).strip() or None

    loan_scope = build_loan_scope_predicates(filters)
    stats = get_summary_stats(
        geo_predicate, geo_params, year_start, year_end, loan_scope, lei=lei
    )
    return jsonify(stats)
