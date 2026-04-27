"""Analytics BigQuery client package.

Public API matches the original bigquery_client.py module: functions are
re-exported here so callers (analytics/blueprint.py) can import them
from justdata.apps.analytics.bq directly. The implementation is split
across client.py / transforms.py / centroids.py / queries/.
"""
from justdata.apps.analytics.bq.client import (
    EVENTS_TABLE,
    LENDER_APPS,
    QUERY_PROJECT,
    TARGET_APPS,
    clear_analytics_cache,
    get_bigquery_client,
    get_valid_user_filter,
)
from justdata.apps.analytics.bq.centroids import (
    get_cbsa_centroids,
    get_county_centroids,
    lookup_cbsa_centroid,
    lookup_county_centroid,
    validate_coordinates,
)
from justdata.apps.analytics.bq.queries.admin import (
    force_full_sync,
    sync_new_events,
)
from justdata.apps.analytics.bq.queries.costs import get_cost_summary
from justdata.apps.analytics.bq.queries.lenders import (
    get_lender_detail,
    get_lender_interest,
)
from justdata.apps.analytics.bq.queries.orgs import (
    get_coalition_opportunities,
    get_summary,
)
from justdata.apps.analytics.bq.queries.usage import (
    get_research_activity,
    get_user_activity_timeline,
    get_user_locations,
)
from justdata.apps.analytics.bq.queries.users import (
    get_entity_users,
    get_user_activity,
    get_users,
)

__all__ = [
    # Client core
    "EVENTS_TABLE",
    "LENDER_APPS",
    "QUERY_PROJECT",
    "TARGET_APPS",
    "clear_analytics_cache",
    "get_bigquery_client",
    "get_valid_user_filter",
    # Centroids
    "get_cbsa_centroids",
    "get_county_centroids",
    "lookup_cbsa_centroid",
    "lookup_county_centroid",
    "validate_coordinates",
    # Admin / sync
    "force_full_sync",
    "sync_new_events",
    # Cost
    "get_cost_summary",
    # Lender queries
    "get_lender_detail",
    "get_lender_interest",
    # Org / coalition
    "get_coalition_opportunities",
    "get_summary",
    # Usage
    "get_research_activity",
    "get_user_activity_timeline",
    "get_user_locations",
    # User
    "get_entity_users",
    "get_user_activity",
    "get_users",
]
