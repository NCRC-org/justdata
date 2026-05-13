"""DotLender blueprint — HMDA dot-density lending map with PDF canvas export."""
import os

from flask import Blueprint, jsonify, render_template, request
from google.cloud.bigquery import ArrayQueryParameter, ScalarQueryParameter

from justdata.apps.dotlender.data.filters import (
    build_loan_scope_predicates,
    validate_filters,
    validate_geography,
)
from justdata.apps.dotlender.data.queries import (
    cbsa_search,
    get_cbsa_counties,
    get_choropleth_data,
    get_loan_dots,
    get_max_year,
    get_state_counties,
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


def _build_geography_from_dict(geo: dict):
    """Build (predicate_sql, [QueryParameter, ...]) from a validated geo dict.

    geo is the output of filters.validate_geography(). The predicate uses
    unqualified `geoid5` because two of the three SQL templates don't alias
    the de_hmda table. BigQuery resolves the ref to the only table in scope
    that has the column.

    Multi-county uses an ArrayQueryParameter with UNNEST.
    """
    geoid5_list = geo.get("geoid5_list") or []
    # State-type with no explicit list: fall back to state_fips prefix match.
    if not geoid5_list and geo.get("state_fips"):
        return (
            "LEFT(geoid5, 2) = @state_fips",
            [ScalarQueryParameter("state_fips", "STRING", geo["state_fips"])],
        )
    if len(geoid5_list) == 1:
        return (
            "geoid5 = @geoid5_0",
            [ScalarQueryParameter("geoid5_0", "STRING", geoid5_list[0])],
        )
    return (
        "geoid5 IN UNNEST(@geoid5_list)",
        [ArrayQueryParameter("geoid5_list", "STRING", geoid5_list)],
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


@dotlender_bp.route("/api/cbsa-search")
@staff_required
def api_cbsa_search():
    """Typeahead for metropolitan CBSAs. GET ?q=<term>"""
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    return jsonify(cbsa_search(q))


@dotlender_bp.route("/api/cbsa-counties/<cbsa_code>")
@staff_required
def api_cbsa_counties(cbsa_code):
    """List of counties (geoid5 + label) for a 5-digit CBSA code."""
    if not cbsa_code.isdigit() or len(cbsa_code) != 5:
        return jsonify({"error": "invalid cbsa_code"}), 400
    return jsonify(get_cbsa_counties(cbsa_code))


@dotlender_bp.route("/api/state-counties/<state_fips>")
@staff_required
def api_state_counties(state_fips):
    """List of counties (geoid5 + label) for a 2-digit state FIPS."""
    if not state_fips.isdigit() or len(state_fips) != 2:
        return jsonify({"error": "invalid state_fips"}), 400
    return jsonify(get_state_counties(state_fips))


def _prep_request(body):
    """Common geography/filter/year/lei prep for the two POST endpoints.

    Returns (geo_predicate, geo_params, filters, year_start, year_end, lei,
    geo_dict) on success. Returns (None, error_response) on validation
    failure.
    """
    try:
        geo = validate_geography(body)
    except ValueError as e:
        return None, (jsonify({"error": "invalid geography", "detail": str(e)}), 400)
    try:
        filters = validate_filters(body.get("filters") or {})
    except ValueError as e:
        return None, (jsonify({"error": "invalid filters", "detail": str(e)}), 400)
    max_year = get_max_year()
    try:
        year_start, year_end = _resolve_year_range(body, max_year)
    except (ValueError, TypeError) as e:
        return None, (jsonify({"error": "invalid year range", "detail": str(e)}), 400)
    lei = body.get("lei") or None
    if lei is not None:
        lei = str(lei).strip() or None
    geo_predicate, geo_params = _build_geography_from_dict(geo)
    return (geo_predicate, geo_params, filters, year_start, year_end, lei, geo), None


@dotlender_bp.route("/api/map-data", methods=["POST"])
@staff_required
def api_map_data():
    """Choropleth + dot-density payload for a geography/filter combination.

    POST JSON body (new contract):
      {
        "geo_type": "metro" | "state",
        "geoid5_list": ["11001", ...],
        "cbsa_code": "47900" (optional),
        "state_fips": "11" (optional, used when geoid5_list is empty),
        "year_start": int (optional),
        "year_end": int (optional),
        "lei": "<lei string>" (optional),
        "filters": { <loan scope filter fields> }
      }
    Legacy {geography_type, geography_value} shape is still accepted.
    """
    body = request.get_json(silent=True) or {}
    prep, err = _prep_request(body)
    if err:
        return err
    geo_predicate, geo_params, filters, year_start, year_end, lei, geo = prep

    loan_scope = build_loan_scope_predicates(filters)
    choropleth = get_choropleth_data(
        geo_predicate, geo_params, year_start, year_end, loan_scope
    )
    dots = get_loan_dots(
        geo_predicate, geo_params, year_start, year_end, loan_scope, lei=lei
    )
    return jsonify(
        {
            "geo_type": geo["geo_type"],
            "geoid5_list": geo["geoid5_list"],
            "cbsa_code": geo["cbsa_code"],
            "state_fips": geo["state_fips"],
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
    prep, err = _prep_request(body)
    if err:
        return err
    geo_predicate, geo_params, filters, year_start, year_end, lei, _geo = prep

    loan_scope = build_loan_scope_predicates(filters)
    stats = get_summary_stats(
        geo_predicate, geo_params, year_start, year_end, loan_scope, lei=lei
    )
    return jsonify(stats)
